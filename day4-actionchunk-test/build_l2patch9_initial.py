"""Build the fixed nine-point z patch initial (new initial + 9 z values from derived)."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NEW_INIT = HERE / 'results' / 'RC8B_INITIALS_20261105' / 'day4-square-initial-stripfold-20261105-015817-115841'
DER_INIT = HERE / 'results' / 'RC8B_L2_DIAG_20261105' / 'day4-square-initial-stripfold-20261104-202215-l2posecontrol'
OUT_ROOT = HERE / 'results' / 'RC8B_L2_DIAG_20261105'
NAME = 'day4-square-initial-stripfold-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-l2patch9'
OUT = OUT_ROOT / NAME
OUT.mkdir(parents=True)

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

new = np.load(NEW_INIT / 'initial_geometry.npz')
der = np.load(DER_INIT / 'initial_geometry.npz')
final_new = np.asarray(new['final'], float)
final_der = np.asarray(der['final'], float)

ROW, COL = 21, 21
assert ROW * COL == 441
row, col = divmod(91, COL)
assert (row, col) == (4, 7)
patch = [r * COL + c for r in range(row - 1, row + 2) for c in range(col - 1, col + 2)]
expected = [69, 70, 71, 90, 91, 92, 111, 112, 113]
assert patch == expected, patch

z_new = {int(i): float(final_new[i, 2]) for i in patch}
z_der = {int(i): float(final_der[i, 2]) for i in patch}
dz = {int(i): z_der[i] - z_new[i] for i in patch}

patch_def = {
    'name': 'l2patch9',
    'source_initial': NEW_INIT.name,
    'source_geometry_sha256': sha(NEW_INIT / 'initial_geometry.npz'),
    'source_result_sha256': sha(NEW_INIT / 'result.json'),
    'reference_initial': DER_INIT.name,
    'reference_geometry_sha256': sha(DER_INIT / 'initial_geometry.npz'),
    'mesh': {'rows': ROW, 'cols': COL, 'ordering': 'row-major',
             'basis': '3x3 vertex patch around #91; offsets (+/-1 col, +/-1 row); verified by index offsets and Euclidean edge lengths'},
    'center_index': 91,
    'center_row_col_zero_based': [row, col],
    'indices': patch,
    'z_new_m': z_new,
    'z_derived_m': z_der,
    'dz_m': dz,
    'rule': 'only z of the nine indices is replaced by the reference z; xy, all other vertices, flat_settled, before/applied and metadata are unchanged',
    'no_smoothing_or_extra_motion': True,
}
(OUT_ROOT / 'patch_definition.json').write_text(json.dumps(patch_def, indent=2) + '\n', encoding='utf-8')
patch_sha = sha(OUT_ROOT / 'patch_definition.json')

patched = final_new.copy()
for i in patch:
    patched[i, 2] = final_der[i, 2]

result = json.loads((NEW_INIT / 'result.json').read_text())
result['initial_diagnostic'] = True
result['diagnostic_control'] = 'nine_point_z_patch'
result['derived_from'] = {
    'source_initial': NEW_INIT.name,
    'source_geometry_sha256': sha(NEW_INIT / 'initial_geometry.npz'),
    'source_result_sha256': sha(NEW_INIT / 'result.json'),
    'reference_initial': DER_INIT.name,
    'reference_geometry_sha256': sha(DER_INIT / 'initial_geometry.npz'),
    'patch_definition_sha256': patch_sha,
}
result['patch'] = {
    'indices': patch,
    'mesh_rows': ROW, 'mesh_cols': COL, 'ordering': 'row-major',
    'z_new_m': z_new, 'z_derived_m': z_der, 'dz_m': dz,
    'only_z_changed': True,
}
result['loaded_state'] = {
    'flat_settled': 'unchanged (bit-identical to the source new initial)',
    'final': 'nine z values replaced by the reference; xy and all other vertices unchanged',
    'velocities_restored': False,
    'velocity_transform': 'none (loader clears velocities)',
    'before_applied': 'unchanged; not read by the rollout',
}
result['protocol'] = {
    'version': 'diagnostic-l2-nine-point-z-patch-v1',
    'kind': 'derived_control',
    'is_task_scoped_generated': False,
    'initial_diagnostic': True,
    'note': 'derived nine-point z patch; not a stage4-initial-v2-task-scoped generated initial; not valid for formal batches',
    'source_initial': NEW_INIT.name,
    'reference_initial': DER_INIT.name,
    'patch_definition_sha256': patch_sha,
    'velocities_restored': False,
}
result['geometry'] = {'center': patched.mean(0).tolist(),
                      'extent': np.ptp(patched, axis=0).tolist(),
                      'note': 'computed from the patched final geometry'}

np.savez_compressed(OUT / 'initial_geometry.npz', before=new['before'], applied=new['applied'],
                    flat_settled=new['flat_settled'], final=patched)
import shutil
shutil.copy2(NEW_INIT / 'initial.png', OUT / 'initial.png')
(OUT / 'result.json').write_text(json.dumps(result, indent=2, default=lambda x: x.tolist() if isinstance(x, np.ndarray) else float(x)) + '\n',
                                 encoding='utf-8')

# audit: exactly nine z values differ; everything else identical
before = np.asarray(new['before'], float); applied = np.asarray(new['applied'], float)
flat = np.asarray(new['flat_settled'], float)
other = [i for i in range(441) if i not in patch]
z_diff = patched[:, 2] - final_new[:, 2]
changed = [int(i) for i in np.where(np.abs(z_diff) > 0)[0]]
assert changed == patch, (changed, patch)
assert np.array_equal(patched[:, :2], final_new[:, :2])
assert np.array_equal(patched[other], final_new[other])
assert np.array_equal(np.asarray(new['before']), before)
assert np.array_equal(np.asarray(new['applied']), applied)
assert np.array_equal(np.asarray(new['flat_settled']), flat)

# local edge length changes (3x3 grid: horizontal, vertical, diagonals)
edges = []
for r in range(row - 1, row + 2):
    for c in range(col - 1, col + 2):
        i = r * COL + c
        for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
            rr, cc = r + dr, c + dc
            if row - 1 <= rr <= row + 1 and col - 1 <= cc <= col + 1:
                j = rr * COL + cc
                if i < j:
                    edges.append((i, j))
edge_stats = []
for i, j in edges:
    l0 = float(np.linalg.norm(final_new[i] - final_new[j]) * 1000)
    l1 = float(np.linalg.norm(patched[i] - patched[j]) * 1000)
    edge_stats.append({'i': int(i), 'j': int(j), 'before_mm': round(l0, 5),
                       'after_mm': round(l1, 5), 'delta_mm': round(l1 - l0, 6)})

# adjacent height continuity: each patch vertex vs grid neighbours (including boundary ring)
continuity = []
for i in patch:
    r, c = divmod(i, COL)
    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        rr, cc = r + dr, c + dc
        if not (0 <= rr < ROW and 0 <= cc < COL):
            continue
        j = rr * COL + cc
        continuity.append({'i': int(i), 'j': int(j),
                           'dz_before_mm': round(float((final_new[i, 2] - final_new[j, 2]) * 1000), 6),
                           'dz_after_mm': round(float((patched[i, 2] - patched[j, 2]) * 1000), 6),
                           'delta_dz_mm': round(float(((patched[i, 2] - patched[j, 2]) -
                                                        (final_new[i, 2] - final_new[j, 2])) * 1000), 6)})

audit = {
    'derived_initial': OUT.name,
    'patch_definition_sha256': patch_sha,
    'source_hashes': result['derived_from'],
    'derived_hashes': {n: sha(OUT / n) for n in ('result.json', 'initial_geometry.npz', 'initial.png')},
    'changed_indices': changed,
    'changed_count': len(changed),
    'only_z_changed': True,
    'xy_unchanged': True,
    'other_vertices_unchanged': True,
    'before_applied_flat_unchanged': True,
    'z_new_m': z_new, 'z_derived_m': z_der, 'dz_m': dz,
    'edge_length_changes': edge_stats,
    'max_abs_edge_length_change_mm': round(max(abs(e['delta_mm']) for e in edge_stats), 6),
    'height_continuity_edges': continuity,
    'max_abs_adjacent_dz_change_mm': round(max(abs(e['delta_dz_mm']) for e in continuity), 6),
    'no_smoothing_or_extra_motion': True,
    'initial_image': 'copied from the source new initial; not re-rendered',
}
(OUT / 'patch_audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
(OUT_ROOT / 'patch_audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')

print('PATCH_INITIAL', OUT)
print('patch', patch)
print('dz_mm', {i: round(dz[i] * 1000, 4) for i in patch})
print('changed', changed)
print('max edge delta mm', audit['max_abs_edge_length_change_mm'])
print('max adjacent dz change mm', audit['max_abs_adjacent_dz_change_mm'])
print('hashes', audit['derived_hashes'])
