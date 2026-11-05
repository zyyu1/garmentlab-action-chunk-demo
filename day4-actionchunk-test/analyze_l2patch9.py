"""Compare the nine-point patch run against the unmodified new 4202 run."""
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NEW = HERE / 'results' / 'RC8B_SEVEN_CASE_20261105' / 'day4-a5-rc2-pfs1-observation-v2-20261105-025057-237749'
PATCH = HERE / 'results' / 'RC8B_L2_DIAG_20261105' / 'l2patch9_run' / 'day4-a5-rc2-pfs1-observation-v2-20261105-061356-846153'
OUT = HERE / 'results' / 'RC8B_L2_DIAG_20261105'


def read(p):
    return json.loads(Path(p).read_text())


def load(p):
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def unique_indices(t):
    out, last = [], None
    for k, v in enumerate(np.asarray(t, float)):
        if last is None or v - last > 1e-9:
            out.append(k); last = v
    return out


new, pat = read(NEW / 'result.json'), read(PATCH / 'result.json')
vn, vp = read(NEW / 'a5-verdict.json')['criteria'], read(PATCH / 'a5-verdict.json')['criteria']

stages = {}
for s in ('initial_loaded', 'after_recovery', 'pre_release', 'release_boundary'):
    a = np.asarray(load(NEW / 'pfs1_stages' / (s + '.npz'))['vertices'], float)
    b = np.asarray(load(PATCH / 'pfs1_stages' / (s + '.npz'))['vertices'], float)
    d = np.linalg.norm(a - b, axis=1) * 1000
    stages[s] = {'max_mm': float(d.max()), 'mean_mm': float(d.mean())}

ta = np.asarray([x['target_pose'] for x in new['actions']], float)
tb = np.asarray([x['target_pose'] for x in pat['actions']], float)
dt = np.abs(ta - tb)
tra = np.asarray(load(NEW / 'success_trace.npz')['vertices'], float)
trb = np.asarray(load(PATCH / 'success_trace.npz')['vertices'], float)
trd = np.linalg.norm(tra - trb, axis=2) * 1000


def bins(run):
    rs = load(run / 'pfs1_release_steps.npz')
    V = np.asarray(rs['vertices'], float); t = np.asarray(rs['sim_time_s'], float)
    t0 = float(t[0]); out = []
    for b in range(20):
        idx = [i for i in range(len(t)) if t0 + .5 * b - 1e-6 <= t[i] <= t0 + .5 * (b + 1) + 1e-6]
        if len(idx) < 2:
            continue
        u = [idx[0] + k for k in unique_indices(t[idx[0]:idx[-1] + 1])]
        dt_ = np.diff(t[u])
        c = np.linalg.norm(V[u[1:]].mean(1) - V[u[:-1]].mean(1), axis=1) * 1000 / dt_
        out.append({'start_s': .5 * b, 'centroid_mm_s': float(c.mean()),
                    'disp_mm': float(np.linalg.norm(V[u[-1]].mean(0) - V[u[0]].mean(0)) * 1000)})
    return out


out = {
    'new_quality': vn['status'], 'patch_quality': vp['status'],
    'new_stability_mm': [vn['stability']['centroid_drift_max_m'] * 1000,
                         vn['stability']['vertex_drift_p95_max_m'] * 1000],
    'patch_stability_mm': [vp['stability']['centroid_drift_max_m'] * 1000,
                           vp['stability']['vertex_drift_p95_max_m'] * 1000],
    'new_stationary_mm': vn['final_geometry']['metrics']['stationary_drift_mean_m'] * 1000,
    'patch_stationary_mm': vp['final_geometry']['metrics']['stationary_drift_mean_m'] * 1000,
    'new_first_fail': min(vn.get('failed_geometry_frames') or [0]),
    'patch_first_fail': min(vp.get('failed_geometry_frames') or [0]),
    'new_fail_count': len(vn.get('failed_geometry_frames') or []),
    'patch_fail_count': len(vp.get('failed_geometry_frames') or []),
    'stages': stages,
    'target_max_mm': float(dt[:, :3].max() * 1000),
    'target_max_yaw_deg': float(math.degrees(dt[:, 3].max())),
    'trace_max_mm': float(trd.max()), 'trace_mean_mm': float(trd.mean()),
    'new_fold_extent': new['fold_metrics']['extent'],
    'patch_fold_extent': pat['fold_metrics']['extent'],
    'bins_new': bins(NEW), 'bins_patch': bins(PATCH),
}
(OUT / 'l2patch9_compare.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
for s, v in stages.items():
    print(s, 'max', round(v['max_mm'], 6), 'mean', round(v['mean_mm'], 6))
print('targets max mm', round(out['target_max_mm'], 6), 'yaw', round(out['target_max_yaw_deg'], 6))
print('trace max/mean', round(out['trace_max_mm'], 6), round(out['trace_mean_mm'], 6))
print('first fail', out['new_first_fail'], out['patch_first_fail'], 'counts', out['new_fail_count'], out['patch_fail_count'])
print('stationary', round(out['new_stationary_mm'], 4), round(out['patch_stationary_mm'], 4))
