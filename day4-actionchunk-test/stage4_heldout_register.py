"""Register the Stage 4 formal-batch held-out seeds (offline; no simulation).

Dev seeds are 4100-4109 (flat, L1), 4200-4209 (perturbed, L2), 4300-4309
(crumpled, L3).  The frozen test rule (STAGE4_TASK_DEFINITION_FREEZE.md §5)
reserves 20 held-out seeds per level, disjoint from dev, fixed before the batch
and shared by single-step and arc4.  This script takes the next contiguous
block after each dev set (4110-4129 / 4210-4229 / 4310-4329) so the choice is
made once, before any result exists, and cannot be re-drawn afterwards.

Initial-state parameters follow the same per-seed rule that reproduces all 30
dev plan entries exactly (tested to 1e-15): translation dx, dy and yaw are the
first three draws of ``numpy.random.default_rng(seed)`` over the ranges frozen
in ``square-difficulty.yaml``.  Dev L2 strip widths were authored values that
cannot be reproduced from that stream, so held-out L2 widths use the declared
range [0.16, 0.18] as the fourth draw of the same per-seed stream, rounded to
6 decimals and persisted here.  L3 strip width is fixed at 0.20.

Usage:
    python -I stage4_heldout_register.py --check
    python -I stage4_heldout_register.py --write
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PLAN = HERE / 'square-initial-plan.json'
SEEDS_OUT = HERE / 'stage4-heldout-seeds.json'

# Frozen level parameters, mirroring square-difficulty.yaml.
LEVELS = {
    'flat': {'translate': (0.0, 0.03), 'yaw': (-0.1745, 0.1745),
             'settle_steps': 120, 'generator': 'day4-square-initial.py'},
    'perturbed': {'translate': (0.0, 0.03), 'yaw': (-0.1745, 0.1745),
                  'settle_steps': 180,
                  'generator': 'day4-square-initial-stripfold.py',
                  'strip': 'bottom'},
    'crumpled': {'translate': (0.0, 0.05), 'yaw': (-0.3491, 0.3491),
                 'settle_steps': 240,
                 'generator': 'day4-square-initial-stripfold.py',
                 'strip': 'left'},
}
DEV_SEEDS = {'flat': list(range(4100, 4110)),
             'perturbed': list(range(4200, 4210)),
             'crumpled': list(range(4300, 4310))}
HELDOUT_SEEDS = {'flat': list(range(4110, 4130)),
                 'perturbed': list(range(4210, 4230)),
                 'crumpled': list(range(4310, 4330))}
STATUS = 'heldout_registered_stage4_formal_v1'


def entry(level, seed):
    cfg = LEVELS[level]
    rng = np.random.default_rng(seed)
    dx = float(rng.uniform(*cfg['translate']))
    dy = float(rng.uniform(*cfg['translate']))
    yaw = float(rng.uniform(*cfg['yaw']))
    row = {'level': level, 'seed': seed, 'translation_xy_m': [dx, dy],
           'yaw_rad': yaw}
    if level == 'flat':
        row['lift_drop_cycles'] = []
        row['settle_steps'] = cfg['settle_steps']
        row['status'] = STATUS
    else:
        row['settle_steps'] = cfg['settle_steps']
        row['status'] = STATUS
        width = 0.2 if level == 'crumpled' else round(float(rng.uniform(0.16, 0.18)), 6)
        row['strips'] = [{'edge': cfg['strip'], 'width_m': width}]
    return row


def dev_rule_ok(plan):
    """All 30 dev entries must still match the per-seed draw rule."""
    bad = []
    for row in plan['episodes']:
        cfg = LEVELS[row['level']]
        rng = np.random.default_rng(row['seed'])
        dx = rng.uniform(*cfg['translate'])
        dy = rng.uniform(*cfg['translate'])
        yaw = rng.uniform(*cfg['yaw'])
        ok = (np.isclose(dx, row['translation_xy_m'][0], rtol=0, atol=1e-15)
              and np.isclose(dy, row['translation_xy_m'][1], rtol=0, atol=1e-15)
              and np.isclose(yaw, row['yaw_rad'], rtol=0, atol=1e-15))
        if not ok:
            bad.append(row['seed'])
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    if not (args.write or args.check):
        ap.error('choose --check or --write')

    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    existing = {row['seed']: row for row in plan['episodes']}

    dev_mismatch = dev_rule_ok(plan)
    assert not dev_mismatch, f'dev entries no longer follow the draw rule: {dev_mismatch}'

    all_dev = {s for group in DEV_SEEDS.values() for s in group}
    all_held = {s for group in HELDOUT_SEEDS.values() for s in group}
    assert len(all_dev) == 30 and len(all_held) == 60
    assert all_dev.isdisjoint(all_held), 'held-out overlaps dev'

    new_rows = []
    for level, seeds in HELDOUT_SEEDS.items():
        assert len(seeds) == 20, (level, len(seeds))
        for seed in seeds:
            row = entry(level, seed)
            if seed in existing:
                assert existing[seed] == row, f'plan entry changed for {seed}'
            new_rows.append(row)

    print(f'{"level":10s} {"seed":5s} {"dx_m":>9s} {"dy_m":>9s} {"yaw_rad":>9s} {"width_m":>8s}')
    for row in new_rows:
        w = row.get('strips', [{}])[0].get('width_m') if 'strips' in row else None
        print(f"{row['level']:10s} {row['seed']:5d} "
              f"{row['translation_xy_m'][0]:9.6f} {row['translation_xy_m'][1]:9.6f} "
              f"{row['yaw_rad']:9.6f} {'' if w is None else f'{w:8.6f}'}")

    per_level = {lvl: [r for r in new_rows if r['level'] == lvl] for lvl in LEVELS}
    for lvl, rows in per_level.items():
        ys = [r['yaw_rad'] for r in rows]
        ts = [t for r in rows for t in r['translation_xy_m']]
        extra = ''
        if 'strips' in rows[0]:
            ws = [r['strips'][0]['width_m'] for r in rows]
            extra = f' widths {min(ws):.6f}..{max(ws):.6f}'
        print(f'{lvl}: n={len(rows)} yaw {min(ys):+.4f}..{max(ys):+.4f} '
              f'translation 0..{max(ts):.4f}{extra}')

    if not args.write:
        print('\ncheck only; nothing written')
        return 0

    plan['episodes'].extend(new_rows)
    plan['episodes'].sort(key=lambda r: r['seed'])
    crlf = b'\r\n' in PLAN.read_bytes()
    text = json.dumps(plan, ensure_ascii=False, indent=2) + '\n'
    if crlf:
        text = text.replace('\n', '\r\n')
    PLAN.write_bytes(text.encode('utf-8'))
    payload = {
        'batch': 'stage4-formal-v1',
        'registered': '2026-11-02',
        'rule': 'next contiguous block after dev; fixed before any run',
        'dev_seeds': DEV_SEEDS,
        'heldout': new_rows,
    }
    SEEDS_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n',
                         encoding='utf-8', newline='\n')
    print('\nwrote', PLAN, hashlib.sha256(PLAN.read_bytes().replace(b'\r\n', b'\n')).hexdigest(), '(LF-normalized)')
    print('wrote', SEEDS_OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
