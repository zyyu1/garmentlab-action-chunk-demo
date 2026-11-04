"""A5 RC1. Sample actual post-OPEN physics steps, preserving partial failures."""
import hashlib
import json
from pathlib import Path

import numpy as np

import pfs1_observation_v2


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
    # Passive observation of every step in the release action, including the
    # opening and retreat.  The wrapper only calls the original step and reads
    # state afterwards; it adds no physics step and no control call.
    release_records = []
    original_step = world.step

    def observed_step(*args, **kwargs):
        value = original_step(*args, **kwargs)
        release_records.append(pfs1_observation_v2.snapshot(
            backend, 'release_step_%03d' % len(release_records)))
        return value

    world.step = observed_step
    try:
        release(target)
    except BaseException:
        try:
            if release_records:
                pfs1_observation_v2.save_records(
                    out, 'pfs1_release_steps_partial', release_records,
                    {'failed': True, 'scope': 'release action partial'})
        except Exception as exc:
            print('PFS1_PARTIAL_SAVE_ERROR', repr(exc), flush=True)
        raise
    finally:
        world.step = original_step
        control.robot_goto_position = original

    zero = int(world.current_time_step_index)
    start_time = float(world.current_time)
    if 'released' not in recorder.samples:
        raise RuntimeError('No detached pre-motion sample')
    recorder.sample('retreated')
    delta = np.array(recorder.samples['retreated']['ee_m']) - recorder.samples['released']['ee_m']
    if delta[2] < .01:
        raise RuntimeError('Retreat upward displacement < 1 cm')
    result['release_clock'] = dict(absolute_step=zero, sim_time_s=start_time, dt_s=dt,
                                   pick_index=int(pick), yaw_rad=float(yaw), upward_displacement_m=float(delta[2]))
    with np.load(out/'cloth_constructed.npz', allow_pickle=False) as grid:
        points = grid['points'].copy()
    vertices, holding, enabled, opened, times, absolute = [], [], [], [], [], []
    trace_records = []
    trace_start = len(release_records)
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
            trace_records.append(pfs1_observation_v2.snapshot(
                backend, 'trace_%03d' % step))
            if step in (180, 240):
                recorder.sample('hold_3s' if step == 180 else 'hold_4s')
    finally:
        name = 'success_trace.npz' if len(times) == 331 else 'partial_trace.npz'
        np.savez_compressed(out/name, initial=initial, local_points=points, vertices=vertices,
                            steps=np.arange(len(times)), absolute_steps=absolute, sim_time_s=times,
                            holding=np.asarray(holding, bool), attachment_enabled=np.asarray(enabled, bool),
                            gripper_open=np.asarray(opened, bool))
        all_records = list(release_records) + trace_records
        if all_records:
            pfs1_observation_v2.save_records(
                out, 'pfs1_release_steps', all_records,
                {'release_records': len(release_records),
                 'trace_records': len(trace_records),
                 'trace_start_index': trace_start,
                 'formal_saved': len(trace_records) >= 331})
            boundary_index = next(
                (i for i, rec in enumerate(all_records)
                 if not rec['holding'] and not rec['attachment_enabled_any']), None)
            if boundary_index is not None:
                boundary = all_records[boundary_index]
                pfs1_observation_v2.save_stage(out, 'release_boundary', boundary)
                index_path = out / 'pfs1_stage_index.json'
                index = json.loads(index_path.read_text()) if index_path.is_file() else []
                pre = next((x for x in index if x['label'] == 'pre_release'), None)
                released = recorder.samples.get('released')
                clock = {
                    't0_definition': 'pre-release last-attached state; first detached physics step is the boundary sample; no zero-step post-disable sample in the RC2 original flow',
                    'pre_release': pre,
                    'release_boundary': {
                        'label': boundary['label'],
                        'sim_time_s': boundary['sim_time_s'],
                        'absolute_step': boundary['absolute_step'],
                        'holding': boundary['holding'],
                        'attachment_enabled_any': boundary['attachment_enabled_any'],
                    },
                    'released_sample': released,
                    'sampling_error_steps': (None if pre is None else
                                             boundary['absolute_step'] - pre['absolute_step']),
                    'definition_note': 'The actual attachment disable is between the pre-release state and the first detached step; report the step/time interval, not an exact instant.',
                }
                (out / 'pfs1_release_clock.json').write_text(
                    json.dumps(clock, indent=2, allow_nan=False) + '\n')
                first = [rec for rec in all_records
                         if boundary['sim_time_s'] - 1e-6 <= rec['sim_time_s']
                         <= boundary['sim_time_s'] + 0.5 + 1e-6]
                if first:
                    pfs1_observation_v2.save_records(
                        out, 'pfs1_first_0_5s', first,
                        {'scope': 'release boundary + 0.5 s', 'boundary_index': boundary_index})
            if len(trace_records) >= 331:
                pfs1_observation_v2.save_records(
                    out, 'pfs1_formal_210_330', trace_records[210:331],
                    {'scope': 'success_trace frames 210..330 inclusive'})
    return vertices[-1]


def finish_metadata(out, result, case, execution):
    clock = result.get('release_clock')
    if clock is None:
        return
    flat = case['level'] == 'flat'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    names = ('result.json', 'initial_geometry.npz')
    meta = dict(protocol='stage4-a5-rc2', task='A_l1_overfold' if flat else 'B_nominal',
                seed=case['seed'], level=case['level'], edge='left' if flat else 'right',
                execution_mode=execution, width_m=.2, overhang_m=.02 if flat else 0.,
                floor_z_m=0., action_count=len(result['actions']),
                recovery_count=sum(a['label']=='rec_release' for a in result['actions']),
                held_check=result['held_check' if flat else 'fold_held_check'], errors=result['errors'],
                initial_hashes={n:sha(Path(result['initial_dir'])/n) for n in names},
                manifest_sha256=sha(Path(__file__).with_name('a5-manifest.json')), **clock)
    (out/'success_meta.json').write_text(json.dumps(meta, indent=2, allow_nan=False))
