"""L2/L3 initial-state generation: flat perturbation + corner lift/drop.

Uses the original GarmentLab Control dynamic attachment (no prepared slots).
The exact per-seed corner/lift/drop parameters come from
square-initial-plan.json.  Development generation only.
"""
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import sys
import traceback
from datetime import datetime
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, '/root/autodl-tmp/garmentlab-action-chunk-demo')
from backends.garmentlab_backend import GarmentLabBackend, _import_garmentlab
from schemas.action import ActionChunk, CartesianAction, GripperCommand
from square_pose_backend import SquarePoseBackend
from square_pose_contract import grasp_to_ee
from square_start import start_with_square


class CornerPoseBackend(SquarePoseBackend):
    """SquarePoseBackend with prepared single-anchor corner slots."""
    def _make_prepared_control(self, env):
        from corner_prepared_control import CornerPreparedControl
        CornerPreparedControl.output_directory = getattr(self, 'output_dir', None)
        return CornerPreparedControl(env)

seed = int(os.environ.get('SQUARE_INITIAL_SEED', '4200'))
plan_file = Path(__file__).with_name('square-initial-plan.json')
initial_plan = json.loads(plan_file.read_text())
rows = [r for r in initial_plan['episodes'] if r['seed'] == seed]
if len(rows) != 1:
    raise ValueError('Seed not in square-initial-plan.json')
case = rows[0]
if case['level'] not in ('perturbed', 'crumpled') or not case['lift_drop_cycles']:
    raise ValueError('This entry generates only L2/L3 lift/drop cases')
corner_labels = initial_plan['corner_labels']
if len(corner_labels) != 4:
    raise ValueError('Expected four corner labels')
out = Path('/root/autodl-tmp') / ('day4-square-initial-liftdrop-' +
                                  datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result = {'probe_version': 'square-initial-liftdrop-v1', 'passed': False,
          'formal_day4_success': False, 'level': case['level'],
          'scope': 'L2/L3 initial-state generation; corner lift/drop; no fold or policy acceptance',
          'initial_case': case, 'lift_drop_records': [], 'actions': [], 'errors': [],
          'physics_profile': 'original robot asset; cloth mass .0001/friction .3/particle friction scale 0; '
                             'room collisions isolated; constructor bend 100',
          'drop_clamp_policy': {'near_y_max': -.25,
                                'scope': 'near-corner drop targets clamped to keep the fixed downward pose reachable; far targets unchanged'}}
b = None
capture_mass = None
original_step = None
state_trace = []
lift_trace = []
trace_active = False
trace_label = 'lift'


def json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f'Unsupported JSON type: {type(value).__name__}')


def record(label, data):
    data = dict(data)
    data['label'] = label
    result['lift_drop_records'].append(data)
    print('LIFTDROP_STEP', label, json.dumps(data, default=json_default), flush=True)


def action(cycle_number, xyz, yaw, command, label):
    target = np.r_[np.asarray(xyz, dtype=float), float(yaw)]
    chunk = ActionChunk(actions=[CartesianAction(target_pose=target.astype(np.float32),
                                                 gripper_command=int(command))])
    response = b.execute(chunk)
    control = b._env.control
    attached = control.attachlist != [None]
    checks = {'executed_one': response['executed_steps'] == 1,
              'not_done': response['done'] is False,
              'holding_consistent': bool(b._holding) == bool(attached),
              'attachment_count': int(attached) == int(b._holding)}
    row = {'cycle': cycle_number, 'label': label, 'target_pose': target.tolist(),
           'command': int(command), 'response': response, 'checks': checks,
           'holding': bool(b._holding), 'attached': bool(attached),
           'gripper_state': int(b._gripper_state),
           'ee': np.asarray(b._env.robots[0].get_cur_ee_pos()[0]).tolist(),
           'step': int(b._step_count['n'])}
    result['actions'].append(row)
    print('LIFTDROP_ACTION', label, json.dumps(response, default=json_default), flush=True)
    if not all(checks.values()):
        raise RuntimeError('Lift/drop action state mismatch: ' + label)
    return row


try:
    source = out / 'source'
    source.mkdir()
    dependencies = ['day4-square-initial-liftdrop.py', 'square-initial-plan.json',
                    'square-difficulty.yaml', 'square_start.py', 'square_pose_backend.py',
                    'square_pose_contract.py', 'corner_prepared_control.py',
                    'multi_prepared_grasp_control.py', 'square_probe_control.py',
                    'single_anchor_hem_control.py', 'multi_grasp_geometry.py',
                    'hem_prepared_grasp_control.py', 'hem_fold_geometry.py',
                    'square_contact_reporting.py', 'square_cloth_40cm.usda',
                    'room_collision_control.py',
                    'garmentlab-action-chunk-demo/backends/garmentlab_backend.py',
                    'garmentlab-action-chunk-demo/backends/base.py',
                    'garmentlab-action-chunk-demo/schemas/action.py',
                    'garmentlab-action-chunk-demo/schemas/observation.py']
    manifest = {}
    for name in dependencies:
        p = Path(name)
        shutil_path = out / 'source' / Path(name).name
        shutil_path.write_bytes(p.read_bytes())
        manifest[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (source / 'manifest.json').write_text(json.dumps(manifest, indent=2, default=json_default),
                                          encoding='utf-8')
    _import_garmentlab()
    from room_collision_control import install_room_collision_control
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
            kwargs['bend_stiffness'] = 100.
            result['constructor_bend_applied'] = 100.
            return original_cloth(*args, **kwargs)

        material_module.ClothPrim = bend_cloth

        def fixed_material(*args, **kwargs):
            if 'particle_friction_scale' in kwargs:
                raise RuntimeError('Unexpected material override')
            kwargs['particle_friction_scale'] = 0.
            return original_material(*args, **kwargs)

        material_module.ParticleMaterial = fixed_material
        b = CornerPoseBackend(garment_usd=str(Path(__file__).with_name('square_cloth_40cm.usda')),
                              prepared_grasp=True, max_action_steps=30000)
        capture_mass = start_with_square(b, out, .0001)
    finally:
        if material_module is not None and original_material is not None:
            material_module.ParticleMaterial = original_material
        if material_module is not None and original_cloth is not None:
            material_module.ClothPrim = original_cloth
        if restore_room is not None:
            restore_room()
    control = b._env.control
    robot = b._env.robots[0]
    robot.open()
    original_world_step = b._env.world.step

    def traced_step(*args, **kwargs):
        value = original_world_step(*args, **kwargs)
        if trace_active:
            try:
                slot = control.active
                ee, q = robot.get_cur_ee_pos()
                block_target = np.asarray(slot.block_target(), dtype=float).reshape(3)
                block_position = slot.block.get_position().numpy().reshape(3)
                block_velocity = b._to_numpy(
                    slot.block.move_block_controller.get_velocities(clone=True)).reshape(-1)
                prim = b._env.world.stage.GetPrimAtPath(slot.block.attachment_path)
                p1 = np.asarray(prim.GetAttribute('points1').Get(), dtype=float)
                pos, quat = slot.block.move_block_controller.get_world_poses()
                pos = pos.detach().cpu().numpy().reshape(3)
                quat = quat.detach().cpu().numpy().reshape(4)
                scale = np.asarray(b._env.world.stage.GetPrimAtPath(
                    slot.block.block_path).GetAttribute('xformOp:scale').Get(), dtype=float)
                desired = Rotation.from_quat(quat[[1, 2, 3, 0]]).apply(p1 * scale) + pos
                gap = None if slot.anchor_ids is None else float(np.linalg.norm(
                    slot.vertices()[slot.anchor_ids] - desired, axis=1).max())
                subtarget = getattr(control, 'probe_subtarget', None)
                ee_target = None if subtarget is None else np.asarray(subtarget['xyz'], dtype=float)
                lift_trace.append({
                    'step': int(b._step_count['n']),
                    'physics_step': int(b._env.world.current_time_step_index),
                    'label': trace_label, 'slot': slot.label,
                    'subtarget': subtarget,
                    'ee': np.asarray(ee).tolist(),
                    'ee_target': None if ee_target is None else ee_target.tolist(),
                    'ee_error': None if ee_target is None else float(np.linalg.norm(np.asarray(ee) - ee_target)),
                    'block_target': block_target.tolist(),
                    'block_position': block_position.tolist(),
                    'block_error': float(np.linalg.norm(block_target - block_position)),
                    'block_velocity': block_velocity.tolist(),
                    'anchor_gap': gap,
                    'joint_velocity': b._to_numpy(robot._robot.get_joint_velocities())[:7].tolist(),
                    'holding': bool(slot.holding), 'enabled': bool(slot.attachment_enabled())})
            except Exception as exc:
                lift_trace.append({'step': int(b._step_count['n']), 'label': trace_label,
                                   'trace_error': repr(exc)})
        return value

    b._env.world.step = traced_step
    home_ee, home_q = robot.get_cur_ee_pos()
    home_ee = np.asarray(home_ee, dtype=float).copy()
    result['home_ee'] = home_ee.tolist()
    result['home_quaternion_wxyz'] = np.asarray(home_q, dtype=float).tolist()
    material = b._env.garment[0].particle_material
    result['material_readback'] = {'friction': float(material.get_friction()),
                                   'particle_friction_scale': float(material.get_particle_friction_scale())}
    if not np.isclose(result['material_readback']['friction'], .3) or \
            result['material_readback']['particle_friction_scale'] != 0:
        raise RuntimeError('Unexpected cloth material')
    runtime = out / 'runtime_source'
    runtime.mkdir()
    for label, obj in [('backend', b), ('environment', b._env), ('robot', robot),
                       ('original_control', control)]:
        p = Path(inspect.getfile(type(obj)))
        raw = p.read_bytes()
        (runtime / (label + '.py')).write_bytes(raw)
        result.setdefault('runtime_source_hashes', {})[label] = {
            'path': str(p), 'sha256': hashlib.sha256(raw).hexdigest()}
    result['scope'] = ('L2/L3 initial-state generation only; corner lift/drop via original dynamic '
                       'attachment; no fold, recovery, or reset reliability claim')
    if control.attachlist != [None]:
        raise RuntimeError('Expected no pre-existing attachment')
    before = b._garment_world_positions().copy()
    center = before.mean(axis=0)
    yaw = float(case['yaw_rad'])
    co, si = np.cos(yaw), np.sin(yaw)
    rotation = np.array([[co, -si, 0], [si, co, 0], [0, 0, 1]])
    moved = (before - center) @ rotation.T + center + np.r_[case['translation_xy_m'], 0.]
    b._set_garment_world_positions(moved.astype(np.float32))
    b._clear_garment_velocities()
    applied = b._garment_world_positions().copy()
    if not np.allclose(applied, moved, atol=1e-5, rtol=0):
        raise RuntimeError('Initial transform readback mismatch')
    b._settle(120)
    flat_settled = b._garment_world_positions().copy()
    result['flat_transform'] = {
        'translation_xy_m': case['translation_xy_m'], 'yaw_rad': yaw,
        'center_before': center.tolist(), 'transform_error_max_m': float(np.max(abs(applied - moved)))}
    with np.load(out / 'cloth_constructed.npz') as constructed:
        local_points = np.asarray(constructed['points'], dtype=float)
    if local_points.shape != (441, 3):
        raise RuntimeError('Unexpected constructed local points')
    corners_local = np.array([[-.2, -.2, 0.], [.2, -.2, 0.], [.2, .2, 0.], [-.2, .2, 0.]])
    if not np.allclose(np.ptp(local_points, axis=0), [.4, .4, 0], atol=1e-6):
        raise RuntimeError('Unexpected local cloth extent')

    def corner_index(label):
        if label < 0 or label >= 4:
            raise ValueError('Invalid corner label')
        square_distance = ((local_points - corners_local[label]) ** 2).sum(axis=1)
        index = int(np.argmin(square_distance))
        if square_distance[index] > 1e-8:
            raise RuntimeError(f'Corner {label} not found in constructed mesh')
        return index

    def snapshot_vertices(label):
        vertices = b._garment_world_positions().copy()
        np.savez_compressed(out / (label + '.npz'), vertices=vertices)
        return vertices

    for cycle_number, cycle in enumerate(case['lift_drop_cycles']):
        index = corner_index(int(cycle['corner_label']))
        vertices = b._garment_world_positions().copy()
        corner = vertices[index].copy()
        approach = grasp_to_ee(corner + [0., 0., .15], yaw)
        grasp = grasp_to_ee(corner, yaw)
        lift_material = corner + [0., 0., float(cycle['lift_height_m'])]
        drop_requested = lift_material + [float(cycle['drop_xy_offset_m'][0]),
                                          float(cycle['drop_xy_offset_m'][1]), 0.]
        drop_material = drop_requested.copy()
        drop_clamped = bool(drop_material[1] > -.25)
        if drop_clamped:
            drop_material[1] = -.25
        lift = grasp_to_ee(lift_material, yaw)
        drop = grasp_to_ee(drop_material, yaw)
        record('cycle_start', {'cycle': cycle_number, 'corner_label': int(cycle['corner_label']),
                               'corner_index': index, 'corner_world': corner.tolist(),
                               'approach': approach.tolist(), 'grasp': grasp.tolist(),
                               'lift': lift.tolist(), 'lift_material': lift_material.tolist(),
                               'drop_requested': drop_requested.tolist(),
                               'drop': drop.tolist(), 'drop_material': drop_material.tolist(),
                               'drop_clamped': drop_clamped, 'near_drop_clamp_y': -.25,
                               'hold_steps': int(cycle['hold_steps'])})
        action(cycle_number, approach, yaw, GripperCommand.OPEN, 'approach')
        action(cycle_number, grasp, yaw, GripperCommand.CLOSE, 'grasp')
        trace_active = os.environ.get('SQUARE_LIFTDROP_DIAG') == '1'
        action(cycle_number, lift, yaw, GripperCommand.HOLD, 'lift')
        trace_active = False
        for _ in range(int(cycle['hold_steps'])):
            b._env.step()
        record('hold_done', {'cycle': cycle_number, 'steps': int(cycle['hold_steps'])})
        action(cycle_number, drop, yaw, GripperCommand.HOLD, 'drop')
        action(cycle_number, drop, yaw, GripperCommand.OPEN, 'release')
        b._settle(int(case['settle_steps']))
        settled = b._garment_world_positions().copy()
        np.savez_compressed(out / ('cycle_%02d_settled.npz' % cycle_number), vertices=settled)
        record('cycle_settled', {'cycle': cycle_number, 'settle_steps': int(case['settle_steps']),
                                 'center': settled.mean(axis=0).tolist(),
                                 'extent': np.ptp(settled, axis=0).tolist()})

    action(0, home_ee, yaw, GripperCommand.OPEN, 'home')
    b._settle(30)
    final = b._garment_world_positions().copy()
    if final.shape != (441, 3) or not np.isfinite(final).all() or np.max(abs(final)) > 2:
        raise RuntimeError('Invalid final geometry')
    if control.attachlist != [None] or b._holding:
        raise RuntimeError('Unexpected attachment after generation')
    import cv2
    from omni.isaac.core.utils.rotations import euler_angles_to_quat
    b._env.camera.camera.set_world_pose(
        position=np.array([0., -.50, 2.80]),
        orientation=euler_angles_to_quat(np.array([0., 90., 90.]), degrees=True))
    for _ in range(5):
        b._env.world.render()
    rgb = np.asarray(b._env.camera.camera.get_rgb())
    if rgb.shape[:2] != (480, 640) or rgb.ndim != 3 or rgb.shape[2] < 3 or not np.isfinite(rgb).all():
        raise RuntimeError('Invalid RGB')
    rgb = rgb[:, :, :3]
    if np.issubdtype(rgb.dtype, np.floating):
        rgb = np.clip(rgb * (255 if rgb.max() <= 1 else 1), 0, 255)
    rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
    if not cv2.imwrite(str(out / 'initial.png'), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise RuntimeError('PNG write failed')
    np.savez_compressed(out / 'initial_geometry.npz', before=before, applied=applied,
                        flat_settled=flat_settled, final=final)
    result['geometry'] = {'center': final.mean(0).tolist(), 'extent': np.ptp(final, axis=0).tolist(),
                          'z_p95': float(np.percentile(final[:, 2], 95)),
                          'corner_indices': [corner_index(int(c['corner_label']))
                                             for c in case['lift_drop_cycles']]}
    result['initial_image'] = str(out / 'initial.png')
    capture_mass('after_lift_drop')
    result['passed'] = True
    print('L2_L3_INITIAL_GENERATION_COMPLETED', flush=True)
except BaseException as exc:
    result['errors'].append(repr(exc))
    traceback.print_exc()
finally:
    try:
        if lift_trace:
            with (out / 'lift_trace.jsonl').open('w', encoding='utf-8') as trace_file:
                for trace_row in lift_trace:
                    trace_file.write(json.dumps(trace_row, default=json_default) + chr(10))
            result['lift_trace_file'] = str(out / 'lift_trace.jsonl')
            result['lift_trace_rows'] = len(lift_trace)
            print('LIFT_TRACE_FILE', out / 'lift_trace.jsonl', flush=True)
        (out / 'result.json').write_text(json.dumps(result, indent=2, default=json_default),
                                         encoding='utf-8')
        print('RESULT_FILE', out / 'result.json', flush=True)
        print('DOWNLOAD_DIR', out, flush=True)
    finally:
        if b is not None:
            try:
                b.stop()
            except Exception as exc:
                print('STOP_ERROR', repr(exc), flush=True)
