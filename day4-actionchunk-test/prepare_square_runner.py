from pathlib import Path
b=Path('day4-actionchunk-test');s=(b/'day4-minimum-half-fold-bend-pair.py').read_text()
s=s.replace('from mass_experiment import start_with_mass','from square_start import start_with_square as start_with_mass\nfrom square_geometry import square_targets')
s=s.replace("'day4-minimum-half-fold-'","'day4-square-l1-'").replace("'minimum-half-fold-bend-pair-v1'","'square-l1-v1'")
s=s.replace("requested_bend=float(os.environ['DAY4_BEND'])","requested_bend=100.")
s=s.replace('b=GarmentLabBackend(prepared_grasp=True)',"b=GarmentLabBackend(garment_usd=str(Path(__file__).with_name('square_cloth_40cm.usda')),prepared_grasp=True)")
s=s.replace('from single_anchor_hem_control import SingleAnchorHemControl as MultiPreparedGraspControl','from square_control import SquareControl as MultiPreparedGraspControl')
s=s.replace("'day4-minimum-half-fold-bend-pair.py'","'day4-square-l1.py'").replace("'mass_experiment.py'","'square_start.py','square_control.py','square_geometry.py','square_cloth_40cm.usda'")
a=s.index("    result['single_changed_path_problem']");z=s.index("    capture_mass('after_half_fold')",a)
s=s[:a]+'''    result['scope']='Procedural single-layer square, single Franka, development only; not Dress057 acceptance'
    result['grasp_model']='Single-point attachment proxy; no physical pinch validation'
    result['interpolation']='Linear segments <=25mm per public target, no hidden fold path'
    result['arrival_rule']='EE<10mm, held block<5mm, arm speed<0.1rad/s for six steps; max120 convergence steps'
    dt=float(b._env.world.get_physics_dt())
    if not np.isclose(dt,1/60):raise RuntimeError('Unexpected dt')
    result['physics_dt']=dt
    pick=c.vertices()[slot.pick_index].copy()
    action(pick+[0,0,.15],GripperCommand.OPEN,'approach')
    pick=c.vertices()[slot.pick_index].copy()
    grasp_target=pick.copy();grasp_target[2]=max(.02,pick[2]+.01)
    action(grasp_target,GripperCommand.OPEN,'descend')
    snapshot('01_before_close')
    action(grasp_target,GripperCommand.CLOSE,'close')
    if c.active is not slot:raise RuntimeError('Expected lower-edge slot')
    grasp,ee=snapshot('02_grasp')
    material_targets=square_targets(grasp[slot.pick_index],plan['fold_line_y'])
    # Offset measured once after grasp. No hidden adaptive mid-segment correction.
    targets=material_targets+(ee-grasp[slot.pick_index])
    result['public_fold_targets']=targets.tolist()
    record_postcross=True
    for label,target in zip(['arc45','arc90','arc135','place'],targets):
        action(target,GripperCommand.HOLD,label)
        snapshot('03_'+label)
    phase='place_hold'
    held_vertices=[]
    for _ in range(60):
        slot._tick(targets[-1],None,follow=True);held_vertices.append(c.vertices())
    placed,ee=snapshot('06_supported_place')
    np.savez_compressed(out/'terminal_hold_trace.npz',vertices=np.asarray(held_vertices),dt=dt)
    result['supported_place_metrics']=hem_metrics(initial,placed,plan)
    result['supported_place_support']=support_summary(placed,plan['source_mask'],slot.pick_index)
    result['geometric_tension_proxies']={'supported_place':edge_length_summary(initial,placed,faces,slot.anchor_ids)}
    action(ee,GripperCommand.OPEN,'release')
    released_block=slot.block.get_position().numpy().copy()
    released,ee=snapshot('07_released')
    phase='released_stationary'
    for _ in range(60):slot._tick(ee,None,follow=False)
    snapshot('08_release_stationary')
    action(ee+[0,0,.15],GripperCommand.OPEN,'retreat')
    snapshot('09_retreated')
    phase='settle_3s'
    for _ in range(round(3/dt)):b._env.step()
    final,_=snapshot('10_final_3s')
    phase='retention_4s'
    for _ in range(round(1/dt)):b._env.step()
    retained,_=snapshot('11_retention_4s')
    result['fold_metrics']=hem_metrics(initial,final,plan)
    result['retention_metrics']=hem_metrics(initial,retained,plan)
    result['fixed_half_centroid_displacement_m']=(retained[~plan['source_mask']]-initial[~plan['source_mask']]).mean(axis=0).tolist()
    result['retention_source_mean_displacement_from_3s_m']=float(np.linalg.norm(retained[plan['source_mask']]-final[plan['source_mask']],axis=1).mean())
    result['release_block_drift_m']=float(np.linalg.norm(slot.block.get_position().numpy()-released_block))
    if len(result['actions'])!=9:raise RuntimeError('Expected exactly 9 public actions')
''' + s[z:]
s=s.replace("result['slot_status_final']=b._env.control.status();result['slot_events']=b._env.control.events", "result['slot_status_final']=b._env.control.status();result['slot_events']=b._env.control.events\n            result['linear_motion_records']=b._env.control.motion_records")
s=s.replace("    if not all(checks.values()):raise RuntimeError('Public action state mismatch: '+label)","    if not all(checks.values()):raise RuntimeError('Public action state mismatch: '+label)\n    if len(result['actions'])>9:raise RuntimeError('Public action budget exceeded')")
(b/'day4-square-l1.py').write_text(s,encoding='utf8')
runner=(b/'run-minimum-half-fold-bend-one.sh').read_text().replace('minimum-half-fold-bend-pair-files.json','square-l1-files.json').replace('day4-minimum-half-fold-bend-pair.py','day4-square-l1.py').replace('day4-minimum-half-fold-log','day4-square-l1-log')
runner+='\nif [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then exit 1; fi\n'
(b/'run-square-l1.sh').write_text(runner,encoding='utf8')
(b/'square_cloth_40cm.usda').write_bytes((b/'square_l1_candidate/square_cloth_40cm.usda').read_bytes())
