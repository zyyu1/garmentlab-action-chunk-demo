#!/usr/bin/env python3
"""Offline audit of the b-right-dev-v1 development runs.

Checks each downloaded result directory against the registered variant manifest,
recomputes the fold metrics from final.npz, compares single/arc4 action traces,
and compares the repeated 4300 single attempt with its first run.

Usage:
  python -I stage4_b_right_audit.py --results <dir holding the result dirs> [--out audit.json]
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

LABELS = ['rec_approach', 'rec_pick', 'rec_lift', 'rec_spread', 'rec_release',
          'fold_approach', 'fold_close', 'fold_arc45', 'fold_arc90',
          'fold_arc135', 'fold_place', 'fold_release']
WIDTH = 0.2
LATERAL_LOCAL = np.array([-1.0, 0.0, 0.0])

DIRS = [
    ('day4-recovery-fold-20261103-023749-213160', 4200, 'single', 'matrix'),
    ('day4-recovery-fold-20261103-025355-106410', 4200, 'arc4', 'matrix'),
    ('day4-recovery-fold-20261103-031351-818421', 4300, 'single', 'matrix'),
    ('day4-recovery-fold-20261103-035003-534230', 4300, 'arc4', 'matrix'),
    ('day4-recovery-fold-20261103-031535-711404', 4300, 'single', 'duplicate'),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def recompute(result_dir):
    with np.load(result_dir / 'final.npz') as data:
        final = np.asarray(data['vertices'], dtype=float)
    with np.load(result_dir / 'cloth_constructed.npz') as data:
        points = np.asarray(data['points'], dtype=float)
    result = json.loads((result_dir / 'result.json').read_text())
    fold = next(r for r in result['records'] if 'pick_world' in r)
    pick = np.asarray(fold['pick_world'], dtype=float)
    yaw = float(result['fold_yaw'])
    R = np.array([[np.cos(yaw), -np.sin(yaw), 0.0],
                  [np.sin(yaw), np.cos(yaw), 0.0],
                  [0.0, 0.0, 1.0]])
    lateral = R @ LATERAL_LOCAL
    fold_local = points[int(fold['pick_index'])]
    moving = points[:, 0] > fold_local[0] - WIDTH
    crossed = float((((final[moving] - pick) @ lateral) > WIDTH).mean())
    return {
        'moving_count': int(moving.sum()),
        'crossed_fraction': crossed,
        'extent': np.ptp(final, axis=0).tolist(),
        'z_p95': float(np.percentile(final[:, 2], 95)),
    }, final


def close(a, b, tol=1e-9):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return a.shape == b.shape and bool(np.allclose(a, b, rtol=0, atol=tol))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', required=True)
    ap.add_argument('--manifest-dir', default=str(Path(__file__).resolve().parent))
    ap.add_argument('--out')
    args = ap.parse_args()

    root = Path(args.results)
    mdir = Path(args.manifest_dir)
    right = json.loads((mdir / 'square-recovery-fold-right-v1-files.json').read_text())
    base = json.loads((mdir / 'square-recovery-fold-files.json').read_text())
    config = json.loads((mdir / 'stage4-b-right-dev-v1.json').read_text())
    plan = json.loads((mdir / 'square-initial-plan.json').read_text())
    plan_rows = {r['seed']: r for r in plan['episodes']}

    checks = []

    def check(name, ok, detail=''):
        checks.append({'check': name, 'ok': bool(ok), 'detail': detail})

    check('base_manifest_raw_sha_matches_config',
          sha(mdir / 'square-recovery-fold-files.json') == config['base_manifest_sha256'],
          config['base_manifest_sha256'][:12])
    check('right_manifest_entry_count', len(right) == 23, str(len(right)))
    check('right_manifest_superset_of_base',
          all(right.get(k) == v for k, v in base.items()),
          'shared entries identical')

    results = {}
    finals = {}
    for name, seed, mode, role in DIRS:
        d = root / name
        r = json.loads((d / 'result.json').read_text())
        vid = json.loads((d / 'variant_identity.json').read_text())
        results[name] = r
        prefix = f'{name}[{seed}/{mode}]'

        check(f'{prefix}:passed', r['passed'] is True, str(r['errors']))
        check(f'{prefix}:fold_edge_right', r['fold_edge'] == 'right', r['fold_edge'])
        check(f'{prefix}:execution_mode', r['execution_mode'] == mode, r['execution_mode'])
        check(f'{prefix}:12_public_actions',
              r['action_count'] == 12 and sum(r['call_horizons']) == 12,
              f"count={r['action_count']} sum={sum(r['call_horizons'])}")
        check(f'{prefix}:labels', r['action_labels'] == LABELS, '')
        check(f'{prefix}:code_files_equal_base_manifest', r['code_files'] == base,
              f"{len(r['code_files'])} entries")
        check(f'{prefix}:variant_code_files_equal_right_manifest',
              vid['code_files'] == right, f"{len(vid['code_files'])} entries")
        check(f'{prefix}:variant_base_code_files_equal_base_manifest',
              vid['base_code_files'] == base, '')
        check(f'{prefix}:variant_config_matches_local', vid['config'] == config, '')
        check(f'{prefix}:variant_not_formal', vid['formal_stage4_success'] is False, '')
        check(f'{prefix}:held_gate', r['fold_held_check']['accepted'] is True,
              f"err={r['fold_held_check']['position_error_m']:.4f} "
              f"gap={r['fold_held_check']['anchor_gap_max_m']:.4f}")

        plan_row = plan_rows[seed]
        init = r['initial_case']
        check(f'{prefix}:initial_case_registered',
              (init['level'] == plan_row['level']
               and close(init['translation_xy_m'], plan_row['translation_xy_m'])
               and abs(init['yaw_rad'] - plan_row['yaw_rad']) < 1e-12
               and init['settle_steps'] == plan_row['settle_steps']),
              f"seed {init['seed']} {init['level']}")

        recomputed, final = recompute(d)
        finals[name] = final
        reported = r['fold_metrics']
        same = all(close(recomputed[k], reported[k], 1e-6) for k in recomputed)
        check(f'{prefix}:metrics_recompute_match', same,
              json.dumps({k: (reported[k] if not isinstance(reported[k], list)
                              else [round(x, 6) for x in reported[k]])
                          for k in recomputed}))

    def actions(name):
        return [(a['label'], a['target_pose'], a['command']) for a in results[name]['actions']]

    for seed, a, b in [(4200, DIRS[0][0], DIRS[1][0]), (4300, DIRS[2][0], DIRS[3][0])]:
        check(f'pair[{seed}]:public_action_trace_identical', actions(a) == actions(b),
              'label/target_pose/command over 12 actions')
        fa = results[a]['fold_metrics']
        fb = results[b]['fold_metrics']
        check(f'pair[{seed}]:fold_metrics_identical', fa == fb, json.dumps(fa))
        check(f'pair[{seed}]:final_vertices_identical',
              close(finals[a], finals[b], 0), 'exact')

    dup_first, dup_second = DIRS[2][0], DIRS[4][0]
    check('duplicate[4300]:public_action_trace_identical',
          actions(dup_first) == actions(dup_second), '')
    check('duplicate[4300]:final_vertices_identical',
          close(finals[dup_first], finals[dup_second], 0), 'exact')
    volatile = sorted(k for k in results[dup_first]
                      if results[dup_first][k] != results[dup_second][k])
    check('duplicate[4300]:no_metric_drift', volatile == [] or set(volatile) <= {
        'initial_dir', 'final_image'},
        'differing keys: ' + ', '.join(volatile))

    failed = [c for c in checks if not c['ok']]
    for c in checks:
        print(('PASS ' if c['ok'] else 'FAIL ') + c['check'] +
              ((' | ' + c['detail']) if c['detail'] else ''))
    print(f'\nAUDIT_SUMMARY checks={len(checks)} failed={len(failed)}')
    summary = {'checks': checks, 'failed': len(failed),
               'fold_metrics': {n: results[n]['fold_metrics'] for n, _, _, _ in DIRS}}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, indent=2) + '\n')
        print('AUDIT_JSON', args.out)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
