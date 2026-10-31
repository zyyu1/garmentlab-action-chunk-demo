"""Local geometry/state-machine checks; deliberately no Isaac import."""
import ast
import hashlib
import json
from pathlib import Path
import types
import numpy as np
from multi_grasp_geometry import select_regions, choose_unused_region

root=Path(__file__).resolve().parent
files=['day4-multi-grasp-test.py','multi_prepared_grasp_control.py','multi_grasp_geometry.py',
       'hem_prepared_grasp_control.py','hem_fold_geometry.py','l1_fold_geometry.py',
       'room_collision_control.py','mass_experiment.py']
for name in files:ast.parse((root/name).read_text(encoding='utf-8'),feature_version=(3,10))
x,y=np.meshgrid(np.linspace(-.4,.4,81),np.linspace(-.7,-.15,56))
vertices=np.column_stack([x.ravel(),y.ravel(),np.full(x.size,.015)])
regions=select_regions(vertices)
assert [x[0] for x in regions]==['right_sleeve','left_sleeve','hem']
assert len({x[1] for x in regions})==3
assert choose_unused_region(vertices,regions,[False]*3,vertices[regions[1][1]])==1
try:choose_unused_region(vertices,regions,[False]*3,[0,0,1]);raise AssertionError('Far target accepted')
except RuntimeError:pass
shifted=vertices+np.array([.01,.02,0])
assert choose_unused_region(shifted,regions,[True,False,False],shifted[regions[1][1]])==1

tree=ast.parse((root/'multi_prepared_grasp_control.py').read_text(encoding='utf-8'))
cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='MultiPreparedGraspControl')
ns={'np':np,'choose_unused_region':choose_unused_region}
exec(compile(ast.Module(body=[cls],type_ignores=[]),'multi-state-machine','exec'),ns)
Manager=ns['MultiPreparedGraspControl']
class Slot:
    def __init__(self,label,pick):
        self.label=label;self.pick_index=pick;self.used=False;self.holding=False
        self.enabled=False;self.alignment_record=None;self.activation_record=None;self.anchor_ids=None
        self.block=types.SimpleNamespace(attachment_path='/constraints/'+label)
    def attachment_enabled(self):return self.enabled
    def vertices(self):return vertices
    def grasp(self,*args):
        assert not self.used;self.used=True;self.holding=True;self.enabled=True
    def ungrasp(self,*args):self.enabled=False;self.holding=False
m=Manager.__new__(Manager);m.active_index=0;m.events=[];m.regions=regions;m.slots=[Slot(*x) for x in regions]
m.world=types.SimpleNamespace(stage=types.SimpleNamespace(GetPrimAtPath=lambda p:types.SimpleNamespace(IsValid=lambda:True)))
for index in range(3):
    target=vertices[regions[index][1]]
    m.grasp([target],[None],[True]);assert m.active_index==index and m.holding
    assert sum(s.enabled for s in m.slots)==1
    try:m.grasp([target],[None],[True]);raise AssertionError('Double CLOSE accepted')
    except RuntimeError:pass
    m.ungrasp([False]);assert not m.holding and not m.attachment_enabled()
    assert m.slots[index].used
try:m.grasp([vertices[regions[0][1]]],[None],[True]);raise AssertionError('Exhausted slots accepted')
except RuntimeError:pass
m.slots[0].enabled=True
try:m.assert_exclusive();raise AssertionError('Unexpected inactive constraint enabled')
except RuntimeError:pass
m.slots[0].enabled=False
m.slots[0].enabled=m.slots[0].holding=True;m.slots[1].enabled=m.slots[1].holding=True
try:m.assert_exclusive();raise AssertionError('Two enabled slots accepted')
except RuntimeError:pass
# Check actual downloaded garment snapshots when available (world geometry only).
real=[]
for p in sorted((root/'results').glob('day4-l1-hem-fold-*/00_initial.npz'))[-3:]:
    with np.load(p,allow_pickle=False) as data:
        if 'vertices' not in data:continue
        current=select_regions(data['vertices']);assert len({x[1] for x in current})==3
        real.append(str(p))
manifest={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}
(root/'multi-grasp-files.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(root/'multi_grasp_local_checks.json').write_text(json.dumps({'python310_syntax':True,
    'synthetic_region_selection':True,'live_geometry_selection':True,'three_slot_state_machine_stub':True,
    'double_close_and_exhaustion_rejected':True,'multiple_attachment_guard':True,
    'real_geometry_snapshots_checked':real,'isaac_gpu_validation':False},indent=2),encoding='utf-8')
print('MULTI_GRASP_OFFLINE_GEOMETRY_AND_STATE_MACHINE_OK; GPU_RUN_PENDING')
