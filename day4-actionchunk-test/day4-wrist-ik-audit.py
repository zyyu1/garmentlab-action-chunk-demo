"""Read-only IK/FK audit after scene initialization; never applies IK actions."""
import sys,json,traceback,inspect
from datetime import datetime
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0,'/root/autodl-tmp/garmentlab-action-chunk-demo')
from backends.garmentlab_backend import GarmentLabBackend
from hem_fold_geometry import hem_arc

out=Path('/root/autodl-tmp')/('day4-wrist-ik-audit-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
r={'scope':'IK/FK only; no solution applied, no collision validation, no formal Day4 success',
   'completed':False,'targets':[]}
b=GarmentLabBackend(prepared_grasp=False)
def cpu(x):return x.detach().cpu().numpy() if hasattr(x,'detach') else np.asarray(x)
try:
    ref=Path('/root/autodl-tmp/day4-l1-hem-fold-20261026-061530-144501')
    prior=json.loads(Path('/root/autodl-tmp/day4-wrist-reach-20261026-063936-107749/result.json').read_text())
    with np.load(ref/'01_grasp.npz') as d:start=d['ee_position'].copy();q0=d['ee_quaternion'].copy()
    with np.load(ref/'fold_definition.npz') as d:line=float(d['fold_line_y'])
    b.start();robot=b._env.robots[0]
    wrapper=robot._kinematic_solover;solver=wrapper.get_kinematics_solver();frame=wrapper.get_end_effector_frame()
    if frame!=robot._controller.rmp_flow_config['end_effector_frame_name']:raise RuntimeError('FK/RMP frame mismatch')
    pos,quat=robot._robot.get_world_pose();solver.set_robot_base_pose(cpu(pos),cpu(quat))
    names=list(solver.get_joint_names());dofs=list(robot._robot.dof_names);ids=[dofs.index(n) for n in names]
    r.update(frame=frame,joint_names=names,ik_signature=str(inspect.signature(solver.compute_inverse_kinematics)))
    limits={}
    for prim in b._env.world.stage.Traverse():
        if prim.GetTypeName()=='PhysicsRevoluteJoint':
            limits[prim.GetName()]=np.deg2rad([prim.GetAttribute('physics:lowerLimit').Get(),prim.GetAttribute('physics:upperLimit').Get()])
    bounds=np.asarray([limits[n] for n in names]);r['joint_limits_radians']=bounds.tolist()
    seeds=[('last_pass',np.asarray(prior['targets'][-2]['joint_positions'])[ids]),
           ('failure',np.asarray(prior['targets'][-1]['joint_positions'])[ids]),
           ('initial',cpu(robot._robot.get_joint_positions())[ids])]
    arc=hem_arc(start,line,lift_height=.12);initial=Rotation.from_quat(q0[[1,2,3,0]])
    previous=None
    for i in range(24,len(arc)):
        target=arc[i];angle=np.pi*max(0,2*(i+1)/len(arc)-1)
        orientation=(Rotation.from_rotvec([angle,0,0])*initial).as_quat()[[3,0,1,2]]
        attempts=[]
        candidates=([('previous_solution',previous)] if previous is not None else [])+seeds
        for label,seed in candidates:
            solution,success=solver.compute_inverse_kinematics(frame,target,orientation,
                warm_start=seed.copy(),position_tolerance=.002,orientation_tolerance=.02)
            q=np.asarray([],dtype=float) if solution is None else cpu(solution).reshape(-1)
            item={'seed':label,'solver_success':bool(success),'solution':q.tolist()}
            if q.shape==seed.shape and np.isfinite(q).all():
                fk,rot=solver.compute_forward_kinematics(frame,q,position_only=False)
                pe=float(np.linalg.norm(cpu(fk).reshape(3)-target))
                re=float((Rotation.from_quat(orientation[[1,2,3,0]])*Rotation.from_matrix(cpu(rot).reshape(3,3)).inv()).magnitude())
                margin=np.minimum(q-bounds[:,0],bounds[:,1]-q)
                item.update(position_error_m=pe,orientation_error_rad=re,min_limit_margin_rad=float(margin.min()),
                    max_joint_change_from_seed_rad=float(np.max(np.abs(q-seed))),
                    verified=bool(success and pe<=.002 and re<=.02 and np.all(margin>=0)))
            else:item['verified']=False
            attempts.append(item)
        valid=[x for x in attempts if x['verified']]
        chosen=min(valid,key=lambda x:x['max_joint_change_from_seed_rad']) if valid else None
        previous=np.asarray(chosen['solution']) if chosen else None
        row={'waypoint':i+1,'target_position':target.tolist(),'target_quaternion_wxyz':orientation.tolist(),
             'any_verified_solution':bool(valid),'attempts':attempts}
        r['targets'].append(row)
        print('IK_AUDIT',json.dumps({'waypoint':i+1,'any_verified_solution':bool(valid),'selected':chosen}),flush=True)
    r['completed']=True
except BaseException as exc:r['error']=repr(exc);traceback.print_exc()
finally:
    (out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
    print('IK_AUDIT_COMPLETED',r['completed'],flush=True)
    print('DOWNLOAD_DIR',out,flush=True)
    b.stop()
