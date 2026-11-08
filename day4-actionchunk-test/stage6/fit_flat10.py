"""Diagnostic 10-trajectory fitting check.

Selects the first 10 flat train episodes by ascending seed (all 7 actions each),
uses the holdingfix data + full-train stats, trains the same single BCNet from
scratch for exactly 500 epochs with no validation/early stopping, and reports
only this training subset.  The formal checkpoint is never touched.
"""
from __future__ import annotations

import argparse
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
               / 'fit_flat10')


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metrics(pred_xyz, pred_grip, target):
    err = np.asarray(pred_xyz, dtype=np.float64) - np.asarray(
        target[:, :3], dtype=np.float64)
    euclid = np.linalg.norm(err, axis=1)
    coord = np.abs(err).mean()
    close = target[:, 4] == 1
    return {
        'n': int(len(target)),
        'n_close': int(close.sum()),
        'xyz_coord_mae_m': float(coord),
        'xyz_euclidean_mean_m': float(euclid.mean()),
        'xyz_euclidean_median_m': float(np.median(euclid)),
        'xyz_euclidean_p95_m': float(np.percentile(euclid, 95)),
        'gripper_accuracy': float(np.mean(pred_grip == target[:, 4])),
        'close_xyz_euclidean_mean_m': float(euclid[close].mean()),
        'close_xyz_euclidean_median_m': float(np.median(euclid[close])),
        'close_xyz_euclidean_p95_m': float(np.percentile(euclid[close], 95)),
        'close_gripper_accuracy': float(np.mean(
            pred_grip[close] == target[close, 4])),
    }


def per_action_table(target, pred_xyz, pred_grip):
    err = np.linalg.norm(
        np.asarray(pred_xyz, dtype=np.float64) - target[:, :3], axis=1)
    out = {}
    for action_index in range(7):
        mask = np.asarray([row['action_index'] == action_index
                           for row in target_meta])
        if not mask.any():
            continue
        out[str(action_index)] = {
            'n': int(mask.sum()),
            'mean_m': float(err[mask].mean()),
            'median_m': float(np.median(err[mask])),
            'max_m': float(err[mask].max()),
            'gripper_accuracy': float(np.mean(
                pred_grip[mask] == target[mask, 4])),
        }
    return out


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

    for path in (str(TRAIN), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from train_bc import BCNet, obs_matrix

    data = np.load(args.data / 'dataset_single.npz', allow_pickle=True)
    arrays = {key: data[key] for key in data.files}
    stats = load_json(args.data / 'stats.json')
    train_mask = arrays['split'] == 'train'
    flat_train_seeds = sorted(set(
        int(seed) for seed in arrays['seed'][
            train_mask & (arrays['level'] == 'flat')].tolist()))
    if len(flat_train_seeds) < 10:
        raise SystemExit('Need at least 10 flat train seeds')
    selected = flat_train_seeds[:10]
    selected_indices = []
    for seed in selected:
        idx = np.where(
            (arrays['seed'] == seed) & (arrays['level'] == 'flat')
            & (arrays['split'] == 'train'))[0]
        if len(idx) != 7:
            raise SystemExit('Seed %d does not have 7 complete actions' % seed)
        selected_indices.extend(int(i) for i in idx)
    if len(selected_indices) != 70:
        raise SystemExit('Expected 70 subset rows, got %d'
                         % len(selected_indices))
    selected_indices = sorted(selected_indices)

    X = obs_matrix(arrays)
    mean = np.asarray(stats['obs_mean'], dtype=np.float32)
    std = np.asarray(stats['obs_std'], dtype=np.float32)
    c_mean = np.asarray(stats['cont_mean'], dtype=np.float64)
    c_std = np.asarray(stats['cont_std'], dtype=np.float64)
    if abs(float(stats['obs_mean'][1339])) > 1e-12 or abs(
            float(stats['obs_std'][1339]) - 1.0) > 1e-12:
        raise SystemExit('Small fit requires identity holding stats')
    X = ((X[selected_indices] - mean) / std).astype(np.float32)
    cont = (arrays['action'][selected_indices, :4].astype(np.float64)
            - c_mean) / c_std
    grip = arrays['action'][selected_indices, 4].astype(np.int64)
    target = arrays['action'][selected_indices].astype(np.float64)
    global target_meta
    target_meta = [
        {'action_index': i % 7, 'seed': int(arrays['seed'][idx]),
         'phase': str(arrays['phase'][idx]), 'command': int(target[i, 4])}
        for i, idx in enumerate(selected_indices)
    ]

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
    Xt = torch.tensor(X, device=dev)
    ct = torch.tensor(cont, device=dev)
    gt = torch.tensor(grip, device=dev)
    curves = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        perm = torch.randperm(len(Xt), device=dev)
        total = cont_loss_sum = grip_loss_sum = 0.0
        for start in range(0, len(perm), args.batch):
            idx = perm[start:start + args.batch]
            pc, pg = model(Xt[idx])
            lc = ((pc - ct[idx]) ** 2).mean()
            lg = F.cross_entropy(pg, gt[idx])
            loss = lc + lg
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += float(loss) * len(idx)
            cont_loss_sum += float(lc) * len(idx)
            grip_loss_sum += float(lg) * len(idx)
        record = {
            'epoch': epoch,
            'train_total': total / len(Xt),
            'train_cont': cont_loss_sum / len(Xt),
            'train_grip': grip_loss_sum / len(Xt),
        }
        if epoch % 10 == 0 or epoch == 1 or epoch == args.epochs:
            model.eval()
            with torch.no_grad():
                pc, pg = model(Xt)
            pred = pc.cpu().numpy().astype(np.float64) * c_std + c_mean
            pred_grip = pg.argmax(1).cpu().numpy()
            record['subset'] = metrics(pred[:, :3], pred_grip, target)
        curves.append(record)

    model.eval()
    with torch.no_grad():
        pc, pg = model(Xt)
    pred = pc.cpu().numpy().astype(np.float64) * c_std + c_mean
    pred_grip = pg.argmax(1).cpu().numpy()
    final_metrics = metrics(pred[:, :3], pred_grip, target)
    final_metrics['per_action_index'] = per_action_table(
        target, pred[:, :3], pred_grip)
    final_metrics['initial_train_total'] = curves[0]['train_total']
    final_metrics['final_train_total'] = curves[-1]['train_total']
    final_metrics['selected_flat_train_seeds'] = selected
    final_metrics['selected_rows'] = len(selected_indices)
    final_metrics['epochs'] = args.epochs
    final_metrics['no_validation_early_stop'] = True
    final_metrics['test_evaluated'] = False

    args.out.mkdir(parents=True, exist_ok=True)
    torch.save({
        'state': model.state_dict(),
        'in_dim': 1340,
        'hidden': 512,
        'mode': 'single',
        'epoch': args.epochs,
        'selected_seeds': selected,
        'dataset_sha256': sha(args.data / 'dataset_single.npz'),
        'stats_sha256': sha(args.data / 'stats.json'),
    }, args.out / 'final.pt')
    predictions = []
    for i, meta in enumerate(target_meta):
        predictions.append({
            **meta,
            'dataset_index': selected_indices[i],
            'true_xyz': target[i, :3].tolist(),
            'true_yaw': float(target[i, 3]),
            'true_gripper': int(target[i, 4]),
            'pred_xyz': pred[i, :3].tolist(),
            'pred_yaw': float(pred[i, 3]),
            'pred_gripper': int(pred_grip[i]),
            'xyz_euclidean_m': float(np.linalg.norm(
                pred[i, :3] - target[i, :3])),
        })
    config = {
        'purpose': 'diagnostic 10-trajectory fit; not a formal model',
        'data': str(args.data / 'dataset_single.npz'),
        'stats': str(args.data / 'stats.json'),
        'dataset_sha256': sha(args.data / 'dataset_single.npz'),
        'stats_sha256': sha(args.data / 'stats.json'),
        'selected_flat_train_seeds': selected,
        'selected_rows': len(selected_indices),
        'architecture': 'BCNet(1340, 512, single)',
        'epochs': args.epochs,
        'batch': args.batch,
        'lr': args.lr,
        'weight_decay': args.weight_decay,
        'seed': args.seed,
        'validation_early_stop': False,
        'test_evaluated': False,
        'loss': 'MSE on standardized cont dims + cross_entropy on gripper',
        'device': dev,
    }
    (args.out / 'config.json').write_text(
        json.dumps(config, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    (args.out / 'curves.json').write_text(
        json.dumps(curves, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    (args.out / 'metrics.json').write_text(
        json.dumps(final_metrics, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    (args.out / 'predictions.json').write_text(
        json.dumps(predictions, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print('FIT_FLAT10_OK')
    print(json.dumps({
        'selected_seeds': selected,
        'selected_rows': len(selected_indices),
        'initial_train_total': final_metrics['initial_train_total'],
        'final_train_total': final_metrics['final_train_total'],
        'final_metrics': final_metrics,
        'curves_len': len(curves),
    }, indent=2))


if __name__ == '__main__':
    main()
