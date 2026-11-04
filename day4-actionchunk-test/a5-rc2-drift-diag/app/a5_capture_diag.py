"""Diagnostic copy of a5_capture.py for the RC2 drift-diagnostic batch.

The only behavioural addition is the passive release-window recorder:
start_release_diag() before the public OPEN/retreat, finish_release_diag()
after the retreated snapshot.  Physics stepping, control frequency, targets,
sampling clock and the original 331-step success trace are unchanged.
"""
import hashlib
import json
from pathlib import Path

import numpy as np


def release_window(backend, recorder, out, result, initial, pick, yaw, release):
    world = backend._env.world
    control = backend._env.control
    dt = float(world.get_physics_dt())
    if not np.isclose(dt, 1 / 60, atol=1e-12, rtol=0):
        raise ValueError('Unexpected physics dt')
    if len(control.slots) != 3:
        raise ValueError('B v1 requires exactly three measured attachment channels')
    original = control.robot_goto_position
    start_ee = np.array(backend._env.robots[0].get_cur_ee_pos()[0], dtype=float)
    target = start_ee + [0., 0., .15]

    def measure_detachment(*args, **kwargs):
        # Existing OPEN semantics call this method after ungrasp, before EE motion.
        if 'released' in recorder.samples or backend._holding or any(s.attachment_enabled() for s in control.slots):
            raise RuntimeError('Retreat began without a unique detached state')
        if int(backend._gripper_state) != 0 or not np.allclose(args[0][0], target, atol=1e-6, rtol=0):
            raise RuntimeError('Observed OPEN target/state mismatch')
        recorder.sample('released')
        return original(*args, **kwargs)

    control.robot_goto_position = measure_detachment
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
    meta = dict(protocol='stage4-a5-rc2-drift-diag-v1',
                task='A_l1_overfold' if flat else 'B_nominal',
                seed=case['seed'], level=case['level'], edge='left' if flat else 'right',
                execution_mode=execution, width_m=.2, overhang_m=.02 if flat else 0.,
                floor_z_m=0., action_count=len(result['actions']),
                recovery_count=sum(a['label'] == 'rec_release' for a in result['actions']),
                held_check=result['held_check' if flat else 'fold_held_check'],
                errors=result['errors'],
                initial_hashes={n: sha(Path(result['initial_dir']) / n) for n in names},
                manifest_sha256=sha(Path(__file__).with_name('a5-rc2-drift-diag-v1-files.json')),
                **clock)
    (out/'success_meta.json').write_text(json.dumps(meta, indent=2, allow_nan=False))
