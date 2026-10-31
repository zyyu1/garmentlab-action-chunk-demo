"""Prepare v7: observation-only additions to v6. No simulator required locally."""
import ast
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent
source=(root/'day4-wrist-ik-execution-v6.py').read_text(encoding='utf-8')
source=source.replace('ik-tail-execution-v6-velocity-gate','ik-tail-execution-v7b-state-config-audit')
helper='''
def audit_value(value):
    if isinstance(value,dict):return {str(k):audit_value(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [audit_value(v) for v in value]
    if value is None or isinstance(value,(bool,int,float,str)):return value
    # USD quaternions become scalar object arrays under np.asarray: handle explicitly.
    if callable(getattr(value,'GetReal',None)) and callable(getattr(value,'GetImaginary',None)):
        return {'type':type(value).__name__,'wxyz':[float(value.GetReal())]+[float(x) for x in value.GetImaginary()]}
    if hasattr(value,'detach'):return audit_value(value.detach().cpu().numpy())
    if isinstance(value,np.ndarray):return audit_value(value.tolist())
    if isinstance(value,np.generic):return audit_value(value.item())
    try:
        converted=np.asarray(value)
        if converted.ndim>0:return audit_value(converted.tolist())
        if converted.dtype.kind!='O':return audit_value(converted.item())
    except Exception:pass
    return {'type':type(value).__name__,'repr':str(value)}

def dump_runtime_audit():
    from pxr import UsdPhysics
    stage=b._env.world.stage
    config={'scope':'Read-only runtime getters and composed USD attributes; no settings changed',
            'runtime_getters':{},'usd_prims':[]}
    subjects={'world':b._env.world,'robot':robot._robot,
              'view':getattr(robot._robot,'_articulation_view',None),
              'controller':robot._articulation_controller}
    getters={'world':['get_physics_dt','get_rendering_dt'],
       'robot':['get_gains','get_max_efforts','get_effort_modes','get_max_joint_velocities',
         'get_solver_position_iteration_count','get_solver_velocity_iteration_count','get_enabled_self_collisions'],
       'view':['get_gains','get_max_efforts','get_effort_modes','get_max_joint_velocities',
         'get_solver_position_iteration_counts','get_solver_velocity_iteration_counts','get_enabled_self_collisions'],
       'controller':['get_gains']}
    for label,obj in subjects.items():
        record={}
        for name in getters[label]:
            try:
                method=getattr(obj,name,None)
                record[name]={'status':'unavailable'} if not callable(method) else {'status':'ok','value':audit_value(method())}
            except Exception as exc:record[name]={'status':'error','error':repr(exc)}
        if label in ('robot','view'):
            try:record['dof_properties']=audit_value(obj.dof_properties)
            except Exception as exc:record['dof_properties_error']=repr(exc)
        config['runtime_getters'][label]=record
        for name in ['get_joint_positions','get_joint_velocities','step']:
            try:
                method=getattr(obj,name,None)
                if callable(method):(out/(label+'_'+name+'_source.py')).write_text(inspect.getsource(method),encoding='utf-8')
            except Exception as exc:config.setdefault('source_errors',{})[label+'.'+name]=repr(exc)
    for prim in stage.Traverse():
        path=str(prim.GetPath())
        if not (path=='/World/Franka' or path.startswith('/World/Franka/') or prim.IsA(UsdPhysics.Scene)):continue
        attrs={}
        for attr in prim.GetAttributes():
            name=attr.GetName()
            if not (name.startswith(('physics:','physx','drive:')) or name in ('xformOp:scale',)):continue
            try:attrs[name]={'value':audit_value(attr.Get()),'authored':attr.HasAuthoredValueOpinion()}
            except Exception as exc:attrs[name]={'error':repr(exc)}
        config['usd_prims'].append({'path':path,'type':prim.GetTypeName(),'attributes':attrs})
    config['source_hashes']={}
    for label,obj in [('backend',b),('environment',b._env),('robot_wrapper',robot)]:
        try:
            original=Path(inspect.getfile(type(obj)))
            raw=original.read_bytes();(out/(label+'_runtime.py')).write_bytes(raw)
            config['source_hashes'][label]={'path':str(original),'sha256':__import__('hashlib').sha256(raw).hexdigest()}
        except Exception as exc:config['source_hashes'][label]={'error':repr(exc)}
    (out/'runtime_config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    result['runtime_config_file']='runtime_config.json'

def sampled_state():
    state={'position':array(robot._robot.get_joint_positions()).copy().tolist(),
           'velocity':array(robot._robot.get_joint_velocities()).copy().tolist()}
    for key in ('current_time','current_time_step_index'):
        try:state[key]=audit_value(getattr(b._env.world,key))
        except Exception as exc:state[key]={'error':repr(exc)}
    return state

'''
needle='def probe_step():\n    global probe_step_count\n    probe_step_count+=1\n    b._env.world.step()'
replacement='''def probe_step():
    global probe_step_count
    before=sampled_state()
    probe_step_count+=1
    b._env.world.step()
    after=sampled_state()
    with (out/'step_states.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'step':probe_step_count,'phase':probe_phase,'before':before,'after':after})+'\\n')'''
assert source.count(needle)==1
source=source.replace(needle,helper+replacement)
needle='    contact_subscription=install_contact_reporting()'
assert source.count(needle)==1
source=source.replace(needle,needle+'\n    dump_runtime_audit()')
ast.parse(source,feature_version=(3,10))
# Compare the control functions structurally: only observations outside these functions changed.
old_tree=ast.parse((root/'day4-wrist-ik-execution-v6.py').read_text(encoding='utf-8'))
new_tree=ast.parse(source)
for name in ('drive','drive_ik','submit_joint_targets','install_contact_reporting'):
    old=next(x for x in old_tree.body if isinstance(x,ast.FunctionDef) and x.name==name)
    new=next(x for x in new_tree.body if isinstance(x,ast.FunctionDef) and x.name==name)
    assert ast.dump(old)==ast.dump(new),name
(root/'day4-wrist-ik-execution-v7b.py').write_text(source,encoding='utf-8',newline='\n')
manifest={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
          ['day4-wrist-ik-execution-v7b.py','hem_fold_geometry.py','l1_fold_geometry.py']}
(root/'wrist-ik-execution-v7b-files.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
runner=(root/'run-wrist-ik-execution-v6.sh').read_text(encoding='utf-8').replace('v6','v7b')
(root/'run-wrist-ik-execution-v7b.sh').write_text(runner,encoding='utf-8',newline='\n')
print('V7B_PYTHON310_AND_CONTROL_AST_OK; NOT_RUN_ON_GPU')
