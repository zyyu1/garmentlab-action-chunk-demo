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
from hem_fold_geometry import hem_plan, hem_metrics, short_segments, hem_arc

out=Path('/root/autodl-tmp')/('day4-l1-hem-fold-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result={'expert_version':'hem-v12-pitch-arc-probe','pipeline_completed':False,'formal_day4_success':False,'scope':'Pilot wrist pitch override outside XYZ+yaw action schema; diagnostic only, not policy demonstration',
        'actions':[], 'metric_threshold_status':'provisional; must freeze before formal acceptance/collection'}
b=GarmentLabBackend(prepared_grasp=True)
writer=None; original_step=None; frame_count=0; image_count=0; frame_errors=0
release_trace=[]; release_monitor=False; motion_phase='before_release'
print('OUTPUT_DIR',out,flush=True)


def action(xyz,command,label):
    xyz=np.asarray(xyz,dtype=float)
    chunk=ActionChunk(actions=[CartesianAction(target_pose=np.r_[xyz,0].astype(np.float32),gripper_command=int(command))])
    result['pending_action']={'label':label,'matrix':chunk.to_matrix().tolist(),
        'pilot_fold_angle_rad':b._env.control.fold_angle}
    response=b.execute(chunk)
    b.get_observation().validate()
    c=b._env.control
    held=int(command)!=int(GripperCommand.OPEN) and (int(command)==int(GripperCommand.CLOSE) or bool(b._holding))
    checks={'executed':response['executed_steps']==1,'not_done':response['done'] is False,
            'holding_consistent':bool(b._holding)==bool(c.holding)==held,
            'attachment_consistent':c.attachment_enabled()==held}
    result['actions'].append({'label':label,'matrix':chunk.to_matrix().tolist(),'response':response,'checks':checks,
        'pilot_fold_angle_rad':c.fold_angle})
    result.pop('pending_action',None)
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
    block_pos,block_q=b._env.control.block.move_block_controller.get_world_poses()
    np.savez_compressed(out/(label+'.npz'),vertices=vertices,ee_position=ee,ee_quaternion=q,
                        block_position=block_pos.detach().cpu().numpy(),
                        block_quaternion=block_q.detach().cpu().numpy(),
                        block_rotation_error_rad=b._env.control.block_rotation_error(),
                        tracked_indices=b._env.control.tracked)
    if 'plan' in globals():
        mask=plan['source_mask']
        drift=(vertices[~mask]-initial[~mask]).mean(axis=0)
        result.setdefault('stage_geometry',{})[label]={
            'stationary_half_centroid_displacement_m':drift.tolist(),
            'moving_half_crossed_fraction':float((vertices[mask,1]>plan['fold_line_y']).mean())}
        print('STAGE_GEOMETRY',label,result['stage_geometry'][label],flush=True)
    rgb=record_frame()
    if rgb is not None:
        cv2.imwrite(str(out/(label+'.png')),cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR));image_count+=1
    print('SNAPSHOT',label,flush=True)
    return vertices,np.asarray(ee).copy()


try:
    if os.environ.get('GARMENTLAB_ATTACHMENT_OVERLAP')!='0.005' or os.environ.get('GARMENTLAB_DISABLED_ATTACHMENT_PROBE')!='0':
        raise RuntimeError('Expected 5 mm overlap and disabled probe=0')
    source=out/'source';source.mkdir()
    files=['day4-l1-hem-fold.py','room_collision_control.py','hem_fold_geometry.py','hem_prepared_grasp_control.py','hem_anchor_alignment_observer.py','l1_fold_geometry.py','mass_experiment.py','anchor_observer.py']
    manifest={}
    for name in files:
        path=Path(__file__).resolve().with_name(name)
        shutil.copy2(path,source/name)
        manifest[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (source/'manifest.json').write_text(json.dumps(manifest,indent=2))
    # Patch only this process's class binding, before control construction/reset.
    from backends.garmentlab_backend import _import_garmentlab
    _import_garmentlab()
    import backends.prepared_grasp_control as prepared_module
    from hem_prepared_grasp_control import HemPreparedGraspControl
    previous_control_class=prepared_module.PreparedGraspControl
    prepared_module.PreparedGraspControl=HemPreparedGraspControl
    from room_collision_control import install_room_collision_control
    restore_room=install_room_collision_control(out)
    import importlib
    garment_module=importlib.import_module('Env.Garment.Garment')
    original_material=garment_module.ParticleMaterial
    def fixed_material(*args,**kwargs):
        if 'particle_friction_scale' in kwargs:
            raise RuntimeError('Unexpected pre-existing particle friction scale argument')
        kwargs['particle_friction_scale']=0.0
        return original_material(*args,**kwargs)
    garment_module.ParticleMaterial=fixed_material
    try:
        capture_mass=start_with_mass(b,out,.0001)
    finally:
        garment_module.ParticleMaterial=original_material
        restore_room()
        prepared_module.PreparedGraspControl=previous_control_class
    from hem_anchor_alignment_observer import PairedAlignmentObserver
    observer=PairedAlignmentObserver(b,out,'aligned');observer.capture('after_start');observer.install()
    import cv2
    from omni.isaac.core.utils.rotations import euler_angles_to_quat
    b._env.camera.camera.set_world_pose(position=np.array([0.,-.50,2.80]),
        orientation=euler_angles_to_quat(np.array([0.,90.,90.]),degrees=True))
    writer=cv2.VideoWriter(str(out/'episode.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),20.,(640,480))
    if not writer.isOpened():raise RuntimeError('Video encoder did not open')
    original_step=b._env.world.step
    def recorded_step(*args,**kwargs):
        value=original_step(*args,**kwargs)
        if int(b._step_count['n'])%3==0:record_frame()
        if release_monitor:
            v=b._garment_world_positions()
            ee_now,_=b._env.robots[0].get_cur_ee_pos()
            release_trace.append({'step':int(b._step_count['n']),'phase':motion_phase,
                'centroid':v.mean(axis=0).tolist(),'min':v.min(axis=0).tolist(),
                'max':v.max(axis=0).tolist(),'ee':np.asarray(ee_now).tolist(),
                'block':b._env.control.block.get_position().numpy().tolist(),
                'attachment_enabled':b._env.control.attachment_enabled()})
            # Diagnostic stop bound, not a folding acceptance threshold.
            if not np.isfinite(v).all() or np.max(np.abs(v))>2.0:
                raise RuntimeError('Cloth escaped 2 m diagnostic bound during '+motion_phase)
        return value
    b._env.world.step=recorded_step
    robot=b._env.robots[0];control=b._env.control
    robot.open()
    for _ in range(120):b._env.step()
    initial,_=snapshot('00_initial')
    plan=hem_plan(initial,control.pick_index)
    np.savez(out/'fold_definition.npz',**plan)
    result['fold_line_y']=plan['fold_line_y'];result['pick_index']=control.pick_index
    anchor=initial[control.pick_index].copy()
    action(anchor+[0,0,.15],GripperCommand.HOLD,'approach')
    anchor=b._garment_world_positions()[control.pick_index].copy()
    for z in (.12,.08,.05,.03,.02):action([anchor[0],anchor[1],z],GripperCommand.HOLD,'descend_'+str(z))
    distance=float(np.linalg.norm(b._garment_world_positions()[control.tracked]-control.block_target(),axis=1).min())
    if distance>=.02:raise RuntimeError('Prepared region too far from grasp')
    action([anchor[0],anchor[1],.02],GripperCommand.CLOSE,'grasp')
    for _ in range(10):b._env.step()
    grasp,ee=snapshot('01_grasp')
    def move_short(target,label):
        start,_=robot.get_cur_ee_pos()
        for i,waypoint in enumerate(short_segments(start,target)):
            action(waypoint,GripperCommand.HOLD,label+'_'+str(i))
    arc=hem_arc(ee,plan['fold_line_y'],lift_height=.12)
    result['arc_waypoints']=arc.tolist()
    result['trajectory']='Low elliptical arc, 0.12 m lift component; nominal path, not exact material isometry'
    rise=None
    control.set_fold_angle(0.0)
    for i,waypoint in enumerate(arc,1):
        control.set_fold_angle(np.pi*i/len(arc))
        action(waypoint,GripperCommand.HOLD,'fold_arc_'+str(i))
        if i==len(arc)//3:
            lifted,_=snapshot('02_lift')
            rise=float(lifted[control.tracked,2].mean()-grasp[control.tracked,2].mean())
            if rise<.05:raise RuntimeError('Cloth did not lift')
        if i==len(arc)//2:snapshot('03_cross_line')
        if i==5*len(arc)//6:snapshot('04_transfer')
    # Keep the measured place position briefly before opening; record actual settling.
    hold_ee,_=robot.get_cur_ee_pos()
    for _ in range(60):control._tick(np.asarray(hold_ee),None,follow=True)
    control.block.set_velocities(np.zeros(6))
    _,ee=snapshot('05_place')
    material=b._env.garment[0].particle_material
    friction=float(material.get_friction())
    scale=float(material.get_particle_friction_scale())
    result['fixed_material_readback']={'friction':friction,'particle_friction_scale':scale,
        'applied_at':'material construction before first reset','changed_at_release':False}
    if not np.isfinite(friction) or abs(friction-.3)>1e-5 or not np.isfinite(scale) or scale!=0.0:
        raise RuntimeError('Fixed material configuration readback failed')
    release_monitor=True;motion_phase='opening'
    action(ee,GripperCommand.OPEN,'release')
    released,ee=snapshot('05b_released')
    result['release_fold_metrics']=hem_metrics(initial,released,plan)
    motion_phase='released_stationary'
    for _ in range(60):control._tick(ee,None,follow=False)
    snapshot('05b_stationary')
    # Avoid continuing the failed vertical path near y=-0.19 above z=0.18.
    # This alternative path still needs physical validation; keep reach tolerances.
    motion_phase='retreat_clear'
    move_short([ee[0],ee[1],.10],'retreat_clear')
    motion_phase='retreat_outward'
    move_short([ee[0],plan['fold_line_y'],.18],'retreat_outward')
    motion_phase='retreat_raise'
    move_short([ee[0],plan['fold_line_y'],.25],'retreat_raise')
    snapshot('05c_retreated')
    motion_phase='final_settle'
    for _ in range(180):b._env.step()
    final,_=snapshot('06_final')
    result['mass_audit']=capture_mass('after_release')
    result['alignment_metrics']=observer.metrics
    result['fold_metrics']=hem_metrics(initial,final,plan)
    result['initial_fold_metrics']=hem_metrics(initial,initial,plan)
    result['cloth_lift_m']=rise
    m=result['fold_metrics']
    criteria={'alignment_mean_m_max':.04,'occupancy_iou_min':.50,'crossed_fraction_min':.80,'z_p95_m_max':.06}
    result['provisional_criteria']=criteria
    result['provisional_checks']={'alignment':m['symmetric_xy_alignment_mean_m']<=.04,
          'occupancy':m['particle_occupancy_iou']>=.50,'crossed':m['moving_half_crossed_fraction']>=.80,
          'height':m['cloth_z_p95_m']<=.06}
    result['provisional_fold_success']=all(result['provisional_checks'].values())
    if control.holding or b._holding or control.attachment_enabled():raise RuntimeError('Release state not cleared')
    if frame_count<10 or image_count<7:raise RuntimeError('Insufficient video or stage images')
    result['pipeline_completed']=True
except BaseException as exc:
    result['error']=repr(exc);traceback.print_exc()
    if original_step is not None:
        try:
            failed,failed_ee=snapshot('99_failure')
            result['failure_ee_position']=failed_ee.tolist()
            if 'plan' in globals():result['failure_fold_metrics']=hem_metrics(initial,failed,plan)
        except Exception as capture_exc:
            result['failure_capture_error']=repr(capture_exc)
finally:
    if original_step is not None:b._env.world.step=original_step
    if writer is not None:writer.release()
    (out/'release_trace.json').write_text(json.dumps(release_trace,indent=2),encoding='utf-8')
    if len(release_trace)>61:
        centers=np.asarray([row['centroid'] for row in release_trace])
        speeds=np.linalg.norm(np.diff(centers,axis=0),axis=1)/float(b._env.world.get_physics_dt())
        result['release_motion_summary']={'last_60_centroid_speed_mean_m_s':float(speeds[-60:].mean()),
            'last_60_centroid_speed_max_m_s':float(speeds[-60:].max()),
            'last_60_centroid_range_m':np.ptp(centers[-60:],axis=0).tolist(),
            'note':'Centroid stability is not full particle equilibrium or fold success'}
        print('RELEASE_MOTION_SUMMARY',json.dumps(result['release_motion_summary']),flush=True)
    result['video']={'frames':frame_count,'stage_images':image_count,'unavailable_frame_reads':frame_errors,'fps':20,
                     'note':'Periodic frames plus stage snapshots; not exact real-time playback.'}
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if result['pipeline_completed']:print('L1_FOLD_PILOT_PIPELINE_COMPLETED',flush=True)
    print('RESULT_FILE',out/'result.json',flush=True)
    print('DOWNLOAD_DIR',out,flush=True)
    b.stop()
