"""Day4 L1 development candidate: square-cloth x-axis centre half-fold.

Same public XYZ+yaw+gripper schema and 9-action development budget as the
y-axis candidate.  Only the fold axis, selected precreated edge slot and edge
geometry change.  No yaw/pitch side channel; no formal success claim.
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

sys.path.insert(0, '/root/autodl-tmp/garmentlab-action-chunk-demo')
from backends.garmentlab_backend import GarmentLabBackend, _import_garmentlab
from schemas.action import ActionChunk, CartesianAction, GripperCommand
from square_pose_backend import SquarePoseBackend
from square_pose_contract import grasp_to_ee, orientation_matrix, orientation_euler
from square_start import start_with_square as start_with_mass
from square_edge_fold_geometry import edge_plan, square_edge_targets
from minimum_fold_geometry import edge_length_summary, support_summary
from l1_fold_geometry import fold_metrics

out = Path('/root/autodl-tmp') / ('day4-square-l1-xfold-v1-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result = {'probe_version': 'square-l1-xfold-v1', 'passed': False, 'formal_day4_success': False,
          'scope': 'Procedural square cloth, single-arm x-axis half-fold development candidate; no formal acceptance',
          'actions': [], 'cycles': [], 'errors': [], 'yaw': 0.,
          'physics_profile': 'Original robot asset; no v9-v11 robot overrides; cloth mass .0001/friction .3/particle friction scale 0; room collisions isolated'}
requested_bend = 100.
if requested_bend not in (100., 10.):
    raise ValueError('Only preregistered bend 100/10 allowed')
result['requested_bend'] = requested_bend
result['physics_profile'] += '; constructor bend intervention recorded separately'
b = SquarePoseBackend(garment_usd=str(Path(__file__).with_name('square_cloth_40cm.usda')), prepared_grasp=True)
postcross_trace = []
postcross_labels = []
record_postcross = False
contact_recorder = None
control_trace = None
original_step = None
capture_mass = None
state_trace = []
phase = 'startup'
writer = None
frame_count = 0
image_count = 0
frame_errors = 0


def json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f'Unsupported JSON type: {type(value).__name__}')


def setup_video():
    global writer, cv2
    import cv2
    from omni.isaac.core.utils.rotations import euler_angles_to_quat
    b._env.camera.camera.set_world_pose(position=np.array([0., -.50, 2.80]),
        orientation=euler_angles_to_quat(np.array([0., 90., 90.]), degrees=True))
    writer = cv2.VideoWriter(str(out / 'episode.mp4'), cv2.VideoWriter_fourcc(*'mp4v'), 20., (640, 480))
    if not writer.isOpened():
        raise RuntimeError('Video writer failed')


def record_frame(label=None):
    global frame_count, image_count, frame_errors
    image = b._env.camera.camera.get_rgb()
    if image is None:
        frame_errors += 1
        return
    image = np.asarray(image)
    if image.ndim != 3 or image.shape[:2] != (480, 640) or image.shape[2] < 3 or not np.isfinite(image).all():
        frame_errors += 1
        return
    rgb = image[:, :, :3]
    if np.issubdtype(rgb.dtype, np.floating):
        rgb = np.clip(rgb * (255 if rgb.max() <= 1 else 1), 0, 255)
    rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
    writer.write(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    frame_count += 1
    if label is not None:
        if not cv2.imwrite(str(out / (label + '.png')), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
            raise RuntimeError('PNG save failed')
        image_count += 1


def snapshot(label):
    c = b._env.control
    vertices = b._garment_world_positions()
    ee, q = b._env.robots[0].get_cur_ee_pos()
    data = {'vertices': vertices, 'ee_position': np.asarray(ee), 'ee_quaternion': np.asarray(q)}
    for i, s in enumerate(c.slots):
        data['tracked_' + str(i)] = s.tracked
        data['anchors_' + str(i)] = s.anchor_ids
        pos, quat = s.block.move_block_controller.get_world_poses()
        data['block_position_' + str(i)] = pos.detach().cpu().numpy()
        data['block_quaternion_' + str(i)] = quat.detach().cpu().numpy()
    np.savez_compressed(out / (label + '.npz'), **data)
    (out / (label + '.json')).write_text(
        json.dumps({'status': c.status(), 'events': c.events}, indent=2, default=json_default), encoding='utf-8')
    if writer is not None:
        record_frame(label)
    return vertices, np.asarray(ee).copy()


def action(xyz, command, label):
    global phase
    phase = label
    chunk = ActionChunk(actions=[CartesianAction(
        target_pose=np.r_[np.asarray(xyz), 0.].astype(np.float32), gripper_command=int(command))])
    result['pending_action'] = {'label': label, 'matrix': chunk.to_matrix().tolist()}
    response = b.execute(chunk)
    b.get_observation().validate()
    c = b._env.control
    c.assert_exclusive()
    enabled = [x['enabled'] for x in c.status()]
    checks = {'executed_one': response['executed_steps'] == 1, 'not_done': response['done'] is False,
              'holding_consistent': bool(b._holding) == c.holding,
              'attachment_count': sum(enabled) == int(c.holding)}
    result['actions'].append({'label': label, 'matrix': chunk.to_matrix().tolist(), 'response': response,
                              'checks': checks, 'slots': c.status()})
    result.pop('pending_action', None)
    if not all(checks.values()):
        raise RuntimeError('Public action state mismatch: ' + label)
    if len(result['actions']) > 9:
        raise RuntimeError('Public action budget exceeded')
    print('MULTI_GRASP_ACTION', label, json.dumps(response), flush=True)


def collision_filter_audit():
    from pxr import Usd, UsdPhysics
    stage = b._env.world.stage
    report = {'groups': {}, 'attachment_bodies': [],
              'scope': 'Read-only USD collision-group dump; contact recorder is the runtime check'}
    for path in ['/World/Collision/robot_group', '/World/Collision/Garment_group',
                 '/World/Collision/Rigid_group', '/World/attach_group']:
        prim = stage.GetPrimAtPath(path)
        if not prim.IsValid():
            report['groups'][path] = {'exists': False}
            continue
        group = UsdPhysics.CollisionGroup(prim)
        api = Usd.CollectionAPI(prim, 'colliders')
        report['groups'][path] = {
            'exists': True,
            'filtered_groups': [str(t) for t in group.GetFilteredGroupsRel().GetTargets()],
            'collider_includes': [str(t) for t in api.GetIncludesRel().GetTargets()],
            'collider_excludes': [str(t) for t in api.GetExcludesRel().GetTargets()]}
    for prim in stage.Traverse():
        p = str(prim.GetPath())
        if p.startswith('/World/Attachment/') and prim.HasAPI(UsdPhysics.RigidBodyAPI):
            enabled = None
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                enabled = UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()
            report['attachment_bodies'].append({'path': p, 'collision_enabled': enabled})
    (out / 'collision_filter_audit.json').write_text(
        json.dumps(report, indent=2, default=json_default), encoding='utf-8')
    return report


def runtime_continuity_report():
    rows = [r for r in state_trace if 'joint_positions' in r]
    if len(rows) < 2:
        return {'samples': len(rows), 'max_arm_joint_delta_rad': None}
    q = np.asarray([r['joint_positions'][:7] for r in rows], dtype=float)
    dq = np.abs(np.diff(q, axis=0))
    k = int(np.unravel_index(np.argmax(dq), dq.shape)[0])
    speed = np.asarray([np.max(np.abs(np.asarray(r['joint_velocity'][:7], dtype=float))) for r in rows])
    return {'samples': len(rows), 'sample_interval_steps': 5,
            'max_arm_joint_delta_rad': float(dq.max()),
            'max_arm_joint_delta_phase': rows[k]['phase'],
            'max_arm_joint_delta_step': rows[k]['step'],
            'max_arm_joint_speed_rad_s': float(speed.max()),
            'max_arm_joint_speed_phase': rows[int(np.argmax(speed))]['phase'],
            'scope': 'Diagnostic sampling every 5 physics steps; not a continuity gate'}


try:
    if os.environ.get('GARMENTLAB_ATTACHMENT_OVERLAP') != '0.005' or os.environ.get('GARMENTLAB_DISABLED_ATTACHMENT_PROBE') != '0':
        raise RuntimeError('Expected 5mm overlap and enabled test mode')
    source = out / 'source'
    source.mkdir()
    dependencies = ['day4-square-l1-xfold-v1.py', 'multi_prepared_grasp_control.py', 'multi_grasp_geometry.py',
                    'hem_prepared_grasp_control.py', 'hem_fold_geometry.py', 'l1_fold_geometry.py',
                    'room_collision_control.py', 'square_start.py', 'square_probe_control.py',
                    'square_proxy_ground_control.py', 'square_control_trace.py', 'square_pose_backend.py',
                    'square_pose_contract.py', 'square_geometry.py', 'square_edge_fold_geometry.py',
                    'square_edge_control.py', 'square_cloth_40cm.usda', 'minimum_fold_geometry.py',
                    'early_descent_geometry.py', 'single_anchor_hem_control.py', 'square_stable_hold.py',
                    'square_contact_reporting.py', 'square_block_contact_recorder_v2.py']
    manifest = {}
    for name in dependencies:
        p = Path(__file__).with_name(name)
        shutil.copy2(p, source / name)
        manifest[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (source / 'manifest.json').write_text(json.dumps(manifest, indent=2, default=json_default), encoding='utf-8')
    _import_garmentlab()
    import backends.prepared_grasp_control as prepared
    from square_edge_control import SquareEdgeProxyGroundControl as MultiPreparedGraspControl
    MultiPreparedGraspControl.enable_early_contact_reporting = True
    MultiPreparedGraspControl.output_directory = out
    from room_collision_control import install_room_collision_control
    previous = prepared.PreparedGraspControl
    prepared.PreparedGraspControl = MultiPreparedGraspControl
    restore_room = None
    material_module = None
    original_material = None
    original_cloth = None
    try:
        restore_room = install_room_collision_control(out)
        material_module = importlib.import_module('Env.Garment.Garment')
        original_material = material_module.ParticleMaterial
        from functools import wraps
        original_cloth = material_module.ClothPrim

        @wraps(original_cloth)
        def bend_cloth(*args, **kwargs):
            if not np.isclose(kwargs.get('bend_stiffness', -1), 100.):
                raise RuntimeError('Unexpected baseline bend')
            for key, expected in [('stretch_stiffness', 10000.), ('shear_stiffness', 100.),
                                  ('spring_damping', .2)]:
                if not np.isclose(kwargs.get(key, -1), expected):
                    raise RuntimeError('Unexpected ' + key)
            kwargs['bend_stiffness'] = requested_bend
            result['constructor_bend_applied'] = requested_bend
            return original_cloth(*args, **kwargs)

        material_module.ClothPrim = bend_cloth

        def fixed_material(*args, **kwargs):
            if 'particle_friction_scale' in kwargs:
                raise RuntimeError('Unexpected material override')
            kwargs['particle_friction_scale'] = 0.
            return original_material(*args, **kwargs)

        material_module.ParticleMaterial = fixed_material
        capture_mass = start_with_mass(b, out, .0001)
    finally:
        if material_module is not None and original_material is not None:
            material_module.ParticleMaterial = original_material
        if material_module is not None and original_cloth is not None:
            material_module.ClothPrim = original_cloth
        if restore_room is not None:
            restore_room()
        prepared.PreparedGraspControl = previous
    c = b._env.control
    robot = b._env.robots[0]
    slot = c.fold_slot
    if slot.label != 'left_sleeve':
        raise RuntimeError('Unexpected fold slot')
    result['proxy_ground_filter'] = {'before': c.proxy_ground_before, 'authored': c.proxy_ground_authored,
                                     'after_reset': c.proxy_ground_after_reset}
    result['contact_reporting_setup_early'] = getattr(c, 'contact_report_early', None)
    result['contact_reporting_after_reset'] = getattr(c, 'contact_report_after_reset', None)

    def capture_springs(label):
        cloth = b._env.garment[0].garment_mesh
        prim = b._env.world.stage.GetPrimAtPath(b._env.garment[0].garment_mesh_prim_path)
        bend = float(prim.GetAttribute('physxAutoParticleCloth:springBendStiffness').Get())
        if not np.isclose(bend, requested_bend):
            raise RuntimeError('Bend USD readback mismatch')
        view = cloth._cloth_prim_view
        if view._physics_view is None:
            raise RuntimeError('Live spring physics view unavailable')
        springs = b._to_numpy(view.get_stretch_stiffnesses(clone=True))
        if not springs.size or not np.isfinite(springs).all():
            raise RuntimeError('Invalid runtime spring array')
        np.save(out / ('runtime_spring_stiffness_' + label + '.npy'), springs)
        result.setdefault('spring_readback', {})[label] = {
            'bend_usd': bend, 'shape': list(springs.shape),
            'min': float(springs.min()), 'max': float(springs.max()),
            'scope': 'SDK get_stretch_stiffnesses reads runtime get_spring_stiffness; entries are not labeled by spring type'}

    capture_springs('after_start')
    robot.open()
    material = b._env.garment[0].particle_material
    readback = {'friction': float(material.get_friction()),
                'particle_friction_scale': float(material.get_particle_friction_scale())}
    if not np.isclose(readback['friction'], .3) or readback['particle_friction_scale'] != 0:
        raise RuntimeError('Unexpected cloth material')
    result['material_readback'] = readback
    kp, kd = robot._articulation_controller.get_gains()
    result['robot_config'] = {'kp': b._to_numpy(kp).tolist(), 'kd': b._to_numpy(kd).tolist(),
                              'solver_position_iterations_usd': int(robot._robot.get_solver_position_iteration_count()),
                              'solver_velocity_iterations_usd': int(robot._robot.get_solver_velocity_iteration_count())}
    runtime = out / 'runtime_source'
    runtime.mkdir()
    for label, obj in [('backend', b), ('environment', b._env), ('robot', robot), ('original_control', c.original)]:
        p = Path(inspect.getfile(type(obj)))
        raw = p.read_bytes()
        (runtime / (label + '.py')).write_bytes(raw)
        result.setdefault('runtime_source_hashes', {})[label] = {
            'path': str(p), 'sha256': hashlib.sha256(raw).hexdigest()}
    result['slots_precreated'] = [{'label': s.label, 'block': s.block.block_path,
                                   'constraint': s.block.attachment_path, 'pick_index': s.pick_index,
                                   'anchor_ids': s.anchor_ids.tolist()} for s in c.slots]
    from square_control_trace import ControlTrace
    control_trace = ControlTrace(robot, b._env.world, out, lambda: phase)
    setup_video()
    from square_block_contact_recorder_v2 import BlockContactRecorderV2
    contact_recorder = BlockContactRecorderV2(b._env.world, c, out, lambda: phase)
    result['diagnostic_scope'] = ('Fixed downward Backend pose, public yaw wired (yaw=0 only), '
                                  'URDF fingertip midpoint proxy; x-axis centre fold; no formal acceptance')
    result['control_semantics'] = '9 public actions; straight linear interpolation <=25mm; no hidden fold path'
    result['legacy_contact_control_scope'] = ('Block-ground positive control intentionally removed by pair filter; '
                                              'false legacy flags are not evidence of logging failure or absence of collisions.')
    result['contact_diagnostic'] = ('PhysxContactReportAPI authored before env.reset(); block-ground events plus early '
                                    'RigidPrimView net-contact-force positive control')
    result['collision_filter_audit'] = collision_filter_audit()
    original_step = b._env.world.step

    def checked_step(*args, **kwargs):
        control_trace.state('before', b._step_count['n'])
        value = original_step(*args, **kwargs)
        c.assert_exclusive()
        control_trace.state('after', b._step_count['n'])
        if int(b._step_count['n']) % 3 == 0:
            record_frame()
        vertices = b._garment_world_positions()
        if record_postcross and int(b._step_count['n']) % 3 == 0:
            postcross_trace.append(vertices.copy())
            postcross_labels.append({'step': int(b._step_count['n']), 'phase': phase})
        if not np.isfinite(vertices).all() or np.max(abs(vertices)) > 2.:
            raise RuntimeError('Mesh escaped diagnostic bound')
        if int(b._step_count['n']) % 5 == 0:
            state_trace.append({'step': int(b._step_count['n']), 'phase': phase, 'slots': c.status(),
                                'cloth_centroid': vertices.mean(axis=0).tolist(),
                                'joint_positions': b._to_numpy(robot._robot.get_joint_positions()).tolist(),
                                'joint_velocity': b._to_numpy(robot._robot.get_joint_velocities()).tolist(),
                                'ee_position': np.asarray(robot.get_cur_ee_pos()[0]).tolist(),
                                'ee_quaternion_wxyz': np.asarray(robot.get_cur_ee_pos()[1]).tolist(),
                                'grasp_reference': c.active.block_target().tolist(),
                                'subtarget': getattr(c, 'probe_subtarget', None)})
            if contact_recorder is not None:
                contact_recorder.sample_force()
        return value

    b._env.world.step = checked_step
    phase = 'initial_settle'
    for _ in range(120):
        b._env.step()
    initial, _ = snapshot('00_initial')
    plan = edge_plan(initial, slot.pick_index)
    np.savez_compressed(out / 'fold_definition.npz', initial_vertices=initial, **plan)
    (out / 'expert_plan.json').write_text(
        json.dumps({k: (v.tolist() if hasattr(v, 'tolist') else v) for k, v in plan.items() if k != 'source_mask'},
                   indent=2, default=json_default), encoding='utf-8')
    result['metric_threshold_status'] = 'provisional only; no success threshold frozen'
    result['stage_metrics'] = {}
    initial_paths = [(s.block.block_path, s.block.attachment_path) for s in c.slots]
    with np.load(out / 'cloth_constructed.npz') as mesh_source:
        faces = mesh_source['faceVertexIndices'].reshape(-1, 3).copy()
    result['scope'] = 'Procedural single-layer square, single Franka, x-axis half-fold development candidate'
    result['grasp_model'] = 'Single-point attachment proxy; no physical pinch validation'
    result['interpolation'] = 'Linear segments <=25mm per public target, no hidden fold path'
    result['arrival_rule'] = 'EE<10mm, held block<5mm, arm speed<0.1rad/s for six steps; max120 convergence steps'
    dt = float(b._env.world.get_physics_dt())
    if not np.isclose(dt, 1 / 60):
        raise RuntimeError('Unexpected dt')
    result['physics_dt'] = dt
    result['fold_axis'] = 'world_y'
    result['fold_line_x'] = float(plan['fold_line_x'])
    result['fold_slot'] = slot.label
    result['pick_index'] = int(slot.pick_index)
    pick = c.vertices()[slot.pick_index].copy()
    action(pick + [0, 0, .15], GripperCommand.OPEN, 'approach')
    pick = c.vertices()[slot.pick_index].copy()
    grasp_target = grasp_to_ee(pick, 0.)
    result['pose_contract'] = {'xyz_frame': 'world right_gripper', 'yaw_rad': 0.,
                               'fixed_euler_roll_pitch': [float(np.pi), 0.],
                               'local_grasp_reference': slot.local_offset.tolist(),
                               'reference_scope': 'URDF named fingertip midpoint, not physical pinch calibration',
                               'material_pick': pick.tolist(), 'ee_target': grasp_target.tolist()}
    action(grasp_target, GripperCommand.OPEN, 'descend')
    snapshot('01_before_close')
    action(grasp_target, GripperCommand.CLOSE, 'close')
    if c.active is not slot:
        raise RuntimeError('Expected left-edge slot')
    grasp_vertices, ee = snapshot('02_grasp')
    material_targets = square_edge_targets(grasp_vertices[slot.pick_index], plan['fold_line_x'])
    targets = np.asarray([grasp_to_ee(point, 0.) for point in material_targets])
    result['public_fold_targets'] = targets.tolist()
    result['material_fold_targets'] = material_targets.tolist()
    result['grasp_frame_conversion'] = {'material_pick': grasp_vertices[slot.pick_index].tolist(),
                                        'ee_target': grasp_target.tolist(),
                                        'rule': 'EE target = live material point - fixed downward grasp offset'}
    record_postcross = True
    for label, target in zip(['arc45', 'arc90', 'arc135', 'place'], targets):
        action(target, GripperCommand.HOLD, label)
        snapshot('03_' + label)
    phase = 'place_hold'
    from square_stable_hold import StableHold
    hold = StableHold(robot, b._env.world, slot, out)
    result['hold_target_joint_positions'] = hold.begin()
    try:
        hold.run(60)
    finally:
        result['hold_summary'] = hold.save()
    placed, ee = snapshot('06_supported_place')
    result['supported_place_metrics'] = fold_metrics(initial, placed, plan)
    result['supported_place_support'] = support_summary(placed, plan['source_mask'], slot.pick_index)
    result['geometric_tension_proxies'] = {
        'supported_place': edge_length_summary(initial, placed, faces, slot.anchor_ids)}
    ee, q = robot.get_cur_ee_pos()
    result['held_check'] = {'position_error_m': float(np.linalg.norm(np.asarray(ee) - targets[-1])),
                            'arm_speed_rad_s': float(np.max(abs(b._to_numpy(robot._robot.get_joint_velocities())[:7]))),
                            'orientation_reached': bool(robot.reach(targets[-1], orientation_euler(0.))),
                            'anchor_gap_max_m': float(slot.max_single_anchor_gap_m)}
    h = result['held_check']
    held_ok = (h['position_error_m'] < .01 and h['arm_speed_rad_s'] < .1 and
               h['orientation_reached'] and h['anchor_gap_max_m'] <= .01)
    action(np.asarray(ee), GripperCommand.OPEN, 'release')
    released_block = slot.block.get_position().numpy().copy()
    released, ee = snapshot('07_released')
    phase = 'released_stationary'
    for _ in range(30):
        slot._tick(np.asarray(ee), orientation_euler(0.), follow=False)
    snapshot('08_release_stationary')
    record_postcross = False
    action(ee + [0, 0, .15], GripperCommand.OPEN, 'retreat')
    snapshot('09_retreated')
    phase = 'settle_3s'
    for _ in range(round(3 / dt)):
        b._env.step()
    final, _ = snapshot('10_final_3s')
    phase = 'retention_4s'
    for _ in range(round(1 / dt)):
        b._env.step()
    retained, _ = snapshot('11_retention_4s')
    result['fold_metrics'] = fold_metrics(initial, final, plan)
    result['retention_metrics'] = fold_metrics(initial, retained, plan)
    result['fixed_half_centroid_displacement_m'] = (
        retained[~plan['source_mask']] - initial[~plan['source_mask']]).mean(axis=0).tolist()
    result['retention_source_mean_displacement_from_3s_m'] = float(
        np.linalg.norm(retained[plan['source_mask']] - final[plan['source_mask']], axis=1).mean())
    result['release_block_drift_m'] = float(
        np.linalg.norm(slot.block.get_position().numpy() - released_block))
    result['development_overlap_indicators'] = {
        'moving_half_crossed_fraction': result['fold_metrics']['moving_half_crossed_fraction'],
        'particle_occupancy_iou': result['fold_metrics']['particle_occupancy_iou'],
        'symmetric_xy_alignment_mean_m': result['fold_metrics']['symmetric_xy_alignment_mean_m'],
        'fixed_half_centroid_displacement_m': result['fixed_half_centroid_displacement_m'],
        'retention_source_mean_displacement_from_3s_m': result['retention_source_mean_displacement_from_3s_m'],
        'release_block_drift_m': result['release_block_drift_m'],
        'cloth_z_p95_m': result['fold_metrics']['cloth_z_p95_m'],
        'scope': 'Particle projection proxies; no frozen success threshold; visual review required'}
    if len(result['actions']) != 9:
        raise RuntimeError('Expected exactly 9 public actions')
    capture_mass('after_half_fold')
    capture_springs('after_half_fold')
    checks = {'only_fold_slot_used': [s.used for s in c.slots] == [False, True, False],
              'all_disabled': not c.attachment_enabled(),
              'not_holding': not c.holding and not b._holding,
              'paths_preserved': initial_paths == [(s.block.block_path, s.block.attachment_path) for s in c.slots],
              'block_stopped': result['release_block_drift_m'] < .001}
    result['lifecycle_checks'] = checks
    if not all(checks.values()):
        raise RuntimeError('x-axis half-fold lifecycle check failed')
    if not held_ok:
        raise RuntimeError('Held pose/velocity gate failed; released and saved')
    result['fold_success_accepted'] = False
    result['development_review_required'] = True
    result['development_repeat_required_if_adopted'] = True
    result['public_action_count'] = len(result['actions'])
    result['public_action_count_within_12'] = len(result['actions']) <= 12
    result['formal_12_action_budget_passed'] = False
    result['runtime_continuity'] = runtime_continuity_report()
    result['pipeline_completed'] = True
    if frame_count < 20 or image_count < 7:
        raise RuntimeError('Insufficient saved visual evidence')
    result['passed'] = True
    print('SQUARE_L1_XFOLD_PIPELINE_COMPLETED', flush=True)
    print('FOLD_PROXY_METRICS', json.dumps(result['fold_metrics']), flush=True)
    print('RETENTION_PROXY_METRICS', json.dumps(result['retention_metrics']), flush=True)
except BaseException as exc:
    result['errors'].append(repr(exc))
    traceback.print_exc()
    if b._started:
        try:
            snapshot('99_failure')
        except Exception as snapshot_error:
            result['failure_snapshot_error'] = repr(snapshot_error)
finally:
    if postcross_trace:
        np.savez_compressed(out / 'postcross_trace.npz', vertices=np.asarray(postcross_trace))
        (out / 'postcross_trace_labels.json').write_text(
            json.dumps(postcross_labels, indent=2, default=json_default), encoding='utf-8')
    result['postcross_trace_frames'] = len(postcross_trace)
    if writer is not None:
        writer.release()
    result['video_frames'] = frame_count
    result['stage_images'] = image_count
    result['frame_errors'] = frame_errors
    result['public_action_count'] = len(result['actions'])
    result['public_action_count_within_12'] = len(result['actions']) <= 12
    result['formal_12_action_budget_passed'] = False
    try:
        result.setdefault('runtime_continuity', runtime_continuity_report())
    except Exception as exc:
        result['runtime_continuity_error'] = repr(exc)
    if contact_recorder is not None:
        contact = contact_recorder.save()
        result['block_contact_report'] = contact
        result['contact_positive_control'] = {
            'event_channel_valid': contact.get('event_channel_valid'),
            'force_channel_valid': contact.get('force_channel_valid'),
            'positive_control_valid': contact.get('positive_control_valid'),
            'independent_force_positive_control': contact.get('independent_force_positive_control'),
            'force_max_norm': contact.get('force_max_norm'),
            'force_positive_samples': contact.get('force_positive_samples'),
            'force_samples': contact.get('force_samples'),
            'event_counts': contact.get('counts'),
            'diagnosis': contact.get('diagnosis')}
        result['contact_channel_valid'] = contact.get('positive_control_valid')
        result['contact_force_channel_valid'] = contact.get('force_channel_valid')
    if b._env is not None:
        try:
            result['slot_status_final'] = b._env.control.status()
            result['slot_events'] = b._env.control.events
            result['linear_motion_records'] = b._env.control.motion_records
        except Exception as exc:
            result['final_status_error'] = repr(exc)
    (out / 'state_trace.json').write_text(json.dumps(state_trace, indent=2, default=json_default), encoding='utf-8')
    (out / 'result.json').write_text(json.dumps(result, indent=2, default=json_default), encoding='utf-8')
    print('SQUARE_L1_XFOLD_PIPELINE_PASSED', result['passed'], flush=True)
    print('RESULT_FILE', out / 'result.json', flush=True)
    print('DOWNLOAD_DIR', out, flush=True)
    if original_step is not None:
        b._env.world.step = original_step
    try:
        if control_trace is not None:
            control_trace.close()
    finally:
        b.stop()
