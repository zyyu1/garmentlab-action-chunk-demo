"""Robot-only delayed-pitch feasibility probe. No grasp or fold acceptance."""
import json
import sys
import traceback
from pathlib import Path
from datetime import datetime
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0,'/root/autodl-tmp/garmentlab-action-chunk-demo')
from backends.garmentlab_backend import GarmentLabBackend
from hem_fold_geometry import hem_arc, short_segments

out=Path('/root/autodl-tmp')/('day4-wrist-ik-execution-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result={'probe_version':'ik-tail-execution-v1',
        'scope':'Robot-only IK tail actuator execution; no attachment; no collision certification or cloth validation',
        'all_targets_reached':False,'formal_day4_success':False,'targets':[]}
b=GarmentLabBackend(prepared_grasp=False)

def array(x):
    return x.detach().cpu().numpy() if hasattr(x,'detach') else np.asarray(x)

def drive(target, quaternion, label):
    target=np.asarray(target,dtype=float)
    consecutive=0
    for step in range(240):
        robot.move(target,quaternion)
        b._env.world.step()
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


def drive_ik(target, quaternion, label):
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
    result['targets'].append(row)
    if not (ok and pe<=.002 and re<=.02 and np.all(goal>=bounds[:,0]) and np.all(goal<=bounds[:,1]) and delta<=.35):
        raise RuntimeError('IK validation or continuity bound failed: '+label)
    count=max(1,int(np.ceil(delta/.005)))
    peak_error=0.0
    # Actuator targets only: never teleport joints or reset velocities.
    for k in range(1,count+1):
        command=seed+(goal-seed)*k/count
        full[ids]=command
        robot._articulation_controller.apply_action(ArticulationAction(joint_positions=full.copy()))
        b._env.world.step()
        actual=array(robot._robot.get_joint_positions())[ids]
        error=float(np.max(np.abs(actual-command)))
        peak_error=max(peak_error,error)
        if not np.isfinite(actual).all() or error>.15:
            row.update(interpolation_step=k,tracking_error_rad=error)
            raise RuntimeError('Joint tracking diverged: '+label)
    full[ids]=goal;consecutive=0
    for step in range(240):
        robot._articulation_controller.apply_action(ArticulationAction(joint_positions=full.copy()))
        b._env.world.step()
        position,actual_q=robot.get_cur_ee_pos()
        pe=float(np.linalg.norm(np.asarray(position)-target))
        re=float((Rotation.from_quat(quaternion[[1,2,3,0]])*Rotation.from_quat(np.asarray(actual_q)[[1,2,3,0]]).inv()).magnitude())
        je=float(np.max(np.abs(array(robot._robot.get_joint_positions())[ids]-goal)))
        reached=pe<.01 and re<.1 and je<.02
        consecutive=consecutive+1 if reached else 0
        if consecutive>=6:break
    row.update(position_error_m=pe,rotation_error_rad=re,joint_error_rad=je,
        peak_interpolation_tracking_error_rad=peak_error,interpolation_steps=count,
        settling_steps=step+1,joint_positions=array(robot._robot.get_joint_positions()).tolist(),reached=consecutive>=6)
    print('IK_EXECUTION',json.dumps(row),flush=True)
    if not row['reached']:raise RuntimeError('IK execution tracking failed: '+label)

try:
    reference=Path('/root/autodl-tmp/day4-l1-hem-fold-20261026-061530-144501')
    with np.load(reference/'01_grasp.npz') as data:
        start=data['ee_position'].copy();q0=data['ee_quaternion'].copy()
    with np.load(reference/'fold_definition.npz') as data:
        line=float(data['fold_line_y'])
    b.start();robot=b._env.robots[0]
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
    arc=hem_arc(start,line,lift_height=.12)
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
    print('ROBOT_ONLY_REACHABLE',result['all_targets_reached'],flush=True)
    print('RESULT_FILE',out/'result.json',flush=True)
    print('DOWNLOAD_DIR',out,flush=True)
    b.stop()
