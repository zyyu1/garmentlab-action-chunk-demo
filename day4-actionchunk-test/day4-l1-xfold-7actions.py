"""L1 x-axis half-fold with exactly 7 public actions.

Compressed from the validated 9-action x-fold:
  approach -> close -> arc45 -> arc90 -> arc135 -> place -> release
The separate descend action is absorbed by close (Control.grasp drives to
the grasp target before closing), and the post-release retreat is dropped.
The physical approach/descend/close trajectory is identical to the 9-action
version; the episode settles after release.

Development revalidation only; not a formal success.
"""
import hashlib
import importlib
import inspect
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
from square_edge_fold_geometry import edge_vertex, edge_plan, square_edge_targets
from l1_fold_geometry import fold_metrics


class FoldPoseBackend(SquarePoseBackend):
    def _make_prepared_control(self, env):
        from square_edge_control import SquareEdgeProxyGroundControl
        SquareEdgeProxyGroundControl.output_directory = getattr(self, 'output_dir', None)
        return SquareEdgeProxyGroundControl(env)


out = Path('/root/autodl-tmp') / ('day4-l1-xfold-7actions-' +
                                  datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result = {'probe_version': 'l1-xfold-7actions-v1', 'passed': False,
          'formal_day4_success': False,
          'scope': 'L1 x-fold revalidation with 7 public actions; no formal acceptance',
          'actions': [], 'errors': [], 'fold_success_accepted': False}
b = None


def json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f'Unsupported JSON type: {type(value).__name__}')


def snapshot(label):
    vertices = b._garment_world_positions().copy()
    np.savez_compressed(out / (label + '.npz'), vertices=vertices)
    return vertices


def action(xyz, command, label):
    target = np.r_[np.asarray(xyz, dtype=float), 0.]
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
    print('XFOLD7_ACTION', label, json.dumps(response, default=json_default), flush=True)
    if not all(checks.values()):
        raise RuntimeError('7-action fold state mismatch: ' + label)
    if len(result['actions']) > 7:
        raise RuntimeError('More than 7 public actions')
    return row


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
    b._settle(120)
    initial = snapshot('00_initial')
    pick_index = edge_vertex(initial)
    plan = edge_plan(initial, pick_index)
    np.savez_compressed(out / 'fold_definition.npz', initial_vertices=initial, **plan)
    pick = control.vertices()[slot.pick_index].copy()
    grasp_target = grasp_to_ee(pick, 0.)
    result['fold_definition'] = {k: (v.tolist() if hasattr(v, 'tolist') else v)
                                 for k, v in plan.items() if k != 'source_mask'}
    result['grasp_target'] = grasp_target.tolist()
    approach_target = pick + np.array([0., 0., .15])
    result['approach_target'] = approach_target.tolist()
    action(approach_target, GripperCommand.OPEN, 'approach')
    snapshot('01_approach')
    action(grasp_target, GripperCommand.CLOSE, 'close')
    if control.active is not slot:
        raise RuntimeError('Expected left-edge slot')
    snapshot('02_close')
    grasp_vertices = control.vertices().copy()
    material_targets = square_edge_targets(grasp_vertices[slot.pick_index], plan['fold_line_x'])
    targets = np.asarray([grasp_to_ee(point, 0.) for point in material_targets])
    result['material_fold_targets'] = material_targets.tolist()
    result['public_fold_targets'] = targets.tolist()
    for label, target in zip(('arc45', 'arc90', 'arc135', 'place'), targets):
        action(target, GripperCommand.HOLD, label)
        snapshot('03_' + label)
    from square_stable_hold import StableHold
    hold = StableHold(robot, b._env.world, slot, out)
    hold.begin()
    try:
        hold.run(60)
    finally:
        result['hold_summary'] = hold.save()
    ee, _ = robot.get_cur_ee_pos()
    ee = np.asarray(ee, dtype=float)
    held_error = float(np.linalg.norm(ee - targets[-1]))
    held_ok = (held_error < .01 and
               float(np.max(np.abs(b._to_numpy(robot._robot.get_joint_velocities())[:7]))) < .1 and
               bool(robot.reach(targets[-1], orientation_euler(0.))) and
               slot.max_single_anchor_gap_m <= .01)
    result['held_check'] = {'position_error_m': held_error,
                            'arm_speed_rad_s': float(np.max(np.abs(
                                b._to_numpy(robot._robot.get_joint_velocities())[:7]))),
                            'anchor_gap_max_m': float(slot.max_single_anchor_gap_m),
                            'accepted': bool(held_ok)}
    action(ee, GripperCommand.OPEN, 'release')
    released = snapshot('04_released')
    for _ in range(30):
        slot._tick(ee, orientation_euler(0.), follow=False)
    snapshot('05_release_stationary')
    b._settle(180)
    final = snapshot('06_final_3s')
    metrics = fold_metrics(initial, final, plan)
    result['fold_metrics'] = metrics
    result['action_count'] = len(result['actions'])
    result['action_labels'] = [a['label'] for a in result['actions']]
    if result['action_count'] != 7:
        raise RuntimeError('Expected exactly 7 public actions')
    if not held_ok:
        raise RuntimeError('Held pose/velocity gate failed; released and saved')
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
    print('L1_XFOLD_7ACTIONS_COMPLETED', flush=True)
except BaseException as exc:
    result['errors'].append(repr(exc))
    traceback.print_exc()
finally:
    try:
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
