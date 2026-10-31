"""Official three-stage position fold pilot via public Cartesian actions.

Development only: no formal quality acceptance, slot reuse or reset acceptance.
"""
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import traceback
from datetime import datetime
import numpy as np

sys.path.insert(0,'/root/autodl-tmp/garmentlab-action-chunk-demo')
from backends.garmentlab_backend import GarmentLabBackend, _import_garmentlab
from schemas.action import ActionChunk, CartesianAction, GripperCommand
from mass_experiment import start_with_mass
from official_fold_geometry import official_plan, live_stage_waypoints
from hem_fold_geometry import short_segments, hem_metrics

out=Path('/root/autodl-tmp')/('day4-single-anchor-sleeve-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result={'probe_version':'single-anchor-first-sleeve-v1','passed':False,'formal_day4_success':False,
        'scope':'First right-sleeve grasp-model counterfactual only; single-vertex proxy; no full fold or physical pinch acceptance',
        'actions':[],'cycles':[],'errors':[],'yaw':0.,'physics_profile':'Original robot asset; no v9-v11 robot overrides; cloth mass .0001/friction .3/particle friction scale 0; room collisions isolated'}
b=GarmentLabBackend(prepared_grasp=True)
original_step=None;capture_mass=None;state_trace=[];phase='startup';writer=None;frame_count=0;image_count=0;frame_errors=0


def setup_video():
    global writer,cv2
    import cv2
    from omni.isaac.core.utils.rotations import euler_angles_to_quat
    b._env.camera.camera.set_world_pose(position=np.array([0.,-.50,2.80]),
        orientation=euler_angles_to_quat(np.array([0.,90.,90.]),degrees=True))
    writer=cv2.VideoWriter(str(out/'episode.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),20.,(640,480))
    if not writer.isOpened():raise RuntimeError('Video writer failed')

def record_frame(label=None):
    global frame_count,image_count,frame_errors
    image=b._env.camera.camera.get_rgb()
    if image is None:
        frame_errors+=1;return
    image=np.asarray(image)
    if image.ndim!=3 or image.shape[:2]!=(480,640) or image.shape[2]<3 or not np.isfinite(image).all():
        frame_errors+=1;return
    rgb=image[:,:,:3]
    if np.issubdtype(rgb.dtype,np.floating):rgb=np.clip(rgb*(255 if rgb.max()<=1 else 1),0,255)
    rgb=np.ascontiguousarray(rgb,dtype=np.uint8)
    writer.write(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR));frame_count+=1
    if label is not None:
        if not cv2.imwrite(str(out/(label+'.png')),cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)):
            raise RuntimeError('PNG save failed')
        image_count+=1

def snapshot(label):
    c=b._env.control;vertices=b._garment_world_positions();ee,q=b._env.robots[0].get_cur_ee_pos()
    data={'vertices':vertices,'ee_position':np.asarray(ee),'ee_quaternion':np.asarray(q)}
    for i,s in enumerate(c.slots):
        data['tracked_'+str(i)]=s.tracked;data['anchors_'+str(i)]=s.anchor_ids
        pos,quat=s.block.move_block_controller.get_world_poses()
        data['block_position_'+str(i)]=pos.detach().cpu().numpy()
        data['block_quaternion_'+str(i)]=quat.detach().cpu().numpy()
    np.savez_compressed(out/(label+'.npz'),**data)
    (out/(label+'.json')).write_text(json.dumps({'status':c.status(),'events':c.events},indent=2),encoding='utf-8')
    if writer is not None:record_frame(label)
    return vertices,np.asarray(ee).copy()

def action(xyz,command,label):
    global phase
    phase=label
    chunk=ActionChunk(actions=[CartesianAction(target_pose=np.r_[np.asarray(xyz),0.].astype(np.float32),gripper_command=int(command))])
    result['pending_action']={'label':label,'matrix':chunk.to_matrix().tolist()}
    response=b.execute(chunk);b.get_observation().validate();c=b._env.control;c.assert_exclusive()
    enabled=[x['enabled'] for x in c.status()]
    checks={'executed_one':response['executed_steps']==1,'not_done':response['done'] is False,
            'holding_consistent':bool(b._holding)==c.holding,
            'attachment_count':sum(enabled)==int(c.holding)}
    result['actions'].append({'label':label,'matrix':chunk.to_matrix().tolist(),'response':response,'checks':checks,'slots':c.status()})
    result.pop('pending_action',None)
    if not all(checks.values()):raise RuntimeError('Public action state mismatch: '+label)
    print('MULTI_GRASP_ACTION',label,json.dumps(response),flush=True)

try:
    if os.environ.get('GARMENTLAB_ATTACHMENT_OVERLAP')!='0.005' or os.environ.get('GARMENTLAB_DISABLED_ATTACHMENT_PROBE')!='0':
        raise RuntimeError('Expected 5mm overlap and enabled test mode')
    source=out/'source';source.mkdir()
    dependencies=['day4-single-anchor-sleeve.py','multi_prepared_grasp_control.py','multi_grasp_geometry.py',
                  'hem_prepared_grasp_control.py','hem_fold_geometry.py','l1_fold_geometry.py',
                  'room_collision_control.py','mass_experiment.py','official_fold_geometry.py','single_anchor_grasp_control.py']
    manifest={}
    for name in dependencies:
        p=Path(__file__).with_name(name);shutil.copy2(p,source/name)
        manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (source/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    _import_garmentlab()
    import backends.prepared_grasp_control as prepared
    from single_anchor_grasp_control import SingleAnchorMultiControl as MultiPreparedGraspControl
    MultiPreparedGraspControl.output_directory=out
    from room_collision_control import install_room_collision_control
    previous=prepared.PreparedGraspControl;prepared.PreparedGraspControl=MultiPreparedGraspControl
    restore_room=None;material_module=None;original_material=None
    try:
        restore_room=install_room_collision_control(out)
        material_module=importlib.import_module('Env.Garment.Garment');original_material=material_module.ParticleMaterial
        def fixed_material(*args,**kwargs):
            if 'particle_friction_scale' in kwargs:raise RuntimeError('Unexpected material override')
            kwargs['particle_friction_scale']=0.
            return original_material(*args,**kwargs)
        material_module.ParticleMaterial=fixed_material
        capture_mass=start_with_mass(b,out,.0001)
    finally:
        if material_module is not None and original_material is not None:material_module.ParticleMaterial=original_material
        if restore_room is not None:restore_room()
        prepared.PreparedGraspControl=previous
    c=b._env.control;robot=b._env.robots[0]
    robot.open()
    material=b._env.garment[0].particle_material
    readback={'friction':float(material.get_friction()),'particle_friction_scale':float(material.get_particle_friction_scale())}
    if not np.isclose(readback['friction'],.3) or readback['particle_friction_scale']!=0:raise RuntimeError('Unexpected cloth material')
    result['material_readback']=readback
    kp,kd=robot._articulation_controller.get_gains()
    result['robot_config']={'kp':b._to_numpy(kp).tolist(),'kd':b._to_numpy(kd).tolist(),
                            'solver_position_iterations_usd':int(robot._robot.get_solver_position_iteration_count()),
                            'solver_velocity_iterations_usd':int(robot._robot.get_solver_velocity_iteration_count())}
    runtime=out/'runtime_source';runtime.mkdir()
    for label,obj in [('backend',b),('environment',b._env),('robot',robot),('original_control',c.original)]:
        p=Path(inspect.getfile(type(obj)));raw=p.read_bytes();(runtime/(label+'.py')).write_bytes(raw)
        result.setdefault('runtime_source_hashes',{})[label]={'path':str(p),'sha256':hashlib.sha256(raw).hexdigest()}
    result['slots_precreated']=[{'label':s.label,'block':s.block.block_path,'constraint':s.block.attachment_path,
                                 'pick_index':s.pick_index,'anchor_ids':s.anchor_ids.tolist()} for s in c.slots]
    setup_video()
    original_step=b._env.world.step
    def checked_step(*args,**kwargs):
        value=original_step(*args,**kwargs);c.assert_exclusive()
        if int(b._step_count['n'])%3==0:record_frame()
        vertices=b._garment_world_positions()
        if not np.isfinite(vertices).all() or np.max(abs(vertices))>2.:raise RuntimeError('Mesh escaped diagnostic bound')
        if int(b._step_count['n'])%5==0:
            state_trace.append({'step':int(b._step_count['n']),'phase':phase,'slots':c.status(),
                                'cloth_centroid':vertices.mean(axis=0).tolist(),
                                'joint_velocity':b._to_numpy(robot._robot.get_joint_velocities()).tolist()})
        return value
    b._env.world.step=checked_step
    phase='initial_settle'
    for _ in range(120):b._env.step()
    initial,_=snapshot('00_initial')
    plan=official_plan(initial,[s.pick_index for s in c.slots])
    np.savez_compressed(out/'fold_definition.npz',initial_vertices=initial,source_mask=plan['source_mask'],fold_line_y=plan['fold_line_y'])
    (out/'expert_plan.json').write_text(json.dumps({k:v for k,v in plan.items() if k!='source_mask'},indent=2),encoding='utf-8')
    result['metric_threshold_status']='provisional only; no success threshold frozen'
    result['stage_metrics']={}
    initial_paths=[(s.block.block_path,s.block.attachment_path) for s in c.slots]
    for number,(slot,stage) in enumerate(zip(c.slots[:1],plan['stages'][:1]),1):
        label=str(number)+'_'+slot.label
        pick=c.vertices()[slot.pick_index].copy()
        action([pick[0],pick[1],.15],GripperCommand.HOLD,label+'_approach')
        for z in (.12,.08,.05,.03,.02):
            pick=c.vertices()[slot.pick_index].copy()
            action([pick[0],pick[1],z],GripperCommand.HOLD,label+'_descend_'+str(z))
        pick=c.vertices()[slot.pick_index].copy()
        waypoints=live_stage_waypoints(stage,pick)
        snapshot(label+'_before_close')
        action([pick[0],pick[1],.02],GripperCommand.CLOSE,label+'_close')
        if c.active is not slot:raise RuntimeError('Unexpected slot selected')
        snapshot(label+'_grasp')
        for move_number,target in enumerate(waypoints,1):
            ee,_=robot.get_cur_ee_pos()
            # Diagnostic public waypoints remain explicit; do not hide action-budget excess.
            for k,point in enumerate(short_segments(ee,target)):
                action(point,GripperCommand.HOLD,label+'_move_'+str(move_number)+'_'+str(k))
            snapshot(label+'_move_'+str(move_number))
        ee,_=robot.get_cur_ee_pos()
        action(ee,GripperCommand.OPEN,label+'_release')
        released_block=slot.block.get_position().numpy().copy()
        phase=label+'_settle'
        for _ in range(120):b._env.step()
        released,ee=snapshot(label+'_released')
        drift=float(np.linalg.norm(slot.block.get_position().numpy()-released_block))
        checks={'all_disabled':not c.attachment_enabled(),'not_holding':not c.holding and not b._holding,
                'paths_preserved':initial_paths==[(s.block.block_path,s.block.attachment_path) for s in c.slots],
                'block_stopped':drift<.001,'selected_region_used':slot.used}
        result['cycles'].append({'slot':slot.label,'reference_stage':stage,'actual_waypoints':waypoints.tolist(),
                                'release_block_drift_m':drift,'checks':checks,
                                'alignment':slot.alignment_record,'activation':slot.activation_record})
        result['stage_metrics'][label]=hem_metrics(initial,released,plan)
        if not all(checks.values()):raise RuntimeError('Stage lifecycle check failed')
        action([ee[0],ee[1],.18],GripperCommand.HOLD,label+'_retreat')
        print('OFFICIAL_POSITION_STAGE_COMPLETED',slot.label,flush=True)
    phase='final_settle'
    for _ in range(180):b._env.step()
    final,_=snapshot('04_final')
    result['hem_proxy_diagnostic_only']=hem_metrics(initial,final,plan)
    result['nominal_fixed_half_centroid_drift_m']=(final[~plan['source_mask']]-initial[~plan['source_mask']]).mean(axis=0).tolist()
    capture_mass('after_single_sleeve_release')
    if [x['slot'] for x in result['cycles']]!=['right_sleeve'] or [s.used for s in c.slots]!=[True,False,False]:
        raise RuntimeError('Expected first sleeve only')
    result['public_action_count']=len(result['actions'])
    result['public_action_count_within_12']=len(result['actions'])<=12
    result['formal_12_action_budget_passed']=False
    result['fold_success_accepted']=False
    result['single_anchor_max_gap_m']={s.label:s.max_single_anchor_gap_m for s in c.slots}
    result['grasp_model']='One manual vertex per precreated slot; auto generation removed before reset; no pitch'
    result['pipeline_completed']=True
    if frame_count<20 or image_count<7:raise RuntimeError('Insufficient saved visual evidence')
    result['passed']=True
    print('SINGLE_ANCHOR_SLEEVE_PIPELINE_COMPLETED',flush=True)
    print('FOLD_PROXY_METRICS',json.dumps(result['hem_proxy_diagnostic_only']),flush=True)
except BaseException as exc:
    result['errors'].append(repr(exc));traceback.print_exc()
    if b._started:
        try:snapshot('99_failure')
        except Exception as snapshot_error:result['failure_snapshot_error']=repr(snapshot_error)
finally:
    if writer is not None:writer.release()
    result['video_frames']=frame_count;result['stage_images']=image_count;result['frame_errors']=frame_errors
    result['public_action_count']=len(result['actions'])
    result['public_action_count_within_12']=len(result['actions'])<=12
    result['formal_12_action_budget_passed']=False
    if b._env is not None:
        try:
            result['slot_status_final']=b._env.control.status();result['slot_events']=b._env.control.events
        except Exception as exc:result['final_status_error']=repr(exc)
    (out/'state_trace.json').write_text(json.dumps(state_trace,indent=2),encoding='utf-8')
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('SINGLE_ANCHOR_SLEEVE_PASSED',result['passed'],flush=True)
    print('RESULT_FILE',out/'result.json',flush=True)
    print('DOWNLOAD_DIR',out,flush=True)
    if original_step is not None:b._env.world.step=original_step
    b.stop()
