"""L2/L3 initial-state generation: flat perturbation + partial edge-strip folds.

The strip is the small-strip version of the validated x-axis half-fold: the
left-edge (and, for L3, bottom-hem) midpoint is lifted along the same
semicircular arc and placed on the sheet.  The folded strip lands on the
stationary part, so it is held by its own weight, unlike a corner dog-ear,
which snaps flat on release.

Uses the prepared single-anchor edge slots.  The original Control path stops
at its 3 cm reach tolerance and closes above the cloth, so it never grasps.
The exact per-seed yaw/translation/strip widths come from
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
from square_pose_contract import grasp_to_ee, orientation_euler
from square_start import start_with_square

EDGE_AXIS = {'left': (0, 1.), 'bottom': (1, 1.), 'right': (0, -1.)}


class StripPoseBackend(SquarePoseBackend):
    """SquarePoseBackend with prepared single-anchor edge slots."""
    def __init__(self, edges, *args, **kwargs):
        self._strip_edges = list(edges)
        super().__init__(*args, **kwargs)

    def _make_prepared_control(self, env):
        from strip_prepared_control import StripPreparedControl
        StripPreparedControl.output_directory = getattr(self, 'output_dir', None)
        return StripPreparedControl(env, self._strip_edges)


def strip_targets(pick, yaw, edge, width):
    axis, sign = EDGE_AXIS[edge]
    lateral = np.zeros(3)
    lateral[axis] = sign
    R = Rotation.from_euler('z', float(yaw)).as_matrix()
    out = []
    for angle in np.arange(1, 5) * np.pi / 4:
        local = lateral * (width - width * np.cos(angle))
        local[2] = .02 * angle / np.pi + width * np.sin(angle)
        out.append(np.asarray(pick, dtype=float) + R @ local)
    return np.asarray(out)


seed = int(os.environ.get('SQUARE_INITIAL_SEED', '4200'))
plan_file = Path(__file__).with_name('square-initial-plan.json')
initial_plan = json.loads(plan_file.read_text())
rows = [r for r in initial_plan['episodes'] if r['seed'] == seed]
if len(rows) != 1:
    raise ValueError('Seed not in square-initial-plan.json')
case = rows[0]
if case['level'] not in ('perturbed', 'crumpled') or not case.get('strips'):
    raise ValueError('This entry generates only L2/L3 strip-fold cases')
edges = [s['edge'] for s in case['strips']]
for strip in case['strips']:
    if strip['edge'] not in EDGE_AXIS or not .06 < float(strip['width_m']) < .15:
        raise ValueError('Invalid strip definition: ' + repr(strip))
out = Path('/root/autodl-tmp') / ('day4-square-initial-stripfold-' +
                                  datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result = {'probe_version': 'square-initial-stripfold-v1', 'passed': False,
          'formal_day4_success': False, 'level': case['level'],
          'scope': 'L2/L3 initial-state generation; partial edge-strip folds; no fold or policy acceptance',
          'initial_case': case, 'strip_records': [], 'actions': [], 'errors': [],
          'physics_profile': 'original robot asset; cloth mass .0001/friction .3/particle friction scale 0; '
                             'room collisions isolated; constructor bend 100',
          'strip_policy': {
              'edges': edges,
              'motion': 'same semicircular arc as the validated x-axis half-fold, radius = strip width',
              'release': 'place target at pick + 2*width inward, 2 cm above the sheet',
              'grasp': 'prepared 5 mm single anchor; pre-grasp drive keeps the 10 mm gate'}}
b = None
capture_mass = None
lift_trace = []
trace_active = False
trace_label = 'strip'
trace_target = None


def json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f'Unsupported JSON type: {type(value).__name__}')


def record(label, data):
    data = dict(data)
    data['label'] = label
    result['strip_records'].append(data)
    print('STRIPFOLD_STEP', label, json.dumps(data, default=json_default), flush=True)


def action(strip_number, xyz, yaw, command, label):
    global trace_target
    target = np.r_[np.asarray(xyz, dtype=float), float(yaw)]
    trace_target = target[:3].copy()
    chunk = ActionChunk(actions=[CartesianAction(target_pose=target.astype(np.float32),
                                                 gripper_command=int(command))])
    response = b.execute(chunk)
    control = b._env.control
    attached = control.attachlist != [None]
    checks = {'executed_one': response['executed_steps'] == 1,
              'not_done': response['done'] is False,
              'holding_consistent': bool(b._holding) == bool(attached),
              'attachment_count': int(attached) == int(b._holding)}
    row = {'strip': strip_number, 'label': label, 'target_pose': target.tolist(),
           'command': int(command), 'response': response, 'checks': checks,
           'holding': bool(b._holding), 'attached': bool(attached),
           'gripper_state': int(b._gripper_state),
           'ee': np.asarray(b._env.robots[0].get_cur_ee_pos()[0]).tolist(),
           'step': int(b._step_count['n'])}
    slot = getattr(control, 'active', None)
    if attached and slot is not None:
        row['block_error_m'] = float(np.linalg.norm(
            np.asarray(slot.block_target(), dtype=float) - slot.block.get_position().numpy()))
        row['max_single_anchor_gap_m'] = float(slot.max_single_anchor_gap_m)
    result['actions'].append(row)
    print('STRIPFOLD_ACTION', label, json.dumps(response, default=json_default), flush=True)
    if not all(checks.values()):
        raise RuntimeError('Strip-fold action state mismatch: ' + label)
    return row


try:
    source = out / 'source'
    source.mkdir()
    dependencies = ['day4-square-initial-stripfold.py', 'square-initial-plan.json',
                    'square-difficulty.yaml', 'square_start.py', 'square_pose_backend.py',
                    'square_pose_contract.py', 'strip_prepared_control.py',
                    'square_proxy_ground_control.py', 'square_probe_control.py',
                    'multi_prepared_grasp_control.py', 'single_anchor_hem_control.py',
                    'multi_grasp_geometry.py', 'hem_prepared_grasp_control.py',
                    'hem_fold_geometry.py', 'square_contact_reporting.py',
                    'square_stable_hold.py', 'square_cloth_40cm.usda',
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
        b = StripPoseBackend(edges,
                             garment_usd=str(Path(__file__).with_name('square_cloth_40cm.usda')),
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
                ee, _ = robot.get_cur_ee_pos()
                ee = np.asarray(ee, dtype=float)
                slot = getattr(control, 'active', None)
                block = control.attachlist[0] if control.attachlist != [None] else None
                if block is None:
                    block_position = None
                    block_target = None
                    block_error = None
                else:
                    block_position = block.get_position().numpy().reshape(3)
                    block_target = np.asarray(slot.block_target(), dtype=float).reshape(3)
                    block_error = float(np.linalg.norm(block_target - block_position))
                target = None if trace_target is None else np.asarray(trace_target, dtype=float)
                lift_trace.append({
                    'step': int(b._step_count['n']),
                    'physics_step': int(b._env.world.current_time_step_index),
                    'label': trace_label,
                    'slot': None if slot is None else slot.label,
                    'target': None if target is None else target.tolist(),
                    'ee': ee.tolist(),
                    'ee_error': None if target is None else float(np.linalg.norm(ee - target)),
                    'block_target': None if block_target is None else block_target.tolist(),
                    'block_position': None if block_position is None else block_position.tolist(),
                    'block_error': block_error,
                    'anchor_gap_max_m': None if slot is None else float(slot.max_single_anchor_gap_m),
                    'joint_velocity': b._to_numpy(robot._robot.get_joint_velocities())[:7].tolist(),
                    'holding': bool(control.holding)})
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
                       ('original_control', control.original)]:
        p = Path(inspect.getfile(type(obj)))
        raw = p.read_bytes()
        (runtime / (label + '.py')).write_bytes(raw)
        result.setdefault('runtime_source_hashes', {})[label] = {
            'path': str(p), 'sha256': hashlib.sha256(raw).hexdigest()}
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
    if not np.allclose(np.ptp(local_points, axis=0), [.4, .4, 0], atol=1e-6):
        raise RuntimeError('Unexpected local cloth extent')

    # Imported after the SimulationApp/backend start: square_stable_hold imports omni.isaac.
    from square_stable_hold import StableHold

    def snapshot(strip_number, label):
        vertices_now = b._garment_world_positions().copy()
        np.savez_compressed(out / ('strip_%02d_%s.npz' % (strip_number, label)),
                            vertices=vertices_now)
        return vertices_now

    for strip_number, strip in enumerate(case['strips']):
        edge = strip['edge']
        width = float(strip['width_m'])
        slot_index = {'right': 0, 'left': 1, 'bottom': 2}[edge]
        slot = control.slots[slot_index]
        pick_index = int(slot.pick_index)
        vertices = b._garment_world_positions().copy()
        pick = vertices[pick_index].copy()
        targets = strip_targets(pick, yaw, edge, width)
        ee_targets = [grasp_to_ee(point, yaw) for point in targets]
        grasp_target = grasp_to_ee(pick, yaw)
        axis, sign = EDGE_AXIS[edge]
        lateral_world = rotation @ (np.eye(3)[axis] * sign)
        pick_local = local_points[pick_index]
        moving = (local_points[:, axis] - pick_local[axis]) * sign < width
        local_reference = center + rotation @ pick_local + np.r_[case['translation_xy_m'], 0.]
        record('strip_start', {
            'strip': strip_number, 'edge': edge, 'width_m': width,
            'slot': slot.label, 'pick_index': pick_index, 'pick_world': pick.tolist(),
            'local_pick': pick_local.tolist(), 'moving_count': int(moving.sum()),
            'lateral_world': lateral_world.tolist(),
            'grasp': grasp_target.tolist(),
            'material_targets': targets.tolist(),
            'ee_targets': [np.asarray(t, dtype=float).tolist() for t in ee_targets]})

        action(strip_number, pick + [0., 0., .15], yaw, GripperCommand.OPEN, 'approach')
        action(strip_number, grasp_target, yaw, GripperCommand.OPEN, 'descend')
        action(strip_number, grasp_target, yaw, GripperCommand.CLOSE, 'close')
        if control.active is not slot:
            raise RuntimeError('Expected strip slot ' + slot.label)
        snapshot(strip_number, 'grasp')
        trace_active = os.environ.get('SQUARE_STRIPFOLD_DIAG') == '1'
        for label, target in zip(('arc45', 'arc90', 'arc135', 'place'), ee_targets):
            trace_label = label
            action(strip_number, target, yaw, GripperCommand.HOLD, label)
            snapshot(strip_number, label)
        trace_active = False
        hold_dir = out / ('hold_%02d' % strip_number)
        hold_dir.mkdir()
        hold = StableHold(robot, b._env.world, slot, hold_dir)
        hold_target = hold.begin()
        try:
            hold.run(60)
        finally:
            hold_summary = hold.save()
        record('hold_summary', {'strip': strip_number, 'target_joint_positions': hold_target,
                                'summary': hold_summary})
        ee, _ = robot.get_cur_ee_pos()
        ee = np.asarray(ee, dtype=float)
        held_error = float(np.linalg.norm(ee - ee_targets[-1]))
        held_ok = (held_error < .01 and
                   np.max(np.abs(b._to_numpy(robot._robot.get_joint_velocities())[:7])) < .1 and
                   bool(robot.reach(ee_targets[-1], orientation_euler(yaw))) and
                   slot.max_single_anchor_gap_m <= .01)
        record('held_check', {'strip': strip_number, 'position_error_m': held_error,
                              'arm_speed_rad_s': float(np.max(np.abs(
                                  b._to_numpy(robot._robot.get_joint_velocities())[:7]))),
                              'anchor_gap_max_m': float(slot.max_single_anchor_gap_m),
                              'accepted': bool(held_ok)})
        if not held_ok:
            raise RuntimeError('Strip held pose/velocity gate failed; released and saved')
        action(strip_number, ee, yaw, GripperCommand.OPEN, 'release')
        snapshot(strip_number, 'release')
        for _ in range(30):
            slot._tick(ee, orientation_euler(yaw), follow=False)
        action(strip_number, ee + [0., 0., .15], yaw, GripperCommand.OPEN, 'retreat')
        snapshot(strip_number, 'retreat')
        b._settle(int(case['settle_steps']))
        settled = snapshot(strip_number, 'settled')
        crossed = float((((settled[moving] - local_reference) @ lateral_world) > width).mean())
        record('strip_settled', {
            'strip': strip_number, 'settle_steps': int(case['settle_steps']),
            'center': settled.mean(axis=0).tolist(),
            'extent': np.ptp(settled, axis=0).tolist(),
            'crossed_fraction': crossed,
            'pick_displacement_m': float(np.linalg.norm(settled[pick_index] - pick))})

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
                          'z_p95': float(np.percentile(final[:, 2], 95))}
    result['initial_image'] = str(out / 'initial.png')
    capture_mass('after_strip_fold')
    result['passed'] = True
    print('L2_L3_STRIPFOLD_GENERATION_COMPLETED', flush=True)
except BaseException as exc:
    result['errors'].append(repr(exc))
    traceback.print_exc()
finally:
    try:
        if lift_trace:
            with (out / 'strip_trace.jsonl').open('w', encoding='utf-8') as trace_file:
                for trace_row in lift_trace:
                    trace_file.write(json.dumps(trace_row, default=json_default) + chr(10))
            result['strip_trace_file'] = str(out / 'strip_trace.jsonl')
            result['strip_trace_rows'] = len(lift_trace)
            print('STRIP_TRACE_FILE', out / 'strip_trace.jsonl', flush=True)
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
