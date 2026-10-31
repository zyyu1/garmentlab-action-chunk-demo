"""Two distinct prepared grabs in one process/episode via public Cartesian actions.

Development lifecycle check only: no folding, slot reuse or reset acceptance.
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

out=Path('/root/autodl-tmp')/('day4-multi-grasp-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result={'probe_version':'multi-prepared-two-region-v1','passed':False,'formal_day4_success':False,
        'scope':'Two distinct prepared regions in one rollout; no fold, used-slot reuse, or episode reset acceptance',
        'actions':[],'cycles':[],'errors':[],'yaw':0.,'physics_profile':'Original robot asset; no v9-v11 robot overrides; cloth mass .0001/friction .3/particle friction scale 0; room collisions isolated'}
b=GarmentLabBackend(prepared_grasp=True)
original_step=None;capture_mass=None;state_trace=[];phase='startup'

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
    dependencies=['day4-multi-grasp-test.py','multi_prepared_grasp_control.py','multi_grasp_geometry.py',
                  'hem_prepared_grasp_control.py','hem_fold_geometry.py','l1_fold_geometry.py',
                  'room_collision_control.py','mass_experiment.py']
    manifest={}
    for name in dependencies:
        p=Path(__file__).with_name(name);shutil.copy2(p,source/name)
        manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (source/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    _import_garmentlab()
    import backends.prepared_grasp_control as prepared
    from multi_prepared_grasp_control import MultiPreparedGraspControl
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
    original_step=b._env.world.step
    def checked_step(*args,**kwargs):
        value=original_step(*args,**kwargs);c.assert_exclusive()
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
    snapshot('00_initial')
    initial_paths=[(s.block.block_path,s.block.attachment_path) for s in c.slots]
    for number,slot in enumerate(c.slots[:2],1):
        label=str(number)+'_'+slot.label
        # Expert uses declared simulation truth internally; public action contains xyz/yaw/gripper only.
        pick=c.vertices()[slot.pick_index].copy()
        action([pick[0],pick[1],.15],GripperCommand.HOLD,label+'_approach')
        for z in (.12,.08,.05,.03,.02):
            pick=c.vertices()[slot.pick_index].copy()
            action([pick[0],pick[1],z],GripperCommand.HOLD,label+'_descend_'+str(z))
        pick=c.vertices()[slot.pick_index].copy()
        snapshot(label+'_before_close')
        action([pick[0],pick[1],.02],GripperCommand.CLOSE,label+'_close')
        if c.active is not slot:raise RuntimeError('Selected unexpected slot')
        grasp,ee=snapshot(label+'_grasp')
        action(ee+[0,0,.10],GripperCommand.HOLD,label+'_lift')
        lifted,ee=snapshot(label+'_lift')
        rise=float(lifted[slot.tracked,2].mean()-grasp[slot.tracked,2].mean())
        follow=float(np.linalg.norm(slot.block_target()-slot.block.get_position().numpy()))
        if rise<.05 or follow>.005:raise RuntimeError('Lift/follow check failed')
        action(ee,GripperCommand.OPEN,label+'_release')
        released_block=slot.block.get_position().numpy().copy()
        phase=label+'_release_settle'
        for _ in range(120):b._env.step()
        released,_=snapshot(label+'_released')
        drop=float(lifted[slot.tracked,2].mean()-released[slot.tracked,2].mean())
        drift=float(np.linalg.norm(slot.block.get_position().numpy()-released_block))
        checks={'lifted':rise>.05,'followed':follow<.005,'released_drop':drop>.05,'block_stopped':drift<.001,
                'all_disabled':not c.attachment_enabled(),'not_holding':not c.holding and not b._holding,
                'paths_preserved':initial_paths==[(s.block.block_path,s.block.attachment_path) for s in c.slots]}
        result['cycles'].append({'slot':slot.label,'cloth_rise_m':rise,'follow_error_m':follow,'cloth_drop_m':drop,
                                  'release_block_drift_m':drift,'checks':checks,'alignment':slot.alignment_record,
                                  'activation':slot.activation_record})
        if not all(checks.values()):raise RuntimeError('Release lifecycle checks failed')
        print('MULTI_GRASP_CYCLE_OK',slot.label,json.dumps(checks),flush=True)
    capture_mass('after_two_releases')
    if [x['slot'] for x in result['cycles']]!=['right_sleeve','left_sleeve']:raise RuntimeError('Expected two distinct slots')
    if [s.used for s in c.slots]!=[True,True,False]:raise RuntimeError('Unexpected slot lifecycle')
    result['passed']=True
    print('TWO_REGION_PREPARED_GRASP_RELEASE_OK',flush=True)
except BaseException as exc:
    result['errors'].append(repr(exc));traceback.print_exc()
finally:
    if b._env is not None:
        try:
            result['slot_status_final']=b._env.control.status();result['slot_events']=b._env.control.events
        except Exception as exc:result['final_status_error']=repr(exc)
    (out/'state_trace.json').write_text(json.dumps(state_trace,indent=2),encoding='utf-8')
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('MULTI_GRASP_PASSED',result['passed'],flush=True)
    print('RESULT_FILE',out/'result.json',flush=True)
    print('DOWNLOAD_DIR',out,flush=True)
    if original_step is not None:b._env.world.step=original_step
    b.stop()
