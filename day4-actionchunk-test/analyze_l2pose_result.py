"""Compare the l2pose diagnostic with old/new 4202 runs (offline)."""
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OLD = HERE / 'results' / 'RC8_SEVEN_CASE_20261104' / 'day4-a5-rc2-pfs1-observation-v2-20261104-234933-939207'
NEW = HERE / 'results' / 'RC8B_SEVEN_CASE_20261105' / 'day4-a5-rc2-pfs1-observation-v2-20261105-025057-237749'
L2 = HERE / 'results' / 'RC8B_L2_DIAG_20261105' / 'l2pose_run' / 'day4-a5-rc2-pfs1-observation-v2-20261105-042455-646408'
OUT = HERE / 'results' / 'RC8B_L2_DIAG_20261105'


def read(p):
    return json.loads(Path(p).read_text())


def load(p):
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def unique_indices(times):
    out, last = [], None
    for k, t in enumerate(np.asarray(times, float)):
        if last is None or t - last > 1e-9:
            out.append(k); last = t
    return out


def fd(V, times):
    V = np.asarray(V, float); times = np.asarray(times, float)
    idx = unique_indices(times)
    dt = np.diff(times[idx])
    p = np.linalg.norm(V[idx[1:]] - V[idx[:-1]], axis=2).mean(1) * 1000 / dt
    c = np.linalg.norm(V[idx[1:]].mean(1) - V[idx[:-1]].mean(1), axis=1) * 1000 / dt
    return float(p.mean()), float(c.mean())


rows = {}
for tag, run in (('old', OLD), ('new', NEW), ('l2pose', L2)):
    v = read(run / 'a5-verdict.json')['criteria']
    r = read(run / 'result.json')
    rs = load(run / 'pfs1_release_steps.npz')
    V = np.asarray(rs['vertices'], float); t = np.asarray(rs['sim_time_s'], float)
    t0 = float(t[0])
    first = load(run / 'pfs1_first_0_5s.npz')
    j = max(i for i in range(len(t)) if t[i] <= t0 + 0.5 + 1e-6)
    p05, c05 = fd(V[:j + 1], t[:j + 1])
    si = [i for i in range(len(t)) if t0 + 1.5 - 1e-9 <= t[i] <= t0 + 8.0 + 1e-9]
    ps, cs = fd(V[si[0]:si[-1] + 1], t[si[0]:si[-1] + 1])
    bins = []
    for b in range(20):
        idx = [i for i in range(len(t)) if t0 + 0.5 * b - 1e-6 <= t[i] <= t0 + 0.5 * (b + 1) + 1e-6]
        if len(idx) < 2:
            continue
        u = [idx[0] + k for k in unique_indices(t[idx[0]:idx[-1] + 1])]
        dt = np.diff(t[u])
        cent = np.linalg.norm(V[u[1:]].mean(1) - V[u[:-1]].mean(1), axis=1) * 1000 / dt
        bins.append({'start_s': 0.5 * b, 'centroid_mm_s': float(cent.mean()),
                     'centroid_disp_mm': float(np.linalg.norm(V[u[-1]].mean(0) - V[u[0]].mean(0)) * 1000)})
    fg = (v.get('final_geometry') or {}).get('metrics') or {}
    rows[tag] = {
        'quality': v['status'], 'checks': v['checks'],
        'centroid_mm': float(v['stability']['centroid_drift_max_m'] * 1000),
        'p95_mm': float(v['stability']['vertex_drift_p95_max_m'] * 1000),
        'centroid_max_mm': float(v['stability']['vertex_drift_max_m'] * 1000),
        'speed_p95_mm_s': float(v['stability']['vertex_speed_p95_max_m_s'] * 1000),
        'stationary_drift_mm': float(fg.get('stationary_drift_mean_m', float('nan')) * 1000),
        'first_0_5s_particle_mm_s': p05, 'first_0_5s_centroid_mm_s': c05,
        'steady_particle_mm_s': ps, 'steady_centroid_mm_s': cs,
        'fold_extent_m': r['fold_metrics']['extent'],
        'fold_yaw_deg': math.degrees(r['fold_yaw']),
        'bins': bins,
    }

(OUT / 'l2pose_compare.json').write_text(json.dumps(rows, indent=2, allow_nan=False) + '\n', encoding='utf-8')

with (OUT / 'l2pose_bins.csv').open('w', newline='', encoding='utf-8') as f:
    import csv
    w = csv.writer(f)
    w.writerow(['start_s', 'old_centroid_mm_s', 'l2pose_centroid_mm_s', 'new_centroid_mm_s',
                'old_disp_mm', 'l2pose_disp_mm', 'new_disp_mm'])
    for ob, lb, nb in zip(rows['old']['bins'], rows['l2pose']['bins'], rows['new']['bins']):
        w.writerow([ob['start_s'], round(ob['centroid_mm_s'], 4), round(lb['centroid_mm_s'], 4),
                    round(nb['centroid_mm_s'], 4), round(ob['centroid_disp_mm'], 4),
                    round(lb['centroid_disp_mm'], 4), round(nb['centroid_disp_mm'], 4)])

for tag in ('old', 'l2pose', 'new'):
    r = rows[tag]
    print(tag, r['quality'], round(r['centroid_mm'], 4), round(r['p95_mm'], 4),
          round(r['stationary_drift_mm'], 4), 'first05', round(r['first_0_5s_centroid_mm_s'], 3),
          'steady', round(r['steady_centroid_mm_s'], 3), 'fold_extent', [round(x, 4) for x in r['fold_extent_m']])
