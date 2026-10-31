"""Prepare configuration-only asset audit; no wrist trajectory execution."""
import ast
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parent
source=(root/'day4-wrist-ik-execution-v9.py').read_text(encoding='utf-8')
source=source.replace('day4-wrist-ik-execution-', 'day4-franka-asset-audit-')
source=source.replace('ik-tail-execution-v9-pre-reset-velocity-zero','franka-asset-provenance-v1b-usd-timecode')
source=source.replace("'scope':'Robot-only IK tail actuator execution; no attachment; no collision certification or cloth validation'", "'scope':'Configuration-only after initialization; no wrist trajectory, grasp or fold execution'")
start=source.index("try:\n    reference=Path(")
end=source.index('except BaseException as exc:',start)
main='''def asset_property_record(attr):
    from pxr import Usd
    record={}
    try:record['composed_value']=audit_value(attr.Get())
    except Exception as exc:record['value_error']=repr(exc)
    try:
        specs=attr.GetPropertyStack(Usd.TimeCode.Default())
        record['property_stack']=[{'layer':x.layer.identifier,'path':str(x.path),
                                  'default':audit_value(x.default)} for x in specs]
    except Exception as exc:record['property_stack_error']=repr(exc)
    return record

try:
    start_with_pre_reset_velocity_zero();robot=b._env.robots[0]
    dump_runtime_audit()
    from pxr import UsdGeom, UsdPhysics
    stage=b._env.world.stage
    audit={'stage_meters_per_unit':float(UsdGeom.GetStageMetersPerUnit(stage)),
           'stage_kilograms_per_unit':None,
           'root_layer':stage.GetRootLayer().identifier,
           'session_layer':stage.GetSessionLayer().identifier,'prims':[],
           'runtime_tensor_methods':{},'scope':'Composed USD origins plus available runtime link properties'}
    kg=getattr(UsdPhysics,'GetStageKilogramsPerUnit',None)
    if callable(kg):audit['stage_kilograms_per_unit']=float(kg(stage))
    for prim in stage.Traverse():
        path=str(prim.GetPath())
        if not(path=='/World/Franka' or path.startswith('/World/Franka/')):continue
        if not(prim.HasAPI(UsdPhysics.RigidBodyAPI) or prim.IsA(UsdPhysics.Joint) or path=='/World/Franka'):continue
        record={'path':path,'attributes':{}}
        try:record['prim_stack']=[{'layer':x.layer.identifier,'path':str(x.path)} for x in prim.GetPrimStack()]
        except Exception as exc:record['prim_stack_error']=repr(exc)
        for attr in prim.GetAttributes():
            name=attr.GetName()
            if not(name.startswith(('drive:','physics:mass','physics:diagonalInertia','physics:centerOfMass','physxArticulation:')) or name.startswith('xformOp:')):continue
            record['attributes'][name]=asset_property_record(attr)
        audit['prims'].append(record)
        (out/'asset_provenance.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    view=robot._robot._articulation_view
    raw=getattr(view,'_physics_view',None)
    for label,obj in [('articulation_view',view),('physics_tensor_view',raw)]:
        names=[n for n in dir(obj) if n.startswith('get_') and any(x in n for x in ('inertia','masse','com','link_transform'))]
        audit['runtime_tensor_methods'][label]={'available_names':names,'values':{}}
        for name in names:
            if name not in ('get_masses','get_inertias','get_coms','get_link_masses','get_link_inertias','get_link_coms','get_link_transforms'):continue
            try:audit['runtime_tensor_methods'][label]['values'][name]={'status':'ok','value':audit_value(getattr(obj,name)())}
            except Exception as exc:audit['runtime_tensor_methods'][label]['values'][name]={'status':'error','error':repr(exc)}
    (out/'asset_provenance.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    result['asset_audit_completed']=True
    result['asset_property_stack_errors']=sum('property_stack_error' in x for p in audit['prims'] for x in p['attributes'].values())
    result['asset_property_stack_successes']=sum('property_stack' in x for p in audit['prims'] for x in p['attributes'].values())
    result['wrist_path_executed']=False
    print('ASSET_PROPERTY_STACK_ERRORS',result['asset_property_stack_errors'],flush=True)
    print('ASSET_PROPERTY_STACK_SUCCESSES',result['asset_property_stack_successes'],flush=True)
    print('FRANKA_ASSET_AUDIT_SAVED',out/'asset_provenance.json',flush=True)
'''
source=source[:start]+main+source[end:]
source=source.replace("    print('CONTACT_EVENT_COUNT',result.get('contact_event_count',0),flush=True)","    print('ASSET_AUDIT_COMPLETED',result.get('asset_audit_completed',False),flush=True)")
ast.parse(source,feature_version=(3,10))
(root/'day4-franka-asset-audit.py').write_text(source,encoding='utf-8',newline='\n')
manifest={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['day4-franka-asset-audit.py','hem_fold_geometry.py','l1_fold_geometry.py']}
(root/'franka-asset-audit-files.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
runner=(root/'run-wrist-ik-execution-v9.sh').read_text(encoding='utf-8').replace('wrist-ik-execution-v9-files.json','franka-asset-audit-files.json').replace('day4-wrist-ik-execution-v9.py','day4-franka-asset-audit.py')
(root/'run-franka-asset-audit.sh').write_text(runner,encoding='utf-8',newline='\n')
tree=ast.parse(source)
main_try=next(x for x in tree.body if isinstance(x,ast.Try))
calls=[x.func.id for x in ast.walk(main_try) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name)]
assert not set(calls)&{'drive','drive_ik','probe_step','submit_joint_targets'}
print('ASSET_AUDIT_PYTHON310_NO_PATH_CALLS_OK; RUNTIME_METHOD_AVAILABILITY_PENDING')
