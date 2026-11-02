#!/usr/bin/env python3
"""Offline audit of the b-right-dev-v2 coverage runs.

Usage:
  python -I stage4_b_right_dev_v2_audit.py --results <dir> --attempts <attempts.jsonl>
      [--out summary.json]

Each attempt row is mapped to <results>/<basename of result_dir>.  The audit
checks the 23-entry variant identity, the 21-entry base identity, the 12 public
actions, the held gate, and recomputes the fold metrics from final.npz.
It reports per-seed outcomes and never upgrades a development pass into a
formal Stage 4 success.
"""
import argparse
import json
from pathlib import Path

import numpy as np

LABELS = ['rec_approach', 'rec_pick', 'rec_lift', 'rec_spread', 'rec_release',
          'fold_approach', 'fold_close', 'fold_arc45', 'fold_arc90',
          'fold_arc135', 'fold_place', 'fold_release']
WIDTH = 0.2
LATERAL_LOCAL = np.array([-1.0, 0.0, 0.0])


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
    return {'moving_count': int(moving.sum()), 'crossed_fraction': crossed,
            'extent': np.ptp(final, axis=0).tolist(),
            'z_p95': float(np.percentile(final[:, 2], 95))}


def close(a, b, tol=1e-6):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return a.shape == b.shape and bool(np.allclose(a, b, rtol=0, atol=tol))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', required=True)
    ap.add_argument('--attempts', required=True)
    ap.add_argument('--manifest-dir', default=str(Path(__file__).resolve().parent))
    ap.add_argument('--out')
    args = ap.parse_args()

    root = Path(args.results)
    mdir = Path(args.manifest_dir)
    config = json.loads((mdir / 'stage4-b-right-dev-v2.json').read_text())
    manifest = json.loads((mdir / 'square-recovery-fold-right-v2-files.json').read_text())
    base = json.loads((mdir / 'square-recovery-fold-files.json').read_text())
    cases = {c['seed']: c['level'] for c in config['development_cases']}

    rows = [json.loads(line) for line in Path(args.attempts).read_text().splitlines() if line.strip()]
    checks = []
    outcomes = []
    seen = set()
    for row in rows:
        seed = row['seed']
        if seed in seen:
            checks.append({'check': f'{seed}:duplicate_attempt_row', 'ok': False,
                           'detail': 'seed recorded twice in attempts.jsonl'})
        seen.add(seed)
        name = Path(row['result_dir']).name if row['result_dir'] else ''
        d = root / name
        prefix = f'{seed}/{name}'
        if not name or not (d / 'result.json').exists():
            checks.append({'check': f'{prefix}:result_downloaded', 'ok': False,
                           'detail': row.get('result_dir', '')})
            outcomes.append({'seed': seed, 'level': row['level'], 'status': 'error'})
            continue
        r = json.loads((d / 'result.json').read_text())
        vid = json.loads((d / 'variant_identity.json').read_text())

        def check(suffix, ok, detail=''):
            checks.append({'check': f'{prefix}:{suffix}', 'ok': bool(ok), 'detail': detail})

        check('registered_seed_level',
              cases.get(seed) == row['level'] == r['initial_case']['level'],
              f"{row['level']}/{r['initial_case']['level']}")
        check('execution_mode', r['execution_mode'] == 'single', r['execution_mode'])
        check('fold_edge_right', r['fold_edge'] == 'right', r['fold_edge'])
        check('12_public_actions',
              r['action_count'] == 12 and sum(r['call_horizons']) == 12,
              f"count={r['action_count']} sum={sum(r['call_horizons'])}")
        check('labels', r['action_labels'] == LABELS, '')
        check('code_files_equal_base', r['code_files'] == base, f"{len(r['code_files'])}")
        check('variant_code_files_equal_right_v2', vid['code_files'] == manifest, f"{len(vid['code_files'])}")
        check('variant_config_matches', vid['config'] == config, '')
        check('variant_not_formal', vid['formal_stage4_success'] is False, '')
        check('held_gate', r['fold_held_check']['accepted'] is True,
              f"err={r['fold_held_check']['position_error_m']:.4f}")
        rec = recompute(d)
        check('metrics_recompute_match',
              all(close(rec[k], r['fold_metrics'][k]) for k in rec), '')
        check('passed', r['passed'] is True, str(r['errors']))

        outcomes.append({'seed': seed, 'level': row['level'],
                         'status': 'passed' if r['passed'] else 'rejected',
                         'crossed': r['fold_metrics']['crossed_fraction'],
                         'extent': r['fold_metrics']['extent'],
                         'z_p95': r['fold_metrics']['z_p95'],
                         'held_gate': r['fold_held_check']['accepted'],
                         'result_dir': name})

    missing = sorted(set(cases) - seen)
    failed = [c for c in checks if not c['ok']]
    for c in checks:
        print(('PASS ' if c['ok'] else 'FAIL ') + c['check'] +
              ((' | ' + c['detail']) if c['detail'] else ''))
    print()
    for o in outcomes:
        if o['status'] == 'error':
            print(f"{o['seed']} {o['level']:9s} ERROR")
        else:
            ext = o['extent']
            print(f"{o['seed']} {o['level']:9s} {o['status']:8s} "
                  f"crossed={o['crossed']:.3f} extent={ext[0]:.4f}x{ext[1]:.4f}x{ext[2]:.4f} "
                  f"z_p95={o['z_p95']:.5f} held={o['held_gate']}")
    counts = {s: sum(1 for o in outcomes if o['status'] == s)
              for s in ('passed', 'rejected', 'error')}
    summary = {'registered': len(cases), 'attempted': len(outcomes),
               'missing_seeds': missing, 'counts': counts,
               'checks': len(checks), 'failed_checks': len(failed),
               'failed_check_names': [c['check'] for c in failed],
               'outcomes': outcomes}
    print(f"\nSUMMARY registered={len(cases)} attempted={len(outcomes)} "
          f"passed={counts['passed']} rejected={counts['rejected']} error={counts['error']} "
          f"missing={missing} checks={len(checks)} failed={len(failed)}")
    print('NOTE development_only=true; formal Stage 4 success remains 0')
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, indent=2) + '\n')
        print('AUDIT_JSON', args.out)
    return 1 if (failed or missing) else 0


if __name__ == '__main__':
    raise SystemExit(main())
