"""Recompute test metrics with explicit coverage and angular conventions.

- XYZ MAE reported per coordinate (mean |dx|,|dy|,|dz| over valid positions) and,
  as a supplement, Euclidean distance MAE.
- yaw uses the wrapped (periodic) difference: |wrap(dyaw)| with wrap to [-pi, pi].
- gripper accuracy is masked (padding excluded).
- H=4 valid positions must cover exactly the same (level, seed, action index)
  triples as the single-step test rows.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from train_bc import BCNet, H, obs_matrix

WRAP = 2 * np.pi


def wrap(a):
    return (a + np.pi) % WRAP - np.pi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', type=Path, required=True)
    ap.add_argument('--runs', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()

    stats = json.loads((a.dataset / 'stats.json').read_text())
    single = np.load(a.dataset / 'dataset_single.npz', allow_pickle=True)
    h4 = np.load(a.dataset / 'dataset_h4.npz', allow_pickle=True)
    cmean = np.asarray(stats['cont_mean'], np.float64)
    cstd = np.asarray(stats['cont_std'], np.float64)

    def prep(d, mode):
        X = obs_matrix(d).astype(np.float32)
        X = ((X - np.asarray(stats['obs_mean'], np.float32)) /
             np.asarray(stats['obs_std'], np.float32)).astype(np.float32)
        return X

    # --- coverage: single test rows vs H4 valid positions -------------------
    st = np.where(single['split'] == 'test')[0]
    ep_pos = {}
    order = []
    for i in range(len(single['seed'])):
        k = (str(single['level'][i]), int(single['seed'][i]))
        if k not in ep_pos:
            ep_pos[k] = []
            order.append(k)
        ep_pos[k].append(i)
    single_keys = set()
    for i in st:
        k = (str(single['level'][i]), int(single['seed'][i]))
        single_keys.add((k[0], k[1], ep_pos[k].index(i)))
    h4_test = np.where(h4['split'] == 'test')[0]
    h4_keys = set()
    h4_valid = 0
    for c in h4_test:
        k = (str(h4['level'][c]), int(h4['seed'][c]))
        s = int(h4['chunk_start_index'][c])
        for j in range(H):
            if int(h4['mask'][c, j]) == 1:
                h4_keys.add((k[0], k[1], s + j))
                h4_valid += 1
    coverage = {'single_test_rows': int(len(st)), 'h4_test_chunks': int(len(h4_test)),
                'h4_positions': int(len(h4_test) * H), 'h4_valid_positions': int(h4_valid),
                'h4_padding_positions': int(len(h4_test) * H - h4_valid),
                'same_actions': bool(single_keys == h4_keys),
                'single_only': sorted(single_keys - h4_keys)[:5],
                'h4_only': sorted(h4_keys - single_keys)[:5]}

    out = {'coverage': coverage,
           'xyz_mae_definition': 'per-coordinate mean |dx|,|dy|,|dz|; Euclidean MAE reported separately',
           'yaw_definition': 'wrapped periodic absolute difference',
           'gripper': 'accuracy, padding excluded for H4'}

    def model_eval(mode, rows):
        ck = torch.load(a.runs / mode / 'best.pt', map_location='cpu')
        m = BCNet(1340, 512, mode)
        m.load_state_dict(ck['state'])
        m.eval()
        X = torch.tensor(prep(single if mode == 'single' else h4, mode)[rows])
        with torch.no_grad():
            pc, pg = m(X)
        if mode == 'single':
            pred = pc.numpy().astype(np.float64) * cstd + cmean
            true = single['action'][rows, :4].astype(np.float64)
            mask = np.ones((len(rows), 1))
            grip_true = single['action'][rows, 4].astype(int)
            grip_pred = pg.argmax(-1).numpy()
        else:
            pred = pc.numpy().astype(np.float64) * cstd + cmean
            true = h4['action'][rows, :, :4].astype(np.float64)
            mask = h4['mask'][rows].astype(np.float64)
            grip_true = h4['action'][rows, :, 4].astype(int)
            grip_pred = pg.argmax(-1).numpy()
        return pred, true, mask, grip_true, grip_pred

    def metrics(pred, true, mask, grip_true, grip_pred, tag, chunked=False):
        d = pred - true
        if chunked:
            w = mask[..., None]
            den = w.sum()
            xyz = np.sum(np.abs(d[..., :3]) * w) / (den * 3)
            euc = np.sum(np.sqrt((d[..., :3] ** 2).sum(-1)) * mask) / mask.sum()
            yaw = np.sum(np.abs(wrap(d[..., 3])) * mask) / mask.sum()
            acc = (np.sum((grip_pred == grip_true) * mask) / mask.sum())
        else:
            valid = mask[:, 0] == 1
            xyz = np.mean(np.abs(d[valid][:, :3]))
            euc = np.mean(np.sqrt((d[valid][:, :3] ** 2).sum(-1)))
            yaw = np.mean(np.abs(wrap(d[valid][:, 3])))
            acc = np.mean(grip_pred[valid] == grip_true[valid])
        return {tag + '_xyz_mae_m': float(xyz), tag + '_xyz_euclid_mae_m': float(euc),
                tag + '_yaw_mae_rad': float(yaw), tag + '_grip_acc': float(acc),
                tag + '_valid_positions': int(mask.sum())}

    ps, ts, ms, gts, gps = model_eval('single', st)
    out.update(metrics(ps, ts, ms, gts, gps, 'single'))
    ph, th, mh, gth, gph = model_eval('h4', h4_test)
    out.update(metrics(ph, th, mh, gth, gph, 'h4_weighted', chunked=True))
    # chunk-averaged variant (for comparison only)
    per_chunk = []
    for c in range(len(h4_test)):
        m1 = int(mh[c].sum())
        d = ph[c][:m1] - th[c][:m1]
        per_chunk.append((np.mean(np.abs(d[:, :3])), np.mean(np.abs(wrap(d[:, 3]))),
                          float((gph[c][:m1] == gth[c][:m1]).mean())))
    pc_a = np.asarray(per_chunk)
    out['h4_chunkavg'] = {'xyz_mae_m': float(pc_a[:, 0].mean()),
                          'yaw_mae_rad': float(pc_a[:, 1].mean()),
                          'grip_acc': float(pc_a[:, 2].mean()),
                          'chunks': int(len(pc_a))}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
