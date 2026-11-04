"""Inspect the rc8b regenerated dev initials (offline)."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NEW = HERE / 'results' / 'RC8B_INITIALS_20261105'
OLD = Path(r'E:\learning\project\thesis\day4-actionchunk-test\results\A5_RC2_AUDIT_20261103T194913Z')
OLD_DIRS = {
    4100: 'day4-square-initial-20261031-094446-203825',
    4201: 'day4-square-initial-stripfold-20261103-060526-426086',
    4202: 'day4-square-initial-stripfold-20261103-062710-242560',
    4302: 'day4-square-initial-stripfold-20261103-094143-137994',
}

rows = []
for d in sorted(NEW.iterdir()):
    if not d.is_dir():
        continue
    r = json.loads((d / 'result.json').read_text())
    case = r['initial_case']
    seed = case['seed']
    proto = r.get('protocol') or {}
    geo = r.get('geometry') or {}
    row = {
        'seed': seed, 'level': case['level'], 'dir': d.name,
        'passed': r.get('passed'), 'errors': r.get('errors'),
        'protocol_version': proto.get('version'),
        'task': proto.get('task'),
        'scale_expected': proto.get('particle_friction_scale_expected'),
        'scale_readback': (r.get('material_readback') or {}).get('particle_friction_scale'),
        'binding': proto.get('material_binding'),
        'generator': (proto.get('generator') or {}).get('script'),
        'extent': geo.get('extent'),
        'z_p95': (r.get('strip_records') or [{}])[0].get('z_p95') if r.get('strip_records') else None,
        'strip_widths': [s.get('width_m') for s in (r.get('strip_records') or [])],
    }
    old_dir = OLD / OLD_DIRS.get(seed, '')
    if (old_dir / 'initial_geometry.npz').is_file() and (d / 'initial_geometry.npz').is_file():
        a = np.load(d / 'initial_geometry.npz')
        b = np.load(old_dir / 'initial_geometry.npz')
        diff = float(np.max(np.abs(a['settled'] - b['settled']))) if 'settled' in a.files else None
        row['old_geometry_max_abs_diff'] = diff
        ob = json.loads((old_dir / 'result.json').read_text())
        row['old_extent'] = (ob.get('geometry') or {}).get('extent')
        row['old_scale'] = (ob.get('material_readback') or {}).get('particle_friction_scale')
    rows.append(row)

for r in rows:
    print(json.dumps(r, ensure_ascii=False))
