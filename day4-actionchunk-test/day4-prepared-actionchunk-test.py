"""Public ActionChunk integration: H=4 free descent, H=1 grasp/lift/release.

No reset, repeated-grasp, yaw, folding-quality, or lifecycle validation.
Derived from the user-supplied successful staged test; backend is unchanged.
"""
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
import hashlib
import shutil
import os
import numpy as np

sys.path.insert(0, '/root/autodl-tmp/garmentlab-action-chunk-demo')
from backends.garmentlab_backend import GarmentLabBackend
from schemas.action import ActionChunk, CartesianAction, GripperCommand
from schemas.observation import GripperState, TaskPhase

output = Path('/root/autodl-tmp') / ('day4-prepared-actionchunk-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
output.mkdir()
print('OUTPUT_DIR', output, flush=True)
b = GarmentLabBackend(prepared_grasp=True)
result = {'passed': False, 'scope': 'single-process single-grasp ActionChunk integration; yaw=0 ignored by backend', 'action_audit': []}


def steps(count):
    for _ in range(count):
        b._env.step()


def execute_waypoints(waypoints):
    actions = []
    for position, command in waypoints:
        xyz = np.asarray(position, dtype=np.float32)
        if xyz.shape != (3,) or not np.isfinite(xyz).all():
            raise ValueError('Expected finite xyz')
        actions.append(CartesianAction(
            target_pose=np.r_[xyz, np.float32(0)].astype(np.float32),
            gripper_command=int(command)))
    chunk = ActionChunk(actions=actions)
    matrix = chunk.to_matrix()
    if matrix.shape != (len(actions), 5):
        raise RuntimeError('Unexpected action matrix shape')
    chunk = ActionChunk.from_matrix(matrix)
    if not np.array_equal(chunk.to_matrix(), matrix):
        raise RuntimeError('ActionChunk matrix roundtrip failed')
    before = int(b._step_count['n'])
    holding_before = bool(b._holding)
    print('EXECUTE_CHUNK', chunk.horizon, matrix.tolist(), flush=True)
    response = b.execute(chunk)
    print('EXECUTE_RESULT', response, flush=True)
    obs = b.get_observation()
    obs.validate()
    control = b._env.control
    last_command = int(chunk.actions[-1].gripper_command)
    expected_holding = last_command == int(GripperCommand.CLOSE) or (
        last_command == int(GripperCommand.HOLD) and holding_before)
    expected_gripper = int(GripperState.CLOSED_HOLDING if expected_holding else GripperState.OPEN)
    expected_phase = int({int(GripperCommand.OPEN): TaskPhase.RELEASE,
                          int(GripperCommand.CLOSE): TaskPhase.GRASP,
                          int(GripperCommand.HOLD): TaskPhase.TRANSFER}[last_command])
    info = response['info']
    checks = {
        'executed_actions': response['executed_steps'] == chunk.horizon,
        'not_done': response['done'] is False and not b.is_done(),
        'steps_advanced': info['step_count'] == int(b._step_count['n']) > before,
        'holding': bool(b._holding) == bool(control.holding) == expected_holding
                   and bool(info['holding']) == expected_holding,
        'attachment_enabled': bool(control.enabled.Get()) == expected_holding,
        'attachment_reference': (control.attachlist[0] is control.block) if expected_holding
                                else (control.attachlist[0] is None),
        'gripper_state': int(obs.gripper_state) == int(info['gripper_state']) == expected_gripper,
        'phase': int(obs.task_phase) == int(info['phase']) == expected_phase,
    }
    audit = {'horizon': chunk.horizon, 'matrix': matrix.tolist(),
             'physics_steps': int(b._step_count['n']) - before,
             'response': response, 'checks': checks}
    result['action_audit'].append(audit)
    if not all(checks.values()):
        raise RuntimeError('ActionChunk checks failed: ' + repr(checks))
    return response


def action(position, command):
    return execute_waypoints([(position, command)])


def snapshot(label):
    control = b._env.control
    vertices = b._garment_world_positions()
    block_pos = control.block.get_position().numpy()
    ee, quat = b._env.robots[0].get_cur_ee_pos()
    if not np.isfinite(block_pos).all():
        raise RuntimeError('Non-finite block position')
    np.savez(output / (label + '.npz'), vertices=vertices,
             tracked_indices=control.tracked, block_position=block_pos,
             ee_position=ee, ee_quaternion=quat)
    mean_z = float(vertices[control.tracked, 2].mean())
    print(label, 'TRACKED_MEAN_Z', mean_z, 'BLOCK', block_pos, 'EE', ee, flush=True)
    return mean_z, block_pos.copy(), np.asarray(ee).copy()


try:
    overlap = float(os.environ.get('GARMENTLAB_ATTACHMENT_OVERLAP', '0.02'))
    probe = os.environ.get('GARMENTLAB_DISABLED_ATTACHMENT_PROBE', '0')
    if overlap != 0.005 or probe != '0':
        raise RuntimeError('Run with overlap=0.005 and disabled probe=0')
    result['settings'] = {'overlap': overlap, 'disabled_probe': probe,
                          'max_action_steps': b.max_action_steps}
    # Capture both repositories' required source files before starting Isaac.
    source_dir = output / 'source'
    source_dir.mkdir()
    files = {
        'backend.py': '/root/autodl-tmp/garmentlab-action-chunk-demo/backends/garmentlab_backend.py',
        'prepared_grasp_control.py': '/root/autodl-tmp/garmentlab-action-chunk-demo/backends/prepared_grasp_control.py',
        'action.py': '/root/autodl-tmp/garmentlab-action-chunk-demo/schemas/action.py',
        'base.py': '/root/autodl-tmp/garmentlab-action-chunk-demo/backends/base.py',
        'observation.py': '/root/autodl-tmp/garmentlab-action-chunk-demo/schemas/observation.py',
        'MyFranka.py': '/root/autodl-tmp/garmentlab_workspace/GarmentLab/Env/Robot/Franka/MyFranka.py',
        'BaseEnv.py': '/root/autodl-tmp/garmentlab_workspace/GarmentLab/Env/env/BaseEnv.py',
        'Control.py': '/root/autodl-tmp/garmentlab_workspace/GarmentLab/Env/env/Control.py',
        'test.py': str(Path(__file__).resolve()),
    }
    manifest = {}
    for name, path in files.items():
        dest = source_dir / name
        shutil.copy2(path, dest)
        manifest[name] = {'source': path, 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest()}
    (source_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    b.start()
    control = b._env.control
    robot = b._env.robots[0]
    robot.open()
    steps(120)
    snapshot('00_settled')

    anchor = b._garment_world_positions()[int(control.tracked[0])].copy()
    approach = anchor + np.array([0.0, 0.0, 0.15])
    print('APPROACH_TARGET', approach, flush=True)
    action(approach, GripperCommand.HOLD)
    snapshot('01_approach')

    # Repeat the descent route validated by the approach probe.
    anchor = b._garment_world_positions()[int(control.tracked[0])].copy()
    # Preserve all five descent waypoints; the public API uses its 1000-step
    # per-waypoint controller limit, rather than the old direct-call limit 300.
    action(np.array([anchor[0], anchor[1], 0.12]), GripperCommand.HOLD)
    descent = [(np.array([anchor[0], anchor[1], height]), GripperCommand.HOLD)
               for height in (0.08, 0.05, 0.03, 0.02)]
    execute_waypoints(descent)  # A real H=4 chunk, before attachment activation.
    pick = descent[-1][0]

    vertices = b._garment_world_positions()
    distance = float(np.linalg.norm(
        vertices[control.tracked] - control.block_target(), axis=1
    ).min())
    print("BEFORE_CLOSE_REGION_DISTANCE", distance, flush=True)
    assert distance < 0.02, "下降后附着位置仍离衣物过远"
    snapshot("01b_before_close")
    print("PICK_TARGET", pick, flush=True)
    action(pick, GripperCommand.CLOSE)
    steps(10)
    grasp_z, grasp_block, grasp_ee = snapshot('02_grasp')

    lift = grasp_ee + np.array([0.0, 0.0, 0.10])
    print('LIFT_TARGET', lift, flush=True)
    action(lift, GripperCommand.HOLD)
    lifted_z, lifted_block, lifted_ee = snapshot('03_lift')
    rise = lifted_z - grasp_z
    follow_error = float(np.linalg.norm(control.block_target() - lifted_block))
    print('ROBOT_DRIVEN_CLOTH_RISE', rise, flush=True)
    print('BLOCK_FOLLOW_ERROR', follow_error, flush=True)
    if rise < 0.05 or follow_error >= 0.01:
        raise RuntimeError('Cloth did not follow the robot lift sufficiently')

    action(lifted_ee, GripperCommand.OPEN)
    steps(120)
    released_z, released_block, _ = snapshot('04_release')
    drop = lifted_z - released_z
    drift = float(np.linalg.norm(released_block - lifted_block))
    print('RELEASE_CLOTH_DROP', drop, flush=True)
    print('RELEASE_BLOCK_DRIFT', drift, flush=True)
    if drop <= 0.03 or drift >= 0.005:
        raise RuntimeError('Release validation failed')
    b.get_observation().validate()
    if b._holding or control.holding:
        raise RuntimeError('Holding state was not cleared')
    result.update(passed=True, cloth_rise=rise, follow_error=follow_error,
                  cloth_drop=drop, release_block_drift=drift)
    print('PREPARED_ACTIONCHUNK_GRASP_LIFT_RELEASE_OK', flush=True)
except BaseException as exc:
    result['error'] = repr(exc)
    traceback.print_exc()
    raise
finally:
    (output / 'result.json').write_text(json.dumps(result, indent=2))
    print('RESULT_FILE', output / 'result.json', flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    b.stop()
