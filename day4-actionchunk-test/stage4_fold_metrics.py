"""Stage 4 step 3: one frozen evaluator for single-step and H=4 fold episodes.

Recomputes ``l1_yaw_fold_geometry.fold_metrics_yaw`` from the saved snapshots of
a downloaded episode directory, so both action representations are scored by
exactly the same code.  This is an offline tool: no simulation, no model.

L1          : initial = 00_initial.npz      final = 06_final_3s.npz
              pick_index / yaw from result.json['fold_definition']
L2/L3       : initial = recovered.npz       final = final.npz
              pick_index from result.json['fold_metrics'], yaw from result['fold_yaw']

The inline metrics recorded by the episode script are cross-checked against the
recomputed ones; any disagreement is an error, not a warning.
"""
import argparse
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import l1_yaw_fold_geometry as geo  # noqa: E402

WIDTH = 0.2
EVALUATOR_MANIFEST = 'stage4-evaluator-files.json'


class SkipEpisode(Exception):
    """Episode cannot be scored under the frozen evaluator (e.g. legacy yaw)."""


def check_evaluator_identity():
    """Verify this evaluator's own files against the frozen manifest.

    The manifest holds the SHA256 of this script and of the geometry module, so
    a scored episode cannot drift with an edited evaluator: any mismatch is an
    error.  The script reads its own bytes from disk for the self-check.
    """
    manifest_path = os.path.join(HERE, EVALUATOR_MANIFEST)
    if not os.path.isfile(manifest_path):
        raise RuntimeError(f'{EVALUATOR_MANIFEST} missing; evaluator identity unknown')
    with open(manifest_path, encoding='utf-8') as handle:
        expected = json.load(handle)
    actual = {}
    for name, digest in expected.items():
        path = os.path.join(HERE, name)
        with open(path, 'rb') as handle:
            got = hashlib.sha256(handle.read()).hexdigest()
        if got != digest:
            raise RuntimeError(f'evaluator file changed: {name}')
        actual[name] = got
    return actual


def load_npz(path, key='vertices'):
    with np.load(path) as data:
        array = np.asarray(data[key], dtype=float)
    if array.shape != (441, 3):
        raise ValueError(f'{path}: expected (441, 3), got {array.shape}')
    if not np.isfinite(array).all():
        raise ValueError(f'{path}: non-finite vertices')
    return array


def local_points(result_dir):
    with np.load(os.path.join(result_dir, 'cloth_constructed.npz')) as data:
        points = np.asarray(data['points'], dtype=float)
    if points.shape != (441, 3):
        raise ValueError('unexpected constructed mesh')
    return points


def evaluate(result_dir, task, write=True):
    result_path = os.path.join(result_dir, 'result.json')
    result = json.load(open(result_path, encoding='utf-8'))
    if task == 'l1':
        initial = load_npz(os.path.join(result_dir, '00_initial.npz'))
        final = load_npz(os.path.join(result_dir, '06_final_3s.npz'))
        definition = result['fold_definition']
        if 'fold_yaw_rad' not in definition:
            raise SkipEpisode('fold_definition has no fold_yaw_rad (pre-yaw-aware run)')
        pick_index = int(definition['pick_index'])
        yaw = float(definition['fold_yaw_rad'])
        overhang = definition.get('fold_overhang_m')
        overhang = 0.0 if overhang is None else float(overhang)
        inline = result.get('fold_metrics', {})
        fold_edge = 'left'
    else:
        initial = load_npz(os.path.join(result_dir, 'recovered.npz'))
        final = load_npz(os.path.join(result_dir, 'final.npz'))
        pick_index = int(result['fold_metrics']['pick_index'])
        if result.get('fold_yaw') is None:
            raise SkipEpisode('no fold_yaw in result.json (pre-recovered-yaw run)')
        yaw = float(result['fold_yaw'])
        overhang = 0.0
        inline = result.get('fold_metrics', {})
        fold_edge = result.get('fold_edge')
        if fold_edge is None:
            fold_edge = 'left' if int(pick_index) == 210 else 'right'
    points = local_points(result_dir)
    lateral = [1., 0., 0.] if fold_edge == 'left' else [-1., 0., 0.]
    metrics = geo.fold_metrics_yaw(initial, final, points, pick_index, yaw, WIDTH,
                                  lateral_local=lateral)

    checks = {}
    if inline:
        for key, recomputed in (('crossed_fraction', 'moving_half_crossed_fraction'),
                                ('moving_count', 'moving_count')):
            if key in inline:
                checks[key] = {'inline': float(inline[key]),
                               'recomputed': float(metrics[recomputed]),
                               'delta': float(inline[key]) - float(metrics[recomputed])}
        extent = np.ptp(final, axis=0)
        checks['extent'] = {'inline': inline.get('extent'),
                            'recomputed': extent.tolist()}
        checks['z_p95'] = {'inline': inline.get('z_p95'),
                           'recomputed': float(np.percentile(final[:, 2], 95))}
        for key, tolerance in (('crossed_fraction', 1e-9), ('moving_count', 0)):
            if key in checks and abs(checks[key]['delta']) > tolerance:
                raise RuntimeError(f'{result_dir}: inline/recomputed {key} disagree')
        if 'extent' in checks and checks['extent']['inline'] is not None:
            if not np.allclose(checks['extent']['inline'], checks['extent']['recomputed'],
                               atol=1e-6, rtol=0):
                raise RuntimeError(f'{result_dir}: inline/recomputed extent disagree')
        if 'z_p95' in checks and checks['z_p95']['inline'] is not None:
            if abs(checks['z_p95']['inline'] - checks['z_p95']['recomputed']) > 1e-6:
                raise RuntimeError(f'{result_dir}: inline/recomputed z_p95 disagree')

    payload = {
        'task': task,
        'result_dir': os.path.abspath(result_dir),
        'seed': result.get('initial_case', {}).get('seed'),
        'level': result.get('initial_case', {}).get('level'),
        'execution_mode': result.get('execution_mode', 'single'),
        'call_horizons': result.get('call_horizons'),
        'evaluator_files': check_evaluator_identity(),
        'fold_edge': fold_edge,
        'passed': result.get('passed'),
        'formal_stage4_success': False,
        'fold_width_m': WIDTH,
        'fold_overhang_m': overhang,
        'pick_index': pick_index,
        'fold_yaw_rad': yaw,
        'metrics': metrics,
        'cross_check_vs_inline': checks,
        'scope': 'Particle projection proxies; not certified triangle overlap or material quality.',
    }
    if write:
        with open(os.path.join(result_dir, 'metrics_full.json'), 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1)
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', choices=('l1', 'l2l3'), required=True)
    parser.add_argument('--result-dir', action='append', required=True,
                        help='downloaded episode directory; repeat for several')
    parser.add_argument('--no-write', action='store_true')
    args = parser.parse_args()
    rows, skipped = [], []
    for directory in args.result_dir:
        try:
            rows.append(evaluate(directory, args.task, write=not args.no_write))
        except SkipEpisode as exc:
            skipped.append((directory, str(exc)))
    print(f"{'seed':>5} {'mode':>7} {'edge':>5} {'passed':>6} {'crossed':>8} "
          f"{'IoU':>6} {'align_mm':>9} {'refl_err_mm':>11} {'z_p95':>7}")
    for row in rows:
        m = row['metrics']
        print(f"{str(row['seed']):>5} {row['execution_mode']:>7} {str(row['fold_edge']):>5} "
              f"{str(row['passed']):>6} {m['moving_half_crossed_fraction']:8.3f} "
              f"{m['particle_occupancy_iou']:6.3f} "
              f"{1000 * m['symmetric_xy_alignment_mean_m']:9.2f} "
              f"{1000 * m['moving_material_reflected_target_mean_error_m']:11.2f} "
              f"{m['cloth_z_p95_m']:7.4f}")
    print(f'evaluated {len(rows)} episode(s) with the frozen fold_metrics_yaw')
    for directory, reason in skipped:
        print(f'skipped {directory}: {reason}')


if __name__ == '__main__':
    main()
