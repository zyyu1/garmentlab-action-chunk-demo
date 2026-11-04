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
from datetime import datetime, timezone
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

seed=int(os.environ.get('SQUARE_INITIAL_SEED','4100'))
plan_file=Path(__file__).with_name('square-initial-plan.json')
initial_plan=json.loads(plan_file.read_text())
rows=[r for r in initial_plan['episodes'] if r['seed']==seed and r['level']=='flat']
if len(rows)!=1:raise ValueError('Only preregistered L1 seeds 4100..4109 supported')
case=rows[0]
if case['lift_drop_cycles']:raise ValueError('Lift/drop generation not validated')
out=Path('/root/autodl-tmp')/('day4-square-initial-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result={'probe_version':'square-initial-v1','passed':False,'formal_day4_success':False,
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

try:
    if os.environ.get('GARMENTLAB_ATTACHMENT_OVERLAP')!='0.005' or os.environ.get('GARMENTLAB_DISABLED_ATTACHMENT_PROBE')!='0':
        raise RuntimeError('Expected 5mm overlap and enabled test mode')
    source=out/'source';source.mkdir()
    dependencies=['day4-square-initial.py','square-initial-plan.json','square-difficulty.yaml','multi_prepared_grasp_control.py','multi_grasp_geometry.py',
                  'hem_prepared_grasp_control.py','hem_fold_geometry.py','l1_fold_geometry.py',
                  'room_collision_control.py','square_start.py','square_probe_control.py','square_contact_recorder.py','square_control_trace.py','square_pose_backend.py','square_pose_contract.py','square_geometry.py','square_cloth_40cm.usda','minimum_fold_geometry.py','early_descent_geometry.py','single_anchor_hem_control.py']
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
    material_prim=str(material.prim_path)
    system_prim=str(b._env.garment[0].particle_system.prim_path)
    if material_prim!='/World/Garment/particleMaterial':
        raise RuntimeError('Unexpected material binding: '+material_prim)
    if not system_prim:
        raise RuntimeError('Missing particle system path')
    result['protocol']={
        'version':'stage4-initial-v2-task-scoped',
        'task':'A_l1_overfold',
        'level':case['level'],
        'seed':seed,
        'particle_friction_scale_expected':0.0,
        'particle_friction_scale_readback':float(readback['particle_friction_scale']),
        'material_binding':{'particle_material':material_prim,'particle_system':system_prim},
        'generator':{'script':'day4-square-initial.py',
                     'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     'files_manifest':'square-initial-files.json',
                     'files_manifest_sha256':hashlib.sha256(Path(__file__).with_name('square-initial-files.json').read_bytes()).hexdigest()},
        'generated_utc':datetime.now(timezone.utc).isoformat()}
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
    result['initial_case']=case
    result['scope']='L1 initial-state generation only; no robot grasp, fold, or reset reliability claim'
    if c.holding or c.attachment_enabled():raise RuntimeError('Initial generation requires disabled attachments')
    before=b._garment_world_positions().copy()
    center=before.mean(axis=0);yaw=case['yaw_rad'];co,si=np.cos(yaw),np.sin(yaw)
    rotation=np.array([[co,-si,0],[si,co,0],[0,0,1]])
    moved=(before-center)@rotation.T+center+np.r_[case['translation_xy_m'],0.]
    b._set_garment_world_positions(moved.astype(np.float32));b._clear_garment_velocities()
    applied=b._garment_world_positions().copy()
    if not np.allclose(applied,moved,atol=1e-5,rtol=0):raise RuntimeError('Initial transform readback mismatch')
    b._settle(case['settle_steps'])
    final=b._garment_world_positions()
    if final.shape!=(441,3) or not np.isfinite(final).all() or np.max(abs(final))>2:raise RuntimeError('Invalid settled geometry')
    if c.holding or c.attachment_enabled():raise RuntimeError('Unexpected active attachment')
    import cv2
    from omni.isaac.core.utils.rotations import euler_angles_to_quat
    b._env.camera.camera.set_world_pose(position=np.array([0.,-.50,2.80]),orientation=euler_angles_to_quat(np.array([0.,90.,90.]),degrees=True))
    # Render without advancing physics: screenshot and geometry refer to the same state.
    for _ in range(5):b._env.world.render()
    rgb=np.asarray(b._env.camera.camera.get_rgb())
    if rgb.shape[:2]!=(480,640) or rgb.ndim!=3 or rgb.shape[2]<3 or not np.isfinite(rgb).all():raise RuntimeError('Invalid RGB')
    rgb=rgb[:,:,:3]
    if np.issubdtype(rgb.dtype,np.floating):rgb=np.clip(rgb*(255 if rgb.max()<=1 else 1),0,255)
    rgb=np.ascontiguousarray(rgb,dtype=np.uint8)
    if not cv2.imwrite(str(out/'initial.png'),cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)):raise RuntimeError('PNG write failed')
    np.savez_compressed(out/'initial_geometry.npz',before=before,applied=applied,settled=final)
    result['geometry']={'center':final.mean(0).tolist(),'extent':np.ptp(final,axis=0).tolist(),'transform_error_max_m':float(np.max(abs(applied-moved)))}
    result['passed']=True;result['formal_day4_success']=False
except BaseException as exc:
    result['errors'].append(repr(exc));traceback.print_exc()
finally:
    try:
        (out/'result.json').write_text(json.dumps(result,indent=2,default=json_default),encoding='utf-8')
        print('RESULT_FILE',out/'result.json',flush=True)
        print('DOWNLOAD_DIR',out,flush=True)
    finally:b.stop()
