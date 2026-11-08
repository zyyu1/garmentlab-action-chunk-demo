"""Behavior-cloning baseline for Stage 5 demos.

State (1340): vertices(441*3) + ee(3) + quat(4) + joints(9) + holding(1).
Trunk (both modes): Linear(1340,512) -> GELU -> LN -> Linear(512,512) -> GELU -> LN.
single : cont head (B,4), gripper logits (B,3).
h4     : cont head (B,4,4), gripper logits (B,4,3), padding excluded from both
         losses (normalized by valid elements).

Continuous loss = MSE on standardized dims 0..3 (stats from train real actions
only, no H4 duplication, padding excluded). Gripper = cross-entropy over the
three command classes (labels not normalized).
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

H = 4


def obs_matrix(d):
    pre = 'obs_vertices_start' if 'obs_vertices_start' in d else 'obs_vertices'
    v = d[pre].reshape(len(d[pre]), -1).astype(np.float32)
    ee = d['obs_ee_start' if 'obs_ee_start' in d else 'obs_ee']
    q = d['obs_quat_start' if 'obs_quat_start' in d else 'obs_quat']
    j = d['obs_joints_start' if 'obs_joints_start' in d else 'obs_joints']
    h = d['obs_holding_start' if 'obs_holding_start' in d else 'obs_holding']
    return np.concatenate([v, ee, q, j, h[:, None]], axis=1)


class BCNet(nn.Module):
    def __init__(self, in_dim=1340, hidden=512, mode='single'):
        super().__init__()
        self.mode = mode
        self.trunk = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.GELU(), nn.LayerNorm(hidden),
            nn.Linear(hidden, hidden), nn.GELU(), nn.LayerNorm(hidden))
        if mode == 'single':
            self.cont = nn.Linear(hidden, 4)
            self.grip = nn.Linear(hidden, 3)
        else:
            self.cont = nn.Linear(hidden, H * 4)
            self.grip = nn.Linear(hidden, H * 3)

    def forward(self, x):
        z = self.trunk(x)
        if self.mode == 'single':
            return self.cont(z), self.grip(z)
        return self.cont(z).reshape(-1, H, 4), self.grip(z).reshape(-1, H, 3)


def masked_cont_mse(pred, target, mask):
    err = ((pred - target) ** 2).mean(-1) * mask
    return err.sum() / mask.sum().clamp_min(1.0)


def masked_ce(logits, target, mask):
    ls = logits.reshape(-1, 3)
    ts = target.reshape(-1).long()
    ce = F.cross_entropy(ls, ts, reduction='none').reshape(mask.shape)
    return (ce * mask).sum() / mask.sum().clamp_min(1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', type=Path, required=True)
    ap.add_argument('--mode', choices=['single', 'h4'], required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--epochs', type=int, default=100)
    ap.add_argument('--batch', type=int, default=128)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()

    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    a.out.mkdir(parents=True, exist_ok=True)

    df = 'dataset_single.npz' if a.mode == 'single' else 'dataset_h4.npz'
    stats = json.loads((a.dataset / 'stats.json').read_text())
    z = np.load(a.dataset / df, allow_pickle=True)
    X = obs_matrix(z)
    assert X.shape[1] == stats['obs_dim'] == 1340, (X.shape, stats['obs_dim'])
    X = (X - np.asarray(stats['obs_mean'], np.float32)) / np.asarray(stats['obs_std'], np.float32)
    X = X.astype(np.float32)
    cont = z['action'][..., :4].astype(np.float32)
    cont = (cont - np.asarray(stats['cont_mean'], np.float32)) / np.asarray(stats['cont_std'], np.float32)
    grip = z['action'][..., 4].astype(np.int64)
    assert grip.min() >= 0 and grip.max() <= 2, np.unique(grip)
    split = z['split']
    mask = z['mask'].astype(np.float32) if a.mode == 'h4' else np.ones((len(X), 1), np.float32)

    tr = np.where(split == 'train')[0]
    va = np.where(split == 'val')[0]
    te = np.where(split == 'test')[0]
    if len(va) == 0:
        cut = max(1, len(tr) // 10)
        va = tr[-cut:]
        tr = tr[:-cut]

    def tens(idx):
        return (torch.tensor(X[idx], device=dev), torch.tensor(cont[idx], device=dev),
                torch.tensor(grip[idx], device=dev), torch.tensor(mask[idx], device=dev))

    model = BCNet(X.shape[1], 512, a.mode).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    Xtr, ctr, gtr, mtr = tens(tr)
    Xva, cva, gva, mva = tens(va)
    best, bad, curves = float('inf'), 0, []
    for ep in range(1, a.epochs + 1):
        model.train()
        perm = torch.randperm(len(Xtr), device=dev)
        tot = 0.0
        for i in range(0, len(perm), a.batch):
            idx = perm[i:i + a.batch]
            pc, pg = model(Xtr[idx])
            if a.mode == 'h4':
                lc = masked_cont_mse(pc, ctr[idx], mtr[idx])
                lg = masked_ce(pg, gtr[idx], mtr[idx])
            else:
                lc = ((pc - ctr[idx]) ** 2).mean()
                lg = F.cross_entropy(pg, gtr[idx])
            loss = lc + lg
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += float(loss) * len(idx)
        model.eval()
        with torch.no_grad():
            pc, pg = model(Xva)
            if a.mode == 'h4':
                vc = float(masked_cont_mse(pc, cva, mva))
                vg = float(masked_ce(pg, gva, mva))
            else:
                vc = float(((pc - cva) ** 2).mean())
                vg = float(F.cross_entropy(pg, gva))
        vl = vc + vg
        curves.append({'epoch': ep, 'train': tot / len(Xtr), 'val_cont': vc, 'val_grip': vg, 'val': vl})
        if vl < best - 1e-6:
            best, bad = vl, 0
            torch.save({'state': model.state_dict(), 'in_dim': X.shape[1], 'hidden': 512,
                        'mode': a.mode, 'stats': stats}, a.out / 'best.pt')
        else:
            bad += 1
            if bad >= 15:
                break

    model.load_state_dict(torch.load(a.out / 'best.pt', map_location=dev)['state'])
    model.eval()
    res = {'mode': a.mode, 'best_val': best, 'epochs_run': len(curves), 'device': dev,
           'splits': {'train': int(len(tr)), 'val': int(len(va)), 'test': int(len(te))},
           'gripper_classes': stats['gripper_classes']}
    with torch.no_grad():
        cstd = torch.tensor(stats['cont_std'], device=dev)
        cmean = torch.tensor(stats['cont_mean'], device=dev)

        def unit_errors(pred, true, mask):
            po = pred * cstd + cmean
            to = true * cstd + cmean
            err = (po - to).abs()
            if a.mode == 'h4':
                w = mask.unsqueeze(-1)
                den = w.sum().clamp_min(1.0)
                return (float((err[..., :3] * w).sum() / (den * 3)),
                        float((err[..., 3] * w.squeeze(-1)).sum() / den))
            return float(err[:, :3].mean()), float(err[:, 3].mean())

        def eval_idx(idx, tag):
            Xe, ce, ge, me = tens(idx)
            pc, pg = model(Xe)
            if a.mode == 'h4':
                vc = float(masked_cont_mse(pc, ce, me))
                vg = float(masked_ce(pg, ge, me))
                acc = float(((pg.argmax(-1) == ge) * me).sum() / me.sum().clamp_min(1.0))
            else:
                vc = float(((pc - ce) ** 2).mean())
                vg = float(F.cross_entropy(pg, ge))
                acc = float((pg.argmax(-1) == ge).float().mean())
            xyz, yaw = unit_errors(pc, ce, me)
            res[tag + '_cont_mse'] = vc
            res[tag + '_grip_ce'] = vg
            res[tag + '_grip_acc'] = acc
            res[tag + '_xyz_mae_m'] = xyz
            res[tag + '_yaw_mae_rad'] = yaw

        eval_idx(tr, 'train')
        eval_idx(va, 'val')
        if len(te):
            eval_idx(te, 'test')
        # per-level test metrics
        levels = z['level']
        res['test_by_level'] = {}
        for lvl in sorted(set(levels[te].tolist())):
            idx = te[levels[te] == lvl]
            Xe, ce, ge, me = tens(idx)
            pc, pg = model(Xe)
            xyz, yaw = unit_errors(pc, ce, me)
            if a.mode == 'h4':
                res['test_by_level'][lvl] = {
                    'n': int(len(idx)),
                    'cont_mse': float(masked_cont_mse(pc, ce, me)),
                    'grip_ce': float(masked_ce(pg, ge, me)),
                    'grip_acc': float(((pg.argmax(-1) == ge) * me).sum() / me.sum().clamp_min(1.0)),
                    'xyz_mae_m': xyz, 'yaw_mae_rad': yaw}
            else:
                res['test_by_level'][lvl] = {
                    'n': int(len(idx)),
                    'cont_mse': float(((pc - ce) ** 2).mean()),
                    'grip_ce': float(F.cross_entropy(pg, ge)),
                    'grip_acc': float((pg.argmax(-1) == ge).float().mean()),
                    'xyz_mae_m': xyz, 'yaw_mae_rad': yaw}
    (a.out / 'metrics.json').write_text(json.dumps(res, indent=2) + '\n', encoding='utf-8')
    (a.out / 'curves.json').write_text(json.dumps(curves, indent=2) + '\n', encoding='utf-8')
    print('TRAIN_OK', json.dumps(res, indent=2))


if __name__ == '__main__':
    main()
