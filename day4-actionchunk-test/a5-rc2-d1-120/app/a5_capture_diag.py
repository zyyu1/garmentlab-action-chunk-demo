"""Diagnostic copy of a5_capture.py for the D1-120 diagnostic batch.

The release window keeps the passive per-step recorder and adds the registered
D1 intervention: exactly 120 internal physics steps inside the final public
OPEN, after ungrasp returns and before the original upward retreat target is
issued.  The wait holds the current position target and open gripper, resets
neither cloth position nor velocity, and is not a public action.  The public
12 actions, targets, commands, horizons and the 331-step success trace remain
unchanged.  Named events and per-step phase labels separate the wait from the
retreat.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

DELAY_CONFIG = 'a5-rc2-d1-120.json'


def registered_delay_steps():
    config = json.loads(Path(__file__).with_name(DELAY_CONFIG).read_text())
    steps = int((config.get('delay') or {}).get('steps', -1))
    if steps != 120:
        raise RuntimeError('D1-120 config must register exactly 120 delay steps')
    return steps


def hold_open_for_steps(backend, world, control, steps):
    """Step physics without issuing a control or changing the cloth state.

    The caller has already returned from ungrasp and has not yet issued the
    original retreat target.  No robot_goto_position/open/close, no cloth
    position write and no velocity clear is performed here.
    """
    steps = int(steps)
    if steps != 120:
        raise ValueError('D1-120 requires exactly 120 wait steps')
    if int(backend._gripper_state) != 0:
        raise RuntimeError('D1 wait requires an open gripper')
    if backend._holding or any(s.attachment_enabled() for s in control.slots):
        raise RuntimeError('D1 wait began before a unique detached state')
    start_step = int(world.current_time_step_index)
    start_time = float(world.current_time)
    ee_start = np.asarray(backend._env.robots[0].get_cur_ee_pos()[0], dtype=float).copy()
    for _ in range(steps):
        if backend._holding or any(s.attachment_enabled() for s in control.slots):
            raise RuntimeError('Attachment returned during D1 wait')
        if int(backend._gripper_state) != 0:
            raise RuntimeError('Gripper not open during D1 wait')
        world.step(render=True)
    end_step = int(world.current_time_step_index)
    end_time = float(world.current_time)
    ee_end = np.asarray(backend._env.robots[0].get_cur_ee_pos()[0], dtype=float).copy()
    elapsed = end_step - start_step
    if elapsed != steps:
        raise RuntimeError('D1 wait advanced %d steps, expected %d' % (elapsed, steps))
    return {
        'requested_steps': steps,
        'start_step': start_step,
        'end_step': end_step,
        'elapsed_steps': elapsed,
        'start_sim_time_s': start_time,
        'end_sim_time_s': end_time,
        'elapsed_sim_time_s': end_time - start_time,
        'ee_start_m': ee_start.tolist(),
        'ee_end_m': ee_end.tolist(),
        'ee_displacement_m': float(np.linalg.norm(ee_end - ee_start)),
        'gripper_state_open': True,
        'attachment_enabled': False,
        'control_calls': 0,
        'target_changes': 0,
        'cloth_position_reset': False,
        'cloth_velocity_reset': False,
        'public_action': False,
        'scope': 'internal_control_stage',
    }


def release_window(backend, recorder, out, result, initial, pick, yaw, release):
    world = backend._env.world
    control = backend._env.control
    dt = float(world.get_physics_dt())
    if not np.isclose(dt, 1 / 60, atol=1e-12, rtol=0):
        raise ValueError('Unexpected physics dt')
    if len(control.slots) != 3:
        raise ValueError('B v1 requires exactly three measured attachment channels')
    original = control.robot_goto_position
    original_ungrasp = control.ungrasp
    start_ee = np.array(backend._env.robots[0].get_cur_ee_pos()[0], dtype=float)
    target = start_ee + [0., 0., .15]

    def measure_ungrasp(*args, **kwargs):
        # The adapter returns after it has disabled attachment and opened the
        # gripper; record the actual return point, before the opening settle.
        value = original_ungrasp(*args, **kwargs)
        recorder.record_event('ungrasp_return')
        return value

    def measure_detachment(*args, **kwargs):
        # Existing OPEN semantics call this method after ungrasp, before EE motion.
        if 'released' in recorder.samples or backend._holding or any(s.attachment_enabled() for s in control.slots):
            raise RuntimeError('Retreat began without a unique detached state')
        if int(backend._gripper_state) != 0 or not np.allclose(args[0][0], target, atol=1e-6, rtol=0):
            raise RuntimeError('Observed OPEN target/state mismatch')
        if len(result.get('actions') or []) + 1 != 12:
            raise RuntimeError('D1 wait must occur on the 12th public action')
        if sum(result.get('call_horizons') or []) != 12:
            raise RuntimeError('D1 wait requires the original 12-action horizon budget')
        recorder.current_phase = 'released'
        recorder.sample('released')
        recorder.record_event('delay_begin')
        recorder.current_phase = 'delay'
        delay = hold_open_for_steps(backend, world, control, registered_delay_steps())
        delay.update({
            'public_action_label': 'release_retreat',
            'public_action_index': len(result.get('actions') or []) + 1,
            'public_action_target': target.tolist(),
            'registered_at': 'a5-rc2-d1-120.json:delay.location',
        })
        result['internal_delay'] = delay
        recorder.record_event('delay_end')
        recorder.current_phase = 'retreat'
        recorder.record_event('retreat_begin')
        value = original(*args, **kwargs)
        recorder.record_event('retreat_end')
        recorder.current_phase = 'retreat_done'
        return value

    control.robot_goto_position = measure_detachment
    control.ungrasp = measure_ungrasp
    failed = False
    try:
        recorder.start_release_diag()
        try:
            release(target)
        except BaseException:
            failed = True
            try:
                recorder.finish_release_diag(failed=True)
            finally:
                raise
    finally:
        control.robot_goto_position = original
        control.ungrasp = original_ungrasp

    zero = int(world.current_time_step_index)
    start_time = float(world.current_time)
    if 'released' not in recorder.samples:
        raise RuntimeError('No detached pre-motion sample')
    recorder.sample('retreated')
    recorder.finish_release_diag(failed=failed)
    delta = np.array(recorder.samples['retreated']['ee_m']) - recorder.samples['released']['ee_m']
    if delta[2] < .01:
        raise RuntimeError('Retreat upward displacement < 1 cm')
    result['release_clock'] = dict(absolute_step=zero, sim_time_s=start_time, dt_s=dt,
                                   pick_index=int(pick), yaw_rad=float(yaw),
                                   upward_displacement_m=float(delta[2]))
    with np.load(out/'cloth_constructed.npz', allow_pickle=False) as grid:
        points = grid['points'].copy()
    vertices, holding, enabled, opened, times, absolute = [], [], [], [], [], []
    try:
        for step in range(331):
            if step:
                world.step(render=True)
            tick = int(world.current_time_step_index)
            now = float(world.current_time)
            if tick != zero + step or abs((now - start_time) - step * dt) > 1e-5:
                raise RuntimeError('Missing, duplicated, or mistimed physics sample')
            frame = np.array(backend._garment_world_positions(), dtype=float, copy=True)
            if frame.shape != (441, 3) or not np.isfinite(frame).all():
                raise ValueError('Invalid cloth readback')
            attachment = [bool(slot.attachment_enabled()) for slot in control.slots]
            vertices.append(frame)
            holding.append(bool(backend._holding))
            enabled.append(attachment)
            opened.append(int(backend._gripper_state) == 0)
            absolute.append(tick)
            times.append(now)
            if step in (180, 240):
                recorder.sample('hold_3s' if step == 180 else 'hold_4s')
    finally:
        name = 'success_trace.npz' if len(times) == 331 else 'partial_trace.npz'
        np.savez_compressed(out/name, initial=initial, local_points=points, vertices=vertices,
                            steps=np.arange(len(times)), absolute_steps=absolute, sim_time_s=times,
                            holding=np.asarray(holding, bool), attachment_enabled=np.asarray(enabled, bool),
                            gripper_open=np.asarray(opened, bool))
    return vertices[-1]


def finish_metadata(out, result, case, execution):
    clock = result.get('release_clock')
    if clock is None:
        return
    flat = case['level'] == 'flat'
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    names = ('result.json', 'initial_geometry.npz')
    meta = dict(protocol='stage4-a5-rc2-d1-120',
                task='A_l1_overfold' if flat else 'B_nominal',
                seed=case['seed'], level=case['level'], edge='left' if flat else 'right',
                execution_mode=execution, width_m=.2, overhang_m=.02 if flat else 0.,
                floor_z_m=0., action_count=len(result['actions']),
                recovery_count=sum(a['label'] == 'rec_release' for a in result['actions']),
                held_check=result['held_check' if flat else 'fold_held_check'],
                errors=result['errors'],
                initial_hashes={n: sha(Path(result['initial_dir']) / n) for n in names},
                manifest_sha256=sha(Path(__file__).with_name('a5-rc2-d1-120-files.json')),
                internal_delay=result.get('internal_delay'),
                **clock)
    (out/'success_meta.json').write_text(json.dumps(meta, indent=2, allow_nan=False))
