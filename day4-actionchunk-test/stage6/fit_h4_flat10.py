"""Diagnostic H=4 fit on the fixed 10 flat/train trajectories."""
from __future__ import annotations

import argparse
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
DEFAULT_OUT = DEFAULT_DATA / 'diagnostics' / 'fit_h4_flat10'
SEEDS = [6114, 6118, 6119, 6124, 6125, 6126, 6127, 6130, 6132, 6134]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
    from train_bc import BCNet, masked_ce, masked_cont_mse, obs_matrix

    z = np.load(args.data / 'dataset_h4.npz', allow_pickle=True)
    stats = json.loads((args.data / 'stats.json').read_text(encoding='utf-8'))
    mask = z['mask'].astype(np.float32)
    selected = np.where(
        (z['level'] == 'flat') & (z['split'] == 'train')
        & np.isin(z['seed'], np.asarray(SEEDS, dtype=np.int64)))[0]
    if len(selected) != 20:
        raise SystemExit('expected 20 flat/train chunks, got %d'
                         % len(selected))
    if int(mask[selected].sum()) != 70:
        raise SystemExit('expected 70 valid actions, got %d'
                         % int(mask[selected].sum()))
    if int(mask[selected].size - mask[selected].sum()) != 10:
        raise SystemExit('expected 10 padding slots')
    X = obs_matrix({key: z[key] for key in z.files})[selected]
    mean = np.asarray(stats['obs_mean'], np.float32)
    std = np.asarray(stats['obs_std'], np.float32)
    X = ((X - mean) / std).astype(np.float32)
    action = np.asarray(z['action'][selected], dtype=np.float64)
    c_mean = np.asarray(stats['cont_mean'], np.float32)
    c_std = np.asarray(stats['cont_std'], np.float32)
    cont = (action[..., :4].astype(np.float32) - c_mean) / c_std
    grip = action[..., 4].astype(np.int64)
    m = mask[selected]

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
    Xt = torch.tensor(X, device=dev)
    ct = torch.tensor(cont, device=dev)
    gt = torch.tensor(grip, device=dev)
    mt = torch.tensor(m, device=dev)
    curves = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        perm = torch.randperm(len(Xt), device=dev)
        total = cont_loss = grip_loss = 0.0
        for start in range(0, len(perm), args.batch):
            idx = perm[start:start + args.batch]
            pc, pg = model(Xt[idx])
            lc = masked_cont_mse(pc, ct[idx], mt[idx])
            lg = masked_ce(pg, gt[idx], mt[idx])
            loss = lc + lg
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += float(loss) * len(idx)
            cont_loss += float(lc) * len(idx)
            grip_loss += float(lg) * len(idx)
        curves.append({'epoch': epoch, 'train_total': total / len(Xt),
                       'train_cont': cont_loss / len(Xt),
                       'train_grip': grip_loss / len(Xt)})
    model.eval()
    with torch.no_grad():
        pc, pg = model(Xt)
    pred = pc.cpu().numpy().astype(np.float64) * c_std + c_mean
    pred_grip = pg.argmax(-1).cpu().numpy()
    valid = m.astype(bool)
    err = pred[..., :3] - action[..., :3]
    euclid = np.linalg.norm(err, axis=-1)
    metrics = {
        'chunks': int(len(Xt)),
        'valid_actions': int(valid.sum()),
        'padding': int((~valid).sum()),
        'initial_train_total': float(curves[0]['train_total']),
        'final_train_total': float(curves[-1]['train_total']),
        'final_cont_mse_masked': float(curves[-1]['train_cont']),
        'final_grip_ce_masked': float(curves[-1]['train_grip']),
        'xyz_coord_mae_m': float(np.abs(err[valid]).mean()),
        'xyz_euclidean_mean_m': float(euclid[valid].mean()),
        'xyz_euclidean_median_m': float(np.median(euclid[valid])),
        'xyz_euclidean_p95_m': float(np.percentile(euclid[valid], 95)),
        'gripper_accuracy': float((pred_grip[valid] == grip[valid]).mean()),
        'per_chunk_position': {
            str(k): {
                'n': int(valid[:, k].sum()),
                'xyz_euclidean_mean_m': float(euclid[valid[:, k], k].mean()),
                'max_m': float(euclid[valid[:, k], k].max()),
                'gripper_accuracy': float(
                    (pred_grip[valid[:, k], k] == grip[valid[:, k], k]).mean()),
            }
            for k in range(4)
        },
        'test_evaluated': False,
        'epochs': args.epochs,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    torch.save({
        'state': model.state_dict(), 'in_dim': 1340, 'hidden': 512,
        'mode': 'h4', 'epoch': args.epochs, 'selected_seeds': SEEDS,
        'dataset_sha256': sha(args.data / 'dataset_h4.npz'),
        'stats_sha256': sha(args.data / 'stats.json'),
    }, args.out / 'final.pt')
    (args.out / 'config.json').write_text(
        json.dumps({
            'purpose': 'H4 diagnostic fit; not a formal model',
            'data': str(args.data / 'dataset_h4.npz'),
            'data_sha256': sha(args.data / 'dataset_h4.npz'),
            'stats_sha256': sha(args.data / 'stats.json'),
            'selected_seeds': SEEDS, 'chunks': len(selected),
            'valid_actions': int(valid.sum()), 'padding': int((~valid).sum()),
            'architecture': 'BCNet(1340, 512, h4)',
            'epochs': args.epochs, 'batch': args.batch, 'lr': args.lr,
            'weight_decay': args.weight_decay, 'seed': args.seed,
            'loss': 'masked cont MSE + masked gripper CE',
            'validation_early_stop': False, 'test_evaluated': False,
        }, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    (args.out / 'curves.json').write_text(
        json.dumps(curves, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    (args.out / 'metrics.json').write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print('FIT_H4_FLAT10_OK')
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
