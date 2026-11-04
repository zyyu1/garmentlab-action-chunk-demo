#!/usr/bin/env python3
"""Offline a5-rc2-pfs1 vs RC2 comparison.

No simulation.  RC2 is the original recovery/fold flow; pfs1 differs only by
particleFrictionScale 0.0 -> 1.0 plus passive observation.

Important: the ClothPrimView.get_velocities() readback in this Isaac build is
not the frame-to-frame cloth displacement.  It is retained in the raw NPZ as
unvalidated data, but all physical speeds in this analysis are finite
differences of the world vertices.  See velocity_readback_diagnostic.json.
"""
import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

SURFACE = '#fcfcfb'; INK = '#0b0b0b'; SECONDARY = '#52514e'
GRID = '#e1e0d9'; AXIS = '#c3c2b7'; BLUE = '#2a78d6'; ORANGE = '#eb6834'; CRITICAL = '#d03b3b'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
    'axes.titlesize': 10, 'axes.labelsize': 9, 'xtick.labelsize': 8,
    'ytick.labelsize': 8, 'legend.fontsize': 7.5,
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE})


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def load(p):
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def rigid2d(a, b):
    a = np.asarray(a, float)[:, :2]; b = np.asarray(b, float)[:, :2]
    ca, cb = a.mean(0), b.mean(0)
    h = (a - ca).T @ (b - cb)
    u, s, vt = np.linalg.svd(h); r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1; r = vt.T @ u.T
    t = cb - r @ ca
    res = b - (a @ r.T + t)
    return math.degrees(math.atan2(r[1, 0], r[0, 0])), float(np.sqrt((res ** 2).sum(1).mean())) * 1000


def displacement(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    d = np.linalg.norm(b - a, axis=1) * 1000
    rot, rms = rigid2d(a, b)
    return {'centroid_mm': float(np.linalg.norm(b.mean(0) - a.mean(0)) * 1000),
            'p95_mm': float(np.percentile(d, 95)), 'max_mm': float(d.max()),
            'rotation_deg': float(rot), 'rigid_rms_mm': float(rms),
            'z_min_m': float(b[:, 2].min()), 'z_max_m': float(b[:, 2].max())}


def unique_indices(times, i=0, j=None):
    """First physical frame at each increasing time; skips duplicated boundary rows."""
    times = np.asarray(times, float)
    if j is None:
        j = len(times) - 1
    out = []
    last = None
    for k in range(int(i), int(j) + 1):
        t = float(times[k])
        if last is None or t - last > 1e-9:
            out.append(k)
            last = t
    return out


def finite_diff(V, times, i=0, j=None):
    """Finite differences of world vertices; never uses the velocity readback."""
    V = np.asarray(V, float); times = np.asarray(times, float)
    idx = unique_indices(times, i, j)
    if len(idx) < 2:
        raise ValueError('invalid finite-difference window')
    dt = np.diff(times[idx])
    if np.any(dt <= 0):
        raise ValueError('non-increasing finite-difference time')
    pdisp = np.linalg.norm(V[idx[1:]] - V[idx[:-1]], axis=2).mean(1) * 1000
    cdisp = np.linalg.norm(V[idx[1:]].mean(1) - V[idx[:-1]].mean(1), axis=1) * 1000
    ang = np.array([abs(rigid2d(V[idx[k]], V[idx[k + 1]])[0]) for k in range(len(idx) - 1)])
    ps, cs, ws = pdisp / dt, cdisp / dt, ang / dt
    return {
        'n_frames': int(len(idx)), 'n_intervals': int(len(idx) - 1),
        'duration_s': float(times[idx[-1]] - times[idx[0]]),
        'first_step': int(idx[0]), 'last_step': int(idx[-1]),
        'particle_mean_speed_mean_mm_s': float(ps.mean()),
        'particle_mean_speed_max_mm_s': float(ps.max()),
        'centroid_speed_mean_mm_s': float(cs.mean()),
        'centroid_speed_max_mm_s': float(cs.max()),
        'angular_speed_mean_deg_s': float(ws.mean()),
        'angular_speed_max_deg_s': float(ws.max()),
        'first_interval_particle_mean_mm_s': float(ps[0]),
        'first_interval_centroid_mm_s': float(cs[0]),
        'first_interval_dt_s': float(dt[0]),
        'first_interval_angular_deg_s': float(ws[0]),
    }


def centroid_direction(V, times, i, j):
    idx = unique_indices(times, i, j)
    delta = (np.asarray(V, float)[idx[-1]].mean(0) - np.asarray(V, float)[idx[0]].mean(0)) * 1000
    return float(math.degrees(math.atan2(delta[1], delta[0])))


def metrics_from_trace(V, times, i, j):
    d = displacement(V[i], V[j])
    d.update({'centroid_speed_mm_s': d['centroid_mm'] / float(times[j] - times[i])})
    d.update(finite_diff(V, times, i, j))
    d['centroid_direction_deg'] = centroid_direction(V, times, i, j)
    return d


def action_compare(r1, r2):
    a, b = r1.get('actions') or [], r2.get('actions') or []
    n = min(len(a), len(b)); target_max = 0.0; ee_max = 0.0
    labels = commands = targets = True
    per_action = []
    for k in range(n):
        labels &= a[k].get('label') == b[k].get('label')
        commands &= int(a[k].get('command', -1)) == int(b[k].get('command', -2))
        x = np.asarray(a[k].get('target_pose'), float); y = np.asarray(b[k].get('target_pose'), float)
        if x.shape != y.shape:
            targets = False
            per_action.append({'index': k, 'label': a[k].get('label'), 'shape_mismatch': True})
        else:
            diff = y - x
            target_max = max(target_max, float(np.max(np.abs(diff))))
            targets &= np.array_equal(x, y)
            per_action.append({'index': k, 'label': a[k].get('label'),
                               'max_abs_mm': float(np.max(np.abs(diff)) * 1000),
                               'vector_mm': (diff * 1000).tolist()})
        if 'ee' in a[k] and 'ee' in b[k]:
            ee_max = max(ee_max, float(np.max(np.abs(np.asarray(a[k]['ee'], float) - np.asarray(b[k]['ee'], float)))))
    return {'rc2_actions': len(a), 'pfs1_actions': len(b), 'labels_identical': bool(labels),
            'commands_identical': bool(commands), 'targets_identical': bool(targets),
            'target_max_abs_diff_m': target_max, 'target_max_abs_diff_mm': target_max * 1000,
            'ee_max_abs_diff_m': ee_max, 'ee_max_abs_diff_mm': ee_max * 1000,
            'per_action': per_action,
            'rc2_horizons': r1.get('call_horizons'), 'pfs1_horizons': r2.get('call_horizons'),
            'rc2_labels': r1.get('action_labels'), 'pfs1_labels': r2.get('action_labels')}


def readback_diagnostic(formal, release, pre, pre_hold, pfs1_dir):
    """Quantify why the view velocity readback is not used as physical velocity."""
    V = np.asarray(formal['vertices'], float); vel = np.asarray(formal['velocities'], float)
    t = np.asarray(formal['sim_time_s'], float)
    fd = finite_diff(V, t, 0, len(t) - 1)
    speeds = np.linalg.norm(vel, axis=2) * 1000
    cvec = vel.mean(1) * 1000
    cs = np.linalg.norm(cvec, axis=1)
    # Per-interval correlation of norms (positions interval k -> readback frame k+1)
    a = np.linalg.norm(vel[1:], axis=2).mean(1)
    b = np.linalg.norm(V[1:] - V[:-1], axis=2).mean(1) * 1000
    corr_norm = float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 0 and np.std(b) > 0 else None
    corr_vec = float(np.corrcoef(vel[1:].reshape(-1), (V[1:] - V[:-1]).reshape(-1))[0, 1])
    # Field constancy across the formal window.
    field_corr = float(np.corrcoef(vel[0].reshape(-1), vel[-1].reshape(-1))[0, 1])
    per_particle_change = float(np.linalg.norm(vel[-1] - vel[0], axis=1).mean() * 1000)
    pos_change = float(np.linalg.norm(V[-1] - V[0], axis=1).mean() * 1000)
    # Release and pre-release cross-checks.
    rV = np.asarray(release['vertices'], float); rvel = np.asarray(release['velocities'], float)
    rt = np.asarray(release['sim_time_s'], float)
    rfd0 = finite_diff(rV, rt, 0, 1)
    rsp = np.linalg.norm(rvel[0], axis=1) * 1000
    # Pre-release hold finite difference: use dt_s sidecar or 1/60.
    hV = np.asarray(pre_hold['vertices'], float)
    hdt = float(np.asarray(pre_hold['dt_s']).reshape(-1)[0]) if 'dt_s' in pre_hold else 1.0 / 60.0
    hfd = finite_diff(hV, np.arange(len(hV)) * hdt, len(hV) - 2, len(hV) - 1)
    psp = np.linalg.norm(np.asarray(pre['velocities'], float), axis=1) * 1000
    ee = np.asarray(formal['ee_m'], float)
    ee_speed = float(np.linalg.norm(np.diff(ee, axis=0), axis=1).mean() * 1000
                     / (t[1] - t[0])) if len(ee) > 1 else None
    return {
        'status': 'unvalidated',
        'validated': False,
        'api': 'ClothPrimView.get_velocities(clone=True) -> PhysicsView.get_velocities()',
        'position_api': 'ClothPrimView.get_world_positions(clone=True)',
        'formal': {
            'readback_particle_mean_mm_s': float(speeds.mean()),
            'readback_particle_median_mm_s': float(np.median(speeds)),
            'readback_particle_p95_mm_s': float(np.percentile(speeds, 95)),
            'readback_particle_max_mm_s': float(speeds.max()),
            'readback_centroid_speed_mean_mm_s': float(cs.mean()),
            'readback_mean_vector_mm_s': (cvec.mean(0)).tolist(),
            'position_derivative_particle_mean_mm_s': float(fd['particle_mean_speed_mean_mm_s']),
            'position_derivative_centroid_mean_mm_s': float(fd['centroid_speed_mean_mm_s']),
            'readback_to_position_ratio_particle': float(speeds.mean() / fd['particle_mean_speed_mean_mm_s']),
            'readback_to_position_ratio_centroid': float(cs.mean() / fd['centroid_speed_mean_mm_s']),
            'readback_norm_vs_position_delta_corr': corr_norm,
            'readback_vector_vs_position_delta_corr': corr_vec,
            'readback_field_corr_first_last': field_corr,
            'readback_per_particle_change_over_window_mm_s': per_particle_change,
            'position_per_particle_change_over_window_mm': pos_change,
            'ee_speed_mm_s': ee_speed,
            'holding_any': bool(np.asarray(formal['holding'], bool).any()),
            'attachment_enabled_any': bool(np.asarray(formal['attachment_enabled_any'], bool).any()),
            'z_min_m': float(V[:, :, 2].min()),
        },
        'release_first_interval': {
            'readback_particle_mean_mm_s': float(rsp.mean()),
            'position_derivative_particle_mean_mm_s': float(rfd0['particle_mean_speed_mean_mm_s']),
            'readback_to_position_ratio_particle': float(rsp.mean() / rfd0['particle_mean_speed_mean_mm_s']),
            'position_derivative_centroid_mm_s': float(rfd0['centroid_speed_mean_mm_s']),
        },
        'pre_release': {
            'readback_particle_mean_mm_s': float(psp.mean()),
            'hold_finite_diff_particle_mean_mm_s': float(hfd['particle_mean_speed_mean_mm_s']),
            'hold_finite_diff_centroid_mm_s': float(hfd['centroid_speed_mean_mm_s']),
            'readback_to_position_ratio_particle': float(psp.mean() / hfd['particle_mean_speed_mean_mm_s']),
        },
        'interpretation': (
            'The readback is nearly static over the formal window and is not the '
            'frame-to-frame displacement of the cloth. The EE is static and attachment/holding '
            'are false, so robot motion does not explain it. It may be an internal solver '
            'velocity or another quantity, but its semantics are not established by the '
            'available API or evidence. It is therefore not used as realized cloth velocity '
            'or as impulse evidence.'
        ),
        'action': 'Use world-position finite differences for kinematics; retain raw readback in NPZ as unvalidated data; do not rerun for this analysis.',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rc2', type=Path, required=True)
    ap.add_argument('--pfs1', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--rc2-release-diag', type=Path,
                    default=Path(__file__).resolve().parent / 'results' / 'STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103' / 'release_diag_analysis.json')
    args = ap.parse_args()
    rc2, pfs1, out = args.rc2.resolve(), args.pfs1.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    r2 = read(rc2 / 'result.json'); p2 = read(pfs1 / 'result.json')
    v2 = read(rc2 / 'a5-verdict.json'); vp = read(pfs1 / 'a5-verdict.json')
    t2 = load(rc2 / 'success_trace.npz'); tp = load(pfs1 / 'success_trace.npz')
    h2 = load(rc2 / 'pre_release_hold.npz'); hp = load(pfs1 / 'pre_release_hold.npz')
    rec2 = load(rc2 / 'recovered.npz')['vertices']
    stages = {label: load(pfs1 / 'pfs1_stages' / (label + '.npz'))
              for label in ('initial_loaded', 'after_recovery', 'pre_release', 'release_boundary')}
    rel = load(pfs1 / 'pfs1_release_steps.npz')
    clock = read(pfs1 / 'pfs1_release_clock.json')
    rel_v = np.asarray(rel['vertices'], float)
    rel_t = np.asarray(rel['sim_time_s'], float)
    first = load(pfs1 / 'pfs1_first_0_5s.npz')
    formal = load(pfs1 / 'pfs1_formal_210_330.npz')

    outj = {
        'scope': 'a5-rc2-pfs1 vs RC2 original 4202 single; offline only',
        'identity': {
            'pfs1_result_dir': str(pfs1),
            'pfs1_manifest_sha256': p2.get('manifest_sha256') or read(pfs1 / 'a5-verdict.json').get('manifest_sha256'),
            'rc2_result_dir': str(rc2),
            'rc2_manifest_sha256': v2.get('manifest_sha256'),
        },
        'actions': action_compare(r2, p2),
    }
    # recovery / pre-release states
    outj['recovery_state'] = displacement(rec2, stages['after_recovery']['vertices'])
    outj['pre_release_state'] = displacement(h2['vertices'][-1], stages['pre_release']['vertices'])
    hdt = float(np.asarray(h2['dt_s']).reshape(-1)[0]) if 'dt_s' in h2 else 1.0 / 60.0
    hpdt = float(np.asarray(hp['dt_s']).reshape(-1)[0]) if 'dt_s' in hp else 1.0 / 60.0
    outj['pre_release_velocity'] = {
        'rc2_finite_diff': finite_diff(h2['vertices'], np.arange(len(h2['vertices'])) * hdt,
                                       len(h2['vertices']) - 2, len(h2['vertices']) - 1),
        'pfs1_finite_diff': finite_diff(hp['vertices'], np.arange(len(hp['vertices'])) * hpdt,
                                        len(hp['vertices']) - 2, len(hp['vertices']) - 1),
        'note': 'world-position finite differences; pre-release hold last interval; readback is reported separately as unvalidated.',
    }
    # release clock and boundary
    outj['release_clock'] = clock
    outj['release_boundary_state'] = {
        'step': int(stages['release_boundary']['absolute_step']),
        'time_s': float(stages['release_boundary']['sim_time_s']),
        'holding': bool(stages['release_boundary']['holding']),
        'attached': bool(stages['release_boundary']['attachment_enabled_any']),
        'z_min_m': float(stages['release_boundary']['vertices'][:, 2].min())}
    # Descriptive nearest-frame state comparisons; NOT time-aligned.
    released_t = float(clock['released_sample']['sim_time_s'])
    retreat_t = float(p2['release_clock']['sim_time_s'])
    def nearest_index(series, t):
        return int(np.argmin(np.abs(series - float(t))))
    i_rel = nearest_index(rel_t, released_t); i_ret = nearest_index(rel_t, retreat_t)
    outj['released_state_descriptive'] = displacement(load(rc2 / 'evidence' / 'released.npz')['vertices'], rel_v[i_rel])
    outj['released_state_descriptive']['note'] = 'nearest pfs1 frame to RC2 released sample; frames are not time-aligned; descriptive only'
    outj['retreated_state_descriptive'] = displacement(load(rc2 / 'evidence' / 'retreated.npz')['vertices'], rel_v[i_ret])
    outj['retreated_state_descriptive']['note'] = 'nearest pfs1 frame to RC2 retreat end; frames are not time-aligned; descriptive only'
    # first 0.5 s finite differences (world positions only).  Use the raw
    # release-step series with a 1e-6 s edge tolerance: the boundary timestamp
    # plus 0.5 s differs from the frame-30 timestamp by only 2.6e-8 s, and the
    # saved first-0.5 file used a tighter 1e-9 tolerance.
    tb = float(clock['release_boundary']['sim_time_s'])
    fV = rel_v; ft = rel_t
    j05 = max(i for i in range(len(ft)) if ft[i] <= tb + .5 + 1e-6)
    outj['pfs1_first_0_5s'] = finite_diff(fV, ft, 0, j05)
    outj['pfs1_first_0_5s']['centroid_direction_deg'] = centroid_direction(fV, ft, 0, j05)
    outj['pfs1_first_0_5s']['first_absolute_step'] = int(rel['absolute_step'][0])
    outj['pfs1_first_0_5s']['last_absolute_step'] = int(rel['absolute_step'][j05])
    outj['pfs1_first_0_5s']['saved_first_file_note'] = (
        'saved pfs1_first_0_5s.npz contains 30 frames / 0.4833 s because its '
        'boundary+0.5 comparison used 1e-9; this analysis uses the frame at '
        'boundary+0.500000026 s (31 frames / 0.5 s).')
    # 0.5 s bins from boundary over the available traced window
    bins = []
    for b in range(20):
        a = tb + .5 * b; z = tb + .5 * (b + 1)
        idx = [i for i in range(len(rel_t)) if a - 1e-6 <= rel_t[i] <= z + 1e-6]
        if len(idx) < 2:
            continue
        m = finite_diff(rel_v, rel_t, idx[0], idx[-1])
        m.update({'bin_start_s': .5 * b, 'bin_end_s': .5 * (b + 1),
                  'partial': bool(rel_t[idx[-1]] < z - 1e-9),
                  'first_absolute_step': int(rel['absolute_step'][idx[0]]),
                  'last_absolute_step': int(rel['absolute_step'][idx[-1]]),
                  'z_min_mm': float(rel_v[idx[0]:idx[-1] + 1, :, 2].min() * 1000),
                  'below_contact_offset_mm': float((.01 - rel_v[idx[0]:idx[-1] + 1, :, 2].min()) * 1000),
                  'ground_penetration_mm': float(max(0.0, -rel_v[idx[0]:idx[-1] + 1, :, 2].min() * 1000))})
        bins.append(m)
    outj['pfs1_bins'] = bins
    # steady window within available trace
    steady_idx = [i for i in range(len(rel_t)) if tb + 1.5 - 1e-9 <= rel_t[i] <= tb + 8.0 + 1e-9]
    outj['pfs1_steady_1_5_to_8_0s'] = finite_diff(rel_v, rel_t, steady_idx[0], steady_idx[-1])
    outj['pfs1_steady_1_5_to_8_0s']['centroid_direction_deg'] = centroid_direction(rel_v, rel_t, steady_idx[0], steady_idx[-1])
    outj['pfs1_steady_1_5_to_8_0s']['note'] = 'available traced post-release window is ~8.05 s; 10 s bins are not available'
    # formal window: endpoint geometry + finite-diff speed + official evaluator stability
    rV = np.asarray(t2['vertices'], float); rt = np.asarray(t2['sim_time_s'], float)
    pV = np.asarray(tp['vertices'], float); pt = np.asarray(tp['sim_time_s'], float)
    outj['formal'] = {
        'rc2_trace': metrics_from_trace(rV, rt, 210, 330),
        'pfs1_trace': metrics_from_trace(pV, pt, 210, 330),
        'rc2_evaluator_stability': v2.get('criteria', {}).get('stability'),
        'pfs1_evaluator_stability': vp.get('criteria', {}).get('stability'),
        'note': 'trace endpoint displacement and world-position finite differences; evaluator stability is the official max-over-window metric.',
    }
    outj['quality'] = {'rc2': v2.get('criteria', {}).get('status'),
                       'pfs1': vp.get('criteria', {}).get('status'),
                       'rc2_checks': v2.get('criteria', {}).get('checks'),
                       'pfs1_checks': vp.get('criteria', {}).get('checks')}
    outj['fold'] = {'rc2': r2.get('fold_metrics'), 'pfs1': p2.get('fold_metrics'),
                    'rc2_held': r2.get('fold_held_check'), 'pfs1_held': p2.get('fold_held_check')}
    outj['recovery_metrics'] = {'rc2': r2.get('recovery_metrics'), 'pfs1': p2.get('recovery_metrics')}
    outj['errors'] = {'rc2': r2.get('errors'), 'pfs1': p2.get('errors')}
    outj['velocity_readback_validation'] = readback_diagnostic(formal, rel, stages['pre_release'], hp, pfs1)
    # Material and contact evidence gaps.
    outj['material_readback'] = {
        'runtime_readback_present': False,
        'readback_note': 'No runtime particleFrictionScale/friction/self-collision readback is stored in the pfs1 result. The source identity proves the constructor argument was set to 1.0; it does not by itself prove the solver-effective value.',
        'base_readback_context': 'D2-A base scene readback recorded friction=0.3, particleFrictionScale=0.0 for the unmodified material; that is not a pfs1 runtime readback.',
        'source_parameter': 'particleFrictionScale 0.0 -> 1.0; friction 0.3 unchanged',
    }
    outj['contact_note'] = 'contact_report.json is absent; RC2 and pfs1 contact report would be robot-rigid only. Zero events are not evidence of no cloth-ground contact; geometric heights are not contact force or impulse.'
    outj['boundaries'] = {
        'one_4202_single_only': True, 'no_retry': True,
        'no_seven_case_rc': True, 'no_freeze': True, 'no_heldout': True,
        'formal_stage4_success_increment': 0,
        'not_ground_friction_fix_claim': True,
    }
    (out / 'comparison.json').write_text(json.dumps(outj, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    # Finite-difference bins CSV only; no readback columns to avoid misuse.
    with (out / 'pfs1_bins.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['bin_start_s', 'bin_end_s', 'partial', 'n_frames', 'n_intervals',
                    'duration_s', 'particle_mean_speed_mean_mm_s', 'particle_mean_speed_max_mm_s',
                    'centroid_speed_mean_mm_s', 'centroid_speed_max_mm_s',
                    'angular_speed_mean_deg_s', 'angular_speed_max_deg_s',
                    'z_min_mm', 'below_contact_offset_mm', 'ground_penetration_mm',
                    'first_absolute_step', 'last_absolute_step'])
        for b in bins:
            w.writerow([b['bin_start_s'], b['bin_end_s'], b['partial'], b['n_frames'], b['n_intervals'],
                        b['duration_s'], b['particle_mean_speed_mean_mm_s'], b['particle_mean_speed_max_mm_s'],
                        b['centroid_speed_mean_mm_s'], b['centroid_speed_max_mm_s'],
                        b['angular_speed_mean_deg_s'], b['angular_speed_max_deg_s'],
                        b['z_min_mm'], b['below_contact_offset_mm'], b['ground_penetration_mm'],
                        b['first_absolute_step'], b['last_absolute_step']])

    # Main comparison figure: finite-difference pfs1 post-release bins and formal traces.
    fig, axes = plt.subplots(3, 1, figsize=(8.6, 7.2), sharex=False)
    x = [(b['bin_start_s'] + b['bin_end_s']) / 2 for b in bins]
    axes[0].plot(x, [b['centroid_speed_mean_mm_s'] for b in bins], color=ORANGE, lw=1.8, marker='o', ms=3, label='pfs1 centroid')
    axes[0].plot(x, [b['particle_mean_speed_mean_mm_s'] for b in bins], color=BLUE, lw=1.2, ls='--', label='pfs1 particle mean')
    axes[0].set_ylabel('speed (mm/s)'); axes[0].set_title('pfs1 particleFrictionScale=1: post-release finite-difference speed (readback not used)')
    axes[0].legend(loc='best')
    axes[1].plot(x, [b['angular_speed_mean_deg_s'] for b in bins], color=ORANGE, lw=1.8, marker='o', ms=3)
    axes[1].set_ylabel('angular speed (deg/s)')
    xx = np.arange(121)
    for tag, V, t, color in (('RC2', rV, rt, BLUE), ('pfs1', pV, pt, ORANGE)):
        d = np.linalg.norm(V[210:331] - V[210], axis=2) * 1000
        cent = np.linalg.norm(V[210:331].mean(1) - V[210].mean(0), axis=1) * 1000
        axes[2].plot(xx, cent, color=color, lw=1.8, label=tag + ' centroid')
        axes[2].plot(xx, np.percentile(d, 95, axis=1), color=color, lw=1.2, ls='--', label=tag + ' P95')
    axes[2].set_xlabel('success_trace step (210..330)'); axes[2].set_ylabel('mm')
    axes[2].set_title('formal window: centroid / vertex P95'); axes[2].legend(loc='best', ncol=2)
    for ax in axes:
        ax.grid(color=GRID, lw=.7); ax.set_axisbelow(True)
        for s in ('top', 'right'): ax.spines[s].set_visible(False)
        for s in ('left', 'bottom'): ax.spines[s].set_color(AXIS)
    fig.tight_layout(); fig.savefig(out / 'pfs1_vs_rc2.png', dpi=180); plt.close(fig)

    # Separate readback diagnostic: do not mix it into the physical comparison.
    rd = outj['velocity_readback_validation']['formal']
    ft = np.asarray(formal['sim_time_s'], float)
    fV = np.asarray(formal['vertices'], float)
    fvel = np.asarray(formal['velocities'], float)
    fig, axes = plt.subplots(2, 1, figsize=(8.6, 5.0), sharex=True)
    axes[0].plot(ft, np.linalg.norm(fvel, axis=2).mean(1) * 1000,
                 color=ORANGE, lw=1.4, label='readback particle mean (unvalidated)')
    axes[0].plot(ft[1:], np.linalg.norm(fV[1:] - fV[:-1], axis=2).mean(1) * 1000 / np.diff(ft),
                 color=BLUE, lw=1.4, label='world-position finite difference')
    axes[0].set_ylabel('mm/s'); axes[0].set_title('formal window: velocity readback vs finite difference')
    axes[0].legend(loc='best')
    axes[1].plot(ft, np.linalg.norm(fvel.mean(1), axis=1) * 1000,
                 color=ORANGE, lw=1.4, label='readback centroid (unvalidated)')
    axes[1].plot(ft[1:], np.linalg.norm(fV[1:].mean(1) - fV[:-1].mean(1), axis=1) * 1000 / np.diff(ft),
                 color=BLUE, lw=1.4, label='world-position finite difference')
    axes[1].set_ylabel('mm/s'); axes[1].set_xlabel('sim time (s)'); axes[1].legend(loc='best')
    for ax in axes:
        ax.grid(color=GRID, lw=.7); ax.set_axisbelow(True)
        for s in ('top', 'right'): ax.spines[s].set_visible(False)
        for s in ('left', 'bottom'): ax.spines[s].set_color(AXIS)
    fig.tight_layout(); fig.savefig(out / 'velocity_readback_check.png', dpi=180); plt.close(fig)

    (out / 'velocity_readback_diagnostic.json').write_text(
        json.dumps(outj['velocity_readback_validation'], indent=2, allow_nan=False) + '\n', encoding='utf-8')

    print('PFS1_COMPARE_OK', out / 'comparison.json')
    print('actions max target diff mm', outj['actions']['target_max_abs_diff_mm'])
    print('recovery', outj['recovery_state'])
    print('pre_release', outj['pre_release_state'])
    print('first0.5', outj['pfs1_first_0_5s'])
    print('steady', outj['pfs1_steady_1_5_to_8_0s'])
    print('formal rc2/pfs1', outj['formal']['rc2_evaluator_stability'], outj['formal']['pfs1_evaluator_stability'])
    print('quality', outj['quality'])
    print('readback', outj['velocity_readback_validation']['formal'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
