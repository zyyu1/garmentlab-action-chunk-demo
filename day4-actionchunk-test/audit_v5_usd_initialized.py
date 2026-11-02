"""Initialization-only USD/PhysX audit. No public actions or rollout after start.

Run next to the pinned v5 sources in /root/autodl-tmp. Uses their startup
verbatim, stopping before robot.open and before any diagnostic motion.
"""
import ast, hashlib, json, os, sys, traceback
from pathlib import Path
import numpy as np

root=Path('/root/autodl-tmp')
sys.path.insert(0,str(root));os.chdir(root)
os.environ['GARMENTLAB_ATTACHMENT_OVERLAP']='0.005'
os.environ['GARMENTLAB_DISABLED_ATTACHMENT_PROBE']='0'
manifest=json.loads((root/'square-grasp-hold-v5-files.json').read_text())
for name,digest in manifest.items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
src=root/'day4-square-grasp-hold-v5.py'
tree=ast.parse(src.read_text());prefix=[]
for node in tree.body:
    if isinstance(node,ast.Try):
        for child in node.body:
            prefix.append(child)
            if isinstance(child,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='robot' for t in child.targets):break
        else:raise RuntimeError('Startup boundary not found')
        break
    prefix.append(node)
else:raise RuntimeError('Main startup not found')
# Separate directory name; startup itself is otherwise unchanged.
for node in ast.walk(ast.Module(body=prefix,type_ignores=[])):
    if isinstance(node,ast.Constant) and node.value=='day4-square-grasp-hold-v5-':node.value='day4-v5-usd-initialized-'
ns={'__name__':'geometry_initialization_audit','__file__':str(src)}
report={'scope':'Initialization only; no public actions; no explicit world.step after startup', 'errors':[]}
try:
    exec(compile(ast.fix_missing_locations(ast.Module(body=prefix,type_ignores=[])),str(src),'exec'),ns)
    from pxr import UsdGeom,UsdPhysics,Gf
    import omni.physics.tensors as tensors
    b=ns['b'];stage=b._env.world.stage
    report['step_after_start']=int(b._env.world.current_time_step_index)
    report['meters_per_unit']=UsdGeom.GetStageMetersPerUnit(stage)
    cache=UsdGeom.XformCache();hand=stage.GetPrimAtPath('/World/Franka/panda_hand')
    invhand=cache.GetLocalToWorldTransform(hand).GetInverse()
    report['colliders']=[]
    for prim in stage.Traverse():
        path=str(prim.GetPath())
        if not prim.HasAPI(UsdPhysics.CollisionAPI):continue
        if not ('finger' in path or 'defaultGroundPlane' in path or '/World/Attachment/' in path):continue
        row={'path':path,'type':prim.GetTypeName(),'attributes':{}}
        for attr in prim.GetAttributes():
            name=attr.GetName()
            if any(s in name for s in ['contactOffset','restOffset','approximation','collisionEnabled','xformOp:','physxConvexDecompositionCollision:']):
                val=attr.Get();row['attributes'][name]=str(val)
        if prim.IsA(UsdGeom.Mesh):
            mat=cache.GetLocalToWorldTransform(prim)*invhand
            points=UsdGeom.Mesh(prim).GetPointsAttr().Get()
            row['mesh_points_hand_frame_m']=[list(mat.Transform(Gf.Vec3d(*map(float,p)))) for p in points]
        row['world_transform_row_major']=[list(v) for v in cache.GetLocalToWorldTransform(prim)]
        report['colliders'].append(row)
    sim=tensors.create_simulation_view('torch');sim.set_subspace_roots('/')
    report['effective_offsets']={}
    for path in ['/World/Franka/panda_leftfinger','/World/Franka/panda_rightfinger','/World/Attachment/attach_2/block','/World/defaultGroundPlane/GroundPlane/CollisionPlane']:
        row={}
        try:
            view=sim.create_rigid_body_view(path)
            if view.count<1 or view.max_shapes<1:raise RuntimeError('No runtime shape matched')
            row={'count':int(view.count),'max_shapes':int(view.max_shapes),
                 'contact_offsets':view.get_contact_offsets().detach().cpu().tolist(),
                 'rest_offsets':view.get_rest_offsets().detach().cpu().tolist()}
        except Exception as e:row={'error':repr(e)}
        report['effective_offsets'][path]=row
    report['step_after_read']=int(b._env.world.current_time_step_index)
    assert report['step_after_read']==report['step_after_start']
    report['source_manifest']=manifest
    report['passed_readout']=all('error' not in r for r in report['effective_offsets'].values())
except BaseException as e:
    report['errors'].append(repr(e));traceback.print_exc()
finally:
    out=ns.get('out',root/'day4-v5-usd-initialized-failed');out.mkdir(exist_ok=True)
    (out/'geometry_readout.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('GEOMETRY_READOUT',out/'geometry_readout.json',flush=True)
    print('OFFSET_SUMMARY',json.dumps(report.get('effective_offsets',{})),flush=True)
    app=getattr(ns.get('b'),'_simulation_app',None)
    if app is not None:app.close()
