#!/usr/bin/env python3
"""Offline a5-rc2-pfs1-observation-v2 review.

No simulation.  V2 physics/control is inherited from pfs1 and only observation
changed.  All speeds are world-vertex finite differences; the raw API readback
is retained as unvalidated data and is not used as physical velocity.
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
    times = np.asarray(times, float)
    if j is None:
        j = len(times) - 1
    out = []; last = None
    for k in range(int(i), int(j) + 1):
        t = float(times[k])
        if last is None or t - last > 1e-9:
            out.append(k); last = t
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
    delta = (V[idx[-1]].mean(0) - V[idx[0]].mean(0)) * 1000
    return {'n_frames': int(len(idx)), 'n_intervals': int(len(idx) - 1),
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
            'centroid_direction_deg': float(math.degrees(math.atan2(delta[1], delta[0])))}


def metrics_from_trace(V, times, i, j):
    d = displacement(V[i], V[j])
    d.update({'centroid_speed_mm_s': d['centroid_mm'] / float(times[j] - times[i])})
    d.update(finite_diff(V, times, i, j))
    return d


def action_compare(r1, r2):
    a, b = r1.get('actions') or [], r2.get('actions') or []
    n = min(len(a), len(b)); target_max = ee_max = 0.0
    labels = commands = True; per_action = []
    for k in range(n):
        labels &= a[k].get('label') == b[k].get('label')
        commands &= int(a[k].get('command', -1)) == int(b[k].get('command', -2))
        x = np.asarray(a[k].get('target_pose'), float); y = np.asarray(b[k].get('target_pose'), float)
        if x.shape != y.shape:
            per_action.append({'index': k, 'label': a[k].get('label'), 'shape_mismatch': True})
        else:
            d = y - x; target_max = max(target_max, float(np.max(np.abs(d))))
            per_action.append({'index': k, 'label': a[k].get('label'),
                               'max_abs_mm': float(np.max(np.abs(d)) * 1000),
                               'vector_mm': (d * 1000).tolist()})
        if 'ee' in a[k] and 'ee' in b[k]:
            ee_max = max(ee_max, float(np.max(np.abs(np.asarray(a[k]['ee'], float) - np.asarray(b[k]['ee'], float)))))
    return {'pfs1_actions': len(a), 'v2_actions': len(b), 'labels_identical': bool(labels),
            'commands_identical': bool(commands), 'target_max_abs_diff_mm': target_max * 1000,
            'ee_max_abs_diff_mm': ee_max * 1000, 'per_action': per_action,
            'horizons_identical': r1.get('call_horizons') == r2.get('call_horizons'),
            'labels': r2.get('action_labels')}


def material_summary(result):
    path = Path(result) / 'material_readbacks.json'
    if not path.is_file():
        return {'present': False}
    data = json.loads(path.read_text())
    rows = {}
    for label, rec in (data.get('stages') or {}).items():
        if label == 'after_construction':
            rows[label] = {
                'friction': (rec.get('friction') or {}).get('value'),
                'particle_friction_scale': (rec.get('particle_friction_scale') or {}).get('value'),
                'expected_ok': rec.get('expected_ok'),
                'scope': rec.get('readback_scope')}
            continue
        pm = rec.get('particle_material') or {}
        rows[label] = {
            'material_path': pm.get('prim_path'),
            'friction': (pm.get('friction') or {}).get('value'),
            'particle_friction_scale': (pm.get('particle_friction_scale') or {}).get('value'),
            'binding_targets': rec.get('binding_targets'),
            'self_collision': rec.get('self_collision_value'),
            'non_particle_collision': rec.get('non_particle_collision_value'),
            'particle_contact_offset': (rec.get('particle_system') or {}).get('particle_contact_offset'),
            'particle_group': rec.get('particle_group'),
            'filter_readback': rec.get('filter_readback'),
            'expected_ok': rec.get('expected_ok'),
            'solver_effective': rec.get('solver_effective')}
    return {'present': True,
            'expected': data.get('expected'),
            'solver_effective': data.get('solver_effective'),
            'velocity_policy': data.get('velocity_policy'),
            'stages': rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pfs1', type=Path, required=True)
    ap.add_argument('--v2', type=Path, required=True)
    ap.add_argument('--rc2', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    p1, p2, rc2, out = args.pfs1.resolve(), args.v2.resolve(), args.rc2.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    r1 = read(p1 / 'result.json'); r2 = read(p2 / 'result.json')
    v1 = read(p1 / 'a5-verdict.json'); v2 = read(p2 / 'a5-verdict.json')
    rr = read(rc2 / 'result.json'); vr = read(rc2 / 'a5-verdict.json')
    t1 = load(p1 / 'success_trace.npz'); t2 = load(p2 / 'success_trace.npz'); tr = load(rc2 / 'success_trace.npz')
    h1 = load(p1 / 'pre_release_hold.npz'); h2 = load(p2 / 'pre_release_hold.npz'); hr = load(rc2 / 'pre_release_hold.npz')
    rec1 = load(p1 / 'recovered.npz')['vertices']; rec2 = load(p2 / 'recovered.npz')['vertices']; recr = load(rc2 / 'recovered.npz')['vertices']
    st1 = {n: load(p1 / 'pfs1_stages' / (n + '.npz')) for n in ('initial_loaded', 'after_recovery', 'pre_release', 'release_boundary')}
    st2 = {n: load(p2 / 'pfs1_stages' / (n + '.npz')) for n in ('initial_loaded', 'after_recovery', 'pre_release', 'release_boundary')}
    rel1 = load(p1 / 'pfs1_release_steps.npz'); rel2 = load(p2 / 'pfs1_release_steps.npz')
    clock1 = read(p1 / 'pfs1_release_clock.json'); clock2 = read(p2 / 'pfs1_release_clock.json')

    outj = {'scope': 'a5-rc2-pfs1-observation-v2 vs a5-rc2-pfs1 and RC2; offline', 'actions': action_compare(r1, r2)}
    outj['recovery_state_vs_pfs1'] = displacement(rec1, rec2)
    outj['pre_release_state_vs_pfs1'] = displacement(h1['vertices'][-1], st2['pre_release']['vertices'])
    outj['recovery_state_vs_rc2'] = displacement(recr, rec2)
    outj['pre_release_state_vs_rc2'] = displacement(hr['vertices'][-1], st2['pre_release']['vertices'])
    for tag, h, dt in (('pfs1', h1, float(np.asarray(h1['dt_s']).reshape(-1)[0]) if 'dt_s' in h1 else 1/60),
                       ('v2', h2, float(np.asarray(h2['dt_s']).reshape(-1)[0]) if 'dt_s' in h2 else 1/60),
                       ('rc2', hr, float(np.asarray(hr['dt_s']).reshape(-1)[0]) if 'dt_s' in hr else 1/60)):
        outj.setdefault('pre_release_velocity', {})[tag] = finite_diff(
            h['vertices'], np.arange(len(h['vertices'])) * dt, len(h['vertices']) - 2, len(h['vertices']) - 1)
    outj['release_clock'] = {'pfs1': clock1, 'v2': clock2}
    outj['release_boundary_state'] = {
        'step': int(st2['release_boundary']['absolute_step']),
        'time_s': float(st2['release_boundary']['sim_time_s']),
        'holding': bool(st2['release_boundary']['holding']),
        'attached': bool(st2['release_boundary']['attachment_enabled_any']),
        'z_min_m': float(st2['release_boundary']['vertices'][:, 2].min())}
    tb = float(clock2['release_boundary']['sim_time_s'])
    V = np.asarray(rel2['vertices'], float); T = np.asarray(rel2['sim_time_s'], float)
    j05 = max(i for i in range(len(T)) if T[i] <= tb + .5 + 1e-6)
    outj['first_0_5s'] = finite_diff(V, T, 0, j05)
    outj['first_0_5s']['first_absolute_step'] = int(rel2['absolute_step'][0])
    outj['first_0_5s']['last_absolute_step'] = int(rel2['absolute_step'][j05])
    bins = []
    for b in range(20):
        a = tb + .5 * b; z = tb + .5 * (b + 1)
        idx = [i for i in range(len(T)) if a - 1e-6 <= T[i] <= z + 1e-6]
        if len(idx) < 2:
            continue
        m = finite_diff(V, T, idx[0], idx[-1])
        m.update({'bin_start_s': .5 * b, 'bin_end_s': .5 * (b + 1),
                  'partial': bool(T[idx[-1]] < z - 1e-6),
                  'z_min_mm': float(V[idx[0]:idx[-1] + 1, :, 2].min() * 1000),
                  'below_contact_offset_mm': float((.01 - V[idx[0]:idx[-1] + 1, :, 2].min()) * 1000),
                  'ground_penetration_mm': float(max(0.0, -V[idx[0]:idx[-1] + 1, :, 2].min() * 1000))})
        bins.append(m)
    outj['bins'] = bins
    steady = [i for i in range(len(T)) if tb + 1.5 - 1e-9 <= T[i] <= tb + 8.0 + 1e-9]
    outj['steady_1_5_to_8_0s'] = finite_diff(V, T, steady[0], steady[-1])
    outj['formal'] = {
        'pfs1_trace': metrics_from_trace(t1['vertices'], t1['sim_time_s'], 210, 330),
        'v2_trace': metrics_from_trace(t2['vertices'], t2['sim_time_s'], 210, 330),
        'rc2_trace': metrics_from_trace(tr['vertices'], tr['sim_time_s'], 210, 330),
        'pfs1_evaluator': v1.get('criteria', {}).get('stability'),
        'v2_evaluator': v2.get('criteria', {}).get('stability'),
        'rc2_evaluator': vr.get('criteria', {}).get('stability')}
    outj['quality'] = {'pfs1': v1.get('criteria', {}).get('status'),
                       'v2': v2.get('criteria', {}).get('status'),
                       'rc2': vr.get('criteria', {}).get('status'),
                       'v2_checks': v2.get('criteria', {}).get('checks'),
                       'v2_errors': v2.get('errors')}
    outj['fold'] = {'pfs1': r1.get('fold_metrics'), 'v2': r2.get('fold_metrics'),
                    'pfs1_held': r1.get('fold_held_check'), 'v2_held': r2.get('fold_held_check')}
    outj['recovery_metrics'] = {'pfs1': r1.get('recovery_metrics'), 'v2': r2.get('recovery_metrics')}
    outj['material_readback'] = material_summary(p2)
    sem_path = p2 / 'pfs1_semantics.json'
    outj['semantics'] = read(sem_path) if sem_path.is_file() else {'present': False}
    ledger_path = p2 / 'pfs1_observation_v2_ledger.json'
    outj['ledger'] = read(ledger_path) if ledger_path.is_file() else {'present': False}
    contact_path = p2 / 'contact_capability.json'
    outj['contact_capability'] = read(contact_path) if contact_path.is_file() else {'present': False}
    # Raw readback diagnostic in v2: document, never use.
    relmeta = read(p2 / 'pfs1_release_steps.json')
    outj['raw_readback'] = {
        'validated': False,
        'status': relmeta.get('readback_velocity_status'),
        'api': 'ClothPrimView.get_velocities(clone=True)',
        'fd_method': relmeta.get('fd_method'),
        'fd_time_source': relmeta.get('fd_time_source'),
        'fd_interval': relmeta.get('fd_interval'),
        'fd_velocity_valid_count': relmeta.get('fd_velocity_valid_count'),
        'fd_velocity_invalid_count': relmeta.get('fd_velocity_invalid_count'),
        'note': 'Raw readback is retained only as unvalidated data; all speeds above are finite differences.'}
    outj['boundaries'] = {'one_4202_single_only': True, 'no_retry': True,
                          'no_4302_yet': True, 'no_seven_case_rc': True,
                          'no_freeze': True, 'no_heldout': True,
                          'formal_stage4_success_increment': 0,
                          'ground_friction_fix_claim': False}
    (out / 'comparison.json').write_text(json.dumps(outj, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    with (out / 'v2_bins.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['bin_start_s', 'bin_end_s', 'partial', 'n_frames',
            'duration_s', 'particle_mean_speed_mean_mm_s', 'particle_mean_speed_max_mm_s',
            'centroid_speed_mean_mm_s', 'centroid_speed_max_mm_s',
            'angular_speed_mean_deg_s', 'angular_speed_max_deg_s',
            'z_min_mm', 'below_contact_offset_mm', 'ground_penetration_mm'])
        for b in bins:
            w.writerow([b['bin_start_s'], b['bin_end_s'], b['partial'], b['n_frames'],
                        b['duration_s'], b['particle_mean_speed_mean_mm_s'],
                        b['particle_mean_speed_max_mm_s'], b['centroid_speed_mean_mm_s'],
                        b['centroid_speed_max_mm_s'], b['angular_speed_mean_deg_s'],
                        b['angular_speed_max_deg_s'], b['z_min_mm'],
                        b['below_contact_offset_mm'], b['ground_penetration_mm']])

    fig, axes = plt.subplots(2, 1, figsize=(8.6, 5.8), sharex=False)
    x = [(b['bin_start_s'] + b['bin_end_s']) / 2 for b in bins]
    axes[0].plot(x, [b['centroid_speed_mean_mm_s'] for b in bins], color=ORANGE, lw=1.8, marker='o', ms=3, label='v2 centroid')
    axes[0].plot(x, [b['particle_mean_speed_mean_mm_s'] for b in bins], color=BLUE, lw=1.2, ls='--', label='v2 particle mean')
    axes[0].set_ylabel('speed (mm/s)'); axes[0].set_title('a5-rc2-pfs1-observation-v2: finite-difference post-release speed')
    axes[0].legend(loc='best')
    xx = np.arange(121)
    for tag, t, color in (('RC2', tr, BLUE), ('pfs1', t1, ORANGE), ('v2', t2, '#2f9e44')):
        vv = t['vertices']; tt = t['sim_time_s']
        d = np.linalg.norm(vv[210:331] - vv[210], axis=2) * 1000
        cent = np.linalg.norm(vv[210:331].mean(1) - vv[210].mean(0), axis=1) * 1000
        axes[1].plot(xx, cent, color=color, lw=1.8, label=tag + ' centroid')
        axes[1].plot(xx, np.percentile(d, 95, axis=1), color=color, lw=1.1, ls='--', label=tag + ' P95')
    axes[1].set_xlabel('success_trace step (210..330)'); axes[1].set_ylabel('mm')
    axes[1].set_title('formal window: centroid / vertex P95'); axes[1].legend(loc='best', ncol=3, fontsize=6.8)
    for ax in axes:
        ax.grid(color=GRID, lw=.7); ax.set_axisbelow(True)
        for s in ('top', 'right'): ax.spines[s].set_visible(False)
        for s in ('left', 'bottom'): ax.spines[s].set_color(AXIS)
    fig.tight_layout(); fig.savefig(out / 'v2_vs_pfs1.png', dpi=180); plt.close(fig)
    print('V2_COMPARE_OK', out / 'comparison.json')
    print('quality', outj['quality'])
    print('first0.5', outj['first_0_5s'])
    print('steady', outj['steady_1_5_to_8_0s'])
    print('formal v2', outj['formal']['v2_evaluator'])
    print('semantics', outj['semantics'].get('observation_semantics') if isinstance(outj['semantics'], dict) else None)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
