"""Offline per-task summary of downloaded Stage 4 folding results.

Reads only `result.json` from downloaded run directories; never imports or
executes run code. Keeps two tasks separate because they have different frozen
fold definitions (L1 overfold vs L2/L3 nominal 20/20) and reports the
single/arc4 split inside each task.

Usage:
    python -I stage4_task_report.py --root results --root ../../thesis/day4-actionchunk-test/results \
        --out results/STAGE4_PER_TASK_20261102/task_report.json
"""

import argparse
import json
import sys
from pathlib import Path

TASK_PREFIX = {'l1': 'day4-l1-xfold-yaw-aware-', 'l2l3': 'day4-recovery-fold-'}

# Fold-boundary metrics differ between the two scripts; missing keys stay None.
METRIC_KEYS = {
    'l1': {'crossed': 'moving_half_crossed_fraction',
           'iou': 'particle_occupancy_iou',
           'align': 'symmetric_xy_alignment_mean_m',
           'reflected': 'moving_material_reflected_target_mean_error_m',
           'z': 'cloth_z_p95_m'},
    'l2l3': {'crossed': 'crossed_fraction',
             'iou': None,
             'align': None,
             'reflected': None,
             'z': 'z_p95'},
}


def classify_failure(result, crossed, z_p95, extent):
    errors = ' | '.join(str(e) for e in result.get('errors') or [])
    if result.get('passed'):
        return 'pass'
    if 'did not cross the fold line' in errors:
        flat = (crossed is not None and crossed < 0.5
                and z_p95 is not None and z_p95 < 0.02
                and extent is not None and max(extent[:2]) > 0.40)
        return 'release_rebound_to_flat' if flat else 'crossed_gate_failed'
    return 'other_failure'


def fold_edge(result, first_target_x):
    """Explicit engine field when present; otherwise infer from the first fold target.

    The legacy combined script had no --fold-edge option and always folded the
    left side. Its results only omit the field, so leftover runs are marked
    "left(inferred)" rather than silently treated as explicit. The inference is
    cross-checked against an explicit left run on the same seed in the report.
    """
    edge = result.get('fold_edge')
    if edge:
        return edge, 'field'
    if first_target_x is None:
        return None, 'absent'
    return ('left(inferred)' if first_target_x < 0 else 'right(inferred)'), 'inferred'


def summarize_dir(path, task):
    result = json.loads((path / 'result.json').read_text(encoding='utf-8'))
    metrics = result.get('fold_metrics') or {}
    keys = METRIC_KEYS[task]
    crossed = metrics.get(keys['crossed']) if keys['crossed'] else None
    z_p95 = metrics.get(keys['z']) if keys['z'] else None
    extent = metrics.get('extent')
    first_x = None
    for record in result.get('records') or []:
        if record.get('label') == 'fold_targets' and record.get('ee_targets'):
            first_x = float(record['ee_targets'][0][0])
            break
    edge, edge_source = fold_edge(result, first_x)
    held = result.get('held_check') or result.get('fold_held_check') or {}
    code = result.get('code_files') or {}
    return {
        'dir': path.name,
        'task': task,
        'seed': (result.get('initial_case') or {}).get('seed'),
        'level': (result.get('initial_case') or {}).get('level'),
        'fold_edge': edge,
        'fold_edge_source': edge_source,
        'mode': result.get('execution_mode'),  # None => pre---execution script
        'code_identity': 'frozen' if code else 'legacy',
        'code_file_count': len(code),
        'action_count': result.get('action_count'),
        'call_horizons': result.get('call_horizons'),
        'overhang_m': (result.get('fold_definition') or {}).get('fold_overhang_m'),
        'passed': bool(result.get('passed')),
        'formal_success': bool(result.get('formal_day4_success')
                               or result.get('fold_success_accepted')),
        'crossed': crossed,
        'iou': metrics.get(keys['iou']) if keys['iou'] else None,
        'align_m': metrics.get(keys['align']) if keys['align'] else None,
        'reflected_m': metrics.get(keys['reflected']) if keys['reflected'] else None,
        'z_p95_m': z_p95,
        'extent_m': extent,
        'held_accepted': held.get('accepted'),
        'held_position_error_m': held.get('position_error_m'),
        'failure': classify_failure(result, crossed, z_p95, extent),
        'errors': result.get('errors') or [],
    }


def collect(roots):
    rows, skipped = [], []
    for root in roots:
        if not root.is_dir():
            skipped.append({'dir': str(root), 'reason': 'root_missing'})
            continue
        for task, prefix in TASK_PREFIX.items():
            for path in sorted(root.glob(prefix + '*')):
                if not path.is_dir():
                    continue
                if not (path / 'result.json').exists():
                    skipped.append({'dir': str(path), 'reason': 'no_result_json'})
                    continue
                rows.append(summarize_dir(path, task))
    return rows, skipped


def group(rows):
    out = {}
    for row in rows:
        key = (row['task'], row['mode'] or 'single(legacy)', row['code_identity'])
        out.setdefault(key, []).append(row)
    return out


def fmt(value, digits=4):
    return 'n/a' if value is None else f'{value:.{digits}f}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', required=True,
                    help='directory containing downloaded run directories')
    ap.add_argument('--out', required=True, help='JSON output path')
    args = ap.parse_args()

    rows, skipped = collect([Path(r) for r in args.root])
    rows.sort(key=lambda r: (r['task'], r['seed'] if r['seed'] is not None else -1,
                             r['dir']))

    print('task seed level edge mode code passed crossed iou align z_p95 extent actions dir')
    for r in rows:
        extent = 'n/a' if not r['extent_m'] else \
            f"{r['extent_m'][0]:.4f}x{r['extent_m'][1]:.4f}"
        print(f"{r['task']} {r['seed']} {r['level']} {r['fold_edge']} "
              f"{r['mode'] or 'single(legacy)'} {r['code_identity']} "
              f"{r['passed']} {fmt(r['crossed'], 3)} {fmt(r['iou'])} "
              f"{fmt(r['align_m'])} {fmt(r['z_p95_m'])} {extent} "
              f"{r['action_count']} {r['dir']}")

    print('\ncounts by task/mode/code_identity:')
    for key, group_rows in sorted(group(rows).items(), key=lambda kv: str(kv[0])):
        passed = sum(1 for r in group_rows if r['passed'])
        seeds = sorted({(r['seed'], r['fold_edge']) for r in group_rows},
                       key=lambda s: (s[0] is None, s[0]))
        seeds_passed = sorted({(r['seed'], r['fold_edge']) for r in group_rows
                               if r['passed']}, key=lambda s: (s[0] is None, s[0]))
        print(f'  {key}: attempts {passed}/{len(group_rows)}, '
              f'seeds_with_at_least_one_pass {len(seeds_passed)}/{len(seeds)} {seeds}')

    if skipped:
        print('\nskipped:')
        for item in skipped:
            print(' ', item['dir'], item['reason'])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'rows': rows, 'skipped': skipped},
                              ensure_ascii=False, indent=1), encoding='utf-8')
    print('\nwrote', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
