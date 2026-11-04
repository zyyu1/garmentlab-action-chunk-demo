#!/usr/bin/env python3
"""Offline review of the a5-rc2-pfs1-observation-v2 4302 single extension.

Compares the fixed particleFrictionScale=1.0 candidate on the pre-registered
4302 seed against the RC2 4302 single baseline.  No simulation is started.

Every physical speed here is a finite difference of world vertex positions.
The ClothPrimView.get_velocities() readback is kept only as unvalidated data.

Outputs (into --out): comparison.json, summary.json, windows.csv, bins.csv,
sticking_checks.json, pfs1_v2_4302_windows.png, formal_compare_4302.png.
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
GRID = '#e1e0d9'; AXIS = '#c3c2b7'; BLUE = '#2a78d6'; ORANGE = '#eb6834'; RED = '#d03b3b'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
    'axes.titlesize': 10, 'axes.labelsize': 9, 'xtick.labelsize': 8,
    'ytick.labelsize': 8, 'legend.fontsize': 7.5,
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE})

CENTROID_LIMIT_MM = 1.0
P95_LIMIT_MM = 3.0


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def load(p):
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


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
    labels = commands = True
    per_action = []
    for k in range(n):
        labels &= a[k].get('label') == b[k].get('label')
        commands &= int(a[k].get('command', -1)) == int(b[k].get('command', -2))
        x = np.asarray(a[k].get('target_pose'), float); y = np.asarray(b[k].get('target_pose'), float)
        if x.shape != y.shape:
            per_action.append({'index': k, 'label': a[k].get('label'), 'shape_mismatch': True})
            continue
        diff = y - x
        target_max = max(target_max, float(np.max(np.abs(diff))))
        xe = np.asarray(a[k].get('returned_ee'), float); ye = np.asarray(b[k].get('returned_ee'), float)
        if xe.shape == ye.shape and xe.size:
            ee_max = max(ee_max, float(np.max(np.abs(ye - xe))))
        per_action.append({'index': k, 'label': a[k].get('label'),
                           'max_abs_mm': float(np.max(np.abs(diff)) * 1000),
                           'vector_mm': (diff * 1000).tolist()})
    return {'rc2_actions': len(a), 'pfs1_actions': len(b),
            'labels_identical': bool(labels), 'commands_identical': bool(commands),
            'target_max_abs_diff_mm': float(target_max * 1000),
            'ee_max_abs_diff_mm': float(ee_max * 1000),
            'rc2_horizons': r1.get('call_horizons'), 'pfs1_horizons': r2.get('call_horizons'),
            'rc2_labels': r1.get('action_labels'), 'pfs1_labels': r2.get('action_labels'),
            'per_action': per_action}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--rc2', type=Path, required=True)
    ap.add_argument('--v2-4202', type=Path, default=None)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--seed', type=int, default=4302)
    ap.add_argument('--expect-manifest', default=None)
    args = ap.parse_args()
    run, rc2, out = args.run.resolve(), args.rc2.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    r = read(run / 'result.json'); v = read(run / 'a5-verdict.json')
    ledger = read(run / 'pfs1_observation_v2_ledger.json')
    semantics = read(run / 'pfs1_semantics.json')
    r2 = read(rc2 / 'result.json'); v2 = read(rc2 / 'a5-verdict.json')

    # ---- integrity: ledger file hashes + evidence manifest ----
    ledger_files = {name: rec for name, rec in (ledger.get('files') or {}).items()}
    ledger_bad = []
    for name, rec in ledger_files.items():
        p = run / name
        if not p.is_file():
            ledger_bad.append((name, 'missing'))
        elif rec.get('sha256') and sha(p) != rec['sha256']:
            ledger_bad.append((name, 'mismatch'))
    evidence_manifest_path = run / 'evidence' / 'manifest.json'
    evidence_entries = read(evidence_manifest_path) if evidence_manifest_path.is_file() else {}
    evidence_bad = []
    for name, want in evidence_entries.items():
        p = run / 'evidence' / name
        if not p.is_file():
            evidence_bad.append((name, 'missing'))
        elif sha(p) != want:
            evidence_bad.append((name, 'mismatch'))

    source_bad = []
    # source snapshots are already covered by evidence/manifest.json

    integrity = {
        'ledger_state': ledger.get('state'),
        'ledger_seed': ledger.get('seed'),
        'ledger_manifest_sha256': ledger.get('manifest_sha256'),
        'expected_manifest_sha256': args.expect_manifest,
        'manifest_match': (ledger.get('manifest_sha256') == args.expect_manifest) if args.expect_manifest else None,
        'ledger_files': len(ledger_files),
        'ledger_bad': ledger_bad,
        'evidence_manifest_entries': len(evidence_entries),
        'evidence_bad': evidence_bad,
        'file_complete': bool(ledger.get('file_complete')),
        'observation_semantics_valid': bool(ledger.get('observation_semantics_valid')),
        'quality_status': ledger.get('quality_status'),
        'overall_valid': bool(ledger.get('overall_valid')),
        'episode_passed': bool(ledger.get('episode_passed')),
        'entry_assess_exit': ledger.get('entry_assess_exit'),
        'semantic_checks': ledger.get('semantic_checks'),
        'semantics_file_valid': bool(semantics.get('observation_semantics', {}).get('valid')),
        'errors': r.get('errors'),
        'action_count': r.get('action_count'),
        'call_horizons': r.get('call_horizons'),
    }

    # ---- evaluator criteria: the official geometry + stability gate ----
    crit = v.get('criteria') or {}
    checks = crit.get('checks') or {}
    stability = crit.get('stability') or {}
    gate = {
        'checks': checks,
        'geometry_entire_window': bool(checks.get('geometry_entire_window')),
        'stable': bool(checks.get('stable')),
        'held': bool(checks.get('held')),
        'released_continuously': bool(checks.get('released_continuously')),
        'budget': bool(checks.get('budget')),
        'no_runtime_error': bool(checks.get('no_runtime_error')),
        'centroid_drift_max_mm': float(stability.get('centroid_drift_max_m', float('nan')) * 1000),
        'vertex_p95_max_mm': float(stability.get('vertex_drift_p95_max_m', float('nan')) * 1000),
        'centroid_limit_mm': CENTROID_LIMIT_MM,
        'p95_limit_mm': P95_LIMIT_MM,
        'pass_1mm_3mm': bool(stability.get('centroid_drift_max_m', 9) * 1000 <= CENTROID_LIMIT_MM
                             and stability.get('vertex_drift_p95_max_m', 9) * 1000 <= P95_LIMIT_MM),
        'first_window_geometry': crit.get('first_window_geometry'),
        'final_geometry': crit.get('final_geometry'),
        'failed_geometry_frames': crit.get('failed_geometry_frames'),
    }

    # ---- release trace: boundary, first 0.5 s, bins, steady ----
    rel = load(run / 'pfs1_release_steps.npz')
    rv = np.asarray(rel['vertices'], float); rt = np.asarray(rel['sim_time_s'], float)
    tb = float(rt[0])
    clock = read(run / 'pfs1_release_clock.json')
    first_json = read(run / 'pfs1_first_0_5s.json')

    j05 = max(i for i in range(len(rt)) if rt[i] <= tb + 0.5 + 1e-6)
    first_0_5 = finite_diff(rv, rt, 0, j05)
    first_0_5['centroid_direction_deg'] = centroid_direction(rv, rt, 0, j05)
    first_0_5['n_frames'] = int(j05 + 1)
    first_0_5['duration_s'] = float(rt[j05] - rt[0])

    bins = []
    for b in range(20):
        z = tb + 0.5 * (b + 1)
        idx = [i for i in range(len(rt)) if tb + 0.5 * b - 1e-9 <= rt[i] <= z + 1e-9]
        if len(idx) < 2:
            continue
        m = finite_diff(rv, rt, idx[0], idx[-1])
        m.update({'bin_start_s': 0.5 * b, 'bin_end_s': 0.5 * (b + 1),
                  'partial': bool(rt[idx[-1]] < z - 1e-9),
                  'z_min_mm': float(rv[idx[0]:idx[-1] + 1, :, 2].min() * 1000),
                  'below_contact_offset_mm': float((0.01 - rv[idx[0]:idx[-1] + 1, :, 2].min()) * 1000),
                  'ground_penetration_mm': float(max(0.0, -rv[idx[0]:idx[-1] + 1, :, 2].min() * 1000))})
        bins.append(m)

    steady_idx = [i for i in range(len(rt)) if tb + 1.5 - 1e-9 <= rt[i] <= tb + 8.0 + 1e-9]
    steady = finite_diff(rv, rt, steady_idx[0], steady_idx[-1])
    steady['centroid_direction_deg'] = centroid_direction(rv, rt, steady_idx[0], steady_idx[-1])
    steady['note'] = 'available traced post-release window is ~8.05 s; 10 s bins are not available'

    # ---- sticking / attachment checks ----
    def arr(name):
        return np.asarray(rel[name])

    att_after = arr('attachment_enabled_any')
    holding_after = arr('holding')
    latched_after = arr('logical_attached')
    cmd_holding_after = arr('command_holding')
    enabled_after = arr('enabled_slots')
    ee = np.asarray(rel['ee_m'], float)
    ap_ = np.asarray(rel['gripper_aperture_m'], float)
    gs = np.asarray(rel['gripper_state'])

    ee_z0 = float(ee[0, 2])
    retreat = [i for i in range(len(ee)) if ee[i, 2] > ee_z0 + 0.001]
    i_ret = retreat[0] if retreat else len(ee) - 1
    zmax = float(ee[:, 2].max())
    stop = [i for i in range(i_ret, len(ee)) if ee[i, 2] >= zmax - 1e-4]
    i_stop = stop[0] if stop else len(ee) - 1

    d_cloth_retreat = (rv[i_ret].mean(0) - rv[0].mean(0)) * 1000
    d_ee_retreat = (ee[i_ret] - ee[0]) * 1000
    cloth_disp_retreat = float(np.linalg.norm(d_cloth_retreat))
    ee_disp_retreat = float(np.linalg.norm(d_ee_retreat))
    if ee_disp_retreat > 1e-9 and cloth_disp_retreat > 1e-9:
        cos_retreat = float(np.dot(d_cloth_retreat, d_ee_retreat)
                            / (cloth_disp_retreat * ee_disp_retreat))
    else:
        cos_retreat = None
    ratio_retreat = cloth_disp_retreat / ee_disp_retreat if ee_disp_retreat > 1e-9 else None
    cloth_disp_tail = float(np.linalg.norm(rv[-1].mean(0) - rv[i_stop].mean(0)) * 1000)
    ee_disp_tail = float(np.linalg.norm(ee[-1] - ee[i_stop]) * 1000)
    tail_duration = float(rt[-1] - rt[i_stop])
    zmin_all = float(rv[:, :, 2].min() * 1000)

    # The public OPEN command latch stays "holding" for a few steps while the
    # attachment is already disabled.  It must be a short contiguous prefix and
    # must never reappear later.
    cmd = cmd_holding_after.astype(bool)
    latch = 0
    while latch < len(cmd) and cmd[latch]:
        latch += 1
    latch_contiguous_prefix = bool(not cmd[latch:].any())
    # gripper_state 0 = open in this backend; aperture must reach the open value.
    gripper_open_after = bool(int(gs[-1]) == 0 and float(ap_[-1]) >= 0.075)
    follows_ee = bool(cos_retreat is not None and cos_retreat > 0.8
                      and ratio_retreat is not None and ratio_retreat > 0.5)

    sticking = {
        'attachment_enabled_any_after_boundary': bool(att_after.any()),
        'logical_attached_after_boundary': bool(latched_after.any()),
        'holding_after_boundary': bool(holding_after.any()),
        'enabled_slots_any_after_boundary': bool(enabled_after.any()),
        'attachment_reactivation': bool(att_after.any() or latched_after.any()
                                        or holding_after.any() or enabled_after.any()),
        'command_holding_latch_steps': int(latch),
        'command_holding_contiguous_prefix_only': latch_contiguous_prefix,
        'gripper_state_first_last': [int(gs[0]), int(gs[-1])],
        'gripper_aperture_first_last_m': [float(ap_[0]), float(ap_[-1])],
        'gripper_open_after_release': gripper_open_after,
        'retreat_index': int(i_ret),
        'retreat_duration_s': float(rt[i_ret] - rt[0]),
        'retreat_end_index': int(i_stop),
        'cloth_centroid_disp_retreat_mm': cloth_disp_retreat,
        'ee_disp_retreat_mm': ee_disp_retreat,
        'cloth_follows_ee_ratio_retreat': ratio_retreat,
        'cloth_follows_ee_cos_retreat': cos_retreat,
        'cloth_follows_ee': follows_ee,
        'post_retreat_seconds': tail_duration,
        'cloth_centroid_disp_after_retreat_mm': cloth_disp_tail,
        'ee_disp_after_retreat_mm': ee_disp_tail,
        'ee_static_after_retreat': bool(ee_disp_tail < 0.5),
        'cloth_still_sliding_after_retreat': bool(cloth_disp_tail > 0.5),
        'z_min_all_mm': zmin_all,
        'ground_penetration_mm': float(max(0.0, -zmin_all)),
        'below_contact_offset_mm': float(10.0 - zmin_all),
        'note': ('attachment/holding/latch must stay false after the release boundary; '
                 'the OPEN command latch is allowed only as a short contiguous prefix; '
                 'cloth following the retreating EE while detached would be abnormal sticking.'),
    }
    sticking['pass'] = bool(
        not sticking['attachment_reactivation']
        and latch_contiguous_prefix and latch <= 12 and gripper_open_after
        and zmin_all > -0.01 and not follows_ee)

    # ---- RC2 baseline windows ----
    t2 = load(rc2 / 'success_trace.npz')
    rc2_trace = metrics_from_trace(np.asarray(t2['vertices'], float),
                                   np.asarray(t2['sim_time_s'], float), 210, 330)
    tr = load(run / 'success_trace.npz')
    new_trace = metrics_from_trace(np.asarray(tr['vertices'], float),
                                   np.asarray(tr['sim_time_s'], float), 210, 330)

    h2 = load(rc2 / 'pre_release_hold.npz')
    rec2 = load(rc2 / 'recovered.npz')['vertices']
    stages = {label: load(run / 'pfs1_stages' / (label + '.npz'))
              for label in ('initial_loaded', 'after_recovery', 'pre_release', 'release_boundary')}
    release_clock = read(run / 'pfs1_release_clock.json')
    hdt = float(np.asarray(h2['dt_s']).reshape(-1)[0]) if 'dt_s' in h2 else 1.0 / 60.0
    pre_hold = {
        'rc2_last_interval': finite_diff(h2['vertices'], np.arange(len(h2['vertices'])) * hdt,
                                         len(h2['vertices']) - 2, len(h2['vertices']) - 1),
        'note': 'RC2 pre-release hold last interval, world-position finite differences',
    }

    outj = {
        'scope': 'a5-rc2-pfs1-observation-v2 extension 4302 single vs RC2 4302 single; offline only',
        'seed': args.seed,
        'identity': {
            'run_result_dir': str(run),
            'run_manifest_sha256': ledger.get('manifest_sha256'),
            'run_config_sha256': ledger.get('config_sha256'),
            'rc2_result_dir': str(rc2),
            'rc2_manifest_sha256': v2.get('manifest_sha256'),
        },
        'integrity': integrity,
        'gate': gate,
        'first_0_5s': first_0_5,
        'saved_first_0_5s_json': first_json,
        'bins': bins,
        'steady_1_5_to_8_0s': steady,
        'release_clock': clock,
        'release_boundary': {
            'step': int(stages['release_boundary']['absolute_step']),
            'time_s': float(stages['release_boundary']['sim_time_s']),
            'holding': bool(stages['release_boundary']['holding']),
            'attached': bool(stages['release_boundary']['attachment_enabled_any']),
            'z_min_m': float(stages['release_boundary']['vertices'][:, 2].min())},
        'sticking': sticking,
        'recovery_state_vs_rc2': displacement(rec2, stages['after_recovery']['vertices']),
        'pre_release_state_vs_rc2_hold': displacement(h2['vertices'][-1], stages['pre_release']['vertices']),
        'pre_release_hold_rc2_last_interval': pre_hold,
        'formal': {
            'rc2_trace': rc2_trace,
            'new_trace': new_trace,
            'rc2_evaluator_stability': v2.get('criteria', {}).get('stability'),
            'new_evaluator_stability': v.get('criteria', {}).get('stability'),
            'note': 'trace endpoint displacement and world-position finite differences; evaluator stability is the official max-over-window metric.',
        },
        'quality': {
            'rc2': v2.get('criteria', {}).get('status'),
            'new': v.get('criteria', {}).get('status'),
            'rc2_checks': v2.get('criteria', {}).get('checks'),
            'new_checks': v.get('criteria', {}).get('checks'),
        },
        'fold': {'rc2': r2.get('fold_metrics'), 'new': r.get('fold_metrics'),
                 'rc2_held': r2.get('fold_held_check'), 'new_held': r.get('fold_held_check')},
        'recovery_metrics': {'rc2': r2.get('recovery_metrics'), 'new': r.get('recovery_metrics')},
        'actions': action_compare(r2, r),
        'errors': {'rc2': r2.get('errors'), 'new': r.get('errors')},
        'material_readback': {
            'present': (run / 'material_readbacks.json').is_file(),
            'stages': sorted((read(run / 'material_readbacks.json').get('stages') or {}).keys())
            if (run / 'material_readbacks.json').is_file() else [],
            'expected': read(run / 'material_readbacks.json').get('expected')
            if (run / 'material_readbacks.json').is_file() else None,
            'solver_effective': read(run / 'material_readbacks.json').get('solver_effective')
            if (run / 'material_readbacks.json').is_file() else None,
            'note': 'scene/USD readback only; solver-effective value is unverified.',
        },
        'contact_capability': read(run / 'contact_capability.json')
        if (run / 'contact_capability.json').is_file() else None,
        'boundaries': {
            'one_4302_single_only': True, 'no_retry': True,
            'no_4202_rerun': True, 'no_seven_case_rc': True, 'no_freeze': True,
            'no_heldout': True, 'formal_stage4_success_increment': 0,
            'not_ground_friction_fix_claim': True,
            'single_seed_does_not_prove_cross_seed': True,
        },
    }

    (out / 'comparison.json').write_text(json.dumps(outj, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    (out / 'sticking_checks.json').write_text(json.dumps(sticking, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    with (out / 'windows.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['window', 'n_frames', 'duration_s', 'centroid_speed_mean_mm_s',
                    'particle_mean_speed_mean_mm_s', 'angular_speed_mean_deg_s',
                    'z_min_mm', 'ground_penetration_mm', 'below_contact_offset_mm'])
        rows = [
            ('boundary_to_0.5s', first_0_5, float(rv[:, :, 2].min() * 1000)),
            ('steady_1.5_8.0s', steady, float(rv[:, :, 2].min() * 1000)),
            ('formal_210_330', new_trace, float(np.asarray(tr['vertices'], float)[:, :, 2].min() * 1000)),
            ('rc2_formal_210_330', rc2_trace, float(np.asarray(t2['vertices'], float)[:, :, 2].min() * 1000)),
        ]
        for name, m, zmin in rows:
            w.writerow([name, m.get('n_frames'), round(m.get('duration_s', 0), 6),
                        round(m.get('centroid_speed_mean_mm_s', 0), 6),
                        round(m.get('particle_mean_speed_mean_mm_s', 0), 6),
                        round(m.get('angular_speed_mean_deg_s', 0), 6),
                        round(zmin, 6), round(max(0.0, -zmin), 6), round(10.0 - zmin, 6)])

    with (out / 'bins.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['bin_start_s', 'bin_end_s', 'partial', 'n_frames', 'n_intervals',
                    'duration_s', 'particle_mean_speed_mean_mm_s', 'particle_mean_speed_max_mm_s',
                    'centroid_speed_mean_mm_s', 'centroid_speed_max_mm_s',
                    'angular_speed_mean_deg_s', 'angular_speed_max_deg_s',
                    'z_min_mm', 'below_contact_offset_mm', 'ground_penetration_mm'])
        for b in bins:
            w.writerow([b['bin_start_s'], b['bin_end_s'], b['partial'], b['n_frames'], b['n_intervals'],
                        round(b['duration_s'], 6),
                        round(b['particle_mean_speed_mean_mm_s'], 6),
                        round(b['particle_mean_speed_max_mm_s'], 6),
                        round(b['centroid_speed_mean_mm_s'], 6),
                        round(b['centroid_speed_max_mm_s'], 6),
                        round(b['angular_speed_mean_deg_s'], 6),
                        round(b['angular_speed_max_deg_s'], 6),
                        round(b['z_min_mm'], 6),
                        round(b['below_contact_offset_mm'], 6),
                        round(b['ground_penetration_mm'], 6)])

    summary = {
        'seed': args.seed,
        'file_complete': integrity['file_complete'],
        'observation_semantics_valid': integrity['observation_semantics_valid'],
        'quality_status': integrity['quality_status'],
        'overall_valid': integrity['overall_valid'],
        'geometry_entire_window': gate['geometry_entire_window'],
        'stable': gate['stable'],
        'centroid_drift_max_mm': gate['centroid_drift_max_mm'],
        'vertex_p95_max_mm': gate['vertex_p95_max_mm'],
        'pass_1mm_3mm': gate['pass_1mm_3mm'],
        'rc2_centroid_drift_max_mm': float((v2.get('criteria', {}).get('stability') or {})
                                           .get('centroid_drift_max_m', float('nan')) * 1000),
        'rc2_vertex_p95_max_mm': float((v2.get('criteria', {}).get('stability') or {})
                                       .get('vertex_drift_p95_max_m', float('nan')) * 1000),
        'first_0_5s_centroid_mm_s': first_0_5['centroid_speed_mean_mm_s'],
        'first_0_5s_particle_mm_s': first_0_5['particle_mean_speed_mean_mm_s'],
        'steady_centroid_mm_s': steady['centroid_speed_mean_mm_s'],
        'steady_particle_mm_s': steady['particle_mean_speed_mean_mm_s'],
        'steady_angular_deg_s': steady['angular_speed_mean_deg_s'],
        'z_min_mm': sticking['z_min_all_mm'],
        'sticking_pass': sticking['pass'],
        'release_reactivation': sticking['attachment_reactivation'],
        'command_holding_latch_steps': sticking['command_holding_latch_steps'],
        'fold_crossed': (r.get('fold_metrics') or {}).get('crossed_fraction'),
        'fold_held_check': r.get('fold_held_check'),
        'ledger_bad': len(integrity['ledger_bad']),
        'evidence_bad': len(integrity['evidence_bad']),
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    # ---- figure 1: post-release windows ----
    x = [(b['bin_start_s'] + b['bin_end_s']) / 2 for b in bins]
    fig, axes = plt.subplots(3, 1, figsize=(8.6, 7.0), sharex=True)
    axes[0].plot(x, [b['centroid_speed_mean_mm_s'] for b in bins], color=ORANGE, lw=1.8,
                 marker='o', ms=3, label='centroid')
    axes[0].plot(x, [b['particle_mean_speed_mean_mm_s'] for b in bins], color=BLUE, lw=1.2,
                 ls='--', label='particle mean')
    axes[0].set_ylabel('speed (mm/s)')
    axes[0].set_title('4302 single: post-release finite-difference speed (readback not used)')
    axes[0].legend(loc='best')
    axes[1].plot(x, [b['angular_speed_mean_deg_s'] for b in bins], color=ORANGE, lw=1.8, marker='o', ms=3)
    axes[1].set_ylabel('angular speed (deg/s)')
    axes[2].plot(x, [b['z_min_mm'] for b in bins], color=BLUE, lw=1.6, marker='o', ms=3)
    axes[2].axhline(10.0, color=SECONDARY, lw=1, ls=':', label='particle contact offset 10 mm')
    axes[2].set_ylabel('z_min (mm)'); axes[2].set_xlabel('time after release (s)')
    axes[2].legend(loc='best')
    for ax in axes:
        ax.grid(color=GRID, lw=.7); ax.set_axisbelow(True)
        for s in ('top', 'right'): ax.spines[s].set_visible(False)
        for s in ('left', 'bottom'): ax.spines[s].set_color(AXIS)
    fig.tight_layout(); fig.savefig(out / 'pfs1_v2_4302_windows.png', dpi=180); plt.close(fig)

    # ---- figure 2: formal trace ----
    Vn = np.asarray(tr['vertices'], float); Vr = np.asarray(t2['vertices'], float)
    xx = np.arange(121)
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    for tag, V, color in (('RC2', Vr, BLUE), ('pfs1-v2 4302', Vn, ORANGE)):
        d = np.linalg.norm(V[210:331] - V[210], axis=2) * 1000
        cent = np.linalg.norm(V[210:331].mean(1) - V[210].mean(0), axis=1) * 1000
        ax.plot(xx, cent, color=color, lw=1.8, label=tag + ' centroid')
        ax.plot(xx, np.percentile(d, 95, axis=1), color=color, lw=1.2, ls='--', label=tag + ' P95')
    ax.axhline(1.0, color=RED, lw=0.9, ls=':', label='centroid limit 1 mm')
    ax.axhline(3.0, color=RED, lw=0.9, ls='-.', label='P95 limit 3 mm')
    ax.set_xlabel('success_trace step (210..330)'); ax.set_ylabel('mm')
    ax.set_title('formal window 210-330: centroid / vertex P95')
    ax.legend(loc='best', ncol=2)
    ax.grid(color=GRID, lw=.7); ax.set_axisbelow(True)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'): ax.spines[s].set_color(AXIS)
    fig.tight_layout(); fig.savefig(out / 'formal_compare_4302.png', dpi=180); plt.close(fig)

    print('PFS1_V2_4302_COMPARE_OK', out / 'comparison.json')
    print('integrity', json.dumps({k: integrity[k] for k in ('file_complete', 'observation_semantics_valid',
                                                             'quality_status', 'overall_valid', 'ledger_bad',
                                                             'evidence_bad')}))
    print('gate', json.dumps({k: gate[k] for k in ('geometry_entire_window', 'stable', 'held',
                                                   'released_continuously', 'centroid_drift_max_mm',
                                                   'vertex_p95_max_mm', 'pass_1mm_3mm')}))
    print('sticking', json.dumps({k: sticking[k] for k in ('attachment_reactivation', 'pass', 'z_min_all_mm',
                                                           'command_holding_latch_steps',
                                                           'cloth_follows_ee_cos_retreat',
                                                           'cloth_follows_ee_ratio_retreat')}))
    print('first0.5', json.dumps({k: first_0_5[k] for k in ('n_frames', 'duration_s',
                                                            'particle_mean_speed_mean_mm_s',
                                                            'centroid_speed_mean_mm_s')}))
    print('steady', json.dumps({k: steady[k] for k in ('centroid_speed_mean_mm_s',
                                                       'particle_mean_speed_mean_mm_s',
                                                       'angular_speed_mean_deg_s')}))
    print('rc2/new formal', rc2_trace['centroid_mm'], new_trace['centroid_mm'],
          rc2_trace['p95_mm'], new_trace['p95_mm'])
    print('actions target/ee diff mm', outj['actions']['target_max_abs_diff_mm'],
          outj['actions']['ee_max_abs_diff_mm'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
