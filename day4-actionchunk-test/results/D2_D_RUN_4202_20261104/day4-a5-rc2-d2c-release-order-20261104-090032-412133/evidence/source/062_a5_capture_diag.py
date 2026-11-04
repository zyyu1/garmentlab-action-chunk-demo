"""Diagnostic copy of a5_capture.py for the D2-C diagnostic batch.

The release window keeps the passive per-step recorder and adds the registered
D2-C intervention: the gripper opens while the attachment remains enabled, the
redundant second open inside ungrasp is suppressed, and the attachment is then
disabled.  Exactly 120 internal physics steps follow inside the final public
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

DELAY_CONFIG = 'a5-rc2-d2c-release-order.json'


def registered_delay_steps():
    config = json.loads(Path(__file__).with_name(DELAY_CONFIG).read_text())
    steps = int((config.get('delay') or {}).get('steps', -1))
    if steps != 120:
        raise RuntimeError('D2-C config must register exactly 120 delay steps')
    return steps


def hold_open_for_steps(backend, world, control, steps):
    """Step physics without issuing a control or changing the cloth state.

    The caller has already returned from ungrasp and has not yet issued the
    original retreat target.  No robot_goto_position/open/close, no cloth
    position write and no velocity clear is performed here.
    """
    steps = int(steps)
    if steps != 120:
        raise ValueError('D2-C requires exactly 120 wait steps')
    if int(backend._gripper_state) != 0:
        raise RuntimeError('D2-C wait requires an open gripper')
    if backend._holding or any(s.attachment_enabled() for s in control.slots):
        raise RuntimeError('D2-C wait began before a unique detached state')
    start_step = int(world.current_time_step_index)
    start_time = float(world.current_time)
    ee_start = np.asarray(backend._env.robots[0].get_cur_ee_pos()[0], dtype=float).copy()
    for _ in range(steps):
        if backend._holding or any(s.attachment_enabled() for s in control.slots):
            raise RuntimeError('Attachment returned during D2-C wait')
        if int(backend._gripper_state) != 0:
            raise RuntimeError('Gripper not open during D2-C wait')
        world.step(render=True)
    end_step = int(world.current_time_step_index)
    end_time = float(world.current_time)
    ee_end = np.asarray(backend._env.robots[0].get_cur_ee_pos()[0], dtype=float).copy()
    elapsed = end_step - start_step
    if elapsed != steps:
        raise RuntimeError('D2-C wait advanced %d steps, expected %d' % (elapsed, steps))
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


def preopen_while_attached(active, world, recorder, control):
    """D2-C intervention: complete the gripper opening before detaching.

    The 10 pre-registered steps allow the gripper to open while the cloth stays
    held, but holding and the real attachment state must remain consistent on
    every step.  The global slot checks are not disabled: control.holding,
    control.attachment_enabled() and control.assert_exclusive() are evaluated
    after each of the 10 physics steps.  Returns the record and the saved bound
    ``open`` method; the caller runs the original ungrasp with that method
    temporarily suppressed, so the total opening is one registered 10-step open
    rather than two (20 steps).
    """
    if not bool(getattr(active, 'holding', False)):
        raise RuntimeError('D2-C preopen requires the active slot to be holding')
    if not bool(active.attachment_enabled()):
        raise RuntimeError('D2-C preopen requires the attachment to be enabled')
    if getattr(active.robot, 'world', world) is not world:
        raise RuntimeError('D2-C preopen robot world differs from recorder world')
    pre_start = int(world.current_time_step_index)
    before_holding = bool(active.holding)
    before_attached = bool(active.attachment_enabled())
    before_extra = recorder.state()
    original_open = active.robot.open
    original_step = world.step
    seen = [0]

    def checked_step(*args, **kwargs):
        value = original_step(*args, **kwargs)
        seen[0] += 1
        if not bool(active.holding):
            raise RuntimeError('D2-C holding changed during preopen step %d' % seen[0])
        if not bool(active.attachment_enabled()):
            raise RuntimeError('D2-C attachment changed during preopen step %d' % seen[0])
        if not bool(control.holding) or not bool(control.attachment_enabled()):
            raise RuntimeError('D2-C control holding/attachment inconsistent at preopen step %d' % seen[0])
        control.assert_exclusive()
        return value

    world.step = checked_step
    try:
        original_open()
    finally:
        world.step = original_step
    pre_end = int(world.current_time_step_index)
    after_preopen_holding = bool(active.holding)
    after_preopen_attached = bool(active.attachment_enabled())
    after_preopen_extra = recorder.state()
    aperture_before = before_extra.get('gripper_aperture_m')
    aperture_after = after_preopen_extra.get('gripper_aperture_m')
    aperture_increased = bool(aperture_before is not None and aperture_after is not None
                              and aperture_after > aperture_before)
    if pre_end - pre_start != 10:
        raise RuntimeError('D2-C preopen must advance exactly 10 steps')
    if seen[0] != 10:
        raise RuntimeError('D2-C preopen consistency wrapper saw %d steps, expected 10' % seen[0])
    if not after_preopen_holding or not after_preopen_attached:
        raise RuntimeError('D2-C attachment changed during preopen')
    if not aperture_increased:
        raise RuntimeError('D2-C gripper aperture did not increase during preopen')
    record = {
        'intervention': 'open_while_attached_then_disable',
        'preopen_start_step': pre_start,
        'preopen_end_step': pre_end,
        'preopen_steps': pre_end - pre_start,
        'preopen_state_checks': seen[0],
        'holding_before': before_holding,
        'holding_after_preopen': after_preopen_holding,
        'attachment_enabled_before': before_attached,
        'attachment_enabled_after_preopen': after_preopen_attached,
        'gripper_aperture_before_m': aperture_before,
        'gripper_aperture_after_preopen_m': aperture_after,
        'gripper_aperture_increased': aperture_increased,
        'suppressed_second_open': True,
        'registered_at': 'a5-rc2-d2c-release-order.json:release_order',
    }
    return record, original_open


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
        # D2-C single-variable intervention: open the gripper while the
        # attachment is still enabled, then let the original ungrasp disable
        # the attachment.  The redundant open() inside the original ungrasp is
        # suppressed so the opening duration stays exactly 10 physics steps.
        active = control.active
        record, original_open = preopen_while_attached(active, world, recorder, control)

        def suppressed_open(*a, **k):
            return None
        active.robot.open = suppressed_open
        try:
            value = original_ungrasp(*args, **kwargs)
        finally:
            active.robot.open = original_open
        disable_step = int(world.current_time_step_index)
        if bool(active.attachment_enabled()) or bool(active.holding):
            raise RuntimeError('D2-C attachment was not disabled after ungrasp')
        boundary_observed = int(getattr(recorder, 'steps', -1))
        record['attachment_disabled_step'] = disable_step
        record['attachment_enabled_after_ungrasp'] = bool(active.attachment_enabled())
        record['preopen_last_state_observed_step'] = boundary_observed
        record['release_boundary_observed_step'] = boundary_observed
        record['release_boundary_backend_step'] = disable_step
        result['release_order'] = record
        recorder.record_event('ungrasp_return')
        return value

    def measure_detachment(*args, **kwargs):
        # Existing OPEN semantics call this method after ungrasp, before EE motion.
        if 'released' in recorder.samples or backend._holding or any(s.attachment_enabled() for s in control.slots):
            raise RuntimeError('Retreat began without a unique detached state')
        if int(backend._gripper_state) != 0 or not np.allclose(args[0][0], target, atol=1e-6, rtol=0):
            raise RuntimeError('Observed OPEN target/state mismatch')
        if len(result.get('actions') or []) + 1 != 12:
            raise RuntimeError('D2-C wait must occur on the 12th public action')
        if sum(result.get('call_horizons') or []) != 12:
            raise RuntimeError('D2-C wait requires the original 12-action horizon budget')
        recorder.current_phase = 'released'
        recorder.sample('released')
        sample = recorder.samples.get('released') or {}
        sample_step = sample.get('observed_step')
        if sample_step is not None and result.get('release_order'):
            order = result['release_order']
            order['released_sample_observed_step'] = int(sample_step)
            order['released_sample_sim_time_s'] = float(sample['sim_time_s'])
            order['release_boundary_sample_step_delta'] = int(sample_step) - int(
                order['release_boundary_observed_step'])
            order['first_wait_state_observed_step'] = int(sample_step) + 1
            result['release_order'] = order
        recorder.record_event('delay_begin')
        recorder.current_phase = 'delay'
        delay = hold_open_for_steps(backend, world, control, registered_delay_steps())
        delay.update({
            'public_action_label': 'release_retreat',
            'public_action_index': len(result.get('actions') or []) + 1,
            'public_action_target': target.tolist(),
            'registered_at': 'a5-rc2-d2c-release-order.json:delay.location',
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
    meta = dict(protocol='stage4-a5-rc2-d2c-release-order',
                task='A_l1_overfold' if flat else 'B_nominal',
                seed=case['seed'], level=case['level'], edge='left' if flat else 'right',
                execution_mode=execution, width_m=.2, overhang_m=.02 if flat else 0.,
                floor_z_m=0., action_count=len(result['actions']),
                recovery_count=sum(a['label'] == 'rec_release' for a in result['actions']),
                held_check=result['held_check' if flat else 'fold_held_check'],
                errors=result['errors'],
                initial_hashes={n: sha(Path(result['initial_dir']) / n) for n in names},
                manifest_sha256=sha(Path(__file__).with_name('a5-rc2-d2c-release-order-files.json')),
                internal_delay=result.get('internal_delay'),
                release_order=result.get('release_order'),
                **clock)
    (out/'success_meta.json').write_text(json.dumps(meta, indent=2, allow_nan=False))
