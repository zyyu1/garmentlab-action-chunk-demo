"""Recovery smoke: unfold an L2/L3 strip-fold initial state with 5 public actions.

Reads an initial-state directory produced by day4-square-initial-stripfold.py:
  - initial_geometry.npz: flat_settled (pre-fold) and final (folded state)
  - result.json: initial_case (yaw, strips) and strip_records (pick index/world)
Sets the cloth to the folded state, then runs:
  approach -> pick(CLOSE) -> lift -> spread_place -> release
using the prepared single-anchor edge slot.  The spread target is the recorded
pre-fold pick position.  Saves the recovered geometry, image and flatness
metrics.  Development only; no fold is executed here.
"""
import argparse
import hashlib
import importlib
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, '/root/autodl-tmp/garmentlab-action-chunk-demo')
from backends.garmentlab_backend import GarmentLabBackend, _import_garmentlab
from schemas.action import ActionChunk, CartesianAction, GripperCommand
from square_pose_backend import SquarePoseBackend
from square_pose_contract import grasp_to_ee
from square_start import start_with_square


class StripPoseBackend(SquarePoseBackend):
    def __init__(self, edges, *args, **kwargs):
        self._strip_edges = list(edges)
        super().__init__(*args, **kwargs)

    def _make_prepared_control(self, env):
        from strip_prepared_control import StripPreparedControl
        StripPreparedControl.output_directory = getattr(self, 'output_dir', None)
        return StripPreparedControl(env, self._strip_edges)


ap = argparse.ArgumentParser()
ap.add_argument('--initial-dir', required=True)
ap.add_argument('--allow-root', action='store_true')
args = ap.parse_args()
init_dir = Path(args.initial_dir)
init = json.loads((init_dir / 'result.json').read_text())
if not init.get('passed'):
    raise ValueError('Initial state did not pass: ' + str(init.get('errors')))
case = init['initial_case']
strips = case['strips']
edges = [s['edge'] for s in strips]
records = [r for r in init['strip_records'] if r['label'] == 'strip_start']
if len(records) != len(strips):
    raise ValueError('Strip record mismatch')
with np.load(init_dir / 'initial_geometry.npz') as data:
    flat = np.asarray(data['flat_settled'], dtype=float)
    folded = np.asarray(data['final'], dtype=float)
if flat.shape != (441, 3) or folded.shape != (441, 3):
    raise ValueError('Unexpected initial geometry')
out = Path('/root/autodl-tmp') / ('day4-strip-recovery-' +
                                  datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir()
result = {'probe_version': 'strip-recovery-smoke-v1', 'passed': False,
          'initial_dir': str(init_dir), 'initial_case': case,
          'actions': [], 'errors': [], 'records': []}
b = None


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
    print('RECOVERY_STEP', label, json.dumps(data, default=json_default), flush=True)


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
    print('RECOVERY_ACTION', label, json.dumps(response, default=json_default), flush=True)
    if not all(checks.values()):
        raise RuntimeError('Recovery action state mismatch: ' + label)
    return row


def rigid_residual(a, b):
    ca, cb = a[:, :2].mean(0), b[:, :2].mean(0)
    H = (a[:, :2] - ca).T @ (b[:, :2] - cb)
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T
    pred = (a[:, :2] - ca) @ R.T + cb
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
        def bend_cloth(*args, **kwargs):
            kwargs['bend_stiffness'] = 100.
            return original_cloth(*args, **kwargs)

        material_module.ClothPrim = bend_cloth

        def fixed_material(*args, **kwargs):
            kwargs['particle_friction_scale'] = 0.
            return original_material(*args, **kwargs)

        material_module.ParticleMaterial = fixed_material
        b = StripPoseBackend(edges, garment_usd=str(Path(__file__).with_name('square_cloth_40cm.usda')),
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
    robot.open()
    b._set_garment_world_positions(folded.astype(np.float32))
    b._clear_garment_velocities()
    readback = b._garment_world_positions().copy()
    if not np.allclose(readback, folded, atol=1e-5, rtol=0):
        raise RuntimeError('Folded state readback mismatch')
    b._settle(30)
    start = b._garment_world_positions().copy()
    record('state_loaded', {'initial_dir': str(init_dir),
                            'n_strips': len(strips), 'edges': edges,
                            'loaded_error_max_m': float(np.max(abs(start - folded)))})
    yaw = float(case['yaw_rad'])
    rec = records[0]  # recovery smoke unfolds the first strip only
    pick_index = int(rec['pick_index'])
    flat_pick = np.asarray(rec['pick_world'], dtype=float)
    current = start[pick_index].copy()
    approach = current + [0., 0., .12]
    pick_target = grasp_to_ee(current, yaw)
    lift_target = grasp_to_ee(current + [0., 0., .08], yaw)
    spread_target = grasp_to_ee(flat_pick + [0., 0., .03], yaw)
    record('recovery_targets', {'strip': rec['strip'], 'edge': rec['edge'],
                                'width_m': rec['width_m'], 'pick_index': pick_index,
                                'folded_pick': current.tolist(),
                                'flat_pick': flat_pick.tolist(),
                                'approach': approach.tolist(),
                                'pick': pick_target.tolist(),
                                'lift': lift_target.tolist(),
                                'spread': spread_target.tolist()})
    action(approach, yaw, GripperCommand.OPEN, 'approach')
    action(pick_target, yaw, GripperCommand.CLOSE, 'pick')
    action(lift_target, yaw, GripperCommand.HOLD, 'lift')
    action(spread_target, yaw, GripperCommand.HOLD, 'spread_place')
    action(spread_target, yaw, GripperCommand.OPEN, 'release')
    b._settle(240)
    recovered = b._garment_world_positions().copy()
    np.savez_compressed(out / 'recovered.npz', vertices=recovered)
    np.savez_compressed(out / 'flat_reference.npz', vertices=flat)
    res_flat = rigid_residual(flat, recovered)
    res_start = rigid_residual(flat, start)
    extent = np.ptp(recovered, axis=0)
    result['recovery_metrics'] = {
        'rigid_residual_vs_flat_max_m': float(res_flat.max()),
        'rigid_residual_vs_flat_p95_m': float(np.percentile(res_flat, 95)),
        'rigid_residual_start_max_m': float(res_start.max()),
        'pick_index': pick_index,
        'pick_displacement_from_flat_m': float(np.linalg.norm(recovered[pick_index] - flat_pick)),
        'recovered_extent': extent.tolist(),
        'recovered_z_p95': float(np.percentile(recovered[:, 2], 95)),
        'action_count': len(result['actions'])}
    if not np.isfinite(recovered).all() or np.max(abs(recovered)) > 2:
        raise RuntimeError('Invalid recovered geometry')
    if control.attachlist != [None] or b._holding:
        raise RuntimeError('Unexpected attachment after recovery')
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
    if not cv2.imwrite(str(out / 'recovered.png'), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise RuntimeError('PNG write failed')
    result['recovered_image'] = str(out / 'recovered.png')
    result['passed'] = True
    print('STRIP_RECOVERY_COMPLETED', flush=True)
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
