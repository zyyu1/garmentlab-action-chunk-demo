from pathlib import Path
import json,hashlib,tarfile,shutil
import numpy as np
b=Path('day4-actionchunk-test/results').resolve();arc=b/'day4-attachment-canary-v2-e5aV7xe4.tar'
assert hashlib.sha256(arc.read_bytes()).hexdigest()=='0512681bfc4223bec4c111a689997d1fe9575c4928f5dd6ad4d46e150961ea2c'
with tarfile.open(arc) as tar:
 for m in tar:
  p=(b/m.name).resolve();assert b in p.parents and (m.isfile() or m.isdir())
  if m.isdir():p.mkdir(parents=True,exist_ok=True)
  else:
   p.parent.mkdir(parents=True,exist_ok=True)
   with tar.extractfile(m) as src,p.open('wb') as dst:shutil.copyfileobj(src,dst)
out=b/'day4-attachment-canary-v2-e5aV7xe4';old=b/'day4-attachment-canary-YqYxWGf9';manifest=json.loads((out/'attachment-canary-v2-files.json').read_text());audit={}
for case in ['rigid','disabled','enabled']:
 d=out/case;r=json.loads((d/'result.json').read_text());t=json.loads((d/'trace.json').read_text());prior=json.loads((old/case/'trace.json').read_text())
 assert r['completed'] and not r['errors'] and len(t)==181 and [x['step'] for x in t]==list(range(181))
 assert hashlib.sha256((d/'day4-attachment-canary-v2.py').read_bytes()).hexdigest()==manifest['day4-attachment-canary-v2.py']==r['source_sha256']
 same=all(all(x[k]==y[k] for k in y) for x,y in zip(t,prior))
 a={'all_v1_trace_fields_exact':same,'held_y_angle_max_rad':max(x['rotvec'][1] for x in t[:121]),'assessment':json.loads((d/'assessment.json').read_text())}
 if case!='rigid':
  a['mass_readbacks']=r['cloth_mass_readbacks'];a['initial_centroid']=t[0]['cloth_mass_centroid_m'];a['gravity_y_moment_start_end_Nm']=[t[i]['cloth_gravity_moment_about_pivot_Nm'][1] for i in [0,120,180]]
  assert all(np.isfinite(x['particle_masses_kg']).all() for x in r['cloth_mass_readbacks'].values())
 audit[case]=a
for n in ['run-attachment-canary-v2.sh','evaluate-attachment-canary-v2.py']:assert hashlib.sha256((out/n).read_bytes()).hexdigest()==manifest[n]
(out/'independent_audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))
