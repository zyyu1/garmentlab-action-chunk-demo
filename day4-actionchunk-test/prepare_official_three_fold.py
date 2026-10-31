"""Build a development fold pilot from the verified two-slot lifecycle driver."""
import ast,hashlib,json
from pathlib import Path
import numpy as np
from official_fold_geometry import official_plan, live_stage_waypoints
root=Path(__file__).resolve().parent
source=(root/'day4-multi-grasp-test.py').read_text(encoding='utf-8')
source=source.replace('Two distinct prepared grabs in one process/episode via public Cartesian actions.','Official three-stage position fold pilot via public Cartesian actions.')
source=source.replace('Development lifecycle check only: no folding, slot reuse or reset acceptance.','Development only: no formal quality acceptance, slot reuse or reset acceptance.')
source=source.replace('day4-multi-grasp-test.py','day4-official-three-fold.py')
source=source.replace("('day4-multi-grasp-'","('day4-official-three-fold-'")
source=source.replace('multi-prepared-two-region-v1','official-three-position-fold-v1')
source=source.replace('Two distinct prepared regions in one rollout; no fold, used-slot reuse, or episode reset acceptance',
                      'Nominal-flat three-stage fold development pilot; no used-slot reuse, episode reset or formal acceptance')
source=source.replace('from mass_experiment import start_with_mass','from mass_experiment import start_with_mass\nfrom official_fold_geometry import official_plan, live_stage_waypoints\nfrom hem_fold_geometry import short_segments, hem_metrics')
source=source.replace("'room_collision_control.py','mass_experiment.py']","'room_collision_control.py','mass_experiment.py','official_fold_geometry.py']")
source=source.replace("original_step=None;capture_mass=None;state_trace=[];phase='startup'","original_step=None;capture_mass=None;state_trace=[];phase='startup';writer=None;frame_count=0;image_count=0;frame_errors=0")
video='''
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

'''
source=source.replace('def snapshot(label):',video+'def snapshot(label):')
source=source.replace('    return vertices,np.asarray(ee).copy()',"    if writer is not None:record_frame(label)\n    return vertices,np.asarray(ee).copy()")
source=source.replace("    original_step=b._env.world.step\n    def checked_step", "    setup_video()\n    original_step=b._env.world.step\n    def checked_step")
source=source.replace("        value=original_step(*args,**kwargs);c.assert_exclusive()", "        value=original_step(*args,**kwargs);c.assert_exclusive()\n        if int(b._step_count['n'])%3==0:record_frame()")
source=source.replace("    snapshot('00_initial')", "    initial,_=snapshot('00_initial')\n    plan=official_plan(initial,[s.pick_index for s in c.slots])\n    np.savez_compressed(out/'fold_definition.npz',initial_vertices=initial,source_mask=plan['source_mask'],fold_line_y=plan['fold_line_y'])\n    (out/'expert_plan.json').write_text(json.dumps({k:v for k,v in plan.items() if k!='source_mask'},indent=2),encoding='utf-8')\n    result['metric_threshold_status']='provisional only; no success threshold frozen'\n    result['stage_metrics']={}")
start=source.index('    for number,slot in enumerate(c.slots[:2],1):')
end=source.index('except BaseException as exc:',start)
new='''    for number,(slot,stage) in enumerate(zip(c.slots,plan['stages']),1):
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
    result['fold_metrics']=hem_metrics(initial,final,plan)
    result['nominal_fixed_half_centroid_drift_m']=(final[~plan['source_mask']]-initial[~plan['source_mask']]).mean(axis=0).tolist()
    capture_mass('after_three_releases')
    if [x['slot'] for x in result['cycles']]!=['right_sleeve','left_sleeve','hem'] or not all(s.used for s in c.slots):
        raise RuntimeError('Expected all three regions used once')
    result['public_action_count']=len(result['actions'])
    result['formal_12_action_budget_passed']=len(result['actions'])<=12
    result['fold_success_accepted']=False
    result['pipeline_completed']=True
    if frame_count<20 or image_count<7:raise RuntimeError('Insufficient saved visual evidence')
    result['passed']=True
    print('OFFICIAL_THREE_POSITION_PIPELINE_COMPLETED',flush=True)
    print('FOLD_PROXY_METRICS',json.dumps(result['fold_metrics']),flush=True)
'''
source=source[:start]+new+source[end:]
source=source.replace("    result['errors'].append(repr(exc));traceback.print_exc()", "    result['errors'].append(repr(exc));traceback.print_exc()\n    if b._started:\n        try:snapshot('99_failure')\n        except Exception as snapshot_error:result['failure_snapshot_error']=repr(snapshot_error)")
source=source.replace("finally:\n    if b._env is not None:","finally:\n    if writer is not None:writer.release()\n    result['video_frames']=frame_count;result['stage_images']=image_count;result['frame_errors']=frame_errors\n    result['public_action_count']=len(result['actions'])\n    result['formal_12_action_budget_passed']=len(result['actions'])<=12\n    if b._env is not None:")
source=source.replace("print('MULTI_GRASP_PASSED'","print('OFFICIAL_THREE_PILOT_PASSED'")
source=source.replace("result['formal_12_action_budget_passed']=len(result['actions'])<=12", "result['public_action_count_within_12']=len(result['actions'])<=12\n    result['formal_12_action_budget_passed']=False")
ast.parse(source,feature_version=(3,10))
assert 'set_fold_angle(' not in source and 'fold_orientation(' not in source
(root/'day4-official-three-fold.py').write_text(source,encoding='utf-8',newline='\n')
runner=(root/'run-multi-grasp-test.sh').read_text(encoding='utf-8').replace('multi-grasp-files.json','official-three-files.json').replace('day4-multi-grasp-test.py','day4-official-three-fold.py').replace('MULTI_GRASP','OFFICIAL_THREE_PILOT').replace('day4-multi-grasp-log','day4-official-three-log')
runner=runner.replace("r=json.loads(path.read_text())", "r=json.loads(path.read_text())\nif r.get('passed') is True:\n    import cv2\n    cap=cv2.VideoCapture(str(path.parent/'episode.mp4'))\n    ok,frame=cap.read();cap.release()\n    if not ok or frame.shape[:2]!=(480,640):raise RuntimeError('Saved fold video cannot be decoded; retain full result')\n    print('OFFICIAL_THREE_VIDEO_DECODE_OK',flush=True)")
(root/'run-official-three-fold.sh').write_text(runner,encoding='utf-8',newline='\n')
files=['day4-official-three-fold.py','multi_prepared_grasp_control.py','multi_grasp_geometry.py',
       'hem_prepared_grasp_control.py','hem_fold_geometry.py','l1_fold_geometry.py',
       'room_collision_control.py','mass_experiment.py','official_fold_geometry.py']
for name in files:ast.parse((root/name).read_text(encoding='utf-8'),feature_version=(3,10))
(root/'official-three-files.json').write_text(json.dumps({n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in files},indent=2),encoding='utf-8')
with np.load(root/'results/day4-multi-grasp-20261026-234353-347208/00_initial.npz') as f:initial=f['vertices'].copy()
data=json.loads((root/'results/day4-multi-grasp-20261026-234353-347208/result.json').read_text())
ids=[s['pick_index'] for s in data['slots_precreated']]
plan=official_plan(initial,ids)
for stage in plan['stages']:
    targets=live_stage_waypoints(stage,initial[stage['pick_index']])
    assert np.allclose(targets,stage['waypoints_xyz'])
    shift=np.array([.01,-.01,0.])
    moved=live_stage_waypoints(stage,initial[stage['pick_index']]+shift)
    assert np.allclose(moved[:,:2],targets[:,:2]+shift[:2]) and np.array_equal(moved[:,2],targets[:,2])
# Affine fit maps all three initial oracle picks exactly, without requiring a wrist pitch.
from official_fold_geometry import NOMINAL_PICKS
assert np.allclose(np.column_stack([NOMINAL_PICKS,np.ones(3)])@plan['xy_affine_transform'],initial[ids,:2])
try:official_plan(initial,[ids[0],ids[0],ids[2]]);raise AssertionError('Duplicate picks accepted')
except ValueError:pass
try:live_stage_waypoints(plan['stages'][0],initial[ids[0]]+[2.,0,0]);raise AssertionError('Outside workspace accepted')
except ValueError:pass
(root/'official_three_local_plan.json').write_text(json.dumps({k:v for k,v in plan.items() if k!='source_mask'},indent=2),encoding='utf-8')
print('OFFICIAL_THREE_SYNTAX_AND_LANDMARK_MAPPING_OK; NO_GPU_RUN')
