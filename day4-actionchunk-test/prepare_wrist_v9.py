"""Generate a fresh-process, pre-first-reset TGS velocity-iteration test."""
import ast
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent
original=(root/'day4-wrist-ik-execution-v7b.py').read_text(encoding='utf-8')
source=original.replace('ik-tail-execution-v7b-state-config-audit','ik-tail-execution-v9-pre-reset-velocity-zero')
helper='''
def start_with_pre_reset_velocity_zero():
    from backends.garmentlab_backend import _import_garmentlab
    FoldEnv,_=_import_garmentlab()
    import omni.timeline
    original_reset=FoldEnv.reset
    calls=[]
    def first_reset(env,*args,**kwargs):
        if calls:raise RuntimeError('Unexpected additional reset during startup')
        timeline=omni.timeline.get_timeline_interface()
        prim=env.world.stage.GetPrimAtPath('/World/Franka')
        if not prim.IsValid():raise RuntimeError('Robot root absent before reset')
        attr=prim.GetAttribute('physxArticulation:solverVelocityIterationCount')
        pos_attr=prim.GetAttribute('physxArticulation:solverPositionIterationCount')
        record={'scope':'USD edit before first FoldEnv.reset / World.reset',
                'timeline_stopped_before':bool(timeline.is_stopped()),
                'time_before':float(env.world.current_time),
                'time_step_before':int(env.world.current_time_step_index),
                'position_iterations_before':int(pos_attr.Get()),
                'velocity_iterations_before':int(attr.Get())}
        result['pre_reset_solver_config']=record
        calls.append(record)
        if not record['timeline_stopped_before'] or record['time_step_before']!=0:
            raise RuntimeError('Expected stopped timeline and zero steps before first reset')
        if (record['position_iterations_before'],record['velocity_iterations_before'])!=(64,64):
            raise RuntimeError('Unexpected initial solver configuration')
        if not attr.Set(0):raise RuntimeError('USD solver property edit failed')
        record['velocity_iterations_after_edit']=int(attr.Get())
        record['position_iterations_after_edit']=int(pos_attr.Get())
        if record['velocity_iterations_after_edit']!=0 or record['position_iterations_after_edit']!=64:
            raise RuntimeError('Unexpected solver config after edit')
        (out/'pre_reset_solver_config.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        value=original_reset(env,*args,**kwargs)
        record['velocity_iterations_after_reset']=int(attr.Get())
        record['position_iterations_after_reset']=int(pos_attr.Get())
        if (record['position_iterations_after_reset'],record['velocity_iterations_after_reset'])!=(64,0):
            raise RuntimeError('Reset overwrote requested configuration')
        (out/'pre_reset_solver_config.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print('PRE_FIRST_RESET_SOLVER_CONFIG_OK velocity 64 -> 0; position 64',flush=True)
        return value
    FoldEnv.reset=first_reset
    try:
        b.start()
    finally:
        FoldEnv.reset=original_reset
    if len(calls)!=1:raise RuntimeError('Pre-reset hook not executed exactly once')

'''
source=source.replace('try:\n    reference=Path(',helper+'try:\n    reference=Path(')
needle='    b.start();robot=b._env.robots[0]'
assert source.count(needle)==1
source=source.replace(needle,'    start_with_pre_reset_velocity_zero();robot=b._env.robots[0]')
ast.parse(source,feature_version=(3,10))
a=ast.parse(original);b=ast.parse(source)
for name in ('drive','drive_ik','submit_joint_targets','probe_step','dump_runtime_audit','install_contact_reporting'):
    assert ast.dump(next(x for x in a.body if isinstance(x,ast.FunctionDef) and x.name==name))==ast.dump(next(x for x in b.body if isinstance(x,ast.FunctionDef) and x.name==name))
(root/'day4-wrist-ik-execution-v9.py').write_text(source,encoding='utf-8',newline='\n')
manifest={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
          ['day4-wrist-ik-execution-v9.py','hem_fold_geometry.py','l1_fold_geometry.py']}
(root/'wrist-ik-execution-v9-files.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
runner=(root/'run-wrist-ik-execution-v7b.sh').read_text(encoding='utf-8').replace('v7b','v9')
(root/'run-wrist-ik-execution-v9.sh').write_text(runner,encoding='utf-8',newline='\n')
print('V9_PYTHON310_AND_UNCHANGED_CONTROL_AST_OK; NOT_RUN_ON_GPU')
