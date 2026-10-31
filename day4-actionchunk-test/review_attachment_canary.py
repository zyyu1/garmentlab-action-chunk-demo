import json,hashlib
from pathlib import Path
import numpy as np
b=Path(__file__).resolve().parent
out=b/'results/day4-attachment-canary-YqYxWGf9'
manifest=json.loads((out/'attachment-canary-files.json').read_text());rows={};traces={}
for name in ['rigid','disabled','enabled']:
 d=out/name;r=json.loads((d/'result.json').read_text());t=json.loads((d/'trace.json').read_text());traces[name]=t
 assert r['completed'] and not r['errors'] and len(t)==181 and [x['step'] for x in t]==list(range(181))
 assert hashlib.sha256((d/'day4-attachment-canary.py').read_bytes()).hexdigest()==manifest['day4-attachment-canary.py']==r['source_sha256']
 a=np.array([x['angle_rad'] for x in t]);rv=np.array([x['rotvec'] for x in t]);vel=np.array([x['velocity'] for x in t]);assert np.isfinite(rv).all() and np.isfinite(vel).all()
 row={'held_angle_max_rad':float(a[:121].max()),'held_rotvec_y_min_max_rad':[float(rv[:121,1].min()),float(rv[:121,1].max())],'post_open_angle_max_rad':float(a[121:].max()),'angle_at_120_rad':float(a[120]),'angle_at_180_rad':float(a[180]),'omega_at_120':vel[120,3:].tolist(),'max_pivot_error_m':max(x['pivot_error_m'] for x in t),'runtime_mass':r['runtime_mass'],'runtime_inertia':r['runtime_inertia']}
 if name!='rigid':
  v=np.array([x['vertices'] for x in t]);assert np.isfinite(v).all()
  row.update(held_anchor_error_max_m=max(x['anchor_error_m'] for x in t[1:121]),open_drop_m=t[120]['anchor_z_mean']-t[180]['anchor_z_mean'],open_gap_m=t[180]['anchor_error_m'],step60_drop_m=t[0]['anchor_z_mean']-t[60]['anchor_z_mean'])
 rows[name]=row
for n in ['evaluate-attachment-canary.py','run-attachment-canary.sh']:
 assert hashlib.sha256((out/n).read_bytes()).hexdigest()==manifest[n]
delta=np.array([x['rotvec'][1]-y['rotvec'][1] for x,y in zip(traces['enabled'][:121],traces['disabled'][:121])]);rows['delta']={'held_positive_y_peak_rad':float(delta.max()),'held_peak_step':int(delta.argmax()),'pre_registered_threshold_rad':.05}
(out/'independent_audit.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
