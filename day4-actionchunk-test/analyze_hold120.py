"""Analyze the recovery-hold120 run: hold decay and downstream comparison."""
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
HOLD = HERE / 'results' / 'RC8B_L2_DIAG_20261105' / 'hold120_run' / 'day4-a5-rc2-pfs1-observation-v2-20261105-064625-336724'
NEW = HERE / 'results' / 'RC8B_SEVEN_CASE_20261105' / 'day4-a5-rc2-pfs1-observation-v2-20261105-025057-237749'
OLD = HERE / 'results' / 'RC8_SEVEN_CASE_20261104' / 'day4-a5-rc2-pfs1-observation-v2-20261104-234933-939207'
OUT = HERE / 'results' / 'RC8B_L2_DIAG_20261105'


def read(p):
    return json.loads(Path(p).read_text())


def load(p):
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def yaw_between(a, b):
    ca, cb = a[:, :2].mean(0), b[:, :2].mean(0)
    h = (a[:, :2] - ca).T @ (b[:, :2] - cb)
    u, s, vt = np.linalg.svd(h)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1; r = vt.T @ u.T
    return float(math.degrees(math.atan2(r[1, 0], r[0, 0])))


hz = load(HOLD / 'recovery_hold_trace.npz')
meta = read(HOLD / 'recovery_hold_metadata.json')
t = np.asarray(hz['sim_time_s'], float)
V = np.asarray(hz['vertices'], float)
fd = np.asarray(hz['fd_velocities'], float)
ee = np.asarray(hz['ee_m'], float)
hold_bins = []
for b in range(4):
    lo, hi = b * 0.5, (b + 1) * 0.5
    idx = [i for i in range(len(t)) if lo - 1e-9 <= t[i] - t[0] <= hi + 1e-9]
    if len(idx) < 2:
        continue
    sel = idx
    dt = t[sel[-1]] - t[sel[0]]
    disp = V[sel[-1]].mean(0) - V[sel[0]].mean(0)
    part = np.linalg.norm(fd[sel[0]:sel[-1]], axis=2) * 1000
    cent = np.linalg.norm(fd[sel[0]:sel[-1]].mean(1), axis=1) * 1000
    hold_bins.append({
        'window_s': [lo, hi], 'frames': len(sel),
        'centroid_speed_mm_s': float(cent.mean()),
        'particle_p95_mm_s': float(np.percentile(part, 95)),
        'particle_mean_mm_s': float(part.mean()),
        'rotation_deg': yaw_between(V[sel[0]], V[sel[-1]]),
        'rotation_rate_deg_s': yaw_between(V[sel[0]], V[sel[-1]]) / dt,
        'centroid_disp_mm': float(np.linalg.norm(disp) * 1000),
        'z_p95_change_mm': float((np.percentile(V[sel[-1]][:, 2], 95) - np.percentile(V[sel[0]][:, 2], 95)) * 1000),
        'ee_drift_mm': float(np.linalg.norm(ee[sel[-1]] - ee[sel[0]]) * 1000),
        'all_holding_false': bool(not hz['holding'][sel].any()),
        'all_attachments_off': bool(not hz['logical_attached'][sel].any() and not hz['attachment_enabled_any'][sel].any()),
    })

events = {e['name']: e for e in read(HOLD / 'result.json')['events']}
r_hold, r_new, r_old = read(HOLD / 'result.json'), read(NEW / 'result.json'), read(OLD / 'result.json')
v_hold, v_new, v_old = read(HOLD / 'a5-verdict.json')['criteria'], read(NEW / 'a5-verdict.json')['criteria'], read(OLD / 'a5-verdict.json')['criteria']

targets_new = np.asarray([x['target_pose'] for x in r_new['actions']], float)
targets_hold = np.asarray([x['target_pose'] for x in r_hold['actions']], float)
target_diff = np.abs(targets_new - targets_hold)

stages = {}
for s in ('pre_release', 'release_boundary'):
    a = np.asarray(load(HOLD / 'pfs1_stages' / (s + '.npz'))['vertices'], float)
    b = np.asarray(load(NEW / 'pfs1_stages' / (s + '.npz'))['vertices'], float)
    d = np.linalg.norm(a - b, axis=1) * 1000
    stages[s] = {'max_mm': float(d.max()), 'mean_mm': float(d.mean()),
                 'centroid_mm': float(np.linalg.norm(a.mean(0) - b.mean(0)) * 1000)}


def bins(run):
    rs = load(run / 'pfs1_release_steps.npz')
    Vv = np.asarray(rs['vertices'], float); tt = np.asarray(rs['sim_time_s'], float)
    t0 = float(tt[0]); out = []
    for b in range(20):
        idx = [i for i in range(len(tt)) if t0 + .5 * b - 1e-6 <= tt[i] <= t0 + .5 * (b + 1) + 1e-6]
        if len(idx) < 2:
            continue
        u, last = [], None
        for i in idx:
            if last is None or tt[i] - last > 1e-9:
                u.append(i); last = tt[i]
        dt = np.diff(tt[u])
        c = np.linalg.norm(Vv[u[1:]].mean(1) - Vv[u[:-1]].mean(1), axis=1) * 1000 / dt
        p = np.linalg.norm(Vv[u[1:]] - Vv[u[:-1]], axis=2).mean(1) * 1000 / dt
        out.append({'start_s': .5 * b, 'centroid_mm_s': float(c.mean()),
                    'particle_mm_s': float(p.mean()),
                    'disp_mm': float(np.linalg.norm(Vv[u[-1]].mean(0) - Vv[u[0]].mean(0)) * 1000)})
    return out


res = {
    'hold': {'frames': int(len(t)), 'intervals': int(len(fd)),
             'duration_s': float(t[-1] - t[0]),
             'bins': hold_bins,
             'retreat_end': events.get('recovery_retreat_end'),
             'hold_begin': events.get('recovery_hold_begin'),
             'hold_end': events.get('recovery_hold_end'),
             'fold_observation': events.get('fold_observation'),
             'all_states_ok': bool(not hz['holding'].any() and not hz['logical_attached'].any()
                                   and not hz['command_holding'].any()
                                   and not hz['attachment_enabled_any'].any()),
             'control_target_constant': bool(np.array_equal(np.asarray(hz['control_target']),
                                                            np.repeat(np.asarray(hz['control_target'])[:1], len(t), 0))),
             'fd_interval_s': np.asarray(hz['fd_interval_s'], float).tolist()},
    'quality': {'old': v_old['status'], 'new': v_new['status'], 'hold120': v_hold['status']},
    'stability_mm': {'old': [v_old['stability']['centroid_drift_max_m'] * 1000, v_old['stability']['vertex_drift_p95_max_m'] * 1000],
                     'new': [v_new['stability']['centroid_drift_max_m'] * 1000, v_new['stability']['vertex_drift_p95_max_m'] * 1000],
                     'hold120': [v_hold['stability']['centroid_drift_max_m'] * 1000, v_hold['stability']['vertex_drift_p95_max_m'] * 1000]},
    'stationary_mm': {'old': v_old['final_geometry']['metrics']['stationary_drift_mean_m'] * 1000,
                      'new': v_new['final_geometry']['metrics']['stationary_drift_mean_m'] * 1000,
                      'hold120': v_hold['final_geometry']['metrics']['stationary_drift_mean_m'] * 1000},
    'first_fail': {'new': min(v_new.get('failed_geometry_frames') or [0]),
                   'hold120': min(v_hold.get('failed_geometry_frames') or [0])},
    'fail_count': {'new': len(v_new.get('failed_geometry_frames') or []),
                   'hold120': len(v_hold.get('failed_geometry_frames') or [])},
    'fold_yaw_diff_deg': float(math.degrees(r_hold['fold_yaw'] - r_new['fold_yaw'])),
    'target_max_mm': float(target_diff[:, :3].max() * 1000),
    'target_max_yaw_deg': float(math.degrees(target_diff[:, 3].max())),
    'stages_vs_new': stages,
    'fold_extent': {'old': r_old['fold_metrics']['extent'], 'new': r_new['fold_metrics']['extent'],
                    'hold120': r_hold['fold_metrics']['extent']},
    'bins_new': bins(NEW), 'bins_hold120': bins(HOLD),
}
(OUT / 'hold120_compare.json').write_text(json.dumps(res, indent=2) + '\n', encoding='utf-8')
print('HOLD120_ANALYSIS frames', res['hold']['frames'], 'intervals', res['hold']['intervals'], 'duration', round(res['hold']['duration_s'], 6))
for b in hold_bins:
    print(' hold', b['window_s'], 'cent', round(b['centroid_speed_mm_s'], 4),
          'p95', round(b['particle_p95_mm_s'], 4), 'rot', round(b['rotation_deg'], 5),
          'ee', round(b['ee_drift_mm'], 5), 'states', b['all_holding_false'], b['all_attachments_off'])
print('quality', res['quality'], 'stab', res['stability_mm'])
print('stationary', res['stationary_mm'], 'firstfail', res['first_fail'], 'fails', res['fail_count'])
print('target max mm', round(res['target_max_mm'], 4), 'yaw', round(res['target_max_yaw_deg'], 5), 'fold_yaw', round(res['fold_yaw_diff_deg'], 5))
print('stages', {k: (round(v['max_mm'], 4), round(v['mean_mm'], 4)) for k, v in stages.items()})
