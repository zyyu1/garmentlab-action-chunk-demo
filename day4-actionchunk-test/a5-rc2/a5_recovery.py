"""Recovery + fold episode for an L2/L3 strip-fold initial state.

5 recovery actions:
  rec_approach -> rec_pick(CLOSE) -> rec_lift -> rec_spread -> rec_release
then 7 fold actions on the recovered cloth, using the cloth-local axis:
  fold_approach -> fold_close -> fold_arc45 -> fold_arc90 -> fold_arc135 ->
  fold_place -> fold_release
Total 12 public actions.  The fold is a half fold (width 0.20) in the
cloth's local frame (initial-case yaw plus the rigid yaw measured on the
recovered cloth).  Default is the left half; `--fold-edge right` mirrors the
arc and uses the otherwise unused right slot.  L3 reuses the left slot for
both recovery and fold via enable_regrasp, so the right slot is the fallback
when that re-grasp destabilizes the fold; L2 recovers the bottom slot and
folds with the unused left (or right) slot.

``--execution`` selects the waypoint representation: ``single`` (default) sends
one public action per waypoint, ``arc4`` sends fold_arc45/fold_arc90/
fold_arc135/fold_place as one H=4 chunk.  The fold targets are computed once,
before fold_approach, so both representations send identical targets.
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
from scipy.spatial.transform import Rotation

sys.path.insert(0, '/root/autodl-tmp/garmentlab-action-chunk-demo')
from backends.garmentlab_backend import GarmentLabBackend, _import_garmentlab
from schemas.action import ActionChunk, CartesianAction, GripperCommand
from rc2_live_backend import LiveSquarePoseBackend as SquarePoseBackend
from square_pose_contract import grasp_to_ee, orientation_euler
from square_start import start_with_square


class StripPoseBackend(SquarePoseBackend):
    def __init__(self, edges, *args, **kwargs):
        self._strip_edges = list(edges)
        super().__init__(*args, **kwargs)

    def _make_prepared_control(self, env):
        from strip_prepared_control import StripPreparedControl
        StripPreparedControl.output_directory = getattr(self, 'output_dir', None)
        return StripPreparedControl(env, self._strip_edges)


def local_arc(pick, yaw, lateral_local, width):
    lateral = np.asarray(lateral_local, dtype=float)
    R = Rotation.from_euler('z', float(yaw)).as_matrix()
    out = []
    for angle in np.arange(1, 5) * np.pi / 4:
        local = lateral * (width - width * np.cos(angle))
        local[2] = .02 * angle / np.pi + width * np.sin(angle)
        out.append(np.asarray(pick, dtype=float) + R @ local)
    return np.asarray(out)


ap = argparse.ArgumentParser()
ap.add_argument('--initial-dir', required=True)
ap.add_argument('--fold-edge', choices=('right',), default='right')
ap.add_argument('--execution', choices=('single', 'arc4'), default='single',
                help='Waypoint representation: one public action per waypoint '
                     '(frozen default), or one H=4 chunk covering '
                     'fold_arc45/fold_arc90/fold_arc135/fold_place. The fold '
                     'targets are computed once, before fold_approach, so both '
                     'representations send identical targets.')
ap.add_argument('--allow-root', action='store_true')
ap.add_argument('--split', choices=['dev','formal'], required=True)
args = ap.parse_args()
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
authorize_initial(init_dir, args.split, args.execution, 'recovery')
strips = case['strips']
strip_records = [r for r in init['strip_records'] if r['label'] == 'strip_start']
if len(strip_records) != len(strips):
    raise ValueError('Strip record mismatch')
with np.load(init_dir / 'initial_geometry.npz') as data:
    flat = np.asarray(data['flat_settled'], dtype=float)
    folded = np.asarray(data['final'], dtype=float)
if flat.shape != (441, 3) or folded.shape != (441, 3):
    raise ValueError('Unexpected initial geometry')
fold_edges = ['left'] if args.fold_edge == 'left' else ['right']
edges = list(dict.fromkeys([s['edge'] for s in strips] + fold_edges))
out = Path('/root/autodl-tmp') / ('day4-a5-rc2-recovery-' +
                                  datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result = {'probe_version': 'recovery-fold-episode-v1', 'passed': False,
          'initial_dir': str(init_dir), 'initial_case': case,
          'fold_edge': args.fold_edge, 'execution_mode': args.execution,
          'control_edges': edges, 'call_horizons': [], 'chunks': [],
          'code_files': code_files,
          'actions': [], 'errors': [], 'records': []}
b = None
evidence = None


def json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f'Unsupported JSON type: {type(value).__name__}')


def record(label, data):
    data = dict(data)
    data['label'] = label
    result['records'].append(data)
    print('EPISODE_STEP', label, json.dumps(data, default=json_default), flush=True)


def action(xyz, yaw, command, label, limit):
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
    print('EPISODE_ACTION', label, json.dumps(response, default=json_default), flush=True)
    if not all(checks.values()):
        raise RuntimeError('Episode action state mismatch: ' + label)
    if len(result['actions']) > limit:
        raise RuntimeError('Action budget exceeded at ' + label)
    return row


def action_chunk(rows, label, limit):
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
    print('EPISODE_CHUNK', label, json.dumps(response, default=json_default), flush=True)
    if not all(checks.values()):
        raise RuntimeError('Episode chunk state mismatch: ' + label)
    if len(result['actions']) > limit:
        raise RuntimeError('Action budget exceeded at ' + label)


def rigid_fit(a, b):
    ca, cb = a[:, :2].mean(0), b[:, :2].mean(0)
    H = (a[:, :2] - ca).T @ (b[:, :2] - cb)
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T
    return R, cb - R @ ca


def rigid_residual(a, b):
    R, t = rigid_fit(a, b)
    pred = a[:, :2] @ R.T + t
    return np.linalg.norm(b[:, :2] - pred, axis=1)


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
        def bend_cloth(*a, **k):
            k['bend_stiffness'] = 100.
            return original_cloth(*a, **k)

        material_module.ClothPrim = bend_cloth

        def fixed_material(*a, **k):
            k['particle_friction_scale'] = 0.
            return original_material(*a, **k)

        material_module.ParticleMaterial = fixed_material
        b = StripPoseBackend(edges, garment_usd=str(Path(__file__).with_name('square_cloth_40cm.usda')),
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
    robot.open()
    b._set_garment_world_positions(folded.astype(np.float32))
    b._clear_garment_velocities()
    if not np.allclose(b._garment_world_positions(), folded, atol=1e-5, rtol=0):
        raise RuntimeError('Folded state readback mismatch')
    b._settle(30)
    yaw = float(case['yaw_rad'])
    # ---- recovery (5 actions) ----
    rec = strip_records[0]
    rec_slot = control.slots[{'right': 0, 'left': 1, 'bottom': 2, 'top': 3}[rec['edge']]]
    rec_pick_index = int(rec['pick_index'])
    flat_pick = np.asarray(rec['pick_world'], dtype=float)
    current = b._garment_world_positions()[rec_pick_index].copy()
    record('recovery_targets', {'edge': rec['edge'], 'width_m': rec['width_m'],
                                'pick_index': rec_pick_index,
                                'folded_pick': current.tolist(),
                                'flat_pick': flat_pick.tolist()})
    action(current + [0., 0., .12], yaw, GripperCommand.OPEN, 'rec_approach', 12)
    action(grasp_to_ee(current, yaw), yaw, GripperCommand.CLOSE, 'rec_pick', 12)
    action(grasp_to_ee(current + [0., 0., .08], yaw), yaw, GripperCommand.HOLD, 'rec_lift', 12)
    action(grasp_to_ee(flat_pick + [0., 0., .03], yaw), yaw, GripperCommand.HOLD, 'rec_spread', 12)
    action(grasp_to_ee(flat_pick + [0., 0., .03], yaw), yaw, GripperCommand.OPEN, 'rec_release', 12)
    b._settle(240)
    recovered = b._garment_world_positions().copy()
    res_flat = rigid_residual(flat, recovered)
    R_rec, _ = rigid_fit(flat[:, :2], recovered[:, :2])
    fold_yaw = float(yaw + np.arctan2(R_rec[1, 0], R_rec[0, 0]))
    result['fold_yaw'] = fold_yaw
    result['recovery_metrics'] = {
        'rigid_residual_vs_flat_max_m': float(res_flat.max()),
        'rigid_residual_vs_flat_p95_m': float(np.percentile(res_flat, 95)),
        'extent': np.ptp(recovered, axis=0).tolist(),
        'z_p95': float(np.percentile(recovered[:, 2], 95))}
    np.savez_compressed(out / 'recovered.npz', vertices=recovered)
    # ---- fold (7 actions, cloth-local half) ----
    fold_slot = control.slots[{'right': 0, 'left': 1}[args.fold_edge]]
    if control.active is rec_slot and args.fold_edge == 'left':
        # Preserve the validated left-fold path: L3 reuses its own left slot.
        # Right-fold fallback leaves the recovery slot used, so CLOSE selects right.
        control.enable_regrasp()
    fold_pick_index = int(fold_slot.pick_index)
    pick = b._garment_world_positions()[fold_pick_index].copy()
    fold_width = .2
    lateral_local = np.array([1. if args.fold_edge == 'left' else -1., 0., 0.])
    material_targets = local_arc(pick, fold_yaw, lateral_local, fold_width)
    ee_targets = [grasp_to_ee(point, fold_yaw) for point in material_targets]
    record('fold_targets', {'edge': args.fold_edge, 'pick_index': fold_pick_index,
                            'pick_world': pick.tolist(),
                            'fold_yaw': fold_yaw,
                            'width_m': fold_width,
                            'material_targets': material_targets.tolist(),
                            'ee_targets': [np.asarray(t, dtype=float).tolist() for t in ee_targets]})
    action(pick + [0., 0., .15], fold_yaw, GripperCommand.OPEN, 'fold_approach', 12)
    action(grasp_to_ee(pick, fold_yaw), fold_yaw, GripperCommand.CLOSE, 'fold_close', 12)
    if control.active is not fold_slot:
        raise RuntimeError('Expected ' + args.fold_edge + ' slot for fold')
    fold_rows = [(target, fold_yaw, GripperCommand.HOLD, 'fold_' + label)
                 for label, target in zip(('arc45', 'arc90', 'arc135', 'place'), ee_targets)]
    if args.execution == 'single':
        fold_horizons = [1, 1, 1, 1]
        for target, row_yaw, command, row_label in fold_rows:
            action(target, row_yaw, command, row_label, 12)
    else:
        fold_horizons = [4]
        action_chunk(fold_rows, 'fold_arc4', 12)
    result['call_horizons'] = [1] * 7 + fold_horizons + [1]
    if sum(result['call_horizons']) != 12:
        raise RuntimeError('Representation horizon mismatch')
    from square_stable_hold import StableHold
    hold_dir = out / 'fold_hold'
    hold_dir.mkdir()
    hold = StableHold(robot, b._env.world, fold_slot, hold_dir)
    hold.begin()
    try:
        # Fixed place hold for both representations, before the final OPEN.
        # Record the last two seconds of cloth motion, without changing control.
        hold_motion = []
        for _ in range(180):
            hold.tick()
            hold_motion.append(b._garment_world_positions().copy())
        fold_slot.block.set_velocities(np.zeros(6))
        np.savez_compressed(out / 'pre_release_hold.npz', vertices=hold_motion,
                            dt_s=float(b._env.world.get_physics_dt()))
    finally:
        result['fold_hold'] = hold.save()
    ee, _ = robot.get_cur_ee_pos()
    ee = np.asarray(ee, dtype=float)
    held_error = float(np.linalg.norm(ee - ee_targets[-1]))
    orientation_reached = bool(robot.reach(ee_targets[-1], orientation_euler(fold_yaw)))
    held_ok = (held_error < .03 and
               float(np.max(np.abs(b._to_numpy(robot._robot.get_joint_velocities())[:7]))) < .1 and
               orientation_reached and
               fold_slot.max_single_anchor_gap_m <= .01)
    result['fold_held_check'] = {
        'position_error_m': held_error,
        'arm_speed_rad_s': float(np.max(np.abs(
            b._to_numpy(robot._robot.get_joint_velocities())[:7]))),
        'anchor_gap_max_m': float(fold_slot.max_single_anchor_gap_m),
        'orientation_reached': orientation_reached, 'accepted': bool(held_ok)}
    from a5_capture import release_window
    final = release_window(b, evidence, out, result, recovered, fold_pick_index, fold_yaw,
                           lambda target: action(target, fold_yaw, GripperCommand.OPEN, 'release_retreat', 12))
    np.savez_compressed(out / 'final.npz', vertices=final)
    R = Rotation.from_euler('z', fold_yaw).as_matrix()
    lateral = R @ lateral_local
    with np.load(out / 'cloth_constructed.npz') as data:
        local_points = np.asarray(data['points'], dtype=float)
    fold_local = local_points[fold_pick_index]
    if args.fold_edge == 'left':
        moving = local_points[:, 0] < fold_local[0] + fold_width
    else:
        moving = local_points[:, 0] > fold_local[0] - fold_width
    crossed = float((((final[moving] - pick) @ lateral) > fold_width).mean())
    result['fold_metrics'] = {
        'moving_count': int(moving.sum()),
        'crossed_fraction': crossed,
        'extent': np.ptp(final, axis=0).tolist(),
        'z_p95': float(np.percentile(final[:, 2], 95)),
        'pick_index': fold_pick_index}
    result['action_count'] = len(result['actions'])
    result['action_labels'] = [a['label'] for a in result['actions']]
    if result['action_count'] != 12:
        raise RuntimeError('Expected exactly 12 public actions')
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
        raise RuntimeError('Fold held gate failed; released and saved')
    if crossed < .5:
        raise RuntimeError('Fold did not cross the fold line')
    if control.attachlist != [None] or b._holding:
        raise RuntimeError('Unexpected attachment after episode')
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
    print('RECOVERY_FOLD_EPISODE_COMPLETED', flush=True)
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
