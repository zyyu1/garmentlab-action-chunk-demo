import ast,json,hashlib,subprocess,tempfile
from pathlib import Path
b=Path('day4-actionchunk-test')
a=(b/'day4-attachment-canary.py').read_text();v=(b/'day4-attachment-canary-v2.py').read_text()
assert a[a.index('    world = World'):a.index('    world.reset()')]==v[v.index('    world = World'):v.index('    world.reset()')]
assert a[a.index('    for step in range(1,181):'):]==v[v.index('    for step in range(1,181):'):]
with tempfile.TemporaryDirectory() as td:
 root=Path(td)
 for case in ['rigid','disabled','enabled']:
  p=root/case;p.mkdir();reads={str(i):{'matches_authored_total_rtol_0_002':True,'unchanged_from_start':True} for i in [0,120,180]}
  r={'completed':True,'errors':[],'cloth_mass_readbacks':reads};(p/'result.json').write_text(json.dumps(r));rows=[]
  for step in range(181):
   angle=min(step*.002,.2) if case!='disabled' else 0
   rows.append({'step':step,'angle_rad':angle,'rotvec':[0,angle,0],'pivot_error_m':0,'enabled':case=='enabled' and step<=120,'anchor_error_m':.001 if step<=120 else .2,'anchor_z_mean':1-step*.003 if case=='disabled' else (1 if step<=120 else .8)})
  (p/'trace.json').write_text(json.dumps(rows))
  x=subprocess.run(['D:/Users/yexun/anaconda3/python.exe',str(b/'evaluate-attachment-canary-v2.py'),td,case],capture_output=True,text=True);assert x.returncode==0,x.stdout+x.stderr
 for row in rows:row['angle_rad']=.02;row['rotvec']=[0,.02,0]
 (p/'trace.json').write_text(json.dumps(rows))
 x=subprocess.run(['D:/Users/yexun/anaconda3/python.exe',str(b/'evaluate-attachment-canary-v2.py'),td,'enabled'],capture_output=True,text=True);assert x.returncode==2 and 'valid_response_below_preregistered_threshold' in x.stdout
 r['cloth_mass_readbacks']['120']['unchanged_from_start']=False;(p/'result.json').write_text(json.dumps(r))
 x=subprocess.run(['D:/Users/yexun/anaconda3/python.exe',str(b/'evaluate-attachment-canary-v2.py'),td,'enabled'],capture_output=True,text=True);assert x.returncode==2 and 'mass_configuration_mismatch_or_recording_failed' in x.stdout
names=['day4-attachment-canary-v2.py','evaluate-attachment-canary-v2.py','run-attachment-canary-v2.sh']
for n in names:
 p=b/n;s=p.read_text();p.write_bytes(s.replace('\r\n','\n').encode())
 if n.endswith('.py'):ast.parse(s)
(b/'attachment-canary-v2-files.json').write_text(json.dumps({n:hashlib.sha256((b/n).read_bytes()).hexdigest() for n in names},indent=2))
(b/'constraint_api_review/v2_local_checks.json').write_text(json.dumps({'scene_code_exact':True,'simulation_loop_exact':True,'syntax_pass':True,'assessment_positive_below_threshold_mass_mismatch_fixtures_pass':True,'gpu_tested':False},indent=2))
print('SCENE_LOOP_UNCHANGED; SYNTAX_AND_ASSESSMENT_FIXTURES_PASS')
