"""Full H=4 training on the corrected data: 500 epochs, no early stopping."""
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

HERE = Path(__file__).resolve().parent
STAGE5 = Path('/root/autodl-tmp/stage5-trial')
TRAIN = STAGE5 / 'training'
DEFAULT_DATA = STAGE5 / 'holdingfix-20261108' / 'h4fix-20261108'
DEFAULT_OUT = DEFAULT_DATA / 'runs' / 'h4_budget500'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def masked_metrics(pred_cont, pred_grip, action, mask, c_mean, c_std):
    valid = mask.astype(bool)
    err = pred_cont[..., :3] - action[..., :3]
    euclid = np.linalg.norm(err, axis=-1)
    return {
        'valid_actions': int(valid.sum()),
        'xyz_coord_mae_m': float(np.abs(err[valid]).mean()),
        'xyz_euclidean_mean_m': float(euclid[valid].mean()),
        'xyz_euclidean_median_m': float(np.median(euclid[valid])),
        'xyz_euclidean_p95_m': float(np.percentile(euclid[valid], 95)),
        'gripper_accuracy': float((pred_grip[valid] == action[..., 4][valid]).mean()),
    }


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
        raise SystemExit('fixed 500 epochs')
    for path in (str(TRAIN), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from train_bc import BCNet, masked_ce, masked_cont_mse, obs_matrix

    z = np.load(args.data / 'dataset_h4.npz', allow_pickle=True)
    stats = json.loads((args.data / 'stats.json').read_text(encoding='utf-8'))
    if stats.get('holding_normalization') != 'identity':
        raise SystemExit('H4 stats must use identity holding')
    if abs(float(stats['obs_mean'][1339])) > 1e-12 or abs(
            float(stats['obs_std'][1339]) - 1.0) > 1e-12:
        raise SystemExit('invalid identity holding stats')
    X = obs_matrix({key: z[key] for key in z.files})
    mean = np.asarray(stats['obs_mean'], np.float32)
    std = np.asarray(stats['obs_std'], np.float32)
    X = ((X - mean) / std).astype(np.float32)
    action = np.asarray(z['action'], dtype=np.float64)
    c_mean = np.asarray(stats['cont_mean'], np.float32)
    c_std = np.asarray(stats['cont_std'], np.float32)
    cont = (action[..., :4].astype(np.float32) - c_mean) / c_std
    grip = action[..., 4].astype(np.int64)
    mask = z['mask'].astype(np.float32)
    split = z['split']
    train_idx = np.where(split == 'train')[0]
    val_idx = np.where(split == 'val')[0]
    if len(train_idx) != 104 or len(val_idx) != 26:
        raise SystemExit('unexpected H4 chunk split: %d/%d'
                         % (len(train_idx), len(val_idx)))
    if int(mask[train_idx].sum()) != 385 or int(mask[val_idx].sum()) != 94:
        raise SystemExit('unexpected H4 valid split')

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = BCNet(1340, 512, 'h4').to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr,
                            weight_decay=args.weight_decay)
    Xtr = torch.tensor(X[train_idx], device=dev)
    ctr = torch.tensor(cont[train_idx], device=dev)
    gtr = torch.tensor(grip[train_idx], device=dev)
    mtr = torch.tensor(mask[train_idx], device=dev)
    Xva = torch.tensor(X[val_idx], device=dev)
    cva = torch.tensor(cont[val_idx], device=dev)
    gva = torch.tensor(grip[val_idx], device=dev)
    mva = torch.tensor(mask[val_idx], device=dev)

    best_val = float('inf')
    best_epoch = 0
    best_state = None
    last_state = None
    updates = 0
    curves = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        perm = torch.randperm(len(Xtr), device=dev)
        total = cont_loss = grip_loss = 0.0
        for start in range(0, len(perm), args.batch):
            idx = perm[start:start + args.batch]
            pc, pg = model(Xtr[idx])
            lc = masked_cont_mse(pc, ctr[idx], mtr[idx])
            lg = masked_ce(pg, gtr[idx], mtr[idx])
            loss = lc + lg
            opt.zero_grad()
            loss.backward()
            opt.step()
            updates += 1
            total += float(loss) * len(idx)
            cont_loss += float(lc) * len(idx)
            grip_loss += float(lg) * len(idx)
        model.eval()
        with torch.no_grad():
            pc, pg = model(Xva)
            vc = float(masked_cont_mse(pc, cva, mva))
            vg = float(masked_ce(pg, gva, mva))
        val_total = vc + vg
        curves.append({'epoch': epoch, 'updates': updates,
                       'train_total': total / len(Xtr),
                       'train_cont': cont_loss / len(Xtr),
                       'train_grip': grip_loss / len(Xtr),
                       'val_cont': vc, 'val_grip': vg, 'val_total': val_total})
        if val_total < best_val - 1e-12:
            best_val = val_total
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        if epoch % 50 == 0 or epoch == 1:
            print('EPOCH %d updates=%d train=%.6f val=%.6f best=%.6f@%d'
                  % (epoch, updates, curves[-1]['train_total'], val_total,
                     best_val, best_epoch))
    last_state = copy.deepcopy(model.state_dict())

    args.out.mkdir(parents=True, exist_ok=True)
    meta = {
        'in_dim': 1340, 'hidden': 512, 'mode': 'h4', 'epochs': args.epochs,
        'batch': args.batch, 'lr': args.lr,
        'weight_decay': args.weight_decay, 'seed': args.seed,
        'dataset_sha256': sha(args.data / 'dataset_h4.npz'),
        'stats_sha256': sha(args.data / 'stats.json'),
        'selected_by': 'minimum total validation loss', 'test_evaluated': False,
    }
    torch.save({**meta, 'state': best_state, 'epoch': best_epoch,
                'val_total': best_val}, args.out / 'best_val.pt')
    torch.save({**meta, 'state': last_state, 'epoch': args.epochs,
                'val_total': curves[-1]['val_total']}, args.out / 'last.pt')

    def eval_state(state):
        model.load_state_dict(state)
        model.eval()
        with torch.no_grad():
            pc, pg = model(torch.tensor(X, device=dev))
            train_pc, train_pg = model(Xtr)
            vc = float(masked_cont_mse(train_pc, ctr, mtr))
            vg = float(masked_ce(train_pg, gtr, mtr))
            val_pc, val_pg = model(Xva)
            vvc = float(masked_cont_mse(val_pc, cva, mva))
            vvg = float(masked_ce(val_pg, gva, mva))
        pred = pc.cpu().numpy().astype(np.float64) * c_std + c_mean
        pred_grip = pg.argmax(-1).cpu().numpy()
        train_metrics = masked_metrics(
            pred[train_idx], pred_grip[train_idx], action[train_idx],
            mask[train_idx], c_mean, c_std)
        val_metrics = masked_metrics(
            pred[val_idx], pred_grip[val_idx], action[val_idx],
            mask[val_idx], c_mean, c_std)
        return {
            'train_masked_cont_mse': vc,
            'train_masked_grip_ce': vg,
            'train_total': vc + vg,
            'train_metrics': train_metrics,
            'val_masked_cont_mse': vvc,
            'val_masked_grip_ce': vvg,
            'val_total': vvc + vvg,
            'val_metrics': val_metrics,
        }

    best_record = eval_state(best_state)
    best_record['epoch'] = best_epoch
    last_record = eval_state(last_state)
    last_record['epoch'] = args.epochs

    # Reload identity check: a fresh BCNet must reproduce best_val outputs.
    ck = torch.load(args.out / 'best_val.pt', map_location='cpu')
    reload_model = BCNet(1340, 512, 'h4').to(dev)
    reload_model.load_state_dict(ck['state'])
    reload_model.eval()
    with torch.no_grad():
        pc, pg = reload_model(Xva)
    reload_check = {
        'epoch': int(ck['epoch']),
        'in_dim': int(ck['in_dim']),
        'hidden': int(ck['hidden']),
        'mode': ck['mode'],
        'state_loaded': True,
        'val_cont': float(masked_cont_mse(
            pc, cva, mva)),
        'val_grip': float(masked_ce(pg, gva, mva)),
        'output_shape': list(pc.shape),
        'finite': bool(torch.isfinite(pc).all() and torch.isfinite(pg).all()),
    }
    (args.out / 'config.json').write_text(
        json.dumps(meta, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    (args.out / 'curves.json').write_text(
        json.dumps(curves, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    (args.out / 'best_val_metrics.json').write_text(
        json.dumps(best_record, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    (args.out / 'last_metrics.json').write_text(
        json.dumps(last_record, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    (args.out / 'reload_check.json').write_text(
        json.dumps(reload_check, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print('TRAIN_H4_OK')
    print(json.dumps({
        'updates_actual': updates,
        'best_val': best_record,
        'last': last_record,
        'reload': reload_check,
        'epochs_run': args.epochs,
    }, indent=2))


if __name__ == '__main__':
    main()
