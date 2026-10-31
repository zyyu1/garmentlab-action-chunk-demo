"""Generate one bounded terminal-placement candidate for minimum Day4 step 1."""
import ast,hashlib,json
from pathlib import Path
import numpy as np
from minimum_fold_geometry import support_summary,supported_material_target,material_to_ee_target
root=Path(__file__).resolve().parent
source=(root/'day4-official-three-fold.py').read_text(encoding='utf-8')
source=source.replace('day4-official-three-fold.py','day4-minimum-half-fold.py')
source=source.replace("('day4-official-three-fold-'","('day4-minimum-half-fold-'")
source=source.replace('official-three-position-fold-v1','minimum-half-fold-supported-place-v1')
source=source.replace('Nominal-flat three-stage fold development pilot; no used-slot reuse, episode reset or formal acceptance',
                      'One hem half-fold development candidate; terminal supported placement only; no formal acceptance')
source=source.replace('from official_fold_geometry import official_plan, live_stage_waypoints',
                      'from hem_fold_geometry import hem_plan, hem_arc\nfrom minimum_fold_geometry import support_summary, supported_material_target, material_to_ee_target, edge_length_summary')
source=source.replace("'mass_experiment.py','official_fold_geometry.py']","'mass_experiment.py','minimum_fold_geometry.py']")
source=source.replace("plan=official_plan(initial,[s.pick_index for s in c.slots])","plan=hem_plan(initial,c.slots[2].pick_index)")
source=source.replace("np.savez_compressed(out/'fold_definition.npz',initial_vertices=initial,source_mask=plan['source_mask'],fold_line_y=plan['fold_line_y'])",
                      "np.savez_compressed(out/'fold_definition.npz',initial_vertices=initial,**plan)")
source=source.replace("json.dumps({k:v for k,v in plan.items() if k!='source_mask'},indent=2)",
                      "json.dumps({k:(v.tolist() if hasattr(v,'tolist') else v) for k,v in plan.items() if k!='source_mask'},indent=2)")
start=source.index("    for number,(slot,stage) in enumerate(zip(c.slots,plan['stages']),1):")
end=source.index('except BaseException as exc:',start)
body='''    slot=c.slots[2]
    with np.load(out/'cloth_constructed.npz') as mesh_source:faces=mesh_source['faceVertexIndices'].reshape(-1,3).copy()
    result['single_changed_path_problem']='Original terminal material point was beyond fixed-half support coverage and source remained elevated; replace terminal placement only'
    result['reference_path']='hem-v11 low arc: lift component .12m, same grasp/descent and original hold prefix'
    result['support_evidence_scope']='Geometric proximity and cloth motion only; no direct particle contact normal force measurement'
    pick=c.vertices()[slot.pick_index].copy()
    action(pick+[0,0,.15],GripperCommand.HOLD,'hem_approach')
    pick=c.vertices()[slot.pick_index].copy()
    for z in (.12,.08,.05,.03,.02):
        action([pick[0],pick[1],z],GripperCommand.HOLD,'hem_descend_'+str(z))
    snapshot('01_before_close')
    action([pick[0],pick[1],.02],GripperCommand.CLOSE,'hem_close')
    if c.active is not slot:raise RuntimeError('Expected hem slot')
    for _ in range(10):b._env.step()
    grasp,ee=snapshot('02_grasp')
    arc=hem_arc(ee,plan['fold_line_y'],lift_height=.12)
    result['low_arc_waypoints_xyz']=arc.tolist()
    for index,target in enumerate(arc,1):
        action(target,GripperCommand.HOLD,'hem_low_arc_'+str(index))
        if index==len(arc)//3:snapshot('03_lift')
        if index==len(arc)//2:snapshot('04_cross_line')
    ee,_=robot.get_cur_ee_pos()
    for _ in range(60):slot._tick(np.asarray(ee),None,follow=True)
    original_place,ee=snapshot('05_original_place')
    result['original_place_metrics']=hem_metrics(initial,original_place,plan)
    result['original_place_support']=support_summary(original_place,plan['source_mask'],slot.pick_index)
    result['geometric_tension_proxies']={'original_place':edge_length_summary(initial,original_place,faces,slot.anchor_ids)}
    selection=supported_material_target(original_place,plan['source_mask'],slot.pick_index,
                                         plan['target_reference'],plan['fold_line_y'])
    material_goal=np.asarray(selection['material_target_xyz'])
    ee_goal=material_to_ee_target(ee,original_place[slot.pick_index],material_goal)
    selection['requested_ee_target_xyz']=ee_goal.tolist()
    result['terminal_placement']=selection
    (out/'terminal_placement.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
    for k,target in enumerate(short_segments(ee,ee_goal)):
        action(target,GripperCommand.HOLD,'supported_place_'+str(k))
    phase='supported_place_hold'
    held_vertices=[]
    # Keep the requested target, rather than freezing the earlier measured pose.
    for _ in range(60):
        slot._tick(ee_goal,None,follow=True)
        held_vertices.append(c.vertices())
    placed,ee=snapshot('06_supported_place')
    result['supported_place_metrics']=hem_metrics(initial,placed,plan)
    result['supported_place_support']=support_summary(placed,plan['source_mask'],slot.pick_index)
    result['geometric_tension_proxies']['supported_place']=edge_length_summary(initial,placed,faces,slot.anchor_ids)
    result['material_goal_error_m']=float(np.linalg.norm(placed[slot.pick_index]-material_goal))
    held_vertices=np.asarray(held_vertices)
    dt=float(b._env.world.get_physics_dt())
    result['pre_release_last30_source_max_step_speed_m_s']=float(np.max(np.linalg.norm(np.diff(held_vertices[-30:,plan['source_mask']],axis=0),axis=2)/dt))
    np.savez_compressed(out/'terminal_hold_trace.npz',vertices=held_vertices,material_goal=material_goal,ee_goal=ee_goal,dt=dt)
    action(ee,GripperCommand.OPEN,'hem_release')
    released_block=slot.block.get_position().numpy().copy()
    released,ee=snapshot('07_released')
    phase='released_stationary'
    for _ in range(60):slot._tick(ee,None,follow=False)
    snapshot('08_release_stationary')
    # Reuse the previously tested retreat route, with no held cloth.
    for label,target in [('retreat_clear',[ee[0],ee[1],.10]),
                         ('retreat_outward',[ee[0],plan['fold_line_y'],.18]),
                         ('retreat_raise',[ee[0],plan['fold_line_y'],.25])]:
        current,_=robot.get_cur_ee_pos()
        for k,point in enumerate(short_segments(current,target)):
            action(point,GripperCommand.HOLD,label+'_'+str(k))
    snapshot('09_retreated')
    phase='post_retreat_settle_180'
    for _ in range(180):b._env.step()
    final,_=snapshot('10_final_3s')
    result['fold_metrics']=hem_metrics(initial,final,plan)
    result['geometric_tension_proxies']['final']=edge_length_summary(initial,final,faces,slot.anchor_ids)
    result['final_support_geometry']=support_summary(final,plan['source_mask'],slot.pick_index)
    result['fixed_half_centroid_displacement_m']=(final[~plan['source_mask']]-initial[~plan['source_mask']]).mean(axis=0).tolist()
    phase='retention_extra_60'
    for _ in range(60):b._env.step()
    retained,_=snapshot('11_retention_4s')
    result['retention_metrics']=hem_metrics(initial,retained,plan)
    result['retention_source_mean_displacement_from_3s_m']=float(np.linalg.norm(retained[plan['source_mask']]-final[plan['source_mask']],axis=1).mean())
    result['release_block_drift_m']=float(np.linalg.norm(slot.block.get_position().numpy()-released_block))
    capture_mass('after_half_fold')
    checks={'only_hem_used':[s.used for s in c.slots]==[False,False,True],
            'all_disabled':not c.attachment_enabled(),'not_holding':not c.holding and not b._holding,
            'paths_preserved':initial_paths==[(s.block.block_path,s.block.attachment_path) for s in c.slots],
            'block_stopped':result['release_block_drift_m']<.001}
    result['lifecycle_checks']=checks
    if not all(checks.values()):raise RuntimeError('Single half-fold lifecycle check failed')
    result['fold_success_accepted']=False
    result['development_review_required']=True
    result['development_repeat_required_if_adopted']=True
    result['pipeline_completed']=True
    if frame_count<20 or image_count<7:raise RuntimeError('Insufficient saved visual evidence')
    result['passed']=True
    print('MINIMUM_HALF_FOLD_PIPELINE_COMPLETED',flush=True)
    print('FINAL_FOLD_PROXY_METRICS',json.dumps(result['fold_metrics']),flush=True)
    print('RETENTION_PROXY_METRICS',json.dumps(result['retention_metrics']),flush=True)
'''
source=source[:start]+body+source[end:]
source=source.replace('OFFICIAL_THREE_PILOT_PASSED','MINIMUM_HALF_FOLD_PIPELINE_PASSED')
source=source.replace('Official three-stage position fold pilot via public Cartesian actions.','Minimum Day4: one hem half-fold, terminal supported-placement candidate.')
ast.parse(source,feature_version=(3,10))
assert 'set_fold_angle(' not in source and 'SingleAnchorMultiControl' not in source
(root/'day4-minimum-half-fold.py').write_text(source,encoding='utf-8',newline='\n')
runner=(root/'run-official-three-fold.sh').read_text(encoding='utf-8').replace('official-three-files.json','minimum-half-fold-files.json').replace('day4-official-three-fold.py','day4-minimum-half-fold.py').replace('OFFICIAL_THREE','MINIMUM_HALF_FOLD').replace('day4-official-three-log','day4-minimum-half-fold-log')
(root/'run-minimum-half-fold.sh').write_text(runner,encoding='utf-8',newline='\n')
files=['day4-minimum-half-fold.py','minimum_fold_geometry.py','multi_prepared_grasp_control.py','multi_grasp_geometry.py',
       'hem_prepared_grasp_control.py','hem_fold_geometry.py','l1_fold_geometry.py','room_collision_control.py','mass_experiment.py']
for name in files:ast.parse((root/name).read_text(encoding='utf-8'),feature_version=(3,10))
(root/'minimum-half-fold-files.json').write_text(json.dumps({n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in files},indent=2),encoding='utf-8')
# Real failed place snapshots must yield bounded support targets; no fake result is claimed.
tests=[]
for name in ['day4-l1-hem-fold-20261026-052424-872450','day4-l1-hem-fold-20261026-055645-888101']:
    p=root/'results'/name
    with np.load(p/'fold_definition.npz') as f:mask=f['source_mask'];pick=int(f['pick_index']);nominal=f['target_reference'];line=float(f['fold_line_y'])
    with np.load(p/'05_place.npz') as f:v=f['vertices'];ee=f['ee_position']
    summary=support_summary(v,mask,pick)
    try:goal=supported_material_target(v,mask,pick,nominal,line)
    except RuntimeError as exc:
        if name.endswith('055645-888101'):raise
        tests.append({'reference':name,'bounded_selection_rejected':repr(exc)})
        continue
    requested=material_to_ee_target(ee,v[pick],goal['material_target_xyz'])
    assert np.isclose(goal['material_target_xyz'][0],nominal[0])
    assert goal['xy_target_correction_m']<=.06 and goal['support_neighborhood_count']>=6
    assert np.allclose(requested-ee,np.asarray(goal['material_target_xyz'])-v[pick])
    tests.append({'reference':name,'support_goal':goal,'ee_goal':requested.tolist()})
try:supported_material_target(v,mask,pick,[100,100,0],line);raise AssertionError('Unsupported target accepted')
except RuntimeError:pass
(root/'minimum_half_fold_local_checks.json').write_text(json.dumps({'syntax_python310':True,'real_snapshot_support_checks':tests,
    'unsupported_target_rejected':True,'gpu_validation':False,'formal_acceptance':False},indent=2),encoding='utf-8')
print('MINIMUM_HALF_FOLD_LOCAL_CHECKS_OK; GPU_RUN_PENDING')
