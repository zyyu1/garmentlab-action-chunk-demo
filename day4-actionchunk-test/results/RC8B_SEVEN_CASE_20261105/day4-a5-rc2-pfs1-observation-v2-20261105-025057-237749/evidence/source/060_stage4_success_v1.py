"""Offline, fail-closed success criteria. No simulator or legacy result mutation.

Contract and rationale: ../STAGE4_SUCCESS_CRITERIA_V1.md.
Existing metrics stay byte-for-byte unchanged; this is a separately versioned layer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from l1_yaw_fold_geometry import fold_metrics_yaw

HERE = Path(__file__).resolve().parent
CONFIG = HERE / 'stage4-success-v1.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def identity():
    manifest = json.loads((HERE / 'stage4-success-v1-files.json').read_text())
    for name, expected in manifest.items():
        if digest(HERE / name) != expected:
            raise ValueError('Evaluator/config identity mismatch: ' + name)
    return manifest


def config():
    return json.loads(CONFIG.read_text())


def array(value, shape):
    a = np.asarray(value, dtype=float)
    if a.shape != shape or not np.isfinite(a).all():
        raise ValueError('Expected finite array ' + str(shape))
    return a


def geometry(initial, final, points, pick_index, yaw, edge, task, floor_z=0.):
    cfg = config(); limits = cfg['tasks'][task]; common = cfg['common_geometry']
    a = array(initial, (441, 3)); b = array(final, (441, 3)); lp = array(points, (441, 3))
    if edge not in limits['edges'] or type(pick_index) is not int or not 0 <= pick_index < 441:
        raise ValueError('Invalid task/edge/pick')
    if not np.isfinite([yaw, floor_z]).all():
        raise ValueError('Invalid frame')
    # Material identity is fixed by the constructed regular 21x21 mesh.
    xs = np.unique(np.round(lp[:, 0], 6)); ys = np.unique(np.round(lp[:, 1], 6))
    if len(xs) != 21 or len(ys) != 21 or not np.allclose(np.diff(xs), .02) or not np.allclose(np.diff(ys), .02):
        raise ValueError('Expected 0.4m regular material grid')
    if len(np.unique(np.round(lp[:, :2], 6), axis=0)) != 441:
        raise ValueError('Duplicate material coordinates')
    sign = 1 if edge == 'left' else -1
    u = sign * lp[:, 0]
    if abs(u[pick_index] - u.min()) > 1e-6:
        raise ValueError('Pick must be on moving free edge')
    moving = u < u[pick_index] + .2 - 1e-6
    free = np.abs(u - u.min()) < 1e-6
    far = np.abs(u - u.max()) < 1e-6
    c, s = np.cos(yaw), np.sin(yaw)
    rotation = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    q = (b - a[pick_index]) @ rotation
    m = fold_metrics_yaw(a, b, lp, pick_index, yaw, .2, [sign, 0, 0])
    # Robust crossing excludes exactly the crease; legacy metric retained above.
    m['crossed_fraction_tolerant'] = float((sign*q[moving, 0] >= .2 - 1e-6).mean())
    m['stationary_drift_mean_m'] = float(np.linalg.norm(b[~moving] - a[~moving], axis=1).mean())
    m['free_edge_overrun_m'] = float(sign*(q[free, 0].mean() - q[far, 0].mean()))
    m['free_edge_height_p90_m'] = float(np.percentile(b[free, 2] - floor_z, 90))
    m['fold_extent_m'], m['tangent_extent_m'] = map(float, np.ptp(q[:, :2], axis=0))
    m['height_p95_m'] = float(np.percentile(b[:, 2] - floor_z, 95))
    m['height_min_m'] = float(b[:, 2].min() - floor_z)
    m['height_max_m'] = float(b[:, 2].max() - floor_z)
    checks = {
        'crossed': m['crossed_fraction_tolerant'] >= common['crossed_min'],
        'overlap': m['particle_occupancy_iou'] >= limits['iou_min'],
        'alignment': m['symmetric_xy_alignment_mean_m'] <= limits['alignment_max_m'],
        'material_target': m['moving_material_reflected_target_mean_error_m'] <= limits['reflected_error_max_m'],
        'stationary_half': m['stationary_drift_mean_m'] <= common['stationary_drift_mean_max_m'],
        'free_edge': limits['free_edge_overrun_min_m'] <= m['free_edge_overrun_m'] <= limits['free_edge_overrun_max_m'],
        'fold_extent': common['fold_extent_min_m'] <= m['fold_extent_m'] <= common['fold_extent_max_m'],
        'tangent_extent': common['tangent_extent_min_m'] <= m['tangent_extent_m'] <= common['tangent_extent_max_m'],
        'height': m['height_p95_m'] <= common['height_p95_max_m'] and m['height_min_m'] >= common['height_min_m'] and m['height_max_m'] <= common['height_max_m'],
    }
    if 'free_edge_height_p90_max_m' in limits:
        checks['free_edge_on_table_proxy'] = m['free_edge_height_p90_m'] <= limits['free_edge_height_p90_max_m']
    return {'metrics': m, 'checks': checks, 'geometry_pass': bool(all(checks.values()))}


def evaluate(meta, data):
    cfg = config(); task = meta['task']; t = cfg['tasks'][task]
    required = {'initial', 'local_points', 'vertices', 'steps', 'holding', 'attachment_enabled', 'gripper_open'}
    if not required <= set(data):
        return {'status': 'incomplete', 'success': None, 'missing': sorted(required-set(data))}
    steps = np.asarray(data['steps'])
    if not np.issubdtype(steps.dtype, np.integer) or not np.array_equal(steps, np.arange(331)):
        return {'status': 'incomplete', 'success': None, 'reason': 'Need every physics step 0..330 after final OPEN completes'}
    v = array(data['vertices'], (331, 441, 3))
    # Non-boolean states are invalid evidence, not truthy coercions.
    for key, shape in [('holding', (331,)), ('gripper_open', (331,)), ('attachment_enabled', (331, 3))]:
        x = np.asarray(data[key])
        if x.shape != shape or x.dtype != np.dtype(bool):
            raise ValueError('Invalid state channel: ' + key)
    if not np.isclose(meta['dt_s'], cfg['sampling']['dt_s'], rtol=0, atol=1e-12):
        raise ValueError('Unexpected physics dt')
    h = meta['held_check']
    array([h['position_error_m'], h['arm_speed_rad_s'], h['anchor_gap_max_m']], (3,))
    if min(h['position_error_m'], h['arm_speed_rad_s'], h['anchor_gap_max_m']) < 0:
        raise ValueError('Negative held error')
    checks = {
        'definition': meta['level'] in t['levels'] and meta['edge'] in t['edges'] and meta['width_m'] == t['width_m'] and meta['overhang_m'] == t['overhang_m'],
        'budget': type(meta['action_count']) is int and meta['action_count'] == t['action_count'] and type(meta['recovery_count']) is int and meta['recovery_count'] == t['recovery_count'],
        'no_runtime_error': meta['errors'] == [],
        'held': h['position_error_m'] < t['held_position_max_m'] and h['arm_speed_rad_s'] < cfg['held']['arm_speed_max_rad_s'] and h['anchor_gap_max_m'] <= cfg['held']['anchor_gap_max_m'] and h['orientation_reached'] is True,
        'released_continuously': not np.any(data['holding']) and not np.any(data['attachment_enabled']) and bool(np.all(data['gripper_open'])),
    }
    frames = [geometry(data['initial'], frame, data['local_points'], meta['pick_index'], meta['yaw_rad'], meta['edge'], task, meta['floor_z_m']) for frame in v[210:331]]
    checks['geometry_entire_window'] = all(f['geometry_pass'] for f in frames)
    w = v[210:331]; d = np.linalg.norm(w-w[0], axis=2)
    speed = np.linalg.norm(np.diff(w, axis=0), axis=2) / meta['dt_s']
    stability = {
        'centroid_drift_max_m': float(np.linalg.norm(w.mean(1)-w[0].mean(0), axis=1).max()),
        'vertex_drift_p95_max_m': float(np.percentile(d, 95, axis=1).max()),
        'vertex_drift_max_m': float(d.max()),
        'vertex_speed_p95_max_m_s': float(np.percentile(speed, 95, axis=1).max()),
        'vertex_speed_max_m_s': float(speed.max()),
    }
    checks['stable'] = all(stability[k] <= limit for k, limit in cfg['stability'].items())
    return {'status': 'accepted' if all(checks.values()) else 'rejected', 'success': bool(all(checks.values())), 'checks': checks, 'stability': stability, 'first_window_geometry': frames[0], 'final_geometry': frames[-1], 'failed_geometry_frames': [210+i for i,f in enumerate(frames) if not f['geometry_pass']]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {'version': config()['version'], 'scope': 'Criteria result only; formal batch eligibility/seed and attempt accounting remain external'}
    try:
        report['evaluator_files'] = identity()
        paths = [args.directory/'success_meta.json', args.directory/'success_trace.npz']
        if not all(p.is_file() for p in paths):
            report.update(status='incomplete', success=None, missing=[p.name for p in paths if not p.is_file()])
        else:
            report['evidence_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            with np.load(paths[1], allow_pickle=False) as z:
                report.update(evaluate(json.loads(paths[0].read_text(encoding='utf-8')), dict(z)))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report.update(status='error', success=None, reason=str(exc))
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'success': report['success']}))


if __name__ == '__main__':
    main()
