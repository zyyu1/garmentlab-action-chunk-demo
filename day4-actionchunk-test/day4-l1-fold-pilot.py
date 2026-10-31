"""Day4 delivery path: one nominal-flat, single-grasp fold candidate with video.

Not a randomized L1 acceptance batch; does not claim reusable reset/regrasp.
"""
import json
import hashlib
import os
from pathlib import Path
import shutil
import sys
import traceback
from datetime import datetime
import numpy as np

sys.path.insert(0,'/root/autodl-tmp/garmentlab-action-chunk-demo')
from backends.garmentlab_backend import GarmentLabBackend
from schemas.action import ActionChunk, CartesianAction, GripperCommand
from mass_experiment import start_with_mass
from l1_fold_geometry import fold_plan, fold_metrics

out=Path('/root/autodl-tmp')/('day4-l1-fold-pilot-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result={'pipeline_completed':False,'formal_day4_success':False,'scope':'Nominal flat pilot; no seeded difficulty or independent reset validation',
        'actions':[], 'metric_threshold_status':'provisional; must freeze before formal acceptance/collection'}
b=GarmentLabBackend(prepared_grasp=True)
writer=None; original_step=None; frame_count=0; image_count=0; frame_errors=0
print('OUTPUT_DIR',out,flush=True)


def action(xyz,command,label):
    xyz=np.asarray(xyz,dtype=float)
    chunk=ActionChunk(actions=[CartesianAction(target_pose=np.r_[xyz,0].astype(np.float32),gripper_command=int(command))])
    response=b.execute(chunk)
    b.get_observation().validate()
    c=b._env.control
    held=int(command)!=int(GripperCommand.OPEN) and (int(command)==int(GripperCommand.CLOSE) or bool(b._holding))
    checks={'executed':response['executed_steps']==1,'not_done':response['done'] is False,
            'holding_consistent':bool(b._holding)==bool(c.holding)==held,
            'attachment_consistent':bool(c.enabled.Get())==held}
    result['actions'].append({'label':label,'matrix':chunk.to_matrix().tolist(),'response':response,'checks':checks})
    print('ACTION',label,response,flush=True)
    if not all(checks.values()):raise RuntimeError('Action state check failed: '+label)


def record_frame():
    global frame_count,frame_errors
    image=b._env.camera.camera.get_rgb()
    if image is None:
        frame_errors+=1;return None
    image=np.asarray(image)
    if image.ndim!=3 or image.shape[:2]!=(480,640) or image.shape[2]<3:
        frame_errors+=1;return None
    rgb=image[:,:,:3]
    if np.issubdtype(rgb.dtype,np.floating):
        rgb=np.clip(rgb*255 if rgb.max()<=1 else rgb,0,255)
    rgb=np.ascontiguousarray(rgb,dtype=np.uint8)
    writer.write(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR));frame_count+=1
    return rgb


def snapshot(label):
    global image_count
    vertices=b._garment_world_positions()
    ee,q=b._env.robots[0].get_cur_ee_pos()
    np.savez_compressed(out/(label+'.npz'),vertices=vertices,ee_position=ee,ee_quaternion=q,
                        tracked_indices=b._env.control.tracked)
    rgb=record_frame()
    if rgb is not None:
        cv2.imwrite(str(out/(label+'.png')),cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR));image_count+=1
    print('SNAPSHOT',label,flush=True)
    return vertices,np.asarray(ee).copy()


try:
    if os.environ.get('GARMENTLAB_ATTACHMENT_OVERLAP')!='0.005' or os.environ.get('GARMENTLAB_DISABLED_ATTACHMENT_PROBE')!='0':
        raise RuntimeError('Expected 5 mm overlap and disabled probe=0')
    source=out/'source';source.mkdir()
    files=['day4-l1-fold-pilot.py','l1_fold_geometry.py','mass_experiment.py','anchor_observer.py','anchor_alignment_observer.py']
    manifest={}
    for name in files:
        path=Path(__file__).resolve().with_name(name)
        shutil.copy2(path,source/name)
        manifest[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (source/'manifest.json').write_text(json.dumps(manifest,indent=2))
    capture_mass=start_with_mass(b,out,.0001)
    from anchor_alignment_observer import PairedAlignmentObserver
    observer=PairedAlignmentObserver(b,out,'aligned');observer.capture('after_start');observer.install()
    import cv2
    from omni.isaac.core.utils.rotations import euler_angles_to_quat
    b._env.camera.camera.set_world_pose(position=np.array([0.,-.50,1.60]),
        orientation=euler_angles_to_quat(np.array([0.,90.,90.]),degrees=True))
    writer=cv2.VideoWriter(str(out/'episode.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),20.,(640,480))
    if not writer.isOpened():raise RuntimeError('Video encoder did not open')
    original_step=b._env.world.step
    def recorded_step(*args,**kwargs):
        value=original_step(*args,**kwargs)
        if int(b._step_count['n'])%3==0:record_frame()
        return value
    b._env.world.step=recorded_step
    robot=b._env.robots[0];control=b._env.control
    robot.open()
    for _ in range(120):b._env.step()
    initial,_=snapshot('00_initial')
    plan=fold_plan(initial,control.tracked)
    np.savez(out/'fold_definition.npz',**plan)
    result['fold_line_x']=plan['fold_line_x']
    anchor=initial[int(control.tracked[0])].copy()
    action(anchor+[0,0,.15],GripperCommand.HOLD,'approach')
    anchor=b._garment_world_positions()[int(control.tracked[0])].copy()
    for z in (.12,.08,.05,.03,.02):action([anchor[0],anchor[1],z],GripperCommand.HOLD,'descend_'+str(z))
    distance=float(np.linalg.norm(b._garment_world_positions()[control.tracked]-control.block_target(),axis=1).min())
    if distance>=.02:raise RuntimeError('Prepared region too far from grasp')
    action([anchor[0],anchor[1],.02],GripperCommand.CLOSE,'grasp')
    for _ in range(10):b._env.step()
    grasp,ee=snapshot('01_grasp')
    lift_z=float(ee[2]+.18)
    action([ee[0],ee[1],lift_z],GripperCommand.HOLD,'lift')
    lifted,ee=snapshot('02_lift')
    rise=float(lifted[control.tracked,2].mean()-grasp[control.tracked,2].mean())
    if rise<.05:raise RuntimeError('Cloth did not lift')
    target=plan['target_reference']
    action([plan['fold_line_x'],target[1],lift_z],GripperCommand.HOLD,'cross_fold_line')
    snapshot('03_cross_line')
    action([target[0],target[1],lift_z],GripperCommand.HOLD,'transfer_to_mirror')
    snapshot('04_transfer')
    for z in (.10,.06,.03):action([target[0],target[1],z],GripperCommand.HOLD,'place_'+str(z))
    _,ee=snapshot('05_place')
    action(ee,GripperCommand.OPEN,'release')
    action([ee[0],ee[1],.25],GripperCommand.HOLD,'retreat')
    for _ in range(180):b._env.step()
    final,_=snapshot('06_final')
    result['mass_audit']=capture_mass('after_release')
    result['alignment_metrics']=observer.metrics
    result['fold_metrics']=fold_metrics(initial,final,plan)
    result['initial_fold_metrics']=fold_metrics(initial,initial,plan)
    result['cloth_lift_m']=rise
    m=result['fold_metrics']
    criteria={'alignment_mean_m_max':.04,'occupancy_iou_min':.50,'crossed_fraction_min':.80,'z_p95_m_max':.06}
    result['provisional_criteria']=criteria
    result['provisional_checks']={'alignment':m['symmetric_xy_alignment_mean_m']<=.04,
          'occupancy':m['particle_occupancy_iou']>=.50,'crossed':m['moving_half_crossed_fraction']>=.80,
          'height':m['cloth_z_p95_m']<=.06}
    result['provisional_fold_success']=all(result['provisional_checks'].values())
    if control.holding or b._holding or bool(control.enabled.Get()):raise RuntimeError('Release state not cleared')
    if frame_count<10 or image_count<7:raise RuntimeError('Insufficient video or stage images')
    result['pipeline_completed']=True
except BaseException as exc:
    result['error']=repr(exc);traceback.print_exc()
finally:
    if original_step is not None:b._env.world.step=original_step
    if writer is not None:writer.release()
    result['video']={'frames':frame_count,'stage_images':image_count,'unavailable_frame_reads':frame_errors,'fps':20,
                     'note':'Periodic frames plus stage snapshots; not exact real-time playback.'}
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if result['pipeline_completed']:print('L1_FOLD_PILOT_PIPELINE_COMPLETED',flush=True)
    print('RESULT_FILE',out/'result.json',flush=True)
    print('DOWNLOAD_DIR',out,flush=True)
    b.stop()
