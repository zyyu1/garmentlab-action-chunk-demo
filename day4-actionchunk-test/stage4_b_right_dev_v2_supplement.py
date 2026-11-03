#!/usr/bin/env python3
"""Supplementary offline audit for the b-right-dev-v2 coverage runs.

The registered audit (stage4_b_right_dev_v2_audit.py) checks the variant/base
code identity, the 12 public actions, the held gate and recomputes fold metrics.
This supplement adds the checks the registered audit does not perform:

  * every initial directory listed in the v2 registry is present, and the
    SHA256 of result.json / initial_geometry.npz still matches the registry;
  * variant_identity.json initial_files hashes match the registry;
  * result.json initial_dir points at the registered initial directory;
  * per-attempt CSV, per-tier summary and a descriptive failure analysis.

It is purely offline.  A development `passed` is never upgraded to a formal
Stage 4 success.

Usage:
  python -I stage4_b_right_dev_v2_supplement.py \
      --results <download root> \
      --attempts <download root>/stage4-b-right-dev-v2-dev-v2/attempts.jsonl \
      --registry <download root>/stage4-b-right-dev-v2-initials.json \
      --manifest-dir <repo>/day4-actionchunk-test \
      --out <summary>/audit_supplement.json \
      --csv <summary>/attempts.csv
"""
import argparse
import csv
import json
import statistics
from pathlib import Path

import numpy as np

LABELS = ['rec_approach', 'rec_pick', 'rec_lift', 'rec_spread', 'rec_release',
          'fold_approach', 'fold_close', 'fold_arc45', 'fold_arc90',
          'fold_arc135', 'fold_place', 'fold_release']
WIDTH = 0.2
LATERAL_LOCAL = np.array([-1.0, 0.0, 0.0])


def sha256(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text())


def recompute(result_dir):
    with np.load(result_dir / 'final.npz') as data:
        final = np.asarray(data['vertices'], dtype=float)
    with np.load(result_dir / 'cloth_constructed.npz') as data:
        points = np.asarray(data['points'], dtype=float)
    result = load_json(result_dir / 'result.json')
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


def stats(values):
    values = [float(v) for v in values if v is not None]
    if not values:
        return None
    return {'n': len(values), 'min': min(values), 'median': statistics.median(values),
            'max': max(values)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', required=True)
    ap.add_argument('--attempts', required=True)
    ap.add_argument('--registry', required=True)
    ap.add_argument('--manifest-dir', default=str(Path(__file__).resolve().parent))
    ap.add_argument('--out')
    ap.add_argument('--csv')
    args = ap.parse_args()

    root = Path(args.results)
    mdir = Path(args.manifest_dir)
    config = load_json(mdir / 'stage4-b-right-dev-v2.json')
    manifest = load_json(mdir / 'square-recovery-fold-right-v2-files.json')
    base = load_json(mdir / 'square-recovery-fold-files.json')
    registry_doc = load_json(args.registry)
    registry = {r['seed']: r for r in registry_doc['seeds']}
    cases = {c['seed']: c['level'] for c in config['development_cases']}
    rows = [json.loads(line) for line in Path(args.attempts).read_text().splitlines()
            if line.strip()]

    checks = []
    attempts = []

    def check(prefix, suffix, ok, detail=''):
        checks.append({'check': f'{prefix}:{suffix}', 'ok': bool(ok), 'detail': str(detail)})

    for row in rows:
        seed = int(row['seed'])
        level = row['level']
        rec = {'seed': seed, 'level': level, 'execution': row.get('execution'),
               'status': 'error', 'script_passed': None, 'identity_ok': False,
               'checks_failed': [], 'errors': [], 'crossed': None,
               'extent': None, 'z_p95': None, 'held_accepted': None,
               'held_position_error_m': None, 'held_arm_speed_rad_s': None,
               'held_anchor_gap_m': None, 'action_count': None,
               'result_dir': '', 'initial_dir': '', 'initial_case': None,
               'recovery_metrics': None, 'fold_yaw': None,
               'register_seed': seed in registry}
        prefix = f'{seed}'
        before = len(checks)

        reg = registry.get(seed)
        idir = Path(row['initial_dir']) if row.get('initial_dir') else None
        rdir_name = Path(row['result_dir']).name if row.get('result_dir') else ''
        rdir = root / rdir_name if rdir_name else None
        rec['initial_dir'] = idir.name if idir else ''
        rec['result_dir'] = rdir_name

        check(prefix, 'registered_seed_level', cases.get(seed) == level
              and reg is not None and reg['level'] == level,
              f"config={cases.get(seed)} registry={reg['level'] if reg else None}")

        if reg is None:
            rec['errors'].append('seed missing from initial registry')
            attempts.append(rec)
            continue
        if idir is None or not idir.exists():
            check(prefix, 'initial_dir_downloaded', False, str(idir))
            rec['errors'].append('initial dir missing from download')
            attempts.append(rec)
            continue

        check(prefix, 'initial_registry_path', Path(reg['initial_dir']).name == idir.name,
              f"{Path(reg['initial_dir']).name} vs {idir.name}")
        for name, digest in reg['files'].items():
            p = idir / name
            check(prefix, f'initial_{name}_hash', p.exists() and sha256(p) == digest,
                  'missing' if not p.exists() else sha256(p)[:12])
        init_result_path = idir / 'result.json'
        if init_result_path.exists():
            ir = load_json(init_result_path)
            check(prefix, 'initial_passed', ir.get('passed') is True, str(ir.get('errors')))
            check(prefix, 'initial_seed_level',
                  ir['initial_case']['seed'] == seed
                  and ir['initial_case']['level'] == level,
                  f"{ir['initial_case']['seed']}/{ir['initial_case']['level']}")
            rec['initial_case'] = ir.get('initial_case')
            png = idir / 'initial.png'
            check(prefix, 'initial_png_480x640', png.exists() and png.stat().st_size > 0,
                  'missing' if not png.exists() else png.stat().st_size)

        if rdir is None or not (rdir / 'result.json').exists():
            check(prefix, 'result_downloaded', False, rdir_name or '<empty>')
            rec['errors'].append('result dir missing from download')
            attempts.append(rec)
            continue

        r = load_json(rdir / 'result.json')
        vid_path = rdir / 'variant_identity.json'
        vid = load_json(vid_path) if vid_path.exists() else None
        check(prefix, 'variant_identity_present', vid is not None, '')
        rec['script_passed'] = r.get('passed') is True
        rec['status'] = 'passed' if rec['script_passed'] else 'rejected'
        rec['errors'] = list(r.get('errors') or [])
        rec['action_count'] = r.get('action_count')
        rec['fold_yaw'] = r.get('fold_yaw')
        rec['initial_case'] = r.get('initial_case') or rec['initial_case']
        rec['recovery_metrics'] = r.get('recovery_metrics')

        check(prefix, 'result_seed_level',
              r['initial_case']['seed'] == seed and r['initial_case']['level'] == level,
              f"{r['initial_case']['seed']}/{r['initial_case']['level']}")
        check(prefix, 'result_initial_dir', Path(r['initial_dir']).name == idir.name,
              f"{Path(r['initial_dir']).name} vs {idir.name}")
        check(prefix, 'execution_single', r.get('execution_mode') == 'single',
              r.get('execution_mode'))
        check(prefix, 'fold_edge_right', r.get('fold_edge') == 'right', r.get('fold_edge'))
        check(prefix, '12_public_actions',
              r.get('action_count') == 12 and sum(r.get('call_horizons', [])) == 12,
              f"count={r.get('action_count')} sum={sum(r.get('call_horizons', []))}")
        check(prefix, 'labels', r.get('action_labels') == LABELS, '')
        check(prefix, 'code_files_equal_base', r.get('code_files') == base,
              f"{len(r.get('code_files') or {})}")
        check(prefix, 'formal_flag_false', r.get('formal_day4_success') is False, '')

        if vid is not None:
            check(prefix, 'variant_code_files_equal_manifest',
                  vid.get('code_files') == manifest,
                  f"{len(vid.get('code_files') or {})}")
            check(prefix, 'variant_base_code_files_equal', vid.get('base_code_files') == base,
                  f"{len(vid.get('base_code_files') or {})}")
            check(prefix, 'variant_config_matches', vid.get('config') == config, '')
            check(prefix, 'variant_fold_edge', vid.get('fold_edge') == 'right', '')
            check(prefix, 'variant_execution', vid.get('execution_mode') == 'single', '')
            check(prefix, 'variant_not_formal', vid.get('formal_stage4_success') is False, '')
            check(prefix, 'variant_initial_files',
                  vid.get('initial_files') == reg['files'],
                  json.dumps(vid.get('initial_files'), sort_keys=True)[:80])

        held = r.get('fold_held_check') or {}
        rec['held_accepted'] = held.get('accepted')
        rec['held_position_error_m'] = held.get('position_error_m')
        rec['held_arm_speed_rad_s'] = held.get('arm_speed_rad_s')
        rec['held_anchor_gap_m'] = held.get('anchor_max_gap_m', held.get('anchor_gap_max_m'))
        check(prefix, 'held_gate', held.get('accepted') is True,
              f"err={held.get('position_error_m')}")

        fm = r.get('fold_metrics') or {}
        rec['crossed'] = fm.get('crossed_fraction')
        rec['extent'] = fm.get('extent')
        rec['z_p95'] = fm.get('z_p95')
        if (rdir / 'final.npz').exists() and (rdir / 'cloth_constructed.npz').exists():
            try:
                rcm = recompute(rdir)
                ok = all(close(rcm[k], fm.get(k)) for k in rcm)
                check(prefix, 'metrics_recompute_match', ok, '')
            except Exception as exc:  # noqa: BLE001 - record, never crash the audit
                check(prefix, 'metrics_recompute_match', False, repr(exc))
        else:
            check(prefix, 'metrics_files_present', False, 'final.npz/cloth_constructed.npz missing')

        rec['identity_ok'] = all(c['ok'] for c in checks[before:])
        rec['checks_failed'] = [c['check'] for c in checks[before:] if not c['ok']]
        attempts.append(rec)

    # ---- per-tier summary -------------------------------------------------
    summary = {}
    for level in ('perturbed', 'crumpled'):
        tier = [a for a in attempts if a['level'] == level]
        counts = {s: sum(1 for a in tier if a['status'] == s)
                  for s in ('passed', 'rejected', 'error')}
        attempted = len(tier)
        summary[level] = {
            'registered': sum(1 for s, l in cases.items() if l == level),
            'attempted': attempted,
            'passed': counts['passed'],
            'rejected': counts['rejected'],
            'error': counts['error'],
            'development_pass_rate': (counts['passed'] / attempted) if attempted else None,
            'identity_ok': sum(1 for a in tier if a['identity_ok']),
            'held_gate_pass': sum(1 for a in tier if a['held_accepted'] is True),
            'crossed': stats([a['crossed'] for a in tier]),
            'z_p95': stats([a['z_p95'] for a in tier]),
            'extent_x': stats([a['extent'][0] for a in tier if a['extent']]),
            'extent_y': stats([a['extent'][1] for a in tier if a['extent']]),
            'seeds': [a['seed'] for a in tier],
            'missing_seeds': sorted(set(s for s, l in cases.items() if l == level)
                                    - {a['seed'] for a in tier}),
        }

    # ---- descriptive failure analysis ------------------------------------
    failure_analysis = []
    for level in ('perturbed', 'crumpled'):
        tier = [a for a in attempts if a['level'] == level]
        for a in tier:
            if a['status'] == 'passed':
                continue
            ic = a.get('initial_case') or {}
            trans = ic.get('translation_xy_m') or [0.0, 0.0]
            strips = ic.get('strips') or []
            failure_analysis.append({
                'seed': a['seed'], 'level': level, 'status': a['status'],
                'errors': a['errors'],
                'crossed': a['crossed'], 'extent': a['extent'], 'z_p95': a['z_p95'],
                'held_accepted': a['held_accepted'],
                'held_position_error_m': a['held_position_error_m'],
                'held_arm_speed_rad_s': a['held_arm_speed_rad_s'],
                'held_anchor_gap_m': a['held_anchor_gap_m'],
                'translation_norm_m': float(np.linalg.norm(trans)),
                'abs_yaw_rad': abs(float(ic.get('yaw_rad') or 0.0)),
                'strip_width_m': strips[0].get('width_m') if strips else None,
                'checks_failed': a['checks_failed'],
                'result_dir': a['result_dir'],
            })

    # pass/fail parameter comparison per tier (descriptive only, n is small)
    comparisons = {}
    for level in ('perturbed', 'crumpled'):
        tier = [a for a in attempts if a['level'] == level]
        for status in ('passed', 'not_passed'):
            sel = tier if status == 'passed' else []
            if status == 'passed':
                sel = [a for a in tier if a['status'] == 'passed']
            else:
                sel = [a for a in tier if a['status'] != 'passed']
            vals_trans, vals_yaw, vals_width = [], [], []
            for a in sel:
                ic = a.get('initial_case') or {}
                trans = ic.get('translation_xy_m') or [0.0, 0.0]
                vals_trans.append(float(np.linalg.norm(trans)))
                vals_yaw.append(abs(float(ic.get('yaw_rad') or 0.0)))
                strips = ic.get('strips') or []
                if strips:
                    vals_width.append(float(strips[0].get('width_m')))
            comparisons.setdefault(level, {})[status] = {
                'n': len(sel),
                'translation_norm_m': stats(vals_trans),
                'abs_yaw_rad': stats(vals_yaw),
                'strip_width_m': stats(vals_width),
            }

    failed = [c for c in checks if not c['ok']]
    overall = {
        'registered': len(cases),
        'attempted': len(attempts),
        'passed': sum(1 for a in attempts if a['status'] == 'passed'),
        'rejected': sum(1 for a in attempts if a['status'] == 'rejected'),
        'error': sum(1 for a in attempts if a['status'] == 'error'),
        'identity_ok': sum(1 for a in attempts if a['identity_ok']),
        'missing_seeds': sorted(set(cases) - {a['seed'] for a in attempts}),
        'checks': len(checks), 'failed_checks': len(failed),
        'failed_check_names': [c['check'] for c in failed],
    }
    doc = {
        'variant': 'b-right-dev-v2',
        'development_only': True,
        'formal_stage4_success': False,
        'config_sha256': sha256(mdir / 'stage4-b-right-dev-v2.json'),
        'variant_manifest_sha256': sha256(mdir / 'square-recovery-fold-right-v2-files.json'),
        'base_manifest_sha256': sha256(mdir / 'square-recovery-fold-files.json'),
        'registry_sha256': sha256(args.registry),
        'attempts_sha256': sha256(args.attempts),
        'overall': overall,
        'per_tier': summary,
        'failure_analysis': failure_analysis,
        'pass_fail_parameter_comparison': comparisons,
        'attempts': attempts,
        'checks': checks,
    }

    for c in failed:
        print(('FAIL ' if not c['ok'] else 'PASS ') + c['check'] +
              ((' | ' + c['detail']) if c['detail'] else ''))
    print()
    print(f"{'seed':>5} {'level':9s} {'status':8s} {'crossed':>8s} "
          f"{'extent_x':>8s} {'extent_y':>8s} {'z_p95':>8s} held checks_failed")
    for a in attempts:
        ext = a['extent'] or [float('nan')] * 3
        print(f"{a['seed']:>5} {a['level']:9s} {a['status']:8s} "
              f"{a['crossed'] if a['crossed'] is not None else float('nan'):8.3f} "
              f"{ext[0]:8.4f} {ext[1]:8.4f} "
              f"{a['z_p95'] if a['z_p95'] is not None else float('nan'):8.5f} "
              f"{str(a['held_accepted']):5s} {len(a['checks_failed'])}")
    print()
    for level, s in summary.items():
        rate = 'n/a' if s['development_pass_rate'] is None else f"{s['development_pass_rate']:.3f}"
        print(f"TIER {level:9s} registered={s['registered']} attempted={s['attempted']} "
              f"passed={s['passed']} rejected={s['rejected']} error={s['error']} "
              f"rate={rate} identity_ok={s['identity_ok']}")
    print(f"OVERALL {json.dumps(overall)}")
    print('NOTE development_only=true; formal Stage 4 success remains 0')

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(doc, indent=2) + '\n')
        print('AUDIT_JSON', args.out)
    if args.csv:
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        fields = ['seed', 'level', 'status', 'script_passed', 'identity_ok', 'crossed',
                  'extent_x', 'extent_y', 'extent_z', 'z_p95', 'held_accepted',
                  'held_position_error_m', 'held_arm_speed_rad_s', 'held_anchor_gap_m',
                  'action_count', 'translation_x', 'translation_y', 'translation_norm_m',
                  'yaw_rad', 'abs_yaw_rad', 'strip_edge', 'strip_width_m',
                  'result_dir', 'errors', 'checks_failed']
        import math
        with open(args.csv, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            for a in attempts:
                ic = a.get('initial_case') or {}
                trans = ic.get('translation_xy_m') or [None, None]
                strips = ic.get('strips') or []
                ext = a['extent'] or [None, None, None]
                writer.writerow({
                    'seed': a['seed'], 'level': a['level'], 'status': a['status'],
                    'script_passed': a['script_passed'], 'identity_ok': a['identity_ok'],
                    'crossed': a['crossed'],
                    'extent_x': ext[0], 'extent_y': ext[1], 'extent_z': ext[2],
                    'z_p95': a['z_p95'], 'held_accepted': a['held_accepted'],
                    'held_position_error_m': a['held_position_error_m'],
                    'held_arm_speed_rad_s': a['held_arm_speed_rad_s'],
                    'held_anchor_gap_m': a['held_anchor_gap_m'],
                    'action_count': a['action_count'],
                    'translation_x': trans[0], 'translation_y': trans[1],
                    'translation_norm_m': (math.hypot(trans[0], trans[1])
                                           if None not in trans else None),
                    'yaw_rad': ic.get('yaw_rad'), 'abs_yaw_rad': abs(ic.get('yaw_rad') or 0.0),
                    'strip_edge': strips[0].get('edge') if strips else None,
                    'strip_width_m': strips[0].get('width_m') if strips else None,
                    'result_dir': a['result_dir'],
                    'errors': ' | '.join(a['errors']),
                    'checks_failed': ' | '.join(a['checks_failed']),
                })
        print('AUDIT_CSV', args.csv)
    return 1 if (failed or overall['missing_seeds']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
