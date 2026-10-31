"""Aligned lift plus three-second measured-position-target hold and per-World.step sampling.

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

mode = os.environ.get('GARMENTLAB_ANCHOR_ALIGNMENT', '')
if mode != 'aligned':
    raise ValueError('This trace requires GARMENTLAB_ANCHOR_ALIGNMENT=aligned')

output = Path('/root/autodl-tmp') / ('day4-aligned-measured-hold-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
output.mkdir()
print('OUTPUT_DIR', output, flush=True)
b = GarmentLabBackend(prepared_grasp=True)
result = {'passed': False, 'experiment_mode': mode, 'scope': 'aligned lift plus 180 measured-position-target hold steps; read-only World.step trace', 'action_audit': []}


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
    observer.capture(label)
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


observer = None
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
        'anchor_observer.py': str(Path(__file__).resolve().with_name('anchor_observer.py')),
        'anchor_alignment_observer.py': str(Path(__file__).resolve().with_name('anchor_alignment_observer.py')),
        'lift_step_observer.py': str(Path(__file__).resolve().with_name('lift_step_observer.py')),
        'lift_hold_step_observer.py': str(Path(__file__).resolve().with_name('lift_hold_step_observer.py')),
    }
    files['measured_hold_step_observer.py'] = str(Path(__file__).resolve().with_name('measured_hold_step_observer.py'))
    baseline = Path('/root/autodl-tmp/day4-aligned-lift-hold-20261024-230123-728994/source/manifest.json')
    expected = json.loads(baseline.read_text())
    for name, item in expected.items():
        if name == 'test.py':
            continue
        actual = hashlib.sha256(Path(files[name]).read_bytes()).hexdigest()
        if actual != item['sha256']:
            raise RuntimeError('Source changed since passed baseline: ' + name)
    print('BASELINE_SOURCE_HASHES_OK', flush=True)
    manifest = {}
    for name, path in files.items():
        dest = source_dir / name
        shutil.copy2(path, dest)
        manifest[name] = {'source': path, 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest()}
    (source_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    b.start()
    control = b._env.control
    robot = b._env.robots[0]
    from anchor_alignment_observer import PairedAlignmentObserver
    observer = PairedAlignmentObserver(b, output, mode)
    observer.capture('after_start')
    observer.install()
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
    from measured_hold_step_observer import MeasuredHoldStepObserver
    tracer = MeasuredHoldStepObserver(b, observer, output)
    hold_completed = False
    try:
        tracer.start(lift)
        action(lift, GripperCommand.HOLD)
        lifted_z, lifted_block, lifted_ee = snapshot('03_lift')
        rise = lifted_z - grasp_z
        follow_error = float(np.linalg.norm(control.block_target() - lifted_block))
        print('ROBOT_DRIVEN_CLOTH_RISE', rise, flush=True)
        print('BLOCK_FOLLOW_ERROR', follow_error, flush=True)
        if rise < 0.05 or follow_error >= 0.01:
            raise RuntimeError('Cloth did not follow the robot lift sufficiently')

        # Check all original lift frames before extending the trajectory.
        original_trace_path = Path('/root/autodl-tmp/day4-aligned-lift-step-20261024-223712-756159/lift_trace/frames.npz')
        with np.load(original_trace_path, allow_pickle=False) as original:
            prefix_checks = {
                key: np.array_equal(np.stack([frame[key] for frame in tracer.frames]), original[key])
                for key in ('vertices','block_position','block_quaternion','block_scale',
                            'ee_position','ee_quaternion','anchor_targets')}
            prefix_checks['physics_steps'] = np.array_equal(
                np.asarray([row['physics_step'] for row in tracer.rows]), original['physics_steps'])
        result['original_lift_trace_exact_checks'] = prefix_checks
        print('ORIGINAL_LIFT_TRACE_REPLAY', prefix_checks, flush=True)
        if not all(prefix_checks.values()):
            raise RuntimeError('Original lift trace does not match before hold extension')

        hold_steps = 180
        hold_target = np.asarray(lifted_ee, dtype=float).copy()
        tracer.begin_hold(hold_steps, hold_target)
        try:
            for _ in range(hold_steps):
                control._tick(hold_target, None, follow=True)
        finally:
            control.block.set_velocities(np.zeros(6))
        held_z, held_block, held_ee = snapshot('03b_hold')
        result['hold'] = {
            'steps':hold_steps, 'seconds':hold_steps*tracer.dt,
            'fixed_ee_target':hold_target.tolist(),
            'original_lift_target':np.asarray(lift).tolist(),
            'orientation_policy':'unchanged: ori=None; measured quaternion recorded, not commanded',
            'ee_before':np.asarray(lifted_ee).tolist(), 'ee_after':np.asarray(held_ee).tolist(),
            'tracked_z_change_m':held_z-lifted_z,
            'follow_error_after_m':float(np.linalg.norm(control.block_target()-held_block)),
            'target_policy':'measured EE xyz at lift completion; braking and drift remain possible'}
        hold_completed = True
    finally:
        result['lift_hold_trace'] = tracer.finish(completed=hold_completed)
    if not result['lift_hold_trace']['capture_complete']:
        raise RuntimeError('Lift+hold trace did not complete')

    action(held_ee, GripperCommand.OPEN)
    steps(120)
    released_z, released_block, _ = snapshot('04_release')
    drop = held_z - released_z
    drift = float(np.linalg.norm(released_block - held_block))
    print('RELEASE_CLOTH_DROP', drop, flush=True)
    print('RELEASE_BLOCK_DRIFT', drift, flush=True)
    if drop <= 0.03 or drift >= 0.005:
        raise RuntimeError('Release validation failed')
    b.get_observation().validate()
    if b._holding or control.holding:
        raise RuntimeError('Holding state was not cleared')
    # Require saved phases and action budgets to match the passed aligned run.
    reference_run = Path('/root/autodl-tmp/day4-aligned-lift-step-20261024-223712-756159')
    replay = {}
    for name in ('00_settled', '01_approach', '01b_before_close', '02_grasp', '03_lift'):
        with np.load(output / (name + '.npz'), allow_pickle=False) as current, np.load(reference_run / (name + '.npz'), allow_pickle=False) as previous:
            replay[name] = all(np.array_equal(current[k], previous[k]) for k in current.files)
    previous_result = json.loads((reference_run / 'result.json').read_text())
    replay['pre_hold_action_matrices'] = [a['matrix'] for a in result['action_audit'][:5]] == [a['matrix'] for a in previous_result['action_audit'][:5]]
    replay['pre_hold_execute_step_counts'] = [a['physics_steps'] for a in result['action_audit'][:5]] == [a['physics_steps'] for a in previous_result['action_audit'][:5]]
    result['reference_replay_exact_checks'] = replay
    print('LIFT_HOLD_REFERENCE_REPLAY', replay, flush=True)
    if not all(replay.values()):
        raise RuntimeError('Trace run differs from aligned reference at a saved phase or action budget')
    result['anchor_diagnostic'] = observer.finish()
    result.update(passed=True, cloth_rise=rise, follow_error=follow_error,
                  cloth_drop=drop, release_block_drift=drift)
    print('ALIGNED_MEASURED_HOLD_TRACE_OK', flush=True)
except BaseException as exc:
    result['error'] = repr(exc)
    traceback.print_exc()
    raise
finally:
    if observer is not None:
        result['alignment_metrics'] = observer.metrics
    (output / 'result.json').write_text(json.dumps(result, indent=2))
    print('RESULT_FILE', output / 'result.json', flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    b.stop()
