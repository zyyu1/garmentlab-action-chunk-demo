"""Offline checks for the Stage 5 BC pipeline (no Isaac Sim, no training).

Verifies:
  * state dim 1340 (vertices + ee + quat + joints + holding)
  * forward shapes for single (B,4)+(B,3) and H=4 (B,4,4)+(B,4,3)
  * gripper labels in {0,1,2}; holding binary
  * padded H=4 targets do not affect the loss
  * H=4 inputs equal the single-step observation at chunk_start_index
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from train_bc import BCNet, H, masked_cont_mse, masked_ce, obs_matrix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', type=Path, required=True)
    a = ap.parse_args()
    stats = json.loads((a.dataset / 'stats.json').read_text())
    single = np.load(a.dataset / 'dataset_single.npz', allow_pickle=True)
    h4 = np.load(a.dataset / 'dataset_h4.npz', allow_pickle=True)
    X = obs_matrix(single)
    Xh = obs_matrix(h4)
    checks = {'obs_dim': int(X.shape[1]), 'obs_dim_h4': int(Xh.shape[1]),
              'single': int(len(X)), 'h4': int(len(Xh))}
    assert X.shape[1] == 1340 and Xh.shape[1] == 1340, (X.shape, Xh.shape)
    assert stats['obs_dim'] == 1340

    hold = single['obs_holding']
    assert set(np.unique(hold).tolist()) <= {0.0, 1.0}, np.unique(hold)
    grip = single['action'][:, 4]
    checks['gripper_values'] = sorted(int(v) for v in np.unique(grip))
    assert set(checks['gripper_values']) <= {0, 1, 2}

    torch.manual_seed(0)
    xs = torch.tensor(X[:8], dtype=torch.float32)
    xh = torch.tensor(Xh[:8], dtype=torch.float32)
    m = BCNet(1340, 512, 'single').eval()
    mh = BCNet(1340, 512, 'h4').eval()
    with torch.no_grad():
        cs, gs = m(xs)
        ch, gh = mh(xh)
    checks['single_shapes'] = [list(cs.shape), list(gs.shape)]
    checks['h4_shapes'] = [list(ch.shape), list(gh.shape)]
    assert cs.shape == (8, 4) and gs.shape == (8, 3)
    assert ch.shape == (8, H, 4) and gh.shape == (8, H, 3)

    # padding invariance: randomize padded targets, masked loss must not change
    ch_t = ch.reshape(8, H, 4)
    gh_t = gh.reshape(8, H, 3)
    mask = torch.tensor(h4['mask'][:8].astype(np.float32))
    cont = torch.tensor(h4['action'][:8, :, :4].astype(np.float32))
    tgt = torch.tensor(h4['action'][:8, :, 4].astype(np.int64))
    b_cont = float(masked_cont_mse(ch_t, cont, mask))
    b_ce = float(masked_ce(gh_t, tgt, mask))
    cont2 = cont.clone()
    tgt2 = tgt.clone()
    pad = mask == 0
    cont2[pad] = torch.randn_like(cont2[pad]) * 100
    tgt2[pad] = torch.randint(0, 3, tgt2[pad].shape)
    a_cont = float(masked_cont_mse(ch_t, cont2, mask))
    a_ce = float(masked_ce(gh_t, tgt2, mask))
    checks['padding_invariance'] = {'cont': [b_cont, a_cont], 'ce': [b_ce, a_ce]}
    assert abs(b_cont - a_cont) < 1e-6 and abs(b_ce - a_ce) < 1e-6

    # H=4 start observation equals single-step observation at chunk_start_index
    counts = {}
    order = []
    for lvl, seed in zip(single['level'], single['seed']):
        key = (str(lvl), int(seed))
        counts[key] = counts.get(key, 0) + 1
        if key not in order:
            order.append(key)
    base = {}
    pos = 0
    for key in order:
        n = counts[key]
        base[key] = (pos, n)
        pos += n
    ok = 0
    for j in range(len(h4['seed'])):
        key = (str(h4['level'][j]), int(h4['seed'][j]))
        b, n = base[key]
        s = int(h4['chunk_start_index'][j])
        for f in ('obs_vertices', 'obs_ee', 'obs_quat', 'obs_joints'):
            assert np.allclose(h4[f + '_start'][j], single[f][b + s]), (key, s, f)
        assert float(h4['obs_holding_start'][j]) == float(single['obs_holding'][b + s])
        ok += 1
    checks['h4_no_future_obs_rows'] = ok

    # backward check: one optimizer step must produce finite gradients
    m.train()
    opt = torch.optim.SGD(m.parameters(), lr=0.01)
    pc, pg = m(xs)
    loss = ((pc - torch.zeros_like(pc)) ** 2).mean() + torch.nn.functional.cross_entropy(
        pg, torch.zeros(len(xs), dtype=torch.long))
    opt.zero_grad()
    loss.backward()
    opt.step()
    checks['backward_ok'] = all(
        p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in m.parameters())
    assert checks['backward_ok']
    print(json.dumps(checks, indent=2))
    print('CHECK_OK')


if __name__ == '__main__':
    main()
