"""Compare 4302 hold120 against the rc8b 4302 single."""
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
HOLD = HERE / 'results' / 'RC8B_L2_DIAG_20261105' / 'hold120_r2_4302' / 'day4-a5-rc2-pfs1-observation-v2-20261105-074146-551052'
REF = HERE / 'results' / 'RC8B_SEVEN_CASE_20261105' / 'day4-a5-rc2-pfs1-observation-v2-20261105-031858-626939'
OUT = HERE / 'results' / 'RC8B_L2_DIAG_20261105'


def read(p):
    return json.loads(Path(p).read_text())


def load(p):
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def yaw(a, b):
    ca, cb = a[:, :2].mean(0), b[:, :2].mean(0)
    h = (a[:, :2] - ca).T @ (b[:, :2] - cb)
    u, s, vt = np.linalg.svd(h); r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1; r = vt.T @ u.T
    return float(math.degrees(math.atan2(r[1, 0], r[0, 0])))


hz = load(HOLD / 'recovery_hold_trace.npz')
t = np.asarray(hz['sim_time_s'], float); V = np.asarray(hz['vertices'], float)
fd = np.asarray(hz['fd_velocities'], float); ee = np.asarray(hz['ee_m'], float)
bins = []
for b in range(4):
    lo, hi = b * .5, (b + 1) * .5
    idx = [i for i in range(len(t)) if lo - 1e-9 <= t[i] - t[0] <= hi + 1e-9]
    part = np.linalg.norm(fd[idx[0]:idx[-1]], axis=2) * 1000
    cent = np.linalg.norm(fd[idx[0]:idx[-1]].mean(1), axis=1) * 1000
    bins.append({'window_s': [lo, hi], 'centroid_mm_s': float(cent.mean()),
                 'particle_p95_mm_s': float(np.percentile(part, 95)),
                 'rotation_deg': yaw(V[idx[0]], V[idx[-1]]),
                 'ee_drift_mm': float(np.linalg.norm(ee[idx[-1]] - ee[idx[0]]) * 1000),
                 'centroid_disp_mm': float(np.linalg.norm(V[idx[-1]].mean(0) - V[idx[0]].mean(0)) * 1000)})

r_h, r_r = read(HOLD / 'result.json'), read(REF / 'result.json')
v_h, v_r = read(HOLD / 'a5-verdict.json')['criteria'], read(REF / 'a5-verdict.json')['criteria']
stages = {}
for s in ('initial_loaded', 'after_recovery', 'pre_release', 'release_boundary'):
    a = np.asarray(load(HOLD / 'pfs1_stages' / (s + '.npz'))['vertices'], float)
    b = np.asarray(load(REF / 'pfs1_stages' / (s + '.npz'))['vertices'], float)
    d = np.linalg.norm(a - b, axis=1) * 1000
    stages[s] = {'max_mm': float(d.max()), 'mean_mm': float(d.mean())}
ta = np.asarray([x['target_pose'] for x in r_r['actions']], float)
tb = np.asarray([x['target_pose'] for x in r_h['actions']], float)
dt = np.abs(ta - tb)

res = {
    'hold': {'frames': len(t), 'intervals': len(fd), 'duration_s': float(t[-1] - t[0]), 'bins': bins,
             'all_states_ok': bool(not hz['holding'].any() and not hz['logical_attached'].any()
                                   and not hz['attachment_enabled_any'].any())},
    'quality': {'reference': v_r['status'], 'hold': v_h['status']},
    'stability_mm': {'reference': [v_r['stability']['centroid_drift_max_m'] * 1000,
                                   v_r['stability']['vertex_drift_p95_max_m'] * 1000],
                     'hold': [v_h['stability']['centroid_drift_max_m'] * 1000,
                              v_h['stability']['vertex_drift_p95_max_m'] * 1000]},
    'stationary_mm': {'reference': v_r['final_geometry']['metrics']['stationary_drift_mean_m'] * 1000,
                      'hold': v_h['final_geometry']['metrics']['stationary_drift_mean_m'] * 1000},
    'first_fail': {'reference': min(v_r.get('failed_geometry_frames') or [0]),
                   'hold': min(v_h.get('failed_geometry_frames') or [0])},
    'target_max_mm': float(dt[:, :3].max() * 1000),
    'target_max_yaw_deg': float(math.degrees(dt[:, 3].max())),
    'fold_yaw_diff_deg': float(math.degrees(r_h['fold_yaw'] - r_r['fold_yaw'])),
    'stages': stages,
    'fold_extent': {'reference': r_r['fold_metrics']['extent'], 'hold': r_h['fold_metrics']['extent']},
}
(OUT / 'hold120_4302_compare.json').write_text(json.dumps(res, indent=2) + '\n', encoding='utf-8')
for b in bins:
    print('hold', b['window_s'], 'cent', round(b['centroid_mm_s'], 5), 'p95', round(b['particle_p95_mm_s'], 5),
          'rot', round(b['rotation_deg'], 5), 'ee', round(b['ee_drift_mm'], 6))
print('quality', res['quality'], 'stab', res['stability_mm'], 'stationary', res['stationary_mm'])
print('target max', round(res['target_max_mm'], 5), 'fold_yaw', round(res['fold_yaw_diff_deg'], 5))
print('stages', {k: (round(v['max_mm'], 4), round(v['mean_mm'], 4)) for k, v in stages.items()})
