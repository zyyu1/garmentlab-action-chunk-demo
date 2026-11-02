"""Day4 step 5: prepared square Backend yaw/hold/re-grasp/reset test.

Development integration only.  Each cycle resets the scene in one Backend
lifetime, runs a rollout, saves per-cycle state and re-parses every save.
"""
import argparse
import json
import sys
import traceback
from pathlib import Path
from datetime import datetime

import numpy as np

sys.path.insert(0, '/root/autodl-tmp/garmentlab-action-chunk-demo')
sys.path.insert(0, '/root/autodl-tmp')
from backends.garmentlab_backend import _import_garmentlab
from backends.prepared_square_backend import PreparedSquareBackend
from schemas.action import ActionChunk, CartesianAction, GripperCommand
from square_start import start_with_square
from square_pose_contract import grasp_to_ee, orientation_matrix, orientation_euler
from square_edge_fold_geometry import edge_plan, square_edge_targets
from l1_fold_geometry import fold_metrics
from room_collision_control import install_room_collision_control
from scipy.spatial.transform import Rotation

out = Path('/root/autodl-tmp') / ('day4-prepared-square-backend-reset-' +
                                  datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result = {'probe_version': 'prepared-square-backend-reset-v1', 'passed': False,
          'formal_day4_success': False, 'fold_success_accepted': False,
          'scope': 'Step5 integration test: yaw, stable hold, same-episode re-grasp, '
                   '10 reset/rollout state isolation; no formal fold acceptance',
          'cycles': [], 'errors': []}
b = None
frame = 0


def json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f'Unsupported JSON type: {type(value).__name__}')


def to_np(value):
    if hasattr(value, 'detach'):
        value = value.detach().cpu().numpy()
    return np.asarray(value, dtype=float).reshape(-1)


def capture_png(path):
    import cv2
    from omni.isaac.core.utils.rotations import euler_angles_to_quat
    b._env.camera.camera.set_world_pose(
        position=np.array([0., -.50, 2.80]),
        orientation=euler_angles_to_quat(np.array([0., 90., 90.]), degrees=True))
    image = b._env.camera.camera.get_rgb()
    if image is None:
        raise RuntimeError('Camera returned no image')
    image = np.asarray(image)
    rgb = image[:, :, :3]
    if np.issubdtype(rgb.dtype, np.floating):
        rgb = np.clip(rgb * (255 if rgb.max() <= 1 else 1), 0, 255)
    rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise RuntimeError('PNG save failed')
    back = cv2.imread(str(path))
    if back is None or back.shape[:2] != (480, 640):
        raise RuntimeError('Saved PNG cannot be decoded')
    return back.shape[:2]


def action(cycle, xyz, yaw, cmd, label):
    global frame
    target = np.r_[np.asarray(xyz, dtype=float), float(yaw)]
    chunk = ActionChunk(actions=[CartesianAction(target_pose=target.astype(np.float32),
                                                 gripper_command=int(cmd))])
    response = b.execute(chunk)
    c = b._env.control
    c.assert_exclusive()
    frame += 1
    row = {'label': label, 'target_pose': target.tolist(), 'command': int(cmd),
           'response': response, 'holding': bool(b._holding),
           'gripper_state': int(b._gripper_state),
           'status': c.status(), 'step': int(b._step_count['n'])}
    cycle['actions'].append(row)
    print('STEP5_ACTION', label, json.dumps(response, default=json_default), flush=True)
    return response


def verify_reset(cycle_dir):
    c = b._env.control
    status = c.status()
    vertices = c.vertices()
    ee, q = b._env.robots[0].get_cur_ee_pos()
    joints = to_np(b._env.robots[0]._robot.get_joint_positions())
    velocities = to_np(b._env.robots[0]._robot.get_joint_velocities())
    c.assert_exclusive()
    slot = c.fold_slot
    paths = [s.block.attachment_path for s in c.slots] + [s.block.block_path for s in c.slots]
    stage = b._env.world.stage
    extent = np.ptp(vertices, axis=0)
    checks = {
        'all_slots_released': all((not s['used']) and (not s['holding']) and (not s['enabled'])
                                  for s in status),
        'not_holding': not c.holding and not b._holding,
        'not_enabled': not c.attachment_enabled(),
        'constraints_exist': all(s['constraint_exists'] for s in status),
        'paths_distinct_and_valid': len(set(paths)) == 6 and all(
            stage.GetPrimAtPath(p).IsValid() for p in paths),
        'fold_slot_label': slot.label,
        'cloth_shape': vertices.shape,
        'cloth_xy_extent': extent[:2].tolist(),
        'cloth_center_xy': vertices[:, :2].mean(axis=0).tolist(),
        'cloth_z_p95': float(np.percentile(vertices[:, 2], 95)),
        'robot_joint_velocity_max': float(np.max(np.abs(velocities[:7]))),
        'finite': bool(np.isfinite(vertices).all() and np.isfinite(ee).all() and
                       np.isfinite(q).all() and np.isfinite(joints).all()),
    }
    if not np.allclose(extent[:2], [.4, .4], atol=.03):
        raise RuntimeError('Reset cloth xy extent mismatch: ' + str(extent[:2]))
    if checks['cloth_z_p95'] > .03:
        raise RuntimeError('Reset cloth not flat: z_p95=' + str(checks['cloth_z_p95']))
    (cycle_dir / 'reset.json').write_text(json.dumps(
        {'checks': checks, 'status': status, 'ee': np.asarray(ee).tolist(),
         'quaternion_wxyz': np.asarray(q).tolist()}, indent=2, default=json_default),
        encoding='utf-8')
    json.loads((cycle_dir / 'reset.json').read_text(encoding='utf-8'))
    np.savez_compressed(cycle_dir / 'reset_state.npz', vertices=vertices,
                        ee=np.asarray(ee), quaternion=np.asarray(q), joints=joints)
    with np.load(cycle_dir / 'reset_state.npz') as saved:
        if saved['vertices'].shape != vertices.shape or not np.isfinite(saved['vertices']).all():
            raise RuntimeError('Reset npz save/read mismatch')
    checks['png_shape'] = capture_png(cycle_dir / 'reset.png')
    return checks


def short_rollout(cycle, do_regrasp):
    c = b._env.control
    initial = c.vertices()
    pick = initial[c.fold_slot.pick_index].copy()
    grasp = grasp_to_ee(pick, 0.)
    action(cycle, pick + [0, 0, .15], .3, GripperCommand.OPEN, 'approach_yaw')
    ee, q = b._env.robots[0].get_cur_ee_pos()
    actual = Rotation.from_quat(np.asarray(q, dtype=float)[[1, 2, 3, 0]]).as_matrix()
    desired = orientation_matrix(.3)
    yaw_error = float(Rotation.from_matrix(desired @ actual.T).magnitude())
    if yaw_error > .05:
        raise RuntimeError(f'Yaw command not reached: {yaw_error}')
    cycle['yaw_error_rad'] = yaw_error
    action(cycle, grasp, 0., GripperCommand.CLOSE, 'close')
    lift = pick + [0, 0, .10]
    action(cycle, lift, 0., GripperCommand.HOLD, 'lift')
    action(cycle, lift, 0., GripperCommand.HOLD, 'hold')
    ee, q = b._env.robots[0].get_cur_ee_pos()
    cycle['held_check'] = {
        'position_error_m': float(np.linalg.norm(np.asarray(ee) - lift)),
        'arm_speed_rad_s': float(np.max(np.abs(to_np(b._env.robots[0]._robot.get_joint_velocities())[:7]))),
        'orientation_reached': bool(b._env.robots[0].reach(lift, orientation_euler(0.))),
        'anchor_gap_max_m': float(c.fold_slot.max_single_anchor_gap_m),
        'hold_summary': b.last_hold_summary,
    }
    action(cycle, np.asarray(ee), 0., GripperCommand.OPEN, 'release')
    action(cycle, np.asarray(ee) + [0, 0, .15], 0., GripperCommand.OPEN, 'retreat')
    if do_regrasp:
        live = c.vertices()
        pick2 = live[c.fold_slot.pick_index].copy()
        grasp2 = grasp_to_ee(pick2, 0.)
        action(cycle, pick2 + [0, 0, .15], 0., GripperCommand.OPEN, 'regrasp_approach')
        action(cycle, grasp2, 0., GripperCommand.CLOSE, 'regrasp_close')
        if c.active is not c.fold_slot:
            raise RuntimeError('Re-grasp did not select the fold slot')
        action(cycle, pick2 + [0, 0, .08], 0., GripperCommand.HOLD, 'regrasp_lift')
        ee, q = b._env.robots[0].get_cur_ee_pos()
        action(cycle, np.asarray(ee), 0., GripperCommand.OPEN, 'regrasp_release')
        # The next reset restores the scene; an extra retreat after the
        # re-grasp is not part of the same-episode re-grasp criterion.
        cycle['regrasp'] = {
            'reuse_count': int(c.fold_slot.reuse_count),
            'activation_record': c.fold_slot.activation_record,
            'anchor_gap_max_m': float(c.fold_slot.max_single_anchor_gap_m),
        }
    cycle['final_status'] = c.status()


def fold_rollout(cycle):
    c = b._env.control
    initial = c.vertices()
    plan = edge_plan(initial, c.fold_slot.pick_index)
    pick = initial[c.fold_slot.pick_index].copy()
    grasp = grasp_to_ee(pick, 0.)
    material = square_edge_targets(pick, plan['fold_line_x'])
    targets = [grasp_to_ee(point, 0.) for point in material]
    action(cycle, pick + [0, 0, .15], 0., GripperCommand.OPEN, 'approach')
    action(cycle, grasp, 0., GripperCommand.CLOSE, 'close')
    for label, target in zip(('arc45', 'arc90', 'arc135', 'place'), targets):
        action(cycle, target, 0., GripperCommand.HOLD, label)
    action(cycle, targets[-1], 0., GripperCommand.HOLD, 'hold')
    ee, q = b._env.robots[0].get_cur_ee_pos()
    cycle['held_check'] = {
        'position_error_m': float(np.linalg.norm(np.asarray(ee) - targets[-1])),
        'arm_speed_rad_s': float(np.max(np.abs(to_np(b._env.robots[0]._robot.get_joint_velocities())[:7]))),
        'orientation_reached': bool(b._env.robots[0].reach(targets[-1], orientation_euler(0.))),
        'anchor_gap_max_m': float(c.fold_slot.max_single_anchor_gap_m),
        'hold_summary': b.last_hold_summary,
    }
    action(cycle, np.asarray(ee), 0., GripperCommand.OPEN, 'release')
    action(cycle, np.asarray(ee) + [0, 0, .15], 0., GripperCommand.OPEN, 'retreat')
    for _ in range(180):
        b._env.step()
    final = c.vertices()
    cycle['fold_metrics'] = fold_metrics(initial, final, plan)
    cycle['final_status'] = c.status()
    np.savez_compressed(cycle['cycle_dir'] / 'fold_final.npz', vertices=final)
    capture_png(cycle['cycle_dir'] / 'final.png')


def save_cycle(cycle):
    path = cycle['cycle_dir'] / 'cycle.json'
    payload = {key: value for key, value in cycle.items() if key != 'cycle_dir'}
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding='utf-8')
    loaded = json.loads(path.read_text(encoding='utf-8'))
    if loaded['cycle'] != cycle['cycle'] or 'actions' not in loaded:
        raise RuntimeError('Cycle JSON save/read mismatch')
    cycle['json_save_ok'] = True
    return path


try:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cycles', type=int, default=10)
    ap.add_argument('--fold-cycles', type=int, default=1)
    ap.add_argument('--regrasp-cycle', type=int, default=2)
    ap.add_argument('--seed', type=int, default=5100)
    ap.add_argument('--allow-root', action='store_true')
    args = ap.parse_args()
    if args.cycles < 1:
        raise ValueError('cycles must be positive')
    if args.fold_cycles > args.cycles:
        raise ValueError('fold-cycles must not exceed cycles')
    result['settings'] = vars(args)
    _import_garmentlab()
    b = PreparedSquareBackend(
        garment_usd=str(Path(__file__).with_name('square_cloth_40cm.usda')),
        output_dir=str(out / 'startup'), settle_steps=120, hold_steps=60,
        auto_regrasp=True, enable_contact_reporting=False)
    restore_room = install_room_collision_control(out)
    try:
        capture_mass = start_with_square(b, out, .0001)
    finally:
        restore_room()
    b.set_output_dir(out / 'startup')
    result['slots_precreated'] = [{'label': s.label, 'pick_index': s.pick_index,
                                   'block': s.block.block_path,
                                   'constraint': s.block.attachment_path}
                                  for s in b._env.control.slots]
    for k in range(1, args.cycles + 1):
        cycle_dir = out / ('cycle_%02d' % k)
        cycle_dir.mkdir()
        b.set_output_dir(cycle_dir)
        cycle = {'cycle': k, 'cycle_dir': cycle_dir, 'actions': [],
                 'reset_seed': args.seed + k}
        print('STEP5_CYCLE_START', k, flush=True)
        b.reset(seed=args.seed + k, apply_difficulty=False)
        cycle['reset_checks'] = verify_reset(cycle_dir)
        if k <= args.fold_cycles:
            cycle['rollout'] = 'fold'
            fold_rollout(cycle)
        else:
            cycle['rollout'] = 'short'
            short_rollout(cycle, do_regrasp=(k == args.regrasp_cycle))
        save_cycle(cycle)
        result['cycles'].append({key: value for key, value in cycle.items() if key != 'cycle_dir'})
        print('STEP5_CYCLE_DONE', k, 'rollout=' + cycle['rollout'], flush=True)
    capture_mass('after_reset_cycles')
    result['passed'] = True
    print('STEP5_RESET_TEST_PASSED', flush=True)
except BaseException as exc:
    result['errors'].append(repr(exc))
    traceback.print_exc()
finally:
    result['cycle_count'] = len(result['cycles'])
    (out / 'result.json').write_text(json.dumps(result, indent=2, default=json_default),
                                     encoding='utf-8')
    print('STEP5_RESULT_FILE', out / 'result.json', flush=True)
    print('STEP5_DOWNLOAD_DIR', out, flush=True)
    if b is not None:
        try:
            b.stop()
        except Exception as exc:
            print('STEP5_STOP_ERROR', repr(exc), flush=True)
