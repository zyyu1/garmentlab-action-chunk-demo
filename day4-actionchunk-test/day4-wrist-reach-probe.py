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

out=Path('/root/autodl-tmp')/('day4-wrist-reach-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result={'probe_version':'opposite-delayed-pitch-v2',
        'scope':'Robot-only opposite delayed pitch; no attachment, no cloth manipulation validation',
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
        drive(target,q,'opposite_delayed_pitch_'+str(i))
    result['all_targets_reached']=True
except BaseException as exc:
    result['error']=repr(exc);traceback.print_exc()
finally:
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('ROBOT_ONLY_REACHABLE',result['all_targets_reached'],flush=True)
    print('RESULT_FILE',out/'result.json',flush=True)
    print('DOWNLOAD_DIR',out,flush=True)
    b.stop()
