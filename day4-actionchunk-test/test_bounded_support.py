from pathlib import Path
import numpy as np,json
from bounded_support import assess,correction,CONFIG
p=Path(__file__).parent/'results/day4-minimum-half-fold-20261031-043028-240166'
h=np.load(p/'terminal_hold_trace.npz');d=np.load(p/'fold_definition.npz');r=json.loads((p/'result.json').read_text())
a=np.load(p/'05_original_place.npz')['vertices'];end=np.load(p/'06_supported_place.npz');v=end['vertices'];mask=d['source_mask'];pick=int(d['pick_index']);g=h['material_goal']
patch=np.flatnonzero((~mask)&(np.linalg.norm(a[:,:2]-g[:2],axis=1)<.015))
gate=assess(h['vertices'],float(h['dt']),mask,pick,patch,g,1.993842,1.982003)
assert not gate['ready'] and not gate['checks']['nearest_xy_m'] and not gate['checks']['speed_p95_m_s']
spent=float(np.linalg.norm(h['ee_goal']-np.load(p/'05_original_place.npz')['ee_position']))
ee,goal,dist=correction(v,end['ee_position'],pick,patch,a[patch],g,spent)
assert dist<=.020000001 and spent+dist<=.060000001
assert np.isfinite(ee).all()
for invalid,budget in [(v,.06),(v.copy(),spent)]:
 if budget!=.06:invalid[patch,1]-=.1
 try:correction(invalid,end['ee_position'],pick,patch,a[patch],g,budget)
 except ValueError:pass
 else:raise AssertionError('Bounds not enforced')
report=dict(old_episode_gate=gate,initial_spent_m=spent,first_correction_ee=ee.tolist(),first_current_patch_goal=goal.tolist(),first_step_m=dist,
 checks=['old unstable placement rejected','20mm step and 60mm cumulative budget','exhausted budget rejected','excessive patch drift rejected'],scope='Offline checks only; no new simulation')
(Path(__file__).parent/'bounded_support_offline_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
