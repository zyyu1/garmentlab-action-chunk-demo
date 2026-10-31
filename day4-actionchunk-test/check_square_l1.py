from pathlib import Path
import ast,json,hashlib,sys
import numpy as np
b=Path('day4-actionchunk-test');sys.path.insert(0,str(b.resolve()))
from square_geometry import square_targets
from hem_fold_geometry import hem_plan,short_segments
from multi_grasp_geometry import select_regions
v=np.load(b/'square_l1_candidate/square_cloth_geometry.npz')['vertices']+[0,-.45,.01]
regions=select_regions(v);pick=regions[2][1];assert pick==10 and v[pick,1]==v[:,1].min()
p=hem_plan(v,pick);targets=square_targets(v[pick],p['fold_line_y'])
assert targets.shape==(4,3) and np.isfinite(targets).all()
assert np.allclose(targets[-1],[v[pick,0],2*p['fold_line_y']-v[pick,1],v[pick,2]+.02])
assert np.all(np.diff(targets[:,1])>0)
for a,z in zip(np.vstack([v[pick],targets[:-1]]),targets):
 seg=np.array(short_segments(a,z));assert np.max(np.linalg.norm(np.diff(np.vstack([a,seg]),axis=0),axis=1))<=.02500001
 assert np.allclose(seg[-1],z)
s=(b/'day4-square-l1.py').read_text().replace('One hem half-fold development candidate; same v4 path with single hem anchor; no formal acceptance','Procedural square cloth, single-arm 9-action development candidate; no formal acceptance')
(b/'day4-square-l1.py').write_text(s,encoding='utf8')
tree=ast.parse(s);dependencies=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='dependencies' for t in n.targets))
assert 'mass_experiment.py' not in dependencies
assert 'set_fold_angle(' not in s and '9945' not in s
runner=(b/'run-square-l1.sh').read_text().replace("print('DOWNLOAD_DIR',path.parent,flush=True)\nPY","print('DOWNLOAD_DIR',path.parent,flush=True)\nif not r.get('passed'):raise SystemExit(2)\nPY")
(b/'run-square-l1.sh').write_text(runner,encoding='utf8')
files=dependencies+['run-square-l1.sh']
for name in files:
 f=b/name;raw=f.read_text(encoding='utf8').replace('\r\n','\n');f.write_bytes(raw.encode())
 if name.endswith('.py'):ast.parse(raw)
manifest={name:hashlib.sha256((b/name).read_bytes()).hexdigest() for name in files}
(b/'square-l1-files.json').write_text(json.dumps(manifest,indent=2))
(b/'square_l1_candidate/preflight.json').write_text(json.dumps({'asset': 'procedural_square_40cm','pick_index_offline':pick,'particle_count':441,'particle_mass_kg':.0001,'expected_total_mass_kg':.0441,'targets_material_xyz':targets.tolist(),'expected_public_action_count':9,'linear_interpolation_max_step_m':.025,'syntax_pass':True,'gpu_tested':False},indent=2))
print('SQUARE_OFFLINE_GEOMETRY_PLAN_SYNTAX_PASS',len(files),'files')
