"""Full-data training-budget control: 500 epochs, no early stopping.

Only changes the training budget relative to the formal holdingfix run.
Data/stats/split, architecture, loss, optimizer, batch and seed are fixed.
Test is never evaluated.  Saves last.pt and best_val.pt in an independent dir.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
STAGE5 = Path('/root/autodl-tmp/stage5-trial')
TRAIN = STAGE5 / 'training'
DEFAULT_DATA = STAGE5 / 'holdingfix-20261108' / 'data'
DEFAULT_OUT = (STAGE5 / 'holdingfix-20261108' / 'diagnostics'
               / 'budget500')
CHECKPOINTS = (100, 200, 300, 400, 500)
GROUPS = ('L1_grasp', 'L2_L3_recovery_grasp', 'L2_L3_fold_grasp')


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def subset_metrics(pred_xyz, pred_grip, target):
    err = np.asarray(pred_xyz, dtype=np.float64) - target[:, :3]
    euclid = np.linalg.norm(err, axis=1)
    return {
        'n': int(len(target)),
        'xyz_euclidean_mean_m': float(euclid.mean()),
        'xyz_euclidean_median_m': float(np.median(euclid)),
        'xyz_euclidean_p95_m': float(np.percentile(euclid, 95)),
        'gripper_accuracy': float(np.mean(pred_grip == target[:, 4])),
    }


def group_indices(arrays, train_idx):
    groups = {name: [] for name in GROUPS}
    for position, index in enumerate(train_idx):
        if int(arrays['action'][index, 4]) != 1:
            continue
        level = str(arrays['level'][index])
        phase = str(arrays['phase'][index])
        if level == 'flat' and phase == 'GRASP':
            groups['L1_grasp'].append(position)
        elif level in ('perturbed', 'crumpled') and phase == 'RECOVERY':
            groups['L2_L3_recovery_grasp'].append(position)
        elif level in ('perturbed', 'crumpled') and phase == 'GRASP':
            groups['L2_L3_fold_grasp'].append(position)
        else:
            raise SystemExit('Unclassified train CLOSE: %r %r %r'
                             % (level, phase, index))
    counts = {name: len(values) for name, values in groups.items()}
    if counts != {'L1_grasp': 31, 'L2_L3_recovery_grasp': 14,
                  'L2_L3_fold_grasp': 14}:
        raise SystemExit('Unexpected train CLOSE group counts: %r' % counts)
    return {name: np.asarray(values, dtype=int)
            for name, values in groups.items()}, counts


def evaluate_train(model, Xt, target, groups):
    model.eval()
    with torch.no_grad():
        pc, pg = model(Xt)
    pred = pc.cpu().numpy().astype(np.float64) * target['c_std'] + target['c_mean']
    pred_grip = pg.argmax(1).cpu().numpy()
    result = {
        'all_actions': subset_metrics(pred[:, :3], pred_grip, target['action']),
        'groups': {},
    }
    for name, positions in groups.items():
        result['groups'][name] = subset_metrics(
            pred[positions, :3], pred_grip[positions],
            target['action'][positions])
    return result


def val_loss(model, Xv, cv, gv):
    model.eval()
    with torch.no_grad():
        pc, pg = model(Xv)
        cont = float(((pc - cv) ** 2).mean())
        grip = float(F.cross_entropy(pg, gv))
    return cont, grip, cont + grip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--epochs', type=int, default=500)
    parser.add_argument('--batch', type=int, default=128)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--weight-decay', type=float, default=1e-4)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()

    if args.epochs != 500:
        raise SystemExit('This control is fixed at 500 epochs')
    for path in (str(TRAIN), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from train_bc import BCNet, obs_matrix

    data = np.load(args.data / 'dataset_single.npz', allow_pickle=True)
    arrays = {key: data[key] for key in data.files}
    stats = load_json(args.data / 'stats.json')
    if stats.get('holding_normalization') != 'identity':
        raise SystemExit('Expected identity holding normalization')
    if abs(float(stats['obs_mean'][1339])) > 1e-12 or abs(
            float(stats['obs_std'][1339]) - 1.0) > 1e-12:
        raise SystemExit('Invalid identity holding stats')

    X = obs_matrix(arrays)
    mean = np.asarray(stats['obs_mean'], np.float32)
    std = np.asarray(stats['obs_std'], np.float32)
    c_mean = np.asarray(stats['cont_mean'], dtype=np.float64)
    c_std = np.asarray(stats['cont_std'], dtype=np.float64)
    X = ((X - mean) / std).astype(np.float32)
    cont = (arrays['action'][:, :4].astype(np.float64) - c_mean) / c_std
    grip = arrays['action'][:, 4].astype(np.int64)
    split = arrays['split']
    train_idx = np.where(split == 'train')[0]
    val_idx = np.where(split == 'val')[0]
    # test is intentionally not indexed or evaluated.
    if len(train_idx) != 385 or len(val_idx) != 94:
        raise SystemExit('Unexpected split sizes: %d/%d'
                         % (len(train_idx), len(val_idx)))
    groups, group_counts = group_indices(arrays, train_idx)
    target = {'action': arrays['action'][train_idx].astype(np.float64),
              'c_mean': c_mean, 'c_std': c_std}

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = BCNet(1340, 512, 'single').to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr,
                            weight_decay=args.weight_decay)
    Xtr = torch.tensor(X[train_idx], device=dev)
    ctr = torch.tensor(cont[train_idx], device=dev)
    gtr = torch.tensor(grip[train_idx], device=dev)
    Xva = torch.tensor(X[val_idx], device=dev)
    cva = torch.tensor(cont[val_idx], device=dev)
    gva = torch.tensor(grip[val_idx], device=dev)

    best_val = float('inf')
    best_epoch = 0
    best_state = None
    last_state = None
    updates = 0
    curves = []
    checkpoint_metrics = {}
    for epoch in range(1, args.epochs + 1):
        model.train()
        perm = torch.randperm(len(Xtr), device=dev)
        total = 0.0
        for start in range(0, len(perm), args.batch):
            idx = perm[start:start + args.batch]
            pc, pg = model(Xtr[idx])
            lc = ((pc - ctr[idx]) ** 2).mean()
            lg = F.cross_entropy(pg, gtr[idx])
            loss = lc + lg
            opt.zero_grad()
            loss.backward()
            opt.step()
            updates += 1
            total += float(loss) * len(idx)
        train_total = total / len(Xtr)
        val_cont, val_grip, val_total = val_loss(model, Xva, cva, gva)
        record = {
            'epoch': epoch,
            'updates': updates,
            'train_total': train_total,
            'val_cont': val_cont,
            'val_grip': val_grip,
            'val_total': val_total,
        }
        curves.append(record)
        if val_total < best_val - 1e-12:
            best_val = val_total
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        if epoch in CHECKPOINTS:
            train_metrics = evaluate_train(model, Xtr, target, groups)
            checkpoint_metrics[str(epoch)] = {
                'epoch': epoch,
                'updates': updates,
                'train_total': train_total,
                'val_total': val_total,
                'train': train_metrics,
            }
        if epoch % 50 == 0 or epoch == 1:
            print('EPOCH %d updates=%d train=%.6f val=%.6f best=%.6f@%d'
                  % (epoch, updates, train_total, val_total, best_val,
                     best_epoch))
    last_state = copy.deepcopy(model.state_dict())

    args.out.mkdir(parents=True, exist_ok=True)
    checkpoint_meta = {
        'in_dim': 1340,
        'hidden': 512,
        'mode': 'single',
        'epochs': args.epochs,
        'batch': args.batch,
        'lr': args.lr,
        'weight_decay': args.weight_decay,
        'seed': args.seed,
        'dataset_sha256': sha(args.data / 'dataset_single.npz'),
        'stats_sha256': sha(args.data / 'stats.json'),
        'selected_by': 'minimum total validation loss',
        'test_evaluated': False,
    }
    torch.save({**checkpoint_meta, 'state': best_state,
                'epoch': best_epoch, 'val_total': best_val},
               args.out / 'best_val.pt')
    torch.save({**checkpoint_meta, 'state': last_state,
                'epoch': args.epochs, 'val_total': curves[-1]['val_total']},
               args.out / 'last.pt')

    def evaluate_state(state, epoch, val_total, train_total, updates_value):
        model.load_state_dict(state)
        model.eval()
        metrics = evaluate_train(model, Xtr, target, groups)
        vc, vg, vt = val_loss(model, Xva, cva, gva)
        return {
            'epoch': epoch,
            'updates': updates_value,
            'train_total': train_total,
            'val_total': vt,
            'val_cont': vc,
            'val_grip': vg,
            'train': metrics,
        }

    best_last_record = evaluate_state(
        best_state, best_epoch, best_val,
        curves[best_epoch - 1]['train_total'],
        curves[best_epoch - 1]['updates'])
    last_record = evaluate_state(
        last_state, args.epochs, curves[-1]['val_total'],
        curves[-1]['train_total'], updates)

    config = {
        'purpose': 'full-data training-budget control; not a formal release',
        'data': str(args.data / 'dataset_single.npz'),
        'stats': str(args.data / 'stats.json'),
        'dataset_sha256': sha(args.data / 'dataset_single.npz'),
        'stats_sha256': sha(args.data / 'stats.json'),
        'split': {'train': len(train_idx), 'val': len(val_idx)},
        'test_evaluated': False,
        'architecture': 'BCNet(1340, 512, single)',
        'loss': 'MSE(cont_norm) + CE(gripper)',
        'optimizer': 'AdamW',
        'epochs': args.epochs,
        'batch': args.batch,
        'lr': args.lr,
        'weight_decay': args.weight_decay,
        'seed': args.seed,
        'early_stop': False,
        'updates_expected': args.epochs * ((len(train_idx) + args.batch - 1)
                                           // args.batch),
        'updates_actual': updates,
        'group_counts': group_counts,
        'checkpoints': list(CHECKPOINTS),
    }
    report = {
        'config': config,
        'curves': curves,
        'checkpoint_metrics': checkpoint_metrics,
        'best_val': best_last_record,
        'last': last_record,
        'group_counts': group_counts,
        'test_evaluated': False,
    }
    (args.out / 'config.json').write_text(
        json.dumps(config, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    (args.out / 'curves.json').write_text(
        json.dumps(curves, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    (args.out / 'checkpoint_metrics.json').write_text(
        json.dumps(checkpoint_metrics, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    (args.out / 'best_val_metrics.json').write_text(
        json.dumps(best_last_record, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    (args.out / 'last_metrics.json').write_text(
        json.dumps(last_record, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    (args.out / 'report.json').write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')

    lines = ['# Full-data 500-epoch budget control', '',
             'Updates actual/expected: %d/%d; test evaluated: false' % (
                 updates, config['updates_expected']), '',
             '| epoch | updates | train loss | val loss | train all Euclid | '
             'L1 mean/P95/acc | recovery mean/P95/acc | fold mean/P95/acc |',
             '|---:|---:|---:|---:|---:|---|---|---|']
    for epoch in CHECKPOINTS:
        rec = checkpoint_metrics[str(epoch)]
        allm = rec['train']['all_actions']
        g = rec['train']['groups']
        def fmt(name):
            s = g[name]
            return '%.6f/%.6f/%.3f' % (
                s['xyz_euclidean_mean_m'], s['xyz_euclidean_p95_m'],
                s['gripper_accuracy'])
        lines.append('| %d | %d | %.6f | %.6f | %.6f | %s | %s | %s |' % (
            epoch, rec['updates'], rec['train_total'], rec['val_total'],
            allm['xyz_euclidean_mean_m'], fmt('L1_grasp'),
            fmt('L2_L3_recovery_grasp'), fmt('L2_L3_fold_grasp')))
    lines += ['', '## best_val and last', '',
              '| checkpoint | epoch | updates | train loss | val loss | '
              'train all Euclid | L1 mean/P95/acc | recovery mean/P95/acc | '
              'fold mean/P95/acc |',
              '|---|---:|---:|---:|---:|---:|---|---|---|']
    for name, rec in (('best_val', best_last_record), ('last', last_record)):
        allm = rec['train']['all_actions']
        g = rec['train']['groups']
        def fmt2(group_name):
            s = g[group_name]
            return '%.6f/%.6f/%.3f' % (
                s['xyz_euclidean_mean_m'], s['xyz_euclidean_p95_m'],
                s['gripper_accuracy'])
        lines.append('| %s | %d | %d | %.6f | %.6f | %.6f | %s | %s | %s |' % (
            name, rec['epoch'], rec['updates'], rec['train_total'],
            rec['val_total'], allm['xyz_euclidean_mean_m'],
            fmt2('L1_grasp'), fmt2('L2_L3_recovery_grasp'),
            fmt2('L2_L3_fold_grasp')))
    lines += ['', 'Only train/val are used; test is not evaluated.']
    (args.out / 'report.md').write_text('\n'.join(lines) + '\n',
                                        encoding='utf-8')
    print('BUDGET500_OK')
    print(json.dumps({
        'updates_actual': updates,
        'updates_expected': config['updates_expected'],
        'checkpoint_metrics': checkpoint_metrics,
        'best_val': best_last_record,
        'last': last_record,
        'best_epoch': best_epoch,
        'best_val_loss': best_val,
    }, indent=2))


if __name__ == '__main__':
    main()
