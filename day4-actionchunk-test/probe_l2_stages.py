"""Quick stage-difference probe for the old/new 4202 pair."""
import json
from pathlib import Path

import numpy as np

OLD = Path(r'E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\results\RC8_SEVEN_CASE_20261104\day4-a5-rc2-pfs1-observation-v2-20261104-234933-939207')
NEW = Path(r'E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\results\RC8B_SEVEN_CASE_20261105\day4-a5-rc2-pfs1-observation-v2-20261105-025057-237749')
OLD_INIT = Path(r'E:\learning\project\thesis\day4-actionchunk-test\results\A5_RC2_AUDIT_20261103T194913Z\day4-square-initial-stripfold-20261103-062710-242560')
NEW_INIT = Path(r'E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\results\RC8B_INITIALS_20261105\day4-square-initial-stripfold-20261105-015817-115841')


def align(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    ca, cb = a[:, :2].mean(0), b[:, :2].mean(0)
    h = (a[:, :2] - ca).T @ (b[:, :2] - cb)
    u, s, vt = np.linalg.svd(h); r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1; r = vt.T @ u.T
    mapped = a.copy(); mapped[:, :2] = (a[:, :2] - ca) @ r.T + cb
    d = np.linalg.norm(mapped - b, axis=1) * 1000
    ang = float(np.degrees(np.arctan2(r[1, 0], r[0, 0])))
    return {'rotation_deg': ang, 'centroid_mm': float(np.linalg.norm(cb - ca) * 1000),
            'resid_p95_mm': float(np.percentile(d, 95)), 'resid_max_mm': float(d.max()),
            'resid_mean_mm': float(d.mean())}


def stats(v):
    v = np.asarray(v, float)
    z = v[:, 2] * 1000
    return {'extent_m': np.ptp(v, axis=0).tolist(), 'z_p50_mm': float(np.percentile(z, 50)),
            'z_p95_mm': float(np.percentile(z, 95)), 'z_max_mm': float(z.max()),
            'frac_above_20mm': float((z > 20).mean())}


print('init final', align(np.load(NEW_INIT / 'initial_geometry.npz')['final'],
                          np.load(OLD_INIT / 'initial_geometry.npz')['final']))
for stage in ('initial_loaded', 'after_recovery', 'pre_release'):
    a = np.load(NEW / 'pfs1_stages' / (stage + '.npz'))['vertices']
    b = np.load(OLD / 'pfs1_stages' / (stage + '.npz'))['vertices']
    print(stage, align(a, b))
    print('  new', stats(a))
    print('  old', stats(b))
r_old = json.loads((OLD / 'result.json').read_text()); r_new = json.loads((NEW / 'result.json').read_text())
print('fold_yaw old/new', r_old['fold_yaw'], r_new['fold_yaw'], 'diff_deg', (r_new['fold_yaw'] - r_old['fold_yaw']) * 180 / np.pi)
for i, (ao, an) in enumerate(zip(r_old['actions'], r_new['actions'])):
    d = np.asarray(an['target_pose']) - np.asarray(ao['target_pose'])
    print(i, ao['label'], 'target diff mm', np.round(d[:3] * 1000, 3), 'yaw deg', round(float(d[3]) * 180 / np.pi, 4))
