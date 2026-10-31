"""Robot-only delayed-pitch feasibility probe. No grasp or fold acceptance."""
import json
import sys
import traceback
import inspect
from pathlib import Path
from datetime import datetime
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0,'/root/autodl-tmp/garmentlab-action-chunk-demo')
from backends.garmentlab_backend import GarmentLabBackend
from hem_fold_geometry import hem_arc, short_segments

out=Path('/root/autodl-tmp')/('day4-wrist-ik-execution-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result={'probe_version':'ik-tail-execution-v11-finite-drive-gains',
        'scope':'Robot-only IK tail actuator execution; no attachment; no collision certification or cloth validation',
        'all_targets_reached':False,'formal_day4_success':False,'targets':[],
        'settle_velocity_limit_rad_s':0.05,'settle_consecutive_steps':6,
        'velocity_gate_scope':'IK tail only; RMP prefix unchanged',
        'script_sha256':__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest()}
b=GarmentLabBackend(prepared_grasp=False)

def array(x):
    return x.detach().cpu().numpy() if hasattr(x,'detach') else np.asarray(x)

probe_phase='initialization'
probe_step_count=0
contact_subscription=None

def install_contact_reporting():
    from pxr import PhysxSchema, UsdPhysics, PhysicsSchemaTools
    from omni.physx import get_physx_simulation_interface
    stage=b._env.world.stage
    paths=[]
    for prim in stage.Traverse():
        if str(prim.GetPath()).startswith('/World/Franka/') and prim.HasAPI(UsdPhysics.RigidBodyAPI):
            PhysxSchema.PhysxContactReportAPI.Apply(prim).CreateThresholdAttr(0.0)
            paths.append(str(prim.GetPath()))
    if not paths:raise RuntimeError('No robot rigid bodies for contact reports')
    result['contact_report_bodies']=paths
    result['contact_event_count']=0
    result['contact_callback_errors']=[]
    def callback(headers,data):
        try:
            for h in headers:
                actors=[str(PhysicsSchemaTools.intToSdfPath(h.actor0)),str(PhysicsSchemaTools.intToSdfPath(h.actor1))]
                if not any(x.startswith('/World/Franka/') for x in actors):continue
                contacts=[]
                for j in range(h.contact_data_offset,h.contact_data_offset+h.num_contact_data):
                    c=data[j]
                    contacts.append({'position':[float(v) for v in c.position],
                        'normal':[float(v) for v in c.normal],'impulse':[float(v) for v in c.impulse]})
                row={'step':probe_step_count,'phase':probe_phase,'type':str(h.type),'actors':actors,
                     'colliders':[str(PhysicsSchemaTools.intToSdfPath(h.collider0)),str(PhysicsSchemaTools.intToSdfPath(h.collider1))],
                     'contacts':contacts}
                with (out/'contacts.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
                result['contact_event_count']+=1
        except Exception as exc:
            if len(result['contact_callback_errors'])<10:result['contact_callback_errors'].append(repr(exc))
    subscription=get_physx_simulation_interface().subscribe_contact_report_events(callback)
    (out/'contacts.jsonl').touch(exist_ok=True)
    return subscription


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

def probe_step():
    global probe_step_count
    before=sampled_state()
    probe_step_count+=1
    b._env.world.step()
    after=sampled_state()
    with (out/'step_states.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'step':probe_step_count,'phase':probe_phase,'before':before,'after':after})+'\n')

def drive(target, quaternion, label):
    global probe_phase
    probe_phase=label
    target=np.asarray(target,dtype=float)
    consecutive=0
    for step in range(240):
        robot.move(target,quaternion)
        probe_step()
        position,actual_q=robot.get_cur_ee_pos()
        pos_error=float(np.linalg.norm(np.asarray(position)-target))
        angle_error=0.0 if quaternion is None else float((
            Rotation.from_quat(np.asarray(quaternion)[[1,2,3,0]])*
            Rotation.from_quat(np.asarray(actual_q)[[1,2,3,0]]).inv()).magnitude())
        reached=pos_error<.01 and angle_error<.1 and bool(robot.reach(target,quaternion))
        consecutive=consecutive+1 if reached else 0
        if consecutive>=6:break
    row={'label':label,'target_position':target.tolist(),
         'target_quaternion_wxyz':None if quaternion is None else quaternion.tolist(),
         'actual_position':np.asarray(position).tolist(),'actual_quaternion_wxyz':np.asarray(actual_q).tolist(),
         'position_error_m':pos_error,'rotation_error_rad':angle_error,
         'joint_positions':array(robot._robot.get_joint_positions()).tolist(),
         'steps':step+1,'reached':consecutive>=6}
    result['targets'].append(row)
    print('REACH_CHECK',json.dumps(row),flush=True)
    if not row['reached']:raise RuntimeError('Pose tracking failed: '+label)


def submit_joint_targets(positions):
    # Explicit indices bypass Isaac 4.0's CUDA-unsafe missing-value loop.
    import torch
    from omni.isaac.core.utils.types import ArticulationAction
    reference=robot._robot.get_joint_positions()
    values=np.asarray(positions,dtype=float)
    if values.ndim!=1 or len(values)!=len(robot._robot.dof_names) or not np.isfinite(values).all():
        raise ValueError('Invalid full joint target')
    if not isinstance(reference,torch.Tensor):
        raise TypeError('Expected Torch articulation state')
    target=torch.as_tensor(values,dtype=reference.dtype,device=reference.device)
    indices=torch.arange(len(values),dtype=torch.long,device=reference.device)
    robot._articulation_controller.apply_action(ArticulationAction(
        joint_positions=target,joint_velocities=torch.zeros_like(target),joint_indices=indices))

def applied_targets():
    try:
        a=robot._articulation_controller.get_applied_action()
        return {key:None if getattr(a,key,None) is None else array(getattr(a,key)).tolist()
                for key in ('joint_positions','joint_velocities','joint_efforts','joint_indices')}
    except Exception as exc:return {'read_error':repr(exc)}

def drive_ik(target, quaternion, label):
    global probe_phase
    probe_phase=label
    from omni.isaac.core.utils.types import ArticulationAction
    wrapper=robot._kinematic_solover
    solver=wrapper.get_kinematics_solver()
    frame=wrapper.get_end_effector_frame()
    if frame!=robot._controller.rmp_flow_config['end_effector_frame_name']:
        raise RuntimeError('IK/RMP frame mismatch')
    base_pos,base_q=robot._robot.get_world_pose()
    solver.set_robot_base_pose(array(base_pos),array(base_q))
    names=list(solver.get_joint_names());dofs=list(robot._robot.dof_names)
    ids=[dofs.index(n) for n in names]
    full=array(robot._robot.get_joint_positions()).copy()
    seed=full[ids].copy()
    solution,ok=solver.compute_inverse_kinematics(frame,target,quaternion,
        warm_start=seed,position_tolerance=.002,orientation_tolerance=.02)
    if solution is None:raise RuntimeError('No IK solution: '+label)
    goal=array(solution).reshape(-1)
    if goal.shape!=seed.shape or not np.isfinite(goal).all():raise RuntimeError('Invalid IK array')
    limits={}
    for prim in b._env.world.stage.Traverse():
        if prim.GetTypeName()=='PhysicsRevoluteJoint':
            limits[prim.GetName()]=np.deg2rad([prim.GetAttribute('physics:lowerLimit').Get(),prim.GetAttribute('physics:upperLimit').Get()])
    bounds=np.asarray([limits[n] for n in names])
    fk,rot=solver.compute_forward_kinematics(frame,goal,position_only=False)
    pe=float(np.linalg.norm(array(fk).reshape(3)-target))
    re=float((Rotation.from_quat(quaternion[[1,2,3,0]])*Rotation.from_matrix(array(rot).reshape(3,3)).inv()).magnitude())
    delta=float(np.max(np.abs(goal-seed)))
    row={'label':label,'controller':'interpolated_joint_position',
         'target_position':target.tolist(),'target_quaternion_wxyz':quaternion.tolist(),
         'seed':seed.tolist(),'solution':goal.tolist(),'ik_success':bool(ok),
         'fk_position_error_m':pe,'fk_rotation_error_rad':re,'max_joint_delta_rad':delta,'reached':False}
    row['pre_switch_applied_targets']=applied_targets()
    row['trace']=[]
    row['joint_names']=names
    result['targets'].append(row)
    if not (ok and pe<=.002 and re<=.02 and np.all(goal>=bounds[:,0]) and np.all(goal<=bounds[:,1]) and delta<=.35):
        raise RuntimeError('IK validation or continuity bound failed: '+label)
    count=max(1,int(np.ceil(delta/.005)))
    peak_error=0.0
    # Actuator targets only: never teleport joints or reset velocities.
    for k in range(1,count+1):
        command=seed+(goal-seed)*k/count
        full[ids]=command
        submit_joint_targets(full)
        probe_step()
        actual=array(robot._robot.get_joint_positions())[ids]
        error=float(np.max(np.abs(actual-command)))
        peak_error=max(peak_error,error)
        row['trace'].append({'phase':'interpolation','step':k,'command':command.tolist(),
            'actual':actual.tolist(),'actual_velocity':array(robot._robot.get_joint_velocities())[ids].tolist(),
            'error_by_joint':(actual-command).tolist(),'applied_targets':applied_targets()})
        if not np.isfinite(actual).all() or error>.15:
            row.update(interpolation_step=k,tracking_error_rad=error)
            raise RuntimeError('Joint tracking diverged: '+label)
    full[ids]=goal;consecutive=0
    for step in range(240):
        submit_joint_targets(full)
        probe_step()
        position,actual_q=robot.get_cur_ee_pos()
        pe=float(np.linalg.norm(np.asarray(position)-target))
        re=float((Rotation.from_quat(quaternion[[1,2,3,0]])*Rotation.from_quat(np.asarray(actual_q)[[1,2,3,0]]).inv()).magnitude())
        je=float(np.max(np.abs(array(robot._robot.get_joint_positions())[ids]-goal)))
        row['trace'].append({'phase':'settling','step':step+1,'command':goal.tolist(),
            'actual':array(robot._robot.get_joint_positions())[ids].tolist(),
            'actual_velocity':array(robot._robot.get_joint_velocities())[ids].tolist(),
            'applied_targets':applied_targets()})
        velocity=array(robot._robot.get_joint_velocities())[ids]
        speed=float(np.max(np.abs(velocity)))
        row['trace'][-1]['joint_speed_max_rad_s']=speed
        row['trace'][-1]['position_error_m']=pe
        row['trace'][-1]['rotation_error_rad']=re
        row['trace'][-1]['joint_error_rad']=je
        if not (np.isfinite(velocity).all() and np.isfinite(je) and np.isfinite(pe) and np.isfinite(re)) or je>.15:
            row.update(settling_step=step+1,tracking_error_rad=je,final_joint_speed_rad_s=speed)
            raise RuntimeError('Settling tracking diverged: '+label)
        reached=pe<.01 and re<.1 and je<.02 and speed<.05
        consecutive=consecutive+1 if reached else 0
        if consecutive>=6:break
    row.update(position_error_m=pe,rotation_error_rad=re,joint_error_rad=je,
        peak_interpolation_tracking_error_rad=peak_error,interpolation_steps=count,
        settling_steps=step+1,final_joint_speed_rad_s=speed,joint_positions=array(robot._robot.get_joint_positions()).tolist(),reached=consecutive>=6)
    print('IK_EXECUTION',json.dumps({k:v for k,v in row.items() if k!='trace'}),flush=True)
    if not row['reached']:raise RuntimeError('IK execution tracking failed: '+label)



EXPECTED_INERTIA_BODIES={'/World/Franka/panda_link0': {'path': '/World/Franka/panda_link0', 'mass_kg': 2.8142027854919434, 'diagonal_inertia_kg_m2': [1.298869733545871e-06, 1.6535527720407117e-06, 2.033116288657766e-06], 'matching_tensor_rows': [0], 'principal_radii_of_gyration_m': [0.0006793680274736083, 0.0007665338457296101, 0.0008499696442182646], 'source': 'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Robots/Franka/franka.usd'}, '/World/Franka/panda_link1': {'path': '/World/Franka/panda_link1', 'mass_kg': 2.359999656677246, 'diagonal_inertia_kg_m2': [1.8686388330024783e-06, 1.4378986179508502e-06, 9.068119766197924e-07], 'matching_tensor_rows': [1], 'principal_radii_of_gyration_m': [0.0008898293268184419, 0.0007805633632436522, 0.0006198729054188767], 'source': 'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Robots/Franka/franka.usd'}, '/World/Franka/panda_link2': {'path': '/World/Franka/panda_link2', 'mass_kg': 2.379518747329712, 'diagonal_inertia_kg_m2': [1.90388720966439e-06, 9.142911494564032e-07, 1.469753669880447e-06], 'matching_tensor_rows': [2], 'principal_radii_of_gyration_m': [0.0008944911390495644, 0.0006198658240966588, 0.0007859188607365145], 'source': 'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Robots/Franka/franka.usd'}, '/World/Franka/panda_link3': {'path': '/World/Franka/panda_link3', 'mass_kg': 2.6498823165893555, 'diagonal_inertia_kg_m2': [1.2930017874168698e-06, 1.5024211279524025e-06, 1.4273459782998543e-06], 'matching_tensor_rows': [3], 'principal_radii_of_gyration_m': [0.0006985319405371213, 0.0007529784510901706, 0.0007339244133323361], 'source': 'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Robots/Franka/franka.usd'}, '/World/Franka/panda_link4': {'path': '/World/Franka/panda_link4', 'mass_kg': 2.6948018074035645, 'diagonal_inertia_kg_m2': [1.3387460739977541e-06, 1.45143246754742e-06, 1.55175541749486e-06], 'matching_tensor_rows': [4], 'principal_radii_of_gyration_m': [0.0007048321248476795, 0.0007338968132233773, 0.0007588365137880803], 'source': 'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Robots/Franka/franka.usd'}, '/World/Franka/panda_link5': {'path': '/World/Franka/panda_link5', 'mass_kg': 2.9812817573547363, 'diagonal_inertia_kg_m2': [3.255657020417857e-06, 2.706604618651909e-06, 1.1502337429192266e-06], 'matching_tensor_rows': [5], 'principal_radii_of_gyration_m': [0.0010450036606878524, 0.0009528200733356755, 0.0006211429217624749], 'source': 'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Robots/Franka/franka.usd'}, '/World/Franka/panda_link6': {'path': '/World/Franka/panda_link6', 'mass_kg': 1.1285806894302368, 'diagonal_inertia_kg_m2': [2.6052563839584764e-07, 3.9897227566143556e-07, 4.7048590090525977e-07], 'matching_tensor_rows': [6], 'principal_radii_of_gyration_m': [0.0004804618695734217, 0.0005945728189471972, 0.000645664634652771], 'source': 'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Robots/Franka/franka.usd'}, '/World/Franka/panda_link7': {'path': '/World/Franka/panda_link7', 'mass_kg': 0.40529125928878784, 'diagonal_inertia_kg_m2': [6.316591338872968e-08, 6.319638856666643e-08, 1.0607720923871966e-07], 'matching_tensor_rows': [7], 'principal_radii_of_gyration_m': [0.00039478238955133817, 0.00039487761189625905, 0.0005115963341922888], 'source': 'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Robots/Franka/franka.usd'}, '/World/Franka/panda_hand': {'path': '/World/Franka/panda_hand', 'mass_kg': 0.5583304762840271, 'diagonal_inertia_kg_m2': [2.3394447623559245e-07, 5.782785805763524e-08, 2.131029361862602e-07], 'matching_tensor_rows': [9], 'principal_radii_of_gyration_m': [0.0006473076364192873, 0.00032182730319393167, 0.0006178016297503633], 'source': 'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Robots/Franka/franka.usd'}, '/World/Franka/panda_leftfinger': {'path': '/World/Franka/panda_leftfinger', 'mass_kg': 0.0140552232041955, 'diagonal_inertia_kg_m2': [4.204130377161164e-10, 3.9026365472594193e-10, 1.3347495331217374e-10], 'matching_tensor_rows': [10, 11], 'principal_radii_of_gyration_m': [0.00017294946164057197, 0.00016663268037779257, 9.744981419585079e-05], 'source': 'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Robots/Franka/franka.usd'}, '/World/Franka/panda_rightfinger': {'path': '/World/Franka/panda_rightfinger', 'mass_kg': 0.0140552232041955, 'diagonal_inertia_kg_m2': [4.204130377161164e-10, 3.9026365472594193e-10, 1.3347495331217374e-10], 'matching_tensor_rows': [10, 11], 'principal_radii_of_gyration_m': [0.00017294946164057197, 0.00016663268037779257, 9.744981419585079e-05], 'source': 'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Robots/Franka/franka.usd'}}
BASELINE_EFFECTIVE_MASSES=[2.8142027854919434, 2.359999656677246, 2.379518747329712, 2.6498823165893555, 2.6948018074035645, 2.9812819957733154, 1.1285806894302368, 0.40529125928878784, 0.10000000149011612, 0.5583304762840271, 0.0140552232041955, 0.0140552232041955]
BASELINE_EFFECTIVE_INERTIAS=[[1.298869733545871e-06, 0.0, 0.0, 0.0, 1.6535527720407117e-06, 0.0, 0.0, 0.0, 2.033116288657766e-06], [1.868638946689316e-06, 0.0, 0.0, 0.0, 1.4378986179508502e-06, 0.0, 0.0, 0.0, 9.068119197763735e-07], [1.90388720966439e-06, 0.0, 0.0, 0.0, 9.142911494564032e-07, 0.0, 0.0, 0.0, 1.469753669880447e-06], [1.2930017874168698e-06, 0.0, 0.0, 0.0, 1.5024210142655647e-06, 0.0, 0.0, 0.0, 1.4273459782998543e-06], [1.3387460739977541e-06, 0.0, 0.0, 0.0, 1.4514325812342577e-06, 0.0, 0.0, 0.0, 1.55175541749486e-06], [3.255657020417857e-06, 0.0, 0.0, 0.0, 2.706604618651909e-06, 0.0, 0.0, 0.0, 1.1502337429192266e-06], [2.6052563839584764e-07, 0.0, 0.0, 0.0, 3.9897227566143556e-07, 0.0, 0.0, 0.0, 4.7048590090525977e-07], [6.316591338872968e-08, 0.0, 0.0, 0.0, 6.319638856666643e-08, 0.0, 0.0, 0.0, 1.060772021332923e-07], [0.00039999998989515007, 0.0, 0.0, 0.0, 0.00039999998989515007, 0.0, 0.0, 0.0, 0.00039999998989515007], [2.3394447623559245e-07, 0.0, 0.0, 0.0, 5.782785450492156e-08, 0.0, 0.0, 0.0, 2.131029361862602e-07], [4.204130377161164e-10, 0.0, 0.0, 0.0, 3.9026365472594193e-10, 0.0, 0.0, 0.0, 1.3347495331217374e-10], [4.204130377161164e-10, 0.0, 0.0, 0.0, 3.9026365472594193e-10, 0.0, 0.0, 0.0, 1.3347495331217374e-10]]
BASELINE_GAINS=[[572957824.0, 572957824.0, 572957824.0, 572957824.0, 572957824.0, 572957824.0, 572957824.0, 10000.0, 0.0], [5729578.0, 5729578.0, 5729578.0, 5729578.0, 5729578.0, 5729578.0, 5729578.0, 1000.0, 0.0]]


ARM_GAIN_PATHS=['/World/Franka/panda_link0/panda_joint1', '/World/Franka/panda_link1/panda_joint2', '/World/Franka/panda_link2/panda_joint3', '/World/Franka/panda_link3/panda_joint4', '/World/Franka/panda_link4/panda_joint5', '/World/Franka/panda_link5/panda_joint6', '/World/Franka/panda_link6/panda_joint7']
ARM_GAIN_SCALE=1e-6

def request_finite_arm_gains(env):
    changes=[]
    for path in ARM_GAIN_PATHS:
        prim=env.world.stage.GetPrimAtPath(path)
        if not prim.IsValid():raise RuntimeError('Missing arm drive: '+path)
        record={'path':path,'scale':ARM_GAIN_SCALE,'attributes':{}}
        for name,expected in [('stiffness',1e7),('damping',1e5)]:
            attr=prim.GetAttribute('drive:angular:physics:'+name)
            before=float(attr.Get())
            if not np.isclose(before,expected,rtol=1e-6):raise RuntimeError('Unexpected drive gain: '+path+' '+name)
            if not attr.Set(before*ARM_GAIN_SCALE):raise RuntimeError('Gain edit failed')
            record['attributes'][name]={'before':before,'after':float(attr.Get())}
        changes.append(record)
    result['arm_gain_overrides']=changes
    (out/'arm_gain_overrides.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')

def request_geometry_inertia(env):
    from pxr import Gf
    changes=[]
    for path,expected in EXPECTED_INERTIA_BODIES.items():
        prim=env.world.stage.GetPrimAtPath(path)
        if not prim.IsValid():raise RuntimeError('Missing inertia body: '+path)
        attr=prim.GetAttribute('physics:diagonalInertia')
        mass=prim.GetAttribute('physics:mass')
        before=[float(v) for v in attr.Get()]
        if not np.allclose(before,expected['diagonal_inertia_kg_m2'],rtol=1e-5,atol=1e-14):
            raise RuntimeError('Unexpected original inertia: '+path)
        if not np.isclose(float(mass.Get()),expected['mass_kg'],rtol=1e-5):raise RuntimeError('Unexpected mass: '+path)
        if not attr.Set(Gf.Vec3f(0.,0.,0.)):raise RuntimeError('Inertia override failed: '+path)
        changes.append({'path':path,'before':before,'after':[float(v) for v in attr.Get()],
                        'mass_before_and_after':float(mass.Get())})
    result['inertia_overrides']=changes
    (out/'inertia_overrides.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')

def verify_effective_inertia():
    raw=robot._robot._articulation_view._physics_view
    masses=array(raw.get_masses()).copy()
    inertia=array(raw.get_inertias()).copy()
    gains=audit_value(robot._articulation_controller.get_gains())
    record={'masses':masses.tolist(),'inertias':inertia.tolist(),'gains':gains}
    result['effective_inertia_verification']=record
    (out/'effective_inertia.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    if masses.shape!=(1,12) or inertia.shape!=(1,12,9):raise RuntimeError('Unexpected tensor shapes')
    if not np.allclose(masses[0],BASELINE_EFFECTIVE_MASSES,rtol=1e-5,atol=1e-7):raise RuntimeError('Mass changed unexpectedly')
    expected_gains=np.asarray(BASELINE_GAINS,dtype=float).copy()
    expected_gains[:,:7]*=ARM_GAIN_SCALE
    if not np.allclose(np.asarray(gains),expected_gains,rtol=1e-5,atol=1e-5):
        raise RuntimeError('Effective gains do not match scaled-arm / unchanged-finger expectation')
    record['expected_gains']=expected_gains.tolist()
    if not np.isfinite(inertia).all() or not np.all(np.linalg.eigvalsh(inertia.reshape(12,3,3))>0):
        raise RuntimeError('Effective inertia is not finite positive definite')
    if np.allclose(inertia[0],BASELINE_EFFECTIVE_INERTIAS,rtol=1e-4,atol=1e-14):
        raise RuntimeError('Effective inertia unchanged; aborting path')
    record['verified']=True
    (out/'effective_inertia.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('GEOMETRY_INERTIA_MASS_AND_FINITE_ARM_GAINS_VERIFIED',flush=True)

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
        request_geometry_inertia(env)
        request_finite_arm_gains(env)
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

try:
    reference=Path('/root/autodl-tmp/day4-l1-hem-fold-20261026-061530-144501')
    with np.load(reference/'01_grasp.npz') as data:
        start=data['ee_position'].copy();q0=data['ee_quaternion'].copy()
        start[2]+=.15
        result['path_z_offset_m']=.15
    with np.load(reference/'fold_definition.npz') as data:
        line=float(data['fold_line_y'])
    start_with_pre_reset_velocity_zero();robot=b._env.robots[0]
    verify_effective_inertia()
    contact_subscription=install_contact_reporting()
    dump_runtime_audit()
    result['runtime_source_exports']={}
    for label,obj in [('articulation_controller',robot._articulation_controller),('rmp_controller',robot._controller)]:
        try:
            source=inspect.getsource(type(obj))
            (out/(label+'_source.py')).write_text(source,encoding='utf-8')
            result['runtime_source_exports'][label]='saved'
        except Exception as exc:result['runtime_source_exports'][label]=repr(exc)
    result['usd_joint_limits_degrees']=[]
    for prim in b._env.world.stage.Traverse():
        if prim.GetTypeName()!='PhysicsRevoluteJoint':continue
        lower=prim.GetAttribute('physics:lowerLimit').Get()
        upper=prim.GetAttribute('physics:upperLimit').Get()
        if lower is not None and upper is not None:
            result['usd_joint_limits_degrees'].append({'path':str(prim.GetPath()),
                'lower':float(lower),'upper':float(upper)})
    robot.open()
    drive(start+[0,0,.15],None,'approach')
    pos,_=robot.get_cur_ee_pos()
    for i,target in enumerate(short_segments(pos,start)):
        drive(target,q0,'descend_'+str(i))
    arc=hem_arc(start,line,final_z=.18,lift_height=.12)
    result['pitch_schedule']='angle=pi*max(0,2*fraction-1); rotation about world X, POSITIVE direction'
    initial=Rotation.from_quat(q0[[1,2,3,0]])
    for i,target in enumerate(arc,1):
        fraction=i/len(arc)
        angle=np.pi*max(0,2*fraction-1)
        q=(Rotation.from_rotvec([angle,0,0])*initial).as_quat()[[3,0,1,2]]
        (drive if i<=24 else drive_ik)(target,q,'opposite_delayed_pitch_'+str(i))
    result['all_targets_reached']=True
except BaseException as exc:
    result['error']=repr(exc);traceback.print_exc()
finally:
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('CONTACT_EVENT_COUNT',result.get('contact_event_count',0),flush=True)
    print('CONTACT_CALLBACK_ERRORS',result.get('contact_callback_errors',[]),flush=True)
    print('ROBOT_ONLY_REACHABLE',result['all_targets_reached'],flush=True)
    print('RESULT_FILE',out/'result.json',flush=True)
    print('DOWNLOAD_DIR',out,flush=True)
    b.stop()
