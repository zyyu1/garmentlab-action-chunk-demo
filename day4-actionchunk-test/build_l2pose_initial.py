"""Build the pose-matched diagnostic initial (old folded geometry + new pose).

Only `final` is transformed; `flat_settled` is left unchanged because the old
and new initials share it bit-for-bit.  The rollout restores positions only and
clears velocities, so no velocity vector is transformed.
"""
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OLD_INIT = Path(r'E:\learning\project\thesis\day4-actionchunk-test\results\A5_RC2_AUDIT_20261103T194913Z\day4-square-initial-stripfold-20261103-062710-242560')
NEW_INIT = HERE / 'results' / 'RC8B_INITIALS_20261105' / 'day4-square-initial-stripfold-20261105-015817-115841'
OUT_ROOT = HERE / 'results' / 'RC8B_L2_DIAG_20261105'
NAME = 'day4-square-initial-stripfold-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-l2posecontrol'
OUT = OUT_ROOT / NAME
OUT.mkdir(parents=True)

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

old = np.load(OLD_INIT / 'initial_geometry.npz')
new = np.load(NEW_INIT / 'initial_geometry.npz')
old_final = np.asarray(old['final'], float)
new_final = np.asarray(new['final'], float)
assert old_final.shape == new_final.shape == (441, 3)

A = old_final[:, :2]; B = new_final[:, :2]
ca, cb = A.mean(0), B.mean(0)
H = (A - ca).T @ (B - cb)
U, S, Vt = np.linalg.svd(H)
R = Vt.T @ U.T
if np.linalg.det(R) < 0:
    Vt[-1, :] *= -1
    R = Vt.T @ U.T
t = cb - R @ ca
theta = math.degrees(math.atan2(R[1, 0], R[0, 0]))

transformed_final = old_final.copy()
transformed_final[:, :2] = (A - ca) @ R.T + cb
assert np.allclose(transformed_final[:, 2], old_final[:, 2], atol=0, rtol=0)

# internal distances preserved
d_old = np.linalg.norm(A[:, None, :] - A[None, :, :], axis=2)
d_new = np.linalg.norm(transformed_final[:, :2][:, None, :] - transformed_final[:, :2][None, :, :], axis=2)
dist_max = float(np.max(np.abs(d_old - d_new)))

# alignment residual to the new initial
res = np.linalg.norm(transformed_final - new_final, axis=1) * 1000
align_p95 = float(np.percentile(res, 95))
align_max = float(res.max())

flat_old = np.asarray(old['flat_settled'], float)
flat_new = np.asarray(new['flat_settled'], float)
flat_equal = bool(np.array_equal(flat_old, flat_new))
assert flat_equal, 'flat_settled differs between old and new initials'

result = json.loads((OLD_INIT / 'result.json').read_text())
result['diagnostic_control'] = 'pose_matched_old_geometry'
result['derived_from'] = {
    'source_initial': OLD_INIT.name,
    'source_result_sha256': sha(OLD_INIT / 'result.json'),
    'source_geometry_sha256': sha(OLD_INIT / 'initial_geometry.npz'),
    'pose_reference_initial': NEW_INIT.name,
    'pose_reference_geometry_sha256': sha(NEW_INIT / 'initial_geometry.npz'),
}
result['transform'] = {
    'fit_vertices': 441,
    'fit_scope': 'final xy, all vertices',
    'rotation_axis': '+z',
    'rotation_deg': theta,
    'center_old_m': ca.tolist(),
    'center_new_m': cb.tolist(),
    'translation_m': t.tolist(),
    'matrix4x4': [[float(R[0, 0]), float(R[0, 1]), 0.0, float(t[0])],
                  [float(R[1, 0]), float(R[1, 1]), 0.0, float(t[1])],
                  [0.0, 0.0, 1.0, 0.0],
                  [0.0, 0.0, 0.0, 1.0]],
    'alignment_residual_vs_new_p95_mm': align_p95,
    'alignment_residual_vs_new_max_mm': align_max,
    'internal_pairwise_distance_max_abs_diff_m': dist_max,
}
result['loaded_state'] = {
    'flat_settled': 'unchanged (bit-identical to the new initial)',
    'flat_settled_equal_new': flat_equal,
    'final': 'transformed (old folded geometry at new overall pose)',
    'velocities_restored': False,
    'velocity_transform': 'none (loader clears velocities; no velocity vector restored)',
    'before_applied': 'unchanged; not read by the rollout',
}
result['protocol'] = {
    'version': 'diagnostic-l2-pose-control-v1',
    'kind': 'derived_control',
    'is_task_scoped_generated': False,
    'note': 'derived control, not a stage4-initial-v2-task-scoped generated initial; not valid for formal batches',
    'source_initial': OLD_INIT.name,
    'pose_reference_initial': NEW_INIT.name,
    'velocities_restored': False,
}
result['geometry'] = {
    'center': transformed_final.mean(0).tolist(),
    'extent': np.ptp(transformed_final, axis=0).tolist(),
    'note': 'computed from the transformed final geometry',
}

np.savez_compressed(OUT / 'initial_geometry.npz', before=old['before'], applied=old['applied'],
                    flat_settled=old['flat_settled'], final=transformed_final)
shutil.copy2(OLD_INIT / 'initial.png', OUT / 'initial.png')
(OUT / 'result.json').write_text(json.dumps(result, indent=2, default=lambda x: x.tolist() if isinstance(x, np.ndarray) else float(x)) + '\n',
                                 encoding='utf-8')

audit = {
    'derived_initial': OUT.name,
    'transform': result['transform'],
    'source_hashes': result['derived_from'],
    'derived_hashes': {name: sha(OUT / name) for name in ('result.json', 'initial_geometry.npz', 'initial.png')},
    'flat_settled_equal_new': flat_equal,
    'z_unchanged': bool(np.array_equal(transformed_final[:, 2], old_final[:, 2])),
    'internal_pairwise_distance_max_abs_diff_m': dist_max,
    'alignment_residual_vs_new_p95_mm': align_p95,
    'alignment_residual_vs_new_max_mm': align_max,
    'initial_image': 'copied from the source old initial; not re-rendered',
}
(OUT / 'transform_audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
(OUT_ROOT / 'transform_audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')

print('DERIVED', OUT)
print('theta_deg', round(theta, 6), 'translation_mm', np.round(t * 1000, 4).tolist())
print('align p95/max mm', round(align_p95, 6), round(align_max, 6))
print('internal distance max diff m', dist_max)
print('derived hashes', audit['derived_hashes'])
