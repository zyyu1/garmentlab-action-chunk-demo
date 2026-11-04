#!/usr/bin/env python3
"""Offline localisation of the old/new 4202 L2 sensitivity (no simulation).

Compares the accepted rc8 4202 run (old initial, generated at 0.0) with the
failed rc8b 4202 run (new initial, generated at 1.0) at loaded, recovered,
pre-release and post-release stages.
"""
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
OLD = HERE / 'results' / 'RC8_SEVEN_CASE_20261104' / 'day4-a5-rc2-pfs1-observation-v2-20261104-234933-939207'
NEW = HERE / 'results' / 'RC8B_SEVEN_CASE_20261105' / 'day4-a5-rc2-pfs1-observation-v2-20261105-025057-237749'
OLD_INIT = Path(r'E:\learning\project\thesis\day4-actionchunk-test\results\A5_RC2_AUDIT_20261103T194913Z\day4-square-initial-stripfold-20261103-062710-242560')
NEW_INIT = HERE / 'results' / 'RC8B_INITIALS_20261105' / 'day4-square-initial-stripfold-20261105-015817-115841'
OUT = HERE / 'results' / 'RC8B_L2_DIAG_20261105'
OUT.mkdir(parents=True, exist_ok=True)

SURFACE = '#fcfcfb'; GRID = '#e1e0d9'; AXIS = '#c3c2b7'; BLUE = '#2a78d6'; ORANGE = '#eb6834'; RED = '#d03b3b'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
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
    mapped = a.copy(); mapped[:, :2] = (a - ca) @ r.T + cb
    d = np.linalg.norm(mapped - b, axis=1) * 1000
    return {'rotation_deg': float(math.degrees(math.atan2(r[1, 0], r[0, 0]))),
            'centroid_mm': float(np.linalg.norm(cb - ca) * 1000),
            'resid_mean_mm': float(d.mean()), 'resid_p95_mm': float(np.percentile(d, 95)),
            'resid_max_mm': float(d.max())}


def zstats(v):
    v = np.asarray(v, float); z = v[:, 2] * 1000
    return {'extent_m': np.ptp(v, axis=0).tolist(),
            'z_p50_mm': float(np.percentile(z, 50)), 'z_p95_mm': float(np.percentile(z, 95)),
            'z_max_mm': float(z.max()), 'frac_above_20mm': float((z > 20).mean())}


def unique_indices(times):
    out, last = [], None
    for k, t in enumerate(np.asarray(times, float)):
        if last is None or t - last > 1e-9:
            out.append(k); last = t
    return out


def fd_window(V, times):
    V = np.asarray(V, float); times = np.asarray(times, float)
    idx = unique_indices(times)
    dt = np.diff(times[idx])
    p = np.linalg.norm(V[idx[1:]] - V[idx[:-1]], axis=2).mean(1) * 1000 / dt
    c = np.linalg.norm(V[idx[1:]].mean(1) - V[idx[:-1]].mean(1), axis=1) * 1000 / dt
    return {'duration_s': float(times[idx[-1]] - times[idx[0]]),
            'particle_mean_mm_s': float(p.mean()), 'centroid_mean_mm_s': float(c.mean())}


def corners(flat):
    x, y = flat[:, 0], flat[:, 1]
    ids = [int(np.argmax(x + y)), int(np.argmax(x - y)), int(np.argmin(x + y)), int(np.argmin(x - y))]
    return sorted(set(ids))


stage_rows = []
for tag, run, init in (('old', OLD, OLD_INIT), ('new', NEW, NEW_INIT)):
    init_final = load(init / 'initial_geometry.npz')['final']
    stages = {s: load(run / 'pfs1_stages' / (s + '.npz')) for s in
              ('initial_loaded', 'after_recovery', 'pre_release', 'release_boundary')}
    stage_rows.append({'run': tag, 'init_final': init_final, 'stages': stages,
                       'result': read(run / 'result.json'), 'verdict': read(run / 'a5-verdict.json')})

old, new = stage_rows
compare = {}
for key in ('init_final',):
    compare[key] = rigid2d(new[key], old[key])
    compare[key].update({'new': zstats(new[key]), 'old': zstats(old[key])})
for s in ('initial_loaded', 'after_recovery', 'pre_release', 'release_boundary'):
    a = new['stages'][s]['vertices']; b = old['stages'][s]['vertices']
    compare[s] = rigid2d(a, b)
    compare[s].update({'new': zstats(a), 'old': zstats(b),
                       't_new': float(new['stages'][s]['sim_time_s']),
                       't_old': float(old['stages'][s]['sim_time_s'])})

# loaded/recovered internal consistency
for tag, row in (('old', old), ('new', new)):
    compare.setdefault('loaded_vs_init', {})[tag] = rigid2d(row['stages']['initial_loaded']['vertices'],
                                                             row['init_final'])

# recovery endpoint raw readback (unvalidated) and average rate
rec = {}
for tag, row in (('old', old), ('new', new)):
    s = row['stages']['after_recovery']
    v = np.asarray(s['readback_velocities'], float)
    rec[tag] = {'readback_mean_mm_s': float(np.linalg.norm(v, axis=1).mean() * 1000),
                'readback_max_mm_s': float(np.linalg.norm(v, axis=1).max() * 1000),
                'readback_validated': bool(s['readback_velocity_validated']),
                't_initial': float(row['stages']['initial_loaded']['sim_time_s']),
                't_recovered': float(s['sim_time_s']),
                'step_initial': int(row['stages']['initial_loaded']['absolute_step']),
                'step_recovered': int(s['absolute_step'])}
    rec[tag]['recovery_duration_s'] = rec[tag]['t_recovered'] - rec[tag]['t_initial']
    rec[tag]['recovered_centroid_shift_mm'] = float(np.linalg.norm(
        np.asarray(s['vertices']).mean(0) - np.asarray(row['stages']['initial_loaded']['vertices']).mean(0)) * 1000)
    rec[tag]['avg_centroid_rate_mm_s'] = rec[tag]['recovered_centroid_shift_mm'] / rec[tag]['recovery_duration_s']

# targets
targets = []
for i, (a, b) in enumerate(zip(old['result']['actions'], new['result']['actions'])):
    d = np.asarray(b['target_pose'], float) - np.asarray(a['target_pose'], float)
    targets.append({'index': i, 'label': a['label'],
                    'dx_mm': float(d[0] * 1000), 'dy_mm': float(d[1] * 1000), 'dz_mm': float(d[2] * 1000),
                    'dyaw_deg': float(math.degrees(d[3])), 'max_abs_mm': float(np.max(np.abs(d[:3])) * 1000)})

# pre-release hold drift
hold = {}
for tag, row in (('old', old), ('new', new)):
    h = load(row['result']['initial_dir'] and (OLD if tag == 'old' else NEW) / 'pre_release_hold.npz')
    V = np.asarray(h['vertices'], float); dt = float(h['dt_s'])
    hold[tag] = {'frames': len(V), 'duration_s': (len(V) - 1) * dt,
                 'centroid_disp_mm': float(np.linalg.norm(V[-1].mean(0) - V[0].mean(0)) * 1000),
                 'max_vertex_disp_mm': float(np.linalg.norm(V[-1] - V[0], axis=1).max() * 1000)}

# post-release bins and formal window
release = {}
for tag, row, run in (('old', old, OLD), ('new', new, NEW)):
    rs = load(run / 'pfs1_release_steps.npz')
    V = np.asarray(rs['vertices'], float); t = np.asarray(rs['sim_time_s'], float)
    t0 = float(t[0])
    bins = []
    for b in range(20):
        lo, hi = t0 + 0.5 * b, t0 + 0.5 * (b + 1)
        idx = [i for i in range(len(t)) if lo - 1e-6 <= t[i] <= hi + 1e-6]
        if len(idx) < 2:
            continue
        idx_u = unique_indices(t[idx[0]:idx[-1] + 1])
        sel = [idx[0] + k for k in idx_u]
        dt = np.diff(t[sel])
        cent = np.linalg.norm(V[sel[1:]].mean(1) - V[sel[:-1]].mean(1), axis=1) * 1000 / dt
        p = np.linalg.norm(V[sel[1:]] - V[sel[:-1]], axis=2).mean(1) * 1000 / dt
        bins.append({'bin': b, 'start_s': 0.5 * b, 'centroid_mm_s': float(cent.mean()),
                     'particle_mm_s': float(p.mean()),
                     'centroid_disp_mm': float(np.linalg.norm(V[sel[-1]].mean(0) - V[sel[0]].mean(0)) * 1000),
                     'z_min_mm': float(V[sel][:, :, 2].min() * 1000)})
    tr = load(run / 'success_trace.npz')
    TV = np.asarray(tr['vertices'], float)
    cent_end = np.linalg.norm(TV[210:331].mean(1) - TV[210].mean(0), axis=1) * 1000
    p95 = np.percentile(np.linalg.norm(TV[210:331] - TV[210], axis=2) * 1000, 95, axis=1)
    release[tag] = {'bins': bins, 'formal_centroid_end_mm': float(cent_end[-1]),
                    'formal_centroid_max_mm': float(cent_end.max()),
                    'formal_p95_end_mm': float(p95[-1]), 'formal_p95_max_mm': float(p95.max()),
                    'first_failed_step': (min(new['verdict']['criteria']['failed_geometry_frames'])
                                          if tag == 'new' and new['verdict']['criteria'].get('failed_geometry_frames') else None)}

first_fail = release['new']['first_failed_step']
first_fail_s = (first_fail - 0) / 60.0 if first_fail is not None else None
formal_start_s = 3.5

summary = {
    'scope': 'offline old/new 4202 L2 sensitivity; no simulation',
    'stage_compare': compare,
    'recovery_endpoint': rec,
    'targets': targets,
    'pre_release_hold': hold,
    'release': {k: {kk: vv for kk, vv in v.items() if kk != 'bins'} for k, v in release.items()},
    'first_failure_step_after_release': first_fail,
    'first_failure_time_after_release_s': first_fail_s,
    'formal_window_start_after_release_s': formal_start_s,
    'fold_yaw_old_deg': math.degrees(old['result']['fold_yaw']),
    'fold_yaw_new_deg': math.degrees(new['result']['fold_yaw']),
    'fold_yaw_diff_deg': math.degrees(new['result']['fold_yaw'] - old['result']['fold_yaw']),
    'fold_extent_old_m': old['result']['fold_metrics']['extent'],
    'fold_extent_new_m': new['result']['fold_metrics']['extent'],
    'stationary_drift_old_m': (old['verdict']['criteria'].get('final_geometry') or {}).get('metrics', {}).get('stationary_drift_mean_m'),
    'stationary_drift_new_m': (new['verdict']['criteria'].get('final_geometry') or {}).get('metrics', {}).get('stationary_drift_mean_m'),
}
(OUT / 'comparison.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')

with (OUT / 'stages.csv').open('w', newline='', encoding='utf-8') as f:
    import csv
    w = csv.writer(f)
    w.writerow(['stage', 'centroid_mm', 'rotation_deg', 'resid_mean_mm', 'resid_p95_mm', 'resid_max_mm',
                'new_extent_x', 'new_extent_y', 'new_z_p95_mm', 'old_extent_x', 'old_extent_y', 'old_z_p95_mm'])
    for key in ('init_final', 'initial_loaded', 'after_recovery', 'pre_release', 'release_boundary'):
        c = compare[key]
        w.writerow([key, round(c['centroid_mm'], 5), round(c['rotation_deg'], 5),
                    round(c['resid_mean_mm'], 5), round(c['resid_p95_mm'], 5), round(c['resid_max_mm'], 5),
                    round(c['new']['extent_m'][0], 5), round(c['new']['extent_m'][1], 5), round(c['new']['z_p95_mm'], 3),
                    round(c['old']['extent_m'][0], 5), round(c['old']['extent_m'][1], 5), round(c['old']['z_p95_mm'], 3)])

with (OUT / 'bins.csv').open('w', newline='', encoding='utf-8') as f:
    import csv
    w = csv.writer(f)
    w.writerow(['bin', 'start_s', 'old_centroid_mm_s', 'new_centroid_mm_s', 'old_particle_mm_s', 'new_particle_mm_s',
                'old_centroid_disp_mm', 'new_centroid_disp_mm', 'old_z_min_mm', 'new_z_min_mm'])
    for ob, nb in zip(release['old']['bins'], release['new']['bins']):
        w.writerow([ob['bin'], ob['start_s'], round(ob['centroid_mm_s'], 5), round(nb['centroid_mm_s'], 5),
                    round(ob['particle_mm_s'], 5), round(nb['particle_mm_s'], 5),
                    round(ob['centroid_disp_mm'], 5), round(nb['centroid_disp_mm'], 5),
                    round(ob['z_min_mm'], 4), round(nb['z_min_mm'], 4)])

fig, axes = plt.subplots(1, 2, figsize=(10.6, 3.6))
keys = ['init_final', 'initial_loaded', 'after_recovery', 'pre_release']
x = np.arange(len(keys))
axes[0].plot(x, [compare[k]['centroid_mm'] for k in keys], marker='o', color=BLUE, label='centroid offset')
axes[0].plot(x, [compare[k]['resid_p95_mm'] for k in keys], marker='s', color=ORANGE, label='P95 residual after alignment')
axes[0].set_xticks(x); axes[0].set_xticklabels(keys, rotation=20)
axes[0].set_ylabel('mm'); axes[0].set_title('old vs new 4202: stage difference'); axes[0].legend(fontsize=7)
xb = [b['start_s'] for b in release['old']['bins']]
axes[1].plot(xb, [b['centroid_mm_s'] for b in release['old']['bins']], color=BLUE, marker='o', ms=3, label='old centroid')
axes[1].plot(xb, [b['centroid_mm_s'] for b in release['new']['bins']], color=ORANGE, marker='o', ms=3, label='new centroid')
axes[1].set_xlabel('time after release (s)'); axes[1].set_ylabel('mm/s'); axes[1].set_title('post-release centroid speed')
axes[1].legend(fontsize=7)
for ax in axes:
    ax.grid(color=GRID, lw=.7); ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(AXIS)
fig.tight_layout(); fig.savefig(OUT / 'l2_stage_release.png', dpi=180); plt.close(fig)

print('L2_DIAG_OK', OUT / 'comparison.json')
for k in keys:
    c = compare[k]
    print(k, 'centroid', round(c['centroid_mm'], 4), 'rot', round(c['rotation_deg'], 4),
          'resid_p95', round(c['resid_p95_mm'], 4), 'resid_max', round(c['resid_max_mm'], 4))
print('recovery', json.dumps(rec))
print('hold', json.dumps(hold))
print('first_fail', first_fail, first_fail_s)
print('fold extent old/new', old['result']['fold_metrics']['extent'], new['result']['fold_metrics']['extent'])
