"""One first-sleeve counterfactual, same path/config as full multipoint pilot."""
import ast,hashlib,json,sys,types
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parent
source=(root/'day4-official-three-fold.py').read_text(encoding='utf-8')
source=source.replace('day4-official-three-fold.py','day4-single-anchor-sleeve.py')
source=source.replace("('day4-official-three-fold-'","('day4-single-anchor-sleeve-'")
source=source.replace('official-three-position-fold-v1','single-anchor-first-sleeve-v1')
source=source.replace('Nominal-flat three-stage fold development pilot; no used-slot reuse, episode reset or formal acceptance',
    'First right-sleeve grasp-model counterfactual only; single-vertex proxy; no full fold or physical pinch acceptance')
source=source.replace('from multi_prepared_grasp_control import MultiPreparedGraspControl','from single_anchor_grasp_control import SingleAnchorMultiControl as MultiPreparedGraspControl')
source=source.replace("'mass_experiment.py','official_fold_geometry.py']","'mass_experiment.py','official_fold_geometry.py','single_anchor_grasp_control.py']")
source=source.replace('zip(c.slots,plan[\'stages\'])','zip(c.slots[:1],plan[\'stages\'][:1])')
source=source.replace("capture_mass('after_three_releases')","capture_mass('after_single_sleeve_release')")
source=source.replace("if [x['slot'] for x in result['cycles']]!=['right_sleeve','left_sleeve','hem'] or not all(s.used for s in c.slots):",
    "if [x['slot'] for x in result['cycles']]!=['right_sleeve'] or [s.used for s in c.slots]!=[True,False,False]:")
source=source.replace("raise RuntimeError('Expected all three regions used once')","raise RuntimeError('Expected first sleeve only')")
source=source.replace("result['fold_metrics']=hem_metrics", "result['hem_proxy_diagnostic_only']=hem_metrics")
source=source.replace("json.dumps(result['fold_metrics'])", "json.dumps(result['hem_proxy_diagnostic_only'])")
source=source.replace('OFFICIAL_THREE_POSITION_PIPELINE_COMPLETED','SINGLE_ANCHOR_SLEEVE_PIPELINE_COMPLETED')
source=source.replace('OFFICIAL_THREE_PILOT_PASSED','SINGLE_ANCHOR_SLEEVE_PASSED')
source=source.replace("    result['pipeline_completed']=True", "    result['single_anchor_max_gap_m']={s.label:s.max_single_anchor_gap_m for s in c.slots}\n    result['grasp_model']='One manual vertex per precreated slot; auto generation removed before reset; no pitch'\n    result['pipeline_completed']=True")
ast.parse(source,feature_version=(3,10))
assert 'set_fold_angle(' not in source
(root/'day4-single-anchor-sleeve.py').write_text(source,encoding='utf-8',newline='\n')
runner=(root/'run-official-three-fold.sh').read_text(encoding='utf-8').replace('official-three-files.json','single-anchor-sleeve-files.json').replace('day4-official-three-fold.py','day4-single-anchor-sleeve.py').replace('OFFICIAL_THREE','SINGLE_ANCHOR_SLEEVE').replace('day4-official-three-log','day4-single-anchor-log')
(root/'run-single-anchor-sleeve.sh').write_text(runner,encoding='utf-8',newline='\n')
files=['day4-single-anchor-sleeve.py','single_anchor_grasp_control.py','official_fold_geometry.py',
       'multi_prepared_grasp_control.py','multi_grasp_geometry.py','hem_prepared_grasp_control.py',
       'hem_fold_geometry.py','l1_fold_geometry.py','room_collision_control.py','mass_experiment.py']
for name in files:ast.parse((root/name).read_text(encoding='utf-8'),feature_version=(3,10))
(root/'single-anchor-sleeve-files.json').write_text(json.dumps({n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in files},indent=2),encoding='utf-8')
# Test manual anchor authoring against a USD-shaped stub, including regen API removal.
tree=ast.parse((root/'single_anchor_grasp_control.py').read_text(encoding='utf-8'))
function=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='author_single_anchor')
class Attr:
    def Set(self,value):self.value=np.asarray(value,dtype=np.float32);return True
    def Get(self):return self.value
class Prim:
    def __init__(self):self.auto=True;self.attrs={x:Attr() for x in ('points0','points1')}
    def HasAPI(self,api):return self.auto
    def RemoveAPI(self,api):self.auto=False;return True
    def GetAttribute(self,name):return self.attrs[name]
ns={'np':np,'PhysxSchema':types.SimpleNamespace(PhysxAutoAttachmentAPI=object()),
    'Gf':types.SimpleNamespace(Vec3f=lambda *x:x),'Vt':types.SimpleNamespace(Vec3fArray=lambda x:x)}
exec(compile(ast.Module(body=[function],type_ignores=[]),'single-anchor-author','exec'),ns)
p=Prim();ns['author_single_anchor'](p,[1.25,2.5,3.75]);assert not p.auto
assert np.array_equal(p.attrs['points0'].Get(),[[1.25,2.5,3.75]]) and np.array_equal(p.attrs['points1'].Get(),[[0,0,0]])
# Geometry and motion functions inherited from baseline; only stage count/grasp model changes.
old=ast.parse((root/'day4-official-three-fold.py').read_text(encoding='utf-8'));new=ast.parse(source)
for name in ('action','snapshot','record_frame'):
    assert ast.dump(next(x for x in old.body if isinstance(x,ast.FunctionDef) and x.name==name))==ast.dump(next(x for x in new.body if isinstance(x,ast.FunctionDef) and x.name==name))
print('SINGLE_ANCHOR_SYNTAX_AUTHORING_AND_PUBLIC_ACTION_AST_OK; GPU_VALIDATION_PENDING')
