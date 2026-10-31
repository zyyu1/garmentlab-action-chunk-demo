"""Minimum Day4: one hem half-fold, terminal supported-placement candidate.

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
from square_pose_backend import SquarePoseBackend
from square_pose_contract import grasp_to_ee,orientation_matrix,orientation_euler
from square_start import start_with_square as start_with_mass
from square_geometry import square_targets, material_grasp_to_ee
from hem_fold_geometry import hem_plan, hem_arc
from early_descent_geometry import early_descent
from minimum_fold_geometry import support_summary, supported_material_target, material_to_ee_target, edge_length_summary
from hem_fold_geometry import short_segments, hem_metrics

out=Path('/root/autodl-tmp')/('day4-square-grasp-hold-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result={'probe_version':'square-grasp-hold-v4-joint-hold','passed':False,'formal_day4_success':False,
        'scope':'Procedural square cloth, single-arm 4-action grasp diagnostic; no formal acceptance',
        'actions':[],'cycles':[],'errors':[],'yaw':0.,'physics_profile':'Original robot asset; no v9-v11 robot overrides; cloth mass .0001/friction .3/particle friction scale 0; room collisions isolated'}
requested_bend=100.
if requested_bend not in (100.,10.):raise ValueError('Only preregistered bend 100/10 allowed')
result['requested_bend']=requested_bend
result['physics_profile']+='; constructor bend intervention recorded separately'
b=SquarePoseBackend(garment_usd=str(Path(__file__).with_name('square_cloth_40cm.usda')),prepared_grasp=True)
postcross_trace=[];postcross_labels=[];record_postcross=False
contact_recorder=None
control_trace=None
original_step=None;capture_mass=None;state_trace=[];phase='startup';writer=None;frame_count=0;image_count=0;frame_errors=0


def json_default(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(f'Unsupported JSON type: {type(value).__name__}')

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
    (out/(label+'.json')).write_text(json.dumps({'status':c.status(),'events':c.events},indent=2,default=json_default),encoding='utf-8')
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
    if len(result['actions'])>9:raise RuntimeError('Public action budget exceeded')
    print('MULTI_GRASP_ACTION',label,json.dumps(response),flush=True)

def collision_filter_audit():
    from pxr import Usd,UsdPhysics
    stage=b._env.world.stage
    report={'groups':{},'attachment_bodies':[],
            'scope':'Read-only USD collision-group dump; contact recorder is the runtime check'}
    for path in ['/World/Collision/robot_group','/World/Collision/Garment_group','/World/Collision/Rigid_group','/World/attach_group']:
        prim=stage.GetPrimAtPath(path)
        if not prim.IsValid():
            report['groups'][path]={'exists':False};continue
        group=UsdPhysics.CollisionGroup(prim)
        api=Usd.CollectionAPI(prim,'colliders')
        includes=[str(t) for t in api.GetIncludesRel().GetTargets()]
        report['groups'][path]={'exists':True,
            'filtered_groups':[str(t) for t in group.GetFilteredGroupsRel().GetTargets()],
            'collider_includes':includes,
            'collider_excludes':[str(t) for t in api.GetExcludesRel().GetTargets()]}
    for prim in stage.Traverse():
        p=str(prim.GetPath())
        if p.startswith('/World/Attachment/') and prim.HasAPI(UsdPhysics.RigidBodyAPI):
            enabled=None
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                enabled=UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()
            report['attachment_bodies'].append({'path':p,'collision_enabled':enabled})
    (out/'collision_filter_audit.json').write_text(json.dumps(report,indent=2,default=json_default),encoding='utf-8')
    return report

try:
    if os.environ.get('GARMENTLAB_ATTACHMENT_OVERLAP')!='0.005' or os.environ.get('GARMENTLAB_DISABLED_ATTACHMENT_PROBE')!='0':
        raise RuntimeError('Expected 5mm overlap and enabled test mode')
    source=out/'source';source.mkdir()
    dependencies=['day4-square-grasp-hold.py','multi_prepared_grasp_control.py','multi_grasp_geometry.py',
                  'hem_prepared_grasp_control.py','hem_fold_geometry.py','l1_fold_geometry.py',
                  'room_collision_control.py','square_start.py','square_probe_control.py','square_control_trace.py','square_pose_backend.py','square_pose_contract.py','square_geometry.py','square_cloth_40cm.usda','minimum_fold_geometry.py','early_descent_geometry.py','single_anchor_hem_control.py','square_stable_hold.py','square_block_contact_recorder.py']
    manifest={}
    for name in dependencies:
        p=Path(__file__).with_name(name);shutil.copy2(p,source/name)
        manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (source/'manifest.json').write_text(json.dumps(manifest,indent=2,default=json_default),encoding='utf-8')
    _import_garmentlab()
    import backends.prepared_grasp_control as prepared
    from square_probe_control import SquareProbeControl as MultiPreparedGraspControl
    MultiPreparedGraspControl.output_directory=out
    from room_collision_control import install_room_collision_control
    previous=prepared.PreparedGraspControl;prepared.PreparedGraspControl=MultiPreparedGraspControl
    restore_room=None;material_module=None;original_material=None;original_cloth=None
    try:
        restore_room=install_room_collision_control(out)
        material_module=importlib.import_module('Env.Garment.Garment');original_material=material_module.ParticleMaterial
        from functools import wraps
        original_cloth=material_module.ClothPrim
        @wraps(original_cloth)
        def bend_cloth(*args,**kwargs):
            if not np.isclose(kwargs.get('bend_stiffness',-1),100.):
                raise RuntimeError('Unexpected baseline bend')
            for key,expected in [('stretch_stiffness',10000.),('shear_stiffness',100.),('spring_damping',.2)]:
                if not np.isclose(kwargs.get(key,-1),expected):raise RuntimeError('Unexpected '+key)
            kwargs['bend_stiffness']=requested_bend
            result['constructor_bend_applied']=requested_bend
            return original_cloth(*args,**kwargs)
        material_module.ClothPrim=bend_cloth
        def fixed_material(*args,**kwargs):
            if 'particle_friction_scale' in kwargs:raise RuntimeError('Unexpected material override')
            kwargs['particle_friction_scale']=0.
            return original_material(*args,**kwargs)
        material_module.ParticleMaterial=fixed_material
        capture_mass=start_with_mass(b,out,.0001)
    finally:
        if material_module is not None and original_material is not None:material_module.ParticleMaterial=original_material
        if material_module is not None and original_cloth is not None:material_module.ClothPrim=original_cloth
        if restore_room is not None:restore_room()
        prepared.PreparedGraspControl=previous
    c=b._env.control;robot=b._env.robots[0]
    def capture_springs(label):
        cloth=b._env.garment[0].garment_mesh
        prim=b._env.world.stage.GetPrimAtPath(b._env.garment[0].garment_mesh_prim_path)
        bend=float(prim.GetAttribute('physxAutoParticleCloth:springBendStiffness').Get())
        if not np.isclose(bend,requested_bend):raise RuntimeError('Bend USD readback mismatch')
        view=cloth._cloth_prim_view
        if view._physics_view is None:raise RuntimeError('Live spring physics view unavailable')
        springs=b._to_numpy(view.get_stretch_stiffnesses(clone=True))
        if not springs.size or not np.isfinite(springs).all():raise RuntimeError('Invalid runtime spring array')
        np.save(out/('runtime_spring_stiffness_'+label+'.npy'),springs)
        result.setdefault('spring_readback',{})[label]={'bend_usd':bend,'shape':list(springs.shape),
            'min':float(springs.min()),'max':float(springs.max()),
            'scope':'SDK get_stretch_stiffnesses reads runtime get_spring_stiffness; entries are not labeled by spring type'}
    capture_springs('after_start')
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
    from square_control_trace import ControlTrace
    control_trace=ControlTrace(robot,b._env.world,out,lambda:phase)
    setup_video()
    from square_block_contact_recorder import BlockContactRecorder
    contact_recorder=BlockContactRecorder(b._env.world,out,lambda:phase)
    result['diagnostic_scope']='Fixed downward Backend pose, public yaw wired, URDF fingertip midpoint proxy; approach/descend/CLOSE/OPEN only; no lift/fold'
    result['hold_control']='joint_space_position_hold_at_converged_config; RMP not called during 60-step stationary hold'
    result['collision_filter_audit']=collision_filter_audit()
    result['per_segment_step_limit']=240
    original_step=b._env.world.step
    def checked_step(*args,**kwargs):
        control_trace.state('before',b._step_count['n'])
        value=original_step(*args,**kwargs);c.assert_exclusive()
        control_trace.state('after',b._step_count['n'])
        if int(b._step_count['n'])%3==0:record_frame()
        vertices=b._garment_world_positions()
        if record_postcross:
            postcross_trace.append(vertices.copy())
            postcross_labels.append({'step':int(b._step_count['n']),'phase':phase})
        if not np.isfinite(vertices).all() or np.max(abs(vertices))>2.:raise RuntimeError('Mesh escaped diagnostic bound')
        if int(b._step_count['n'])%5==0:
            state_trace.append({'step':int(b._step_count['n']),'phase':phase,'slots':c.status(),
                                'cloth_centroid':vertices.mean(axis=0).tolist(),
                                'joint_velocity':b._to_numpy(robot._robot.get_joint_velocities()).tolist(),
                                'ee_position':np.asarray(robot.get_cur_ee_pos()[0]).tolist(),
                                'ee_quaternion_wxyz':np.asarray(robot.get_cur_ee_pos()[1]).tolist(),
                                'grasp_reference':c.active.block_target().tolist(),
                                'physics_step':int(b._env.world.current_time_step_index),
                                'subtarget':getattr(c,'probe_subtarget',None)})
        return value
    b._env.world.step=checked_step
    phase='initial_settle'
    for _ in range(120):b._env.step()
    initial,_=snapshot('00_initial')
    plan=hem_plan(initial,c.slots[2].pick_index)
    np.savez_compressed(out/'fold_definition.npz',initial_vertices=initial,**plan)
    (out/'expert_plan.json').write_text(json.dumps({k:(v.tolist() if hasattr(v,'tolist') else v) for k,v in plan.items() if k!='source_mask'},indent=2,default=json_default),encoding='utf-8')
    result['metric_threshold_status']='provisional only; no success threshold frozen'
    result['stage_metrics']={}
    initial_paths=[(s.block.block_path,s.block.attachment_path) for s in c.slots]
    slot=c.slots[2]
    with np.load(out/'cloth_constructed.npz') as mesh_source:faces=mesh_source['faceVertexIndices'].reshape(-1,3).copy()
    result['scope']='Procedural single-layer square, single Franka, development only; not Dress057 acceptance'
    result['grasp_model']='Single-point attachment proxy; no physical pinch validation'
    result['interpolation']='Linear segments <=25mm per public target, no hidden fold path'
    result['arrival_rule']='EE<10mm, held block<5mm, arm speed<0.1rad/s for six steps; max120 convergence steps'
    dt=float(b._env.world.get_physics_dt())
    if not np.isclose(dt,1/60):raise RuntimeError('Unexpected dt')
    result['physics_dt']=dt
    pick=c.vertices()[slot.pick_index].copy()
    action(pick+[0,0,.15],GripperCommand.OPEN,'approach')
    pick=c.vertices()[slot.pick_index].copy()
    grasp_target=grasp_to_ee(pick,0.)
    result['pose_contract']={'xyz_frame':'world right_gripper','yaw_rad':0.,'fixed_euler_roll_pitch':[float(np.pi),0.],
        'local_grasp_reference':slot.local_offset.tolist(),'reference_scope':'URDF named fingertip midpoint, not physical pinch calibration',
        'material_pick':pick.tolist(),'ee_target':grasp_target.tolist()}
    action(grasp_target,GripperCommand.OPEN,'descend')
    snapshot('01_before_close')
    result['descent_completed']=True
    action(grasp_target,GripperCommand.CLOSE,'close')
    snapshot('02_grasp')
    phase='held_stationary'
    from square_stable_hold import StableHold
    hold=StableHold(robot,b._env.world,slot,out)
    result['hold_target_joint_positions']=hold.begin()
    try:
        hold.run(60)
    finally:
        result['hold_summary']=hold.save()
    snapshot('03_held')
    ee,q=robot.get_cur_ee_pos()
    result['held_check']={'position_error_m':float(np.linalg.norm(np.asarray(ee)-grasp_target)),
        'arm_speed_rad_s':float(np.max(abs(b._to_numpy(robot._robot.get_joint_velocities())[:7]))),
        'orientation_reached':bool(robot.reach(grasp_target,np.array([np.pi,0.,0.]))),
        'anchor_gap_max_m':float(slot.max_single_anchor_gap_m)}
    h=result['held_check']
    held_ok=h['position_error_m']<.01 and h['arm_speed_rad_s']<.1 and h['orientation_reached'] and h['anchor_gap_max_m']<=.01
    action(np.asarray(ee),GripperCommand.OPEN,'release')
    phase='released_stationary'
    for _ in range(30):slot._tick(np.asarray(ee),orientation_euler(0.),follow=False)
    snapshot('04_released')
    if not held_ok:raise RuntimeError('Held pose/velocity gate failed; released and saved')
    if c.holding or c.attachment_enabled():raise RuntimeError('Release failed')
    result['passed']=True
    result['fold_success_accepted']=False
    print('SQUARE_GRASP_HOLD_COMPLETED_NO_FOLD',flush=True)
except BaseException as exc:
    result['errors'].append(repr(exc));traceback.print_exc()
    if b._started:
        try:snapshot('99_failure')
        except Exception as snapshot_error:result['failure_snapshot_error']=repr(snapshot_error)
finally:
    try:
        if contact_recorder is not None:result['block_contact_report']=contact_recorder.save()
        if postcross_trace:
            np.savez_compressed(out/'postcross_trace.npz',vertices=np.asarray(postcross_trace))
            (out/'postcross_trace_labels.json').write_text(json.dumps(postcross_labels,indent=2,default=json_default),encoding='utf-8')
        result['postcross_trace_frames']=len(postcross_trace)
        if writer is not None:writer.release()
        result['video_frames']=frame_count;result['stage_images']=image_count;result['frame_errors']=frame_errors
        result['public_action_count']=len(result['actions'])
        result['public_action_count_within_12']=len(result['actions'])<=12
        result['formal_12_action_budget_passed']=False
        if b._env is not None:
            try:
                result['slot_status_final']=b._env.control.status();result['slot_events']=b._env.control.events
                result['linear_motion_records']=b._env.control.motion_records
            except Exception as exc:result['final_status_error']=repr(exc)
        (out/'state_trace.json').write_text(json.dumps(state_trace,indent=2,default=json_default),encoding='utf-8')
        (out/'result.json').write_text(json.dumps(result,indent=2,default=json_default),encoding='utf-8')
        print('MINIMUM_HALF_FOLD_PIPELINE_PASSED',result['passed'],flush=True)
        print('RESULT_FILE',out/'result.json',flush=True)
        print('DOWNLOAD_DIR',out,flush=True)
    finally:
        if original_step is not None:b._env.world.step=original_step
        try:
            if control_trace is not None:control_trace.close()
        finally:b.stop()
