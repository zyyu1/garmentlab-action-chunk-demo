"""Stage-wise comparison of the repeat runs against their originals."""
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE / 'results' / 'RC8B_L2_DIAG_20261105'
PAIRS = {
    'l2pose': (BASE / 'l2pose_run' / 'day4-a5-rc2-pfs1-observation-v2-20261105-042455-646408',
               BASE / 'l2pose_repeat1' / 'day4-a5-rc2-pfs1-observation-v2-20261105-050830-340362'),
    'rc8b': (HERE / 'results' / 'RC8B_SEVEN_CASE_20261105' / 'day4-a5-rc2-pfs1-observation-v2-20261105-025057-237749',
             BASE / 'rc8b_repeat1' / 'day4-a5-rc2-pfs1-observation-v2-20261105-052531-038610'),
}
OLD = HERE / 'results' / 'RC8_SEVEN_CASE_20261104' / 'day4-a5-rc2-pfs1-observation-v2-20261104-234933-939207'


def read(p):
    return json.loads(Path(p).read_text())


def load(p):
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


out = {}
for name, (a, b) in PAIRS.items():
    ra, rb = read(a / 'result.json'), read(b / 'result.json')
    va, vb = read(a / 'a5-verdict.json')['criteria'], read(b / 'a5-verdict.json')['criteria']
    stages = {}
    for s in ('initial_loaded', 'after_recovery', 'pre_release', 'release_boundary'):
        va_ = np.asarray(load(a / 'pfs1_stages' / (s + '.npz'))['vertices'], float)
        vb_ = np.asarray(load(b / 'pfs1_stages' / (s + '.npz'))['vertices'], float)
        d = np.linalg.norm(va_ - vb_, axis=1) * 1000
        stages[s] = {'max_mm': float(d.max()), 'mean_mm': float(d.mean()),
                     'z_max_mm': float(np.max(np.abs(va_[:, 2] - vb_[:, 2])) * 1000)}
    ta = np.asarray([x['target_pose'] for x in ra['actions']], float)
    tb = np.asarray([x['target_pose'] for x in rb['actions']], float)
    dt = np.abs(ta - tb)
    tr_a = np.asarray(load(a / 'success_trace.npz')['vertices'], float)
    tr_b = np.asarray(load(b / 'success_trace.npz')['vertices'], float)
    tr_d = np.linalg.norm(tr_a - tr_b, axis=2) * 1000
    out[name] = {
        'original': str(a.name), 'repeat': str(b.name),
        'quality_original': va['status'], 'quality_repeat': vb['status'],
        'stability_original_mm': [va['stability']['centroid_drift_max_m'] * 1000,
                                  va['stability']['vertex_drift_p95_max_m'] * 1000],
        'stability_repeat_mm': [vb['stability']['centroid_drift_max_m'] * 1000,
                                vb['stability']['vertex_drift_p95_max_m'] * 1000],
        'stationary_original_mm': (va.get('final_geometry') or {}).get('metrics', {}).get('stationary_drift_mean_m', float('nan')) * 1000,
        'stationary_repeat_mm': (vb.get('final_geometry') or {}).get('metrics', {}).get('stationary_drift_mean_m', float('nan')) * 1000,
        'stages': stages,
        'target_max_mm': float(dt[:, :3].max() * 1000),
        'target_max_yaw_deg': float(math.degrees(dt[:, 3].max())),
        'formal_trace_max_mm': float(tr_d.max()),
        'formal_trace_mean_mm': float(tr_d.mean()),
        'first_fail_original': min(va.get('failed_geometry_frames') or [0]),
        'first_fail_repeat': min(vb.get('failed_geometry_frames') or [0]),
        'fold_extent_original': ra['fold_metrics']['extent'],
        'fold_extent_repeat': rb['fold_metrics']['extent'],
    }

(BASE / 'repeat_compare.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
for name, r in out.items():
    print(name, r['quality_original'], r['quality_repeat'],
          'stab', [round(x, 6) for x in r['stability_original_mm']], [round(x, 6) for x in r['stability_repeat_mm']])
    for s, v in r['stages'].items():
        print('  ', s, 'max', round(v['max_mm'], 6), 'mean', round(v['mean_mm'], 6))
    print('   targets max mm', round(r['target_max_mm'], 6), 'yaw', round(r['target_max_yaw_deg'], 6),
          'trace max', round(r['formal_trace_max_mm'], 6), 'first fail', r['first_fail_original'], r['first_fail_repeat'])
