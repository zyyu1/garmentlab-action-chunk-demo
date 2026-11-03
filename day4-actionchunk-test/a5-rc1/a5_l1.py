"""L1 yaw-aware x-axis half-fold with exactly 7 public actions.

Same compressed 7-action schedule as the validated L1 x-fold:
  approach -> close -> arc45 -> arc90 -> arc135 -> place -> release
but the initial flat state is loaded from a stored L1 initial case (with
translation and yaw), the fold yaw is measured from that settled cloth, and
the half-fold arc and all public poses are expressed in the cloth-local frame.

``--overhang`` (default 0) extends only the final place target laterally past
the nominal half-fold point; the default reproduces the nominal half fold.

``--execution`` selects the waypoint representation: ``single`` (default) sends
one public action per waypoint, ``arc4`` sends arc45/arc90/arc135/place as one
H=4 chunk.  Both build the targets from the same measured ``grasp_pick`` after
CLOSE, so the targets are identical by construction.

Development revalidation only; not a formal success.
"""
import argparse
import hashlib
import importlib
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, '/root/autodl-tmp/garmentlab-action-chunk-demo')
from backends.garmentlab_backend import GarmentLabBackend, _import_garmentlab
from schemas.action import ActionChunk, CartesianAction, GripperCommand
from square_pose_backend import SquarePoseBackend
from square_pose_contract import grasp_to_ee, orientation_euler
from square_start import start_with_square
from l1_yaw_fold_geometry import fold_metrics_yaw, local_arc, measure_yaw


class FoldPoseBackend(SquarePoseBackend):
    def _make_prepared_control(self, env):
        from square_edge_control import SquareEdgeProxyGroundControl
        SquareEdgeProxyGroundControl.output_directory = getattr(self, 'output_dir', None)
        return SquareEdgeProxyGroundControl(env)


ap = argparse.ArgumentParser()
ap.add_argument('--initial-dir', required=True)
ap.add_argument('--allow-root', action='store_true')
ap.add_argument('--overhang', type=float, default=0.,
                help='Lateral extension of the final place target past the '
                     'nominal half-fold point, in metres (default 0).')
ap.add_argument('--execution', choices=('single', 'arc4'), default='single',
                help='Waypoint representation: one public action per waypoint '
                     '(frozen default), or one H=4 chunk covering '
                     'arc45/arc90/arc135/place. Targets are identical in both.')
ap.add_argument('--split', choices=['dev','formal'], required=True)
args = ap.parse_args()
if args.overhang != .02:
    raise ValueError('Overhang must be within [0, 0.04] m')
manifest_path = Path(__file__).with_name('a5-manifest.json')
code_files = json.loads(manifest_path.read_text())
if code_files.get(Path(__file__).name) != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
    raise RuntimeError('Script bytes do not match ' + manifest_path.name)
init_dir = Path(args.initial_dir)
init = json.loads((init_dir / 'result.json').read_text())
if not init.get('passed'):
    raise ValueError('Initial state did not pass')
case = init['initial_case']
from a5_entry import authorize_initial
authorize_initial(init_dir, args.split, args.execution, 'l1')
if case.get('level') != 'flat':
    raise ValueError('L1 yaw-aware fold requires a flat initial case')
with np.load(init_dir / 'initial_geometry.npz') as data:
    settled = np.asarray(data['settled'], dtype=float)
if settled.shape != (441, 3) or not np.isfinite(settled).all():
    raise ValueError('Unexpected initial geometry')
out = Path('/root/autodl-tmp') / ('day4-a5-l1-' +
                                  datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result = {'probe_version': 'l1-xfold-yaw-aware-v1', 'passed': False,
          'formal_day4_success': False, 'fold_success_accepted': False,
          'scope': 'L1 yaw-aware x-fold revalidation with 7 public actions; no formal acceptance',
          'initial_dir': str(init_dir), 'initial_case': case,
          'initial_files': {name: hashlib.sha256((init_dir / name).read_bytes()).hexdigest()
                            for name in ('result.json', 'initial_geometry.npz')},
          'execution_mode': args.execution, 'call_horizons': [], 'chunks': [],
          'code_files': code_files,
          'actions': [], 'errors': []}
b = None
evidence = None


def json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f'Unsupported JSON type: {type(value).__name__}')


def snapshot(label):
    vertices = b._garment_world_positions().copy()
    payload = {'vertices': vertices}
    try:
        view = b._env.garment[0].garment_mesh._cloth_prim_view
        velocities = view.get_world_velocities(clone=True).detach().cpu().numpy()[0]
        if velocities.shape == vertices.shape and np.isfinite(velocities).all():
            payload['velocities'] = velocities
    except Exception as exc:
        payload['velocity_error'] = np.array([repr(exc)])
    np.savez_compressed(out / (label + '.npz'), **payload)
    return vertices


def action(xyz, yaw, command, label):
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
    row = {'label': label, 'target_pose': target.tolist(), 'command': int(command),
           'response': response, 'checks': checks, 'holding': bool(b._holding),
           'attached': bool(attached), 'ee': np.asarray(
               b._env.robots[0].get_cur_ee_pos()[0]).tolist(),
           'step': int(b._step_count['n'])}
    slot = getattr(control, 'active', None)
    if attached and slot is not None:
        row['block_error_m'] = float(np.linalg.norm(
            np.asarray(slot.block_target(), dtype=float) - slot.block.get_position().numpy()))
        row['max_single_anchor_gap_m'] = float(slot.max_single_anchor_gap_m)
    result['actions'].append(row)
    print('L1_YAW_ACTION', label, json.dumps(response, default=json_default), flush=True)
    if not all(checks.values()):
        raise RuntimeError('Yaw-aware fold state mismatch: ' + label)
    if len(result['actions']) > 7:
        raise RuntimeError('More than 7 public actions')
    return row


def action_chunk(rows, label):
    """Execute 2-4 ordered waypoints inside one public ActionChunk.

    The targets are the same arrays the single-step path would send; only the
    call boundary changes.  Per-row state is read after the chunk returns, so a
    row's ``ee``/``step``/``block_error_m`` describe the end of the chunk.
    """
    if not 2 <= len(rows) <= 4:
        raise ValueError('Chunk horizon must be within [2, 4]')
    targets = [np.r_[np.asarray(xyz, dtype=float), float(row_yaw)] for xyz, row_yaw, _, _ in rows]
    chunk = ActionChunk(actions=[
        CartesianAction(target_pose=target.astype(np.float32), gripper_command=int(command))
        for target, (_, _, command, _) in zip(targets, rows)])
    response = b.execute(chunk)
    control = b._env.control
    attached = control.attachlist != [None]
    checks = {'executed_horizon': response['executed_steps'] == len(rows),
              'not_done': response['done'] is False,
              'holding_consistent': bool(b._holding) == bool(attached),
              'attachment_count': int(attached) == int(b._holding)}
    ee = np.asarray(b._env.robots[0].get_cur_ee_pos()[0], dtype=float)
    step = int(b._step_count['n'])
    slot = getattr(control, 'active', None)
    chunk_index = len(result['chunks'])
    for index, ((xyz, row_yaw, command, row_label), target) in enumerate(zip(rows, targets)):
        row = {'label': row_label, 'target_pose': target.tolist(), 'command': int(command),
               'response': response, 'checks': checks, 'holding': bool(b._holding),
               'attached': bool(attached), 'ee': ee.tolist(), 'ee_scope': 'after_chunk',
               'step': step, 'chunk_label': label, 'chunk_index': chunk_index,
               'chunk_size': len(rows), 'row_in_chunk': index}
        if attached and slot is not None:
            row['block_error_m'] = float(np.linalg.norm(
                np.asarray(slot.block_target(), dtype=float) - slot.block.get_position().numpy()))
            row['max_single_anchor_gap_m'] = float(slot.max_single_anchor_gap_m)
        result['actions'].append(row)
    result['chunks'].append({'label': label, 'horizon': len(rows),
                             'labels': [r[3] for r in rows],
                             'targets': [t.tolist() for t in targets],
                             'response': response, 'checks': checks,
                             'ee_after_chunk': ee.tolist(), 'step': step})
    print('L1_YAW_CHUNK', label, json.dumps(response, default=json_default), flush=True)
    if not all(checks.values()):
        raise RuntimeError('Yaw-aware chunk state mismatch: ' + label)
    if len(result['actions']) > 7:
        raise RuntimeError('More than 7 public actions')


try:
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
            kwargs['bend_stiffness'] = 100.
            return original_cloth(*args, **kwargs)

        material_module.ClothPrim = bend_cloth

        def fixed_material(*args, **kwargs):
            kwargs['particle_friction_scale'] = 0.
            return original_material(*args, **kwargs)

        material_module.ParticleMaterial = fixed_material
        b = FoldPoseBackend(garment_usd=str(Path(__file__).with_name('square_cloth_40cm.usda')),
                            prepared_grasp=True, max_action_steps=30000)
        start_with_square(b, out, .0001)
        from episode_evidence import attach_evidence
        evidence = attach_evidence(b, out, __file__, code_files)
    finally:
        if material_module is not None and original_material is not None:
            material_module.ParticleMaterial = original_material
        if material_module is not None and original_cloth is not None:
            material_module.ClothPrim = original_cloth
        if restore_room is not None:
            restore_room()
    control = b._env.control
    robot = b._env.robots[0]
    slot = control.fold_slot
    if slot.label != 'left_sleeve':
        raise RuntimeError('Unexpected fold slot')
    robot.open()
    b._set_garment_world_positions(settled.astype(np.float32))
    b._clear_garment_velocities()
    if not np.allclose(b._garment_world_positions(), settled, atol=1e-5, rtol=0):
        raise RuntimeError('Initial state readback mismatch')
    b._settle(30)
    initial = snapshot('00_initial')
    with np.load(out / 'cloth_constructed.npz') as data:
        local_points = np.asarray(data['points'], dtype=float)
    if local_points.shape != (441, 3):
        raise ValueError('Unexpected constructed mesh')
    yaw_case = float(case['yaw_rad'])
    yaw_measured, fit_max, fit_p95 = measure_yaw(local_points, initial)
    yaw_delta = float(np.arctan2(np.sin(yaw_measured - yaw_case),
                                 np.cos(yaw_measured - yaw_case)))
    if abs(yaw_delta) > .02:
        raise RuntimeError('Measured yaw disagrees with initial-case yaw')
    yaw = yaw_measured
    result['fold_yaw'] = yaw
    result['fold_yaw_case'] = yaw_case
    result['fold_yaw_measured'] = yaw_measured
    result['fold_yaw_delta'] = yaw_delta
    result['initial_metrics'] = {
        'extent': np.ptp(initial, axis=0).tolist(),
        'z_p95': float(np.percentile(initial[:, 2], 95)),
        'rigid_fit_residual_max_m': fit_max,
        'rigid_fit_residual_p95_m': fit_p95}
    pick_index = int(slot.pick_index)
    pick = initial[pick_index].copy()
    pick_local = local_points[pick_index]
    fold_width = .2
    material_targets = local_arc(pick, yaw, np.array([1., 0., 0.]), fold_width,
                                 overhang=args.overhang)
    targets = np.asarray([grasp_to_ee(point, yaw) for point in material_targets])
    rotation = np.array([[np.cos(yaw), -np.sin(yaw), 0.],
                         [np.sin(yaw), np.cos(yaw), 0.],
                         [0., 0., 1.]])
    result['fold_definition'] = {
        'fold_line_axis': 'cloth-local y',
        'fold_direction_local': [1., 0., 0.],
        'fold_edge': 'left',
        'fold_yaw_rad': yaw,
        'fold_width_m': fold_width,
        'fold_overhang_m': float(args.overhang),
        'pick_index': pick_index,
        'pick_reference_local': pick_local.tolist(),
        'pick_reference_world': pick.tolist(),
        'fold_line_local_x': float(pick_local[0] + fold_width),
        'target_reference_local': [float(pick_local[0] + 2 * fold_width + args.overhang), 0., 0.],
        'target_reference_world': (pick + rotation @ np.array(
            [2 * fold_width + args.overhang, 0., 0.])).tolist()}
    result['material_fold_targets'] = material_targets.tolist()
    result['public_fold_targets'] = targets.tolist()
    approach_target = pick + np.array([0., 0., .15])
    result['approach_target'] = approach_target.tolist()
    action(approach_target, yaw, GripperCommand.OPEN, 'approach')
    snapshot('01_approach')
    action(grasp_to_ee(pick, yaw), yaw, GripperCommand.CLOSE, 'close')
    if control.active is not slot:
        raise RuntimeError('Expected left-edge slot')
    snapshot('02_close')
    grasp_pick = control.vertices()[pick_index].copy()
    if np.linalg.norm(grasp_pick - pick) > .01:
        raise RuntimeError('Grasp pick moved more than 10 mm before arc')
    material_targets = local_arc(grasp_pick, yaw, np.array([1., 0., 0.]), fold_width,
                                 overhang=args.overhang)
    targets = np.asarray([grasp_to_ee(point, yaw) for point in material_targets])
    result['grasp_pick_world'] = grasp_pick.tolist()
    result['material_fold_targets'] = material_targets.tolist()
    result['public_fold_targets'] = targets.tolist()
    arc_rows = [(target, yaw, GripperCommand.HOLD, label)
                for label, target in zip(('arc45', 'arc90', 'arc135', 'place'), targets)]
    if args.execution == 'single':
        arc_horizons = [1, 1, 1, 1]
        for target, row_yaw, command, label in arc_rows:
            action(target, row_yaw, command, label)
            snapshot('03_' + label)
    else:
        arc_horizons = [4]
        action_chunk(arc_rows, 'arc4')
        snapshot('03_place')
    result['call_horizons'] = [1, 1] + arc_horizons + [1]
    if sum(result['call_horizons']) != 7:
        raise RuntimeError('Representation horizon mismatch')
    from square_stable_hold import StableHold
    hold = StableHold(robot, b._env.world, slot, out)
    hold.begin()
    try:
        hold.run(60)
    finally:
        result['hold_summary'] = hold.save()
    hold_end = snapshot('03_hold_end')
    result['hold_end_metrics'] = fold_metrics_yaw(initial, hold_end, local_points,
                                                 pick_index, yaw, width=fold_width)
    ee, _ = robot.get_cur_ee_pos()
    ee = np.asarray(ee, dtype=float)
    held_error = float(np.linalg.norm(ee - targets[-1]))
    orientation_reached = bool(robot.reach(targets[-1], orientation_euler(yaw)))
    held_ok = (held_error < .01 and
               float(np.max(np.abs(b._to_numpy(robot._robot.get_joint_velocities())[:7]))) < .1 and
               orientation_reached and
               slot.max_single_anchor_gap_m <= .01)
    result['held_check'] = {'position_error_m': held_error,
                            'arm_speed_rad_s': float(np.max(np.abs(
                                b._to_numpy(robot._robot.get_joint_velocities())[:7]))),
                            'anchor_gap_max_m': float(slot.max_single_anchor_gap_m),
                            'orientation_reached': orientation_reached, 'accepted': bool(held_ok)}
    from a5_capture import release_window
    final = release_window(b, evidence, out, result, initial, pick_index, yaw,
                           lambda target: action(target, yaw, GripperCommand.OPEN, 'release_retreat'))
    np.savez_compressed(out / 'final.npz', vertices=final)
    metrics = fold_metrics_yaw(initial, final, local_points, pick_index, yaw,
                               width=fold_width)
    result['fold_metrics'] = metrics
    result['action_count'] = len(result['actions'])
    result['action_labels'] = [a['label'] for a in result['actions']]
    if result['action_count'] != 7:
        raise RuntimeError('Expected exactly 7 public actions')
    if result['action_count'] != sum(result['call_horizons']):
        raise RuntimeError('Representation/action count mismatch')
    if len(result['chunks']) != (0 if args.execution == 'single' else 1):
        raise RuntimeError('Unexpected chunk count')
    result['action_count'] = len(result['actions'])
    result['action_labels'] = [a['label'] for a in result['actions']]
    result['formal_12_action_budget_passed'] = result['action_count'] <= 12
    result['formal_day4_success'] = False
    result['fold_success_accepted'] = False
    if not held_ok:
        raise RuntimeError('Held pose/velocity gate failed; released and saved')
    if metrics['moving_half_crossed_fraction'] < .5:
        raise RuntimeError('Fold did not cross the fold line')
    if control.attachlist != [None] or b._holding:
        raise RuntimeError('Unexpected attachment after fold')
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
    if not cv2.imwrite(str(out / 'final.png'), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise RuntimeError('PNG write failed')
    result['final_image'] = str(out / 'final.png')
    result['passed'] = True
    print('L1_YAW_XFOLD_COMPLETED', flush=True)
except BaseException as exc:
    result['errors'].append(repr(exc))
    traceback.print_exc()
finally:
    try:
        if evidence is not None:
            try:
                result['evidence'] = evidence.finish(result)
            except Exception as exc:
                result['errors'].append('Evidence finalization: ' + repr(exc))
                result['passed'] = False
        from a5_capture import finish_metadata
        finish_metadata(out, result, case, args.execution)
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
