"""Stage 6 minimal single-step BC closed-loop entry.

What this runner does
---------------------
* Reuses the frozen Stage 4/5 candidate initialization, task material patches,
  Backend classes and 331-frame release recorder from the Stage 5 app.
* Loads the existing Stage 5 reduced ``single`` checkpoint and train-only
  ``stats.json`` through ``training/bc_policy.py``.
* At every public action: observe -> predict -> execute.  It never injects an
  expert waypoint, expert recovery action or expert fold arc.
* L1 (flat) budget is <= 7 public actions; L2/L3 (perturbed/crumpled) <= 12.
* The policy decides *when* to release.  The terminal OPEN target is the frozen
  public release/retreat target (current EE + [0, 0, 0.15] m); that override is
  recorded explicitly and is not an expert fold action.
* The original ``a5_capture.release_window`` records the [0..330] frame window,
  the original clock, ``success_trace.npz`` and the evidence retention samples.
* The original ``stage4_success_v1.evaluate`` is called through
  ``stage6/bc_eval_adapter.py``.  Success additionally requires the terminal
  release/retreat event, a complete 331-frame trace, the original clock match,
  complete evidence and a consistent read-only step hook.  Missing terminal or
  evidence conditions can never be reported as success.

This file is Stage 6 code; it does not modify the frozen candidate/app files.
It is intended to run on the GPU host, not in the offline validation round.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
TRAINING = Path(os.environ.get('STAGE6_TRAINING', HERE.parent / 'training'))
LOCAL_RESULTS = HERE.parent / 'results' / 'STAGE5_REDUCED_50_10_10'
LOCAL_APP = HERE.parent / 'a5-rc8b-recovery-hold120-rc7-r2' / 'app'
LOCAL_REPO = HERE.parents[1]
DEFAULT_APP = Path('/root/autodl-tmp/stage5-trial/app')
DEFAULT_REPO = Path('/root/autodl-tmp/garmentlab-action-chunk-demo')
DEFAULT_OUT = Path('/root/autodl-tmp')

# Stage 5 reduced 50/10/10 identity (README §6 and local hashes).
EXPECTED_CHECKPOINT_SHA256 = (
    '5bff9e671c54b5240b93fefb5c67507987553153bad4b5ca0a5bb92d20e48ad6')
EXPECTED_STATS_SHA256 = (
    '8f1788d11803be7e22729758cf071f68d49ec5bae80aa387a3327112fcae746a')


# ----------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------
def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError('Unsupported JSON type: %s' % type(value).__name__)


def _json_safe(value):
    """Convert numpy/non-finite values to strict-JSON-safe objects."""
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _write_json(path, payload):
    path = Path(path)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2,
                   default=_json_default, allow_nan=False) + '\n',
        encoding='utf-8')


def _first_file(candidates, what):
    tried = []
    for candidate in candidates:
        if candidate is None:
            continue
        path = Path(candidate)
        if path.is_file():
            return path.resolve()
        tried.append(str(path))
    raise SystemExit('%s not found; tried: %s' % (what, '; '.join(tried)))


def _first_app(candidates):
    tried = []
    for candidate in candidates:
        if candidate is None:
            continue
        path = Path(candidate)
        if (path / 'a5_l1.py').is_file() and (path / 'a5_capture.py').is_file():
            return path.resolve()
        tried.append(str(path))
    raise SystemExit('Stage 5 app dir not found; tried: %s' % '; '.join(tried))


def _first_repo(candidates):
    tried = []
    for candidate in candidates:
        if candidate is None:
            continue
        path = Path(candidate)
        if (path / 'backends' / 'garmentlab_backend.py').is_file():
            return path.resolve()
        tried.append(str(path))
    raise SystemExit('repository root not found; tried: %s' % '; '.join(tried))


def _normalize_dataset_file(value):
    if value is None:
        return None
    path = Path(value)
    if path.is_dir():
        path = path / 'stats.json'
    return path


def _normalize_checkpoint(value):
    if value is None:
        return None
    path = Path(value)
    if path.is_dir():
        path = path / 'best.pt'
    return path


def resolve_app(value):
    return _first_app([value, os.environ.get('STAGE6_APP'), DEFAULT_APP,
                       LOCAL_APP, HERE.parent])


def resolve_repo(value):
    return _first_repo([value, os.environ.get('STAGE6_REPO'),
                        DEFAULT_REPO, LOCAL_REPO])


def resolve_checkpoint(value):
    explicit = _normalize_checkpoint(value)
    return _first_file([
        explicit, os.environ.get('STAGE6_CHECKPOINT'),
        LOCAL_RESULTS / 'runs' / 'single' / 'best.pt',
        TRAINING / 'runs' / 'single' / 'best.pt',
        Path('/root/autodl-tmp/stage5-trial/training/runs/single/best.pt'),
        Path('/root/autodl-tmp/stage5-trial/results/STAGE5_REDUCED_50_10_10/runs/single/best.pt'),
    ], 'Stage 5 reduced single checkpoint (best.pt)')


def resolve_stats(value):
    explicit = _normalize_dataset_file(value)
    return _first_file([
        explicit, os.environ.get('STAGE6_STATS'),
        LOCAL_RESULTS / 'dataset' / 'stats.json',
        LOCAL_RESULTS / 'archive' / 'stats.json',
        TRAINING / 'final' / 'stats.json',
        Path('/root/autodl-tmp/stage5-trial/training/final/stats.json'),
        Path('/root/autodl-tmp/stage5-trial/results/STAGE5_REDUCED_50_10_10/dataset/stats.json'),
    ], 'Stage 5 reduced train-only stats.json')


def _wrap_angle(value):
    return float(np.arctan2(np.sin(value), np.cos(value)))


def _slot_label(slot):
    return None if slot is None else str(getattr(slot, 'label', type(slot).__name__))


def _engaged_state(backend):
    """Read the actual holding/attachment state (no mutation)."""
    control = backend._env.control
    attached = bool(control.attachlist != [None])
    enabled = [bool(slot.attachment_enabled()) for slot in control.slots]
    holding = bool(backend._holding)
    gripper_state = int(getattr(backend, '_gripper_state', -1))
    return {
        'holding': holding,
        'attached': attached,
        'enabled_slots': enabled,
        'enabled_any': bool(any(enabled)),
        'engaged': bool(holding or attached or any(enabled)),
        'gripper_state': gripper_state,
        'gripper_open': gripper_state == 0,
        'attachlist': [None if s is None else _slot_label(s)
                       for s in getattr(control, 'attachlist', [])],
    }


def _expected_fold_slot(control, level):
    return control.fold_slot if level == 'flat' else control.slots[0]


# ----------------------------------------------------------------------
# runtime imports (kept out of module import so py_compile works on CPU)
# ----------------------------------------------------------------------
def load_runtime(args):
    app = resolve_app(args.app_dir)
    repo = resolve_repo(args.repo_root)
    for path in (str(repo), str(app), str(TRAINING), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)

    from backends.garmentlab_backend import _import_garmentlab
    from schemas.action import ActionChunk, CartesianAction, GripperCommand
    from rc2_live_backend import LiveSquarePoseBackend
    from square_pose_contract import orientation_euler
    from square_start import start_with_square
    from l1_yaw_fold_geometry import measure_yaw
    import pfs1_observation_v2
    from episode_evidence import attach_evidence
    from a5_capture import finish_metadata
    from audit_episode_evidence import audit
    from bc_eval_adapter import physical_verdict, LEVEL_BUDGET
    from bc_policy import BCPolicy
    from h4_policy import H4Policy
    from step_hook import StepHook

    return SimpleNamespace(
        app=app, repo=repo, training=TRAINING,
        _import_garmentlab=_import_garmentlab,
        ActionChunk=ActionChunk, CartesianAction=CartesianAction,
        GripperCommand=GripperCommand,
        LiveSquarePoseBackend=LiveSquarePoseBackend,
        orientation_euler=orientation_euler,
        start_with_square=start_with_square,
        measure_yaw=measure_yaw,
        pfs1=pfs1_observation_v2,
        attach_evidence=attach_evidence,
        finish_metadata=finish_metadata,
        audit=audit,
        physical_verdict=physical_verdict,
        LEVEL_BUDGET=LEVEL_BUDGET,
        BCPolicy=BCPolicy,
        H4Policy=H4Policy,
        StepHook=StepHook,
        np=np,
    )


# ----------------------------------------------------------------------
# frozen initialization / material / Backend reuse
# ----------------------------------------------------------------------
def _build_backend(rt, level, case, out):
    usd = str(Path(rt.app) / 'square_cloth_40cm.usda')
    if not Path(usd).is_file():
        raise FileNotFoundError('square cloth USD not found: ' + usd)

    if level == 'flat':
        class FoldPoseBackend(rt.LiveSquarePoseBackend):
            def _make_prepared_control(self, env):
                from square_edge_control import SquareEdgeProxyGroundControl
                SquareEdgeProxyGroundControl.output_directory = getattr(
                    self, 'output_dir', None)
                return SquareEdgeProxyGroundControl(env)

        backend = FoldPoseBackend(
            garment_usd=usd, prepared_grasp=True, max_action_steps=30000)
    else:
        class StripPoseBackend(rt.LiveSquarePoseBackend):
            def __init__(self, edges, *args, **kwargs):
                self._strip_edges = list(edges)
                super().__init__(*args, **kwargs)

            def _make_prepared_control(self, env):
                from strip_prepared_control import StripPreparedControl
                StripPreparedControl.output_directory = getattr(
                    self, 'output_dir', None)
                return StripPreparedControl(env, self._strip_edges)

        strips = case.get('strips') or []
        if not strips:
            raise ValueError('L2/L3 initial case has no strip records')
        edges = list(dict.fromkeys([str(s['edge']) for s in strips] + ['right']))
        backend = StripPoseBackend(
            edges, garment_usd=usd, prepared_grasp=True, max_action_steps=30000)

    # Set before start(); the prepared control factory reads this attribute.
    backend.output_dir = out
    return backend


@contextmanager
def _material_patch(rt, out, level):
    """Reuse the frozen L1/L2/L3 material construction patches exactly."""
    from room_collision_control import install_room_collision_control

    rt._import_garmentlab()
    restore_room = install_room_collision_control(out)
    module = importlib.import_module('Env.Garment.Garment')
    original_material = module.ParticleMaterial
    original_cloth = module.ClothPrim

    @wraps(original_cloth)
    def bend_cloth(*args, **kwargs):
        kwargs['bend_stiffness'] = 100.
        return original_cloth(*args, **kwargs)

    module.ClothPrim = bend_cloth
    scale = 0.0 if level == 'flat' else 1.0

    def fixed_material(*args, **kwargs):
        kwargs['particle_friction_scale'] = scale
        material = original_material(*args, **kwargs)
        rt.pfs1.capture_material_object(
            material, out, 'after_construction', expected_scale=scale)
        return material

    module.ParticleMaterial = fixed_material
    try:
        yield scale
    finally:
        module.ParticleMaterial = original_material
        module.ClothPrim = original_cloth
        restore_room()


def _load_initial(rt, backend, init_dir, level, out):
    with np.load(init_dir / 'initial_geometry.npz', allow_pickle=False) as data:
        key = 'settled' if level == 'flat' else 'final'
        if key not in data:
            raise ValueError('initial_geometry.npz missing key: ' + key)
        target = np.asarray(data[key], dtype=np.float64)
    if target.shape != (441, 3) or not np.isfinite(target).all():
        raise ValueError('Invalid initial geometry: %r' % (target.shape,))

    robot = backend._env.robots[0]
    robot.open()
    backend._set_garment_world_positions(target.astype(np.float32))
    backend._clear_garment_velocities()
    if not np.allclose(backend._garment_world_positions(), target,
                       atol=1e-5, rtol=0):
        raise RuntimeError('Initial state readback mismatch')
    backend._settle(30)
    initial = np.asarray(backend._garment_world_positions(), dtype=np.float64)
    rt.pfs1.record_stage(backend, out, 'initial_loaded')
    rt.pfs1.record_material_stage(
        backend, out, 'after_initial_settle',
        expected_scale=0.0 if level == 'flat' else 1.0)
    return initial


def _load_local_points(out):
    with np.load(Path(out) / 'cloth_constructed.npz', allow_pickle=False) as data:
        points = np.asarray(data['points'], dtype=np.float64)
    if points.shape != (441, 3) or not np.isfinite(points).all():
        raise ValueError('Unexpected constructed mesh')
    return points


# ----------------------------------------------------------------------
# observe -> predict -> execute
# ----------------------------------------------------------------------
def _observe(rt, backend):
    vertices = np.asarray(backend._garment_world_positions(), dtype=np.float64)
    robot = backend._env.robots[0]
    ee, quat = robot.get_cur_ee_pos()
    ee = np.asarray(backend._to_numpy(ee), dtype=np.float64).reshape(-1)
    if quat is None:
        raise ValueError('EE quaternion unavailable')
    quat = np.asarray(backend._to_numpy(quat), dtype=np.float64).reshape(-1)
    joints = np.asarray(
        backend._to_numpy(robot._robot.get_joint_positions()),
        dtype=np.float32).reshape(-1)
    if joints.shape != (9,):
        raise ValueError('Expected 9 joint positions, got %r' % (joints.shape,))
    holding = bool(backend._holding)
    obs = rt.BCPolicy.build_obs(vertices, ee, quat, joints, holding)
    world = backend._env.world
    return {
        'obs': obs,
        'vertices': vertices,
        'ee': ee,
        'quat': quat,
        'joints': joints,
        'holding': holding,
        'sim_time_s': float(world.current_time),
        'absolute_step': int(world.current_time_step_index),
        'backend_step': int(backend._step_count['n']),
    }


def _predict(rt, policy, observation):
    prediction = policy.predict(observation['obs'])
    xyz = np.asarray(prediction.get('xyz'), dtype=np.float64).reshape(-1)
    yaw = float(prediction.get('yaw', float('nan')))
    gripper = int(prediction.get('gripper', -1))
    if xyz.shape != (3,) or not np.isfinite(xyz).all():
        raise ValueError('Non-finite policy XYZ: %r' % (xyz,))
    if not np.isfinite(yaw):
        raise ValueError('Non-finite policy yaw')
    if gripper not in (0, 1, 2):
        raise ValueError('Invalid policy gripper command: %r' % (gripper,))
    out = {'xyz': xyz, 'yaw': yaw, 'gripper': gripper}
    if 'inference_ms' in prediction:
        out['inference_ms'] = prediction['inference_ms']
    return out


def _execute_action(rt, backend, result, target, yaw, command, label,
                    policy=None, obs_row=None):
    target_pose = np.r_[np.asarray(target, dtype=np.float64).reshape(3),
                        float(yaw)]
    if target_pose.shape != (4,) or not np.isfinite(target_pose).all():
        raise ValueError('Invalid action target: %r' % (target_pose,))

    if obs_row is not None:
        obs_row['action_target'] = target_pose.copy()
        obs_row['action_command'] = int(command)
        obs_row['action_label'] = label

    chunk = rt.ActionChunk(actions=[rt.CartesianAction(
        target_pose=target_pose.astype(np.float32),
        gripper_command=int(command))])
    response = backend.execute(chunk)

    control = backend._env.control
    attached = bool(control.attachlist != [None])
    checks = {
        'executed_one': response.get('executed_steps') == 1,
        'not_done': response.get('done') is False,
        'holding_consistent': bool(backend._holding) == bool(attached),
        'attachment_count': int(attached) == int(backend._holding),
    }
    slot = getattr(control, 'active', None)
    ee = np.asarray(backend._env.robots[0].get_cur_ee_pos()[0],
                    dtype=np.float64).reshape(-1)
    row = {
        'label': label,
        'target_pose': target_pose.tolist(),
        'command': int(command),
        'response': response,
        'checks': checks,
        'holding': bool(backend._holding),
        'attached': bool(attached),
        'active_slot': _slot_label(slot),
        'ee': ee.tolist(),
        'step': int(backend._step_count['n']),
        'policy': policy,
        # Stage 6 executes the policy's own target/yaw/gripper command.  The
        # original Backend OPEN may move the robot to that target; that is
        # Backend behaviour, not a Stage 6 override.
        'target_override': False,
        'model_target_preserved': True,
    }
    if attached and slot is not None:
        try:
            row['block_error_m'] = float(np.linalg.norm(
                np.asarray(slot.block_target(), dtype=float)
                - slot.block.get_position().numpy()))
        except Exception as exc:
            row['block_error_m'] = None
            row['block_error_error'] = repr(exc)
        row['max_single_anchor_gap_m'] = float(
            getattr(slot, 'max_single_anchor_gap_m', float('nan')))
    result['actions'].append(row)
    print('BC_ACTION', label, json.dumps(response, default=_json_default),
          flush=True)
    if not all(checks.values()):
        raise RuntimeError('BC action state mismatch: ' + label)
    return row


def _held_check(rt, backend, last_target, last_yaw, tolerance):
    robot = backend._env.robots[0]
    control = backend._env.control
    ee = np.asarray(robot.get_cur_ee_pos()[0], dtype=np.float64).reshape(3)
    speed = float(np.max(np.abs(
        backend._to_numpy(robot._robot.get_joint_velocities())[:7])))
    if last_target is None:
        last_target = ee
        last_yaw = 0.0
    last_target = np.asarray(last_target, dtype=np.float64).reshape(3)
    orientation_reached = bool(
        robot.reach(last_target, rt.orientation_euler(float(last_yaw))))
    slot = getattr(control, 'active', None)
    attached = bool(control.attachlist != [None])
    gap = (float(getattr(slot, 'max_single_anchor_gap_m', 1e9))
           if attached and slot is not None else 1e9)
    position_error = float(np.linalg.norm(ee - last_target))
    accepted = bool(
        attached and slot is not None
        and position_error < float(tolerance)
        and speed < .1
        and orientation_reached
        and gap <= .01)
    return {
        'position_error_m': position_error,
        'arm_speed_rad_s': speed,
        'anchor_gap_max_m': gap,
        'orientation_reached': orientation_reached,
        'attached': attached,
        'active_slot': _slot_label(slot),
        'tolerance_m': float(tolerance),
        'accepted': accepted,
    }


def _make_fold_reference(rt, backend, out, result, level, case,
                         local_points, state, source, slot):
    state = np.asarray(state, dtype=np.float64)
    if state.shape != (441, 3) or not np.isfinite(state).all():
        raise ValueError('Invalid fold reference state')
    if slot is None:
        raise ValueError('Missing fold slot')
    try:
        yaw_measured, fit_max, fit_p95 = rt.measure_yaw(local_points, state)
        measure_error = None
    except BaseException as exc:
        yaw_measured = float(case['yaw_rad'])
        fit_max = float('nan')
        fit_p95 = float('nan')
        measure_error = repr(exc)

    reference = {
        'level': level,
        'source': source,
        'edge': 'left' if level == 'flat' else 'right',
        'width_m': 0.2,
        'overhang_m': 0.02 if level == 'flat' else 0.0,
        'pick_index': int(slot.pick_index),
        'slot_label': _slot_label(slot),
        'yaw_rad': float(yaw_measured),
        'yaw_measured': float(yaw_measured),
        'yaw_case': float(case['yaw_rad']),
        'yaw_delta_vs_case': _wrap_angle(
            float(yaw_measured) - float(case['yaw_rad'])),
        'fit_residual_max_m': float(fit_max),
        'fit_residual_p95_m': float(fit_p95),
        'measure_error': measure_error,
        'initial_step': int(backend._step_count['n']),
        'initial_time_s': float(backend._env.world.current_time),
    }
    if level == 'flat' and abs(reference['yaw_delta_vs_case']) > .02:
        raise RuntimeError('Measured yaw disagrees with initial-case yaw')

    np.savez_compressed(
        Path(out) / 'fold_initial.npz',
        vertices=state,
        pick_index=reference['pick_index'],
        yaw_rad=reference['yaw_rad'])
    reference['fold_initial_file'] = 'fold_initial.npz'
    reference['fold_initial_sha256'] = _sha256(Path(out) / 'fold_initial.npz')
    result['fold_reference'] = reference
    return {
        'state': state,
        'pick_index': reference['pick_index'],
        'yaw': reference['yaw_rad'],
        'slot': slot,
        'reference': reference,
    }


# ----------------------------------------------------------------------
# terminal release / original 331-frame window
# ----------------------------------------------------------------------
def _execute_terminal_open(rt, backend, result, evidence, prediction, obs_row):
    """Execute the policy's terminal OPEN target/yaw unchanged.

    A read-only ``robot_goto_position`` observer samples the detached state
    before the Backend performs the OPEN motion.  It does not alter args,
    target, gripper command, or motion.  The original Backend OPEN semantics
    (ungrasp when holding, then move to the requested target) are retained.
    """
    if evidence is None:
        raise RuntimeError('No evidence recorder for terminal OPEN')
    control = backend._env.control
    original_goto = control.robot_goto_position
    release_observation = {}

    def observed_goto(*args, **kwargs):
        try:
            state = _engaged_state(backend)
            if not state['engaged'] and 'released' not in evidence.samples:
                evidence.sample('released')
                ee = np.asarray(
                    backend._env.robots[0].get_cur_ee_pos()[0],
                    dtype=np.float64).reshape(3)
                target = None
                if args and args[0]:
                    target = np.asarray(args[0][0], dtype=np.float64).reshape(3)
                release_observation.update({
                    'ee_m': ee.tolist(),
                    'target': None if target is None else target.tolist(),
                    'state': state,
                })
        except BaseException as exc:
            result['errors'].append('release observation: ' + repr(exc))
        return original_goto(*args, **kwargs)

    control.robot_goto_position = observed_goto
    try:
        row = _execute_action(
            rt, backend, result, prediction['xyz'], prediction['yaw'],
            int(rt.GripperCommand.OPEN), 'bc_release_open',
            policy=prediction, obs_row=obs_row)
    finally:
        control.robot_goto_position = original_goto

    if 'released' not in evidence.samples:
        # No Backend goto call (or no detached transition): keep the actual
        # post-action state as evidence rather than inventing a pre-motion one.
        evidence.sample('released')
    evidence.sample('retreated')
    row['release_observation'] = release_observation
    return row


def _record_release_window(rt, backend, out, result, evidence, initial,
                           pick_index, yaw, upward_displacement_m):
    """Record the original 331-frame [0..330] window after the terminal OPEN.

    This mirrors ``a5_capture.release_window``'s post-release loop and array
    names, but it starts only after the policy's own OPEN action has completed.
    It adds no action, no target override and no extra physics step.
    """
    world = backend._env.world
    control = backend._env.control
    dt = float(world.get_physics_dt())
    if not np.isclose(dt, 1 / 60, atol=1e-12, rtol=0):
        raise ValueError('Unexpected physics dt')
    if len(control.slots) != 3:
        raise ValueError('B v1 requires exactly three measured attachment channels')

    zero = int(world.current_time_step_index)
    start = float(world.current_time)
    result['release_clock'] = {
        'absolute_step': zero,
        'sim_time_s': start,
        'dt_s': dt,
        'pick_index': int(pick_index),
        'yaw_rad': float(yaw),
        'upward_displacement_m': float(upward_displacement_m),
        'target_override': False,
        'source': ('Stage 6 model-target terminal OPEN; original 331-frame '
                   'post-release window'),
    }
    with np.load(Path(out) / 'cloth_constructed.npz',
                 allow_pickle=False) as grid:
        points = np.asarray(grid['points'], dtype=np.float64)

    vertices, holding, enabled, opened, times, absolute = [], [], [], [], [], []
    trace_records = []
    try:
        for step in range(331):
            if step:
                world.step(render=True)
            tick = int(world.current_time_step_index)
            now = float(world.current_time)
            if tick != zero + step or abs((now - start) - step * dt) > 1e-5:
                raise RuntimeError('Missing, duplicated, or mistimed physics sample')
            frame = np.array(backend._garment_world_positions(),
                             dtype=np.float64, copy=True)
            if frame.shape != (441, 3) or not np.isfinite(frame).all():
                raise ValueError('Invalid cloth readback')
            attachment = [bool(slot.attachment_enabled())
                          for slot in control.slots]
            vertices.append(frame)
            holding.append(bool(backend._holding))
            enabled.append(attachment)
            opened.append(int(getattr(backend, '_gripper_state', -1)) == 0)
            absolute.append(tick)
            times.append(now)
            trace_records.append(rt.pfs1.snapshot(
                backend, 'trace_%03d' % step))
            if step in (180, 240):
                evidence.sample('hold_3s' if step == 180 else 'hold_4s')
    finally:
        name = ('success_trace.npz' if len(times) == 331
                else 'partial_trace.npz')
        np.savez_compressed(
            Path(out) / name,
            initial=np.asarray(initial, dtype=np.float64),
            local_points=points,
            vertices=np.asarray(vertices, dtype=np.float64),
            steps=np.arange(len(times)),
            absolute_steps=np.asarray(absolute, dtype=np.int64),
            sim_time_s=np.asarray(times, dtype=np.float64),
            holding=np.asarray(holding, dtype=bool),
            attachment_enabled=np.asarray(enabled, dtype=bool),
            gripper_open=np.asarray(opened, dtype=bool))
        if trace_records:
            rt.pfs1.save_records(
                out, 'pfs1_release_window', trace_records,
                {'scope': 'Stage 6 post-release 331-frame window',
                 'frames': len(trace_records),
                 'target_override': False})
            if len(trace_records) >= 331:
                rt.pfs1.save_records(
                    out, 'pfs1_formal_210_330', trace_records[210:331],
                    {'scope': 'success window frames 210..330'})
    return np.asarray(vertices[-1], dtype=np.float64)


def _save_partial_trace(rt, backend, out, result, initial, pick_index, yaw,
                        reasons):
    path = Path(out) / 'partial_trace.npz'
    if path.is_file():
        result['partial_trace'] = {
            'path': 'partial_trace.npz',
            'frames': int(np.load(path, allow_pickle=False)['vertices'].shape[0]),
            'sha256': _sha256(path),
            'reasons': list(reasons),
        }
        return
    world = backend._env.world
    control = backend._env.control
    with np.load(Path(out) / 'cloth_constructed.npz',
                 allow_pickle=False) as grid:
        points = np.asarray(grid['points'], dtype=np.float64)
    frame = np.asarray(backend._garment_world_positions(), dtype=np.float64)
    enabled = [bool(slot.attachment_enabled()) for slot in control.slots]
    zero = int(world.current_time_step_index)
    now = float(world.current_time)
    np.savez_compressed(
        path,
        initial=np.asarray(initial, dtype=np.float64),
        local_points=points,
        vertices=np.asarray([frame], dtype=np.float64),
        steps=np.asarray([0], dtype=np.int64),
        absolute_steps=np.asarray([zero], dtype=np.int64),
        sim_time_s=np.asarray([now], dtype=np.float64),
        holding=np.asarray([bool(backend._holding)], dtype=bool),
        attachment_enabled=np.asarray([enabled], dtype=bool),
        gripper_open=np.asarray(
            [int(getattr(backend, '_gripper_state', -1)) == 0], dtype=bool),
        pick_index=np.asarray(int(pick_index)),
        yaw_rad=np.asarray(float(yaw)),
        terminal_reason=np.asarray('; '.join(reasons)))
    result['partial_trace'] = {
        'path': 'partial_trace.npz',
        'frames': 1,
        'sha256': _sha256(path),
        'reasons': list(reasons),
    }


def _terminal_release(rt, backend, out, result, evidence, case, level, fold,
                      last_target, last_yaw, prediction, obs_row,
                      grasp_count, release_count):
    control = backend._env.control
    expected_slot = _expected_fold_slot(control, level)
    active_slot = getattr(control, 'active', None)
    fold_slot_ok = bool(active_slot is expected_slot and fold is not None)
    held = _held_check(
        rt, backend, last_target, last_yaw,
        tolerance=.01 if level == 'flat' else .03)
    result['held_check'] = held
    if level != 'flat':
        result['fold_held_check'] = held
    reference_ok = bool(
        fold is not None
        and fold['reference'].get('measure_error') is None)

    initial = fold['state'] if fold is not None else np.asarray(
        backend._garment_world_positions(), dtype=np.float64)
    pick_index = (fold['pick_index'] if fold is not None
                  else int(expected_slot.pick_index))
    yaw = fold['yaw'] if fold is not None else float(case['yaw_rad'])

    result['events'].append({
        'name': 'bc_pre_release',
        'policy_action_index': int(len(result['actions'])),
        'step': int(backend._step_count['n']),
        'sim_time_s': float(backend._env.world.current_time),
        'holding': bool(backend._holding),
        'active_slot': _slot_label(active_slot),
        'expected_fold_slot': _slot_label(expected_slot),
        'held_check_ok': bool(held['accepted']),
        'fold_slot_ok': fold_slot_ok,
        'fold_reference_ok': reference_ok,
        'target_override': False,
    })
    terminal = {
        'policy_open': True,
        'policy_step_index': int(len(result['actions'])),
        'policy_target': np.asarray(prediction['xyz'], dtype=float).tolist(),
        'policy_yaw': float(prediction['yaw']),
        'policy_gripper': int(prediction['gripper']),
        'grasp_count': int(grasp_count),
        'intermediate_release_count': int(release_count),
        'active_slot': _slot_label(active_slot),
        'expected_fold_slot': _slot_label(expected_slot),
        'fold_slot_ok': fold_slot_ok,
        'fold_reference_ok': reference_ok,
        'held_check_ok': bool(held['accepted']),
        'held_check': held,
        'target_override': False,
        'model_target_preserved': True,
        'retreat_override': False,
        'release_rule': ('policy OPEN target is executed unchanged; physical '
                         'release requires actual detached/open state and '
                         'actual upward displacement >= 0.01 m; expert target '
                         'equality is recorded separately, not a BC gate'),
        'release_action_label': 'bc_release_open',
        'release_action_step': None,
        'executed_target': None,
        'executed_yaw': None,
        'released_ee': None,
        'retreated_ee': None,
        'upward_displacement_m': None,
        # Expert identity/consistency field only; never a Stage 6 success gate.
        'expert_target_consistency': None,
        'expert_target_required': None,
        'expert_target_distance_m': None,
        'expert_target_atol_m': .002,
        'expert_target_reasons': [],
        # Physical release/retreat requirement from the frozen release window.
        'physical_retreat_ok': None,
        'frozen_target_ok': None,       # compatibility alias of expert identity
        'frozen_retreat_ok': None,      # compatibility alias of physical retreat
        'detached_ok': None,
        'terminal_ok': False,
        'reasons': [],
        'release_clock': None,
        'trace_frames': 0,
        'fold_reference': None if fold is None else fold['reference'],
    }
    result['terminal_release'] = terminal

    try:
        rt.pfs1.record_stage(backend, out, 'pre_release')
        rt.pfs1.record_material_stage(
            backend, out, 'pre_release',
            expected_scale=0.0 if level == 'flat' else 1.0)
        row = _execute_terminal_open(
            rt, backend, result, evidence, prediction, obs_row)
    except BaseException as exc:
        terminal['reasons'].append('terminal OPEN execution: ' + repr(exc))
        try:
            _save_partial_trace(rt, backend, out, result, initial,
                                pick_index, yaw, terminal['reasons'])
        except BaseException as save_exc:
            result['errors'].append('Partial trace save: ' + repr(save_exc))
        result['terminal_release'] = terminal
        raise

    terminal['release_action_step'] = int(row['step'])
    terminal['executed_target'] = list(row['target_pose'][:3])
    terminal['executed_yaw'] = float(row['target_pose'][3])
    released = evidence.samples.get('released')
    retreated = evidence.samples.get('retreated')
    if released is None or retreated is None:
        terminal['reasons'].append('missing released/retreated sample')

    if released is not None and retreated is not None:
        released_ee = np.asarray(released['ee_m'], dtype=np.float64).reshape(3)
        retreated_ee = np.asarray(retreated['ee_m'], dtype=np.float64).reshape(3)
        upward = float(retreated_ee[2] - released_ee[2])
        target = np.asarray(prediction['xyz'], dtype=np.float64).reshape(3)
        required_expert_target = released_ee + np.array([0.0, 0.0, 0.15])
        target_ok = bool(np.allclose(
            target, required_expert_target, atol=.002, rtol=0))
        retreat_ok = bool(upward >= .01)
        released_detached = bool(
            not released['holding'] and not released['attached'])
        after_state = _engaged_state(backend)
        detached_ok = bool(
            released_detached and not after_state['engaged']
            and after_state['gripper_open'])
        terminal.update({
            'released_ee': released_ee.tolist(),
            'retreated_ee': retreated_ee.tolist(),
            'upward_displacement_m': upward,
            'expert_target_consistency': target_ok,
            'expert_target_required': required_expert_target.tolist(),
            'expert_target_distance_m': float(
                np.linalg.norm(target - required_expert_target)),
            'physical_retreat_ok': retreat_ok,
            'frozen_target_ok': target_ok,
            'frozen_retreat_ok': retreat_ok,
            'detached_ok': detached_ok,
            'after_state': after_state,
        })
        if not target_ok:
            # Expert identity consistency only; not a Stage 6 success gate.
            terminal['expert_target_reasons'].append(
                'policy OPEN target differs from expert pre-release EE + '
                '[0,0,0.15] m')
        if not retreat_ok:
            terminal['reasons'].append(
                'actual upward displacement < 0.01 m')
        if not detached_ok:
            terminal['reasons'].append(
                'actual holding/attachment state is not detached/open')

    if not fold_slot_ok:
        terminal['reasons'].append('active slot is not the expected fold slot')
    if not reference_ok:
        terminal['reasons'].append('fold reference measurement failed')
    if not held['accepted']:
        terminal['reasons'].append('pre-release held check failed')

    terminal['terminal_ok'] = bool(
        not terminal['reasons']
        and terminal.get('physical_retreat_ok') is True
        and terminal.get('detached_ok') is True
        and held['accepted'] and fold_slot_ok and reference_ok)
    result['terminal_release'] = terminal

    if terminal['terminal_ok']:
        try:
            final = _record_release_window(
                rt, backend, out, result, evidence, initial, pick_index, yaw,
                float(terminal['upward_displacement_m']))
        except BaseException as exc:
            terminal['reasons'].append('331-frame window: ' + repr(exc))
            terminal['terminal_ok'] = False
            try:
                _save_partial_trace(rt, backend, out, result, initial,
                                    pick_index, yaw, terminal['reasons'])
            except BaseException as save_exc:
                result['errors'].append('Partial trace save: ' + repr(save_exc))
            result['terminal_release'] = terminal
            raise
        np.savez_compressed(Path(out) / 'final.npz', vertices=final)
        terminal['release_clock'] = result.get('release_clock')
        terminal['trace_frames'] = 331
        result['terminal_release'] = terminal
    else:
        try:
            _save_partial_trace(rt, backend, out, result, initial,
                                pick_index, yaw, terminal['reasons'])
        except BaseException as save_exc:
            result['errors'].append('Partial trace save: ' + repr(save_exc))

    for sample_name, event_name in (
            ('released', 'bc_release_begin'),
            ('retreated', 'bc_retreat_end'),
            ('hold_3s', 'bc_hold_3s'),
            ('hold_4s', 'bc_hold_4s')):
        sample = evidence.samples.get(sample_name)
        if sample is not None:
            result['events'].append({
                'name': event_name,
                'sample': sample_name,
                'sim_time_s': sample.get('sim_time_s'),
                'observed_step': sample.get('observed_step'),
            })

    clock = result.get('release_clock')
    if clock:
        zero = int(clock['absolute_step'])
        start = float(clock['sim_time_s'])
        dt = float(clock['dt_s'])
        result['events'].append({
            'name': 'bc_trace_begin',
            'absolute_step': zero,
            'sim_time_s': start,
        })
        result['events'].append({
            'name': 'bc_trace_end',
            'absolute_step': zero + 330,
            'sim_time_s': start + 330 * dt,
        })
        result['events'].append({
            'name': 'bc_terminal_release',
            'policy_step_index': terminal['policy_step_index'],
            'absolute_step': zero,
            'sim_time_s': start,
            'upward_displacement_m': float(
                clock.get('upward_displacement_m', 0.0)),
            'target_override': False,
            'terminal_ok': bool(terminal['terminal_ok']),
            'expert_target_consistency': terminal.get(
                'expert_target_consistency'),
        })
    else:
        result['events'].append({
            'name': 'bc_terminal_rejected',
            'policy_step_index': terminal['policy_step_index'],
            'target_override': False,
            'terminal_ok': False,
            'reasons': list(terminal['reasons']),
        })
    return None


# ----------------------------------------------------------------------
# policy loop
# ----------------------------------------------------------------------
def _run_policy(rt, backend, out, result, evidence, case, level, args,
                local_points, policy, initial, obs_rows=None):
    if obs_rows is None:
        obs_rows = []
    control = backend._env.control
    level_limit = int(rt.LEVEL_BUDGET[level])
    budget = int(min(level_limit, args.max_actions
                     if args.max_actions is not None else level_limit))
    result['budget'] = {
        'level_limit': level_limit,
        'requested': int(args.max_actions if args.max_actions is not None
                         else level_limit),
        'used': 0,
        'within_limit': True,
    }
    grasp_events = 0
    release_events = 0
    nonterminal_opens = 0
    repeated_closes = 0
    initial_or_idle_opens = 0
    fold = None
    last_target = None
    last_yaw = None

    if level == 'flat':
        slot = control.fold_slot
        fold = _make_fold_reference(
            rt, backend, out, result, level, case, local_points,
            initial, 'initial_settled', slot)
        result['events'].append({
            'name': 'bc_fold_reference',
            'source': 'initial_settled',
            'pick_index': fold['pick_index'],
            'yaw_rad': fold['yaw'],
            'slot_label': _slot_label(slot),
            'step': int(backend._step_count['n']),
            'sim_time_s': float(backend._env.world.current_time),
        })

    while len(result['actions']) < budget:
        before = _engaged_state(backend)
        observation = _observe(rt, backend)
        prediction = _predict(rt, policy, observation)
        action_index = len(result['actions'])
        obs_row = dict(observation)
        obs_row['prediction'] = dict(prediction)
        obs_row['action_target'] = np.r_[prediction['xyz'], prediction['yaw']]
        obs_row['action_command'] = int(prediction['gripper'])
        obs_row['action_label'] = 'pending'
        obs_rows.append(obs_row)
        result.setdefault('policy_calls', []).append({
            'call_index': len(result['policy_calls']),
            'start_action_index': action_index,
            'observation': {
                'sim_time_s': observation['sim_time_s'],
                'absolute_step': observation['absolute_step'],
                'backend_step': observation['backend_step'],
                'holding': observation['holding'],
                'engaged_before': before['engaged'],
            },
            'predicted_actions': [dict(prediction)],
            'inference_ms': prediction.get('inference_ms'),
            'execute_k': 1,
            'remaining_budget': int(budget - action_index),
            'stop_reason': None,
        })

        print('BC_OBS', action_index,
              json.dumps({
                  'sim_time_s': observation['sim_time_s'],
                  'absolute_step': observation['absolute_step'],
                  'holding': observation['holding'],
                  'engaged': before['engaged'],
                  'grasp_events': grasp_events,
              }), flush=True)
        print('BC_PREDICT', action_index, json.dumps({
            'xyz': prediction['xyz'].tolist(),
            'yaw': prediction['yaw'],
            'gripper': prediction['gripper'],
        }), flush=True)

        # L2/L3 fold reference: first non-engaged action after the recovery
        # release.  This is the post-recovery state before the fold approach.
        if (level != 'flat' and grasp_events == 1 and fold is None
                and not before['engaged']):
            state = np.asarray(
                backend._garment_world_positions(), dtype=np.float64)
            slot = control.slots[0]
            fold = _make_fold_reference(
                rt, backend, out, result, level, case, local_points,
                state, 'post_recovery_nonengaged', slot)
            result['events'].append({
                'name': 'bc_fold_reference',
                'source': 'post_recovery_nonengaged',
                'pick_index': fold['pick_index'],
                'yaw_rad': fold['yaw'],
                'slot_label': _slot_label(slot),
                'step': int(backend._step_count['n']),
                'sim_time_s': float(backend._env.world.current_time),
            })

        command = int(prediction['gripper'])
        if command == int(rt.GripperCommand.OPEN):
            required_grasps = 1 if level == 'flat' else 2
            terminal = bool(before['engaged']
                            and grasp_events >= required_grasps)
            if terminal:
                _terminal_release(
                    rt, backend, out, result, evidence, case, level, fold,
                    last_target, last_yaw, prediction, obs_row,
                    grasp_events, release_events)
                break

            if before['engaged'] and level != 'flat' and grasp_events == 1:
                label = 'bc_recovery_release'
            elif grasp_events == 0:
                label = 'bc_initial_open_%03d' % action_index
            elif level != 'flat' and grasp_events == 1:
                label = 'bc_fold_approach_open_%03d' % action_index
            else:
                label = 'bc_nonterminal_open_%03d' % action_index
            row = _execute_action(
                rt, backend, result, prediction['xyz'], prediction['yaw'],
                int(rt.GripperCommand.OPEN), label,
                policy=prediction, obs_row=obs_row)
            after = _engaged_state(backend)
            nonterminal_opens += 1
            if before['engaged'] and not after['engaged']:
                release_events += 1
                event_name = ('bc_recovery_release'
                              if level != 'flat' and grasp_events == 1
                              else 'bc_nonterminal_release')
            elif not before['engaged'] and not after['engaged']:
                initial_or_idle_opens += 1
                event_name = ('bc_fold_approach_open'
                              if level != 'flat' and grasp_events == 1
                              else 'bc_initial_or_idle_open')
            else:
                event_name = 'bc_open_no_release'
            last_target = np.asarray(row['target_pose'][:3], dtype=float)
            last_yaw = float(row['target_pose'][3])
            result['events'].append({
                'name': event_name,
                'label': label,
                'policy_action_index': action_index,
                'grasp_events_before': int(grasp_events),
                'step': row['step'],
                'sim_time_s': float(backend._env.world.current_time),
                'target_pose': row['target_pose'],
                'target_override': False,
                'engaged_before': bool(before['engaged']),
                'engaged_after': bool(after['engaged']),
                'holding_after': row['holding'],
            })
            continue

        if command == int(rt.GripperCommand.CLOSE):
            if before['engaged']:
                label = 'bc_repeated_close_%03d' % action_index
            else:
                label = 'bc_grasp_%02d' % (grasp_events + 1)
            row = _execute_action(
                rt, backend, result, prediction['xyz'], prediction['yaw'],
                int(rt.GripperCommand.CLOSE), label,
                policy=prediction, obs_row=obs_row)
            after = _engaged_state(backend)
            if not before['engaged'] and after['engaged']:
                grasp_events += 1
                event_name = 'bc_grasp'
            elif before['engaged'] and after['engaged']:
                repeated_closes += 1
                event_name = 'bc_repeated_close'
            else:
                event_name = 'bc_grasp_failed'
            last_target = np.asarray(row['target_pose'][:3], dtype=float)
            last_yaw = float(row['target_pose'][3])
            result['events'].append({
                'name': event_name,
                'label': label,
                'policy_action_index': action_index,
                'grasp_events_after': int(grasp_events),
                'step': row['step'],
                'sim_time_s': float(backend._env.world.current_time),
                'target_pose': row['target_pose'],
                'target_override': False,
                'engaged_before': bool(before['engaged']),
                'engaged_after': bool(after['engaged']),
                'holding_after': row['holding'],
            })
            continue

        # HOLD (or any non-OPEN/CLOSE command): execute the policy action and
        # record only real state transitions; a HOLD does not create a grasp.
        label = 'bc_hold_%03d' % action_index
        row = _execute_action(
            rt, backend, result, prediction['xyz'], prediction['yaw'],
            command, label, policy=prediction, obs_row=obs_row)
        after = _engaged_state(backend)
        event_name = None
        if not before['engaged'] and after['engaged']:
            grasp_events += 1
            event_name = 'bc_unexpected_grasp_on_hold'
        elif before['engaged'] and not after['engaged']:
            release_events += 1
            event_name = 'bc_unexpected_release_on_hold'
        last_target = np.asarray(row['target_pose'][:3], dtype=float)
        last_yaw = float(row['target_pose'][3])
        if event_name is not None:
            result['events'].append({
                'name': event_name,
                'label': label,
                'policy_action_index': action_index,
                'grasp_events_after': int(grasp_events),
                'step': row['step'],
                'sim_time_s': float(backend._env.world.current_time),
                'target_pose': row['target_pose'],
                'target_override': False,
                'engaged_before': bool(before['engaged']),
                'engaged_after': bool(after['engaged']),
                'holding_after': row['holding'],
            })

    if len(result['actions']) >= budget and 'terminal_release' not in result:
        result['events'].append({
            'name': 'bc_budget_exhausted_without_terminal_release',
            'used': len(result['actions']),
            'level_limit': level_limit,
        })
    result['budget']['used'] = len(result['actions'])
    result['budget']['within_limit'] = bool(
        len(result['actions']) <= level_limit)
    result['bc_grasps'] = grasp_events
    result['bc_release_events'] = release_events
    result['bc_recovery_releases'] = release_events
    result['bc_nonterminal_opens'] = nonterminal_opens
    result['bc_repeated_closes'] = repeated_closes
    result['bc_initial_or_idle_opens'] = initial_or_idle_opens
    result['bc_grasp_events'] = grasp_events
    return obs_rows, budget


# ----------------------------------------------------------------------
# evidence/verdict
# ----------------------------------------------------------------------
def _save_observations(out, rows, result):
    rows = [row for row in rows if 'obs' in row]
    if not rows:
        return
    try:
        action_target = np.asarray([
            row.get('action_target',
                    np.r_[row['prediction']['xyz'], row['prediction']['yaw']])
            for row in rows], dtype=np.float64)
        action_command = np.asarray([
            int(row.get('action_command',
                        row['prediction']['gripper'])) for row in rows],
            dtype=np.int64)
        labels = np.asarray([
            str(row.get('action_label', '')) for row in rows], dtype=str)
        path = Path(out) / 'bc_observations.npz'
        np.savez_compressed(
            path,
            obs=np.asarray([row['obs'] for row in rows], dtype=np.float32),
            vertices=np.asarray([row['vertices'] for row in rows], dtype=np.float64),
            ee=np.asarray([row['ee'] for row in rows], dtype=np.float64),
            quat=np.asarray([row['quat'] for row in rows], dtype=np.float64),
            joints=np.asarray([row['joints'] for row in rows], dtype=np.float32),
            holding=np.asarray([row['holding'] for row in rows], dtype=bool),
            sim_time_s=np.asarray([
                row['sim_time_s'] for row in rows], dtype=np.float64),
            absolute_step=np.asarray([
                row['absolute_step'] for row in rows], dtype=np.int64),
            backend_step=np.asarray([
                row['backend_step'] for row in rows], dtype=np.int64),
            prediction_xyz=np.asarray([
                row['prediction']['xyz'] for row in rows], dtype=np.float64),
            prediction_yaw=np.asarray([
                row['prediction']['yaw'] for row in rows], dtype=np.float64),
            prediction_gripper=np.asarray([
                row['prediction']['gripper'] for row in rows], dtype=np.int64),
            action_target=action_target,
            action_command=action_command,
            action_label=labels)
        result['bc_observations'] = {
            'path': 'bc_observations.npz',
            'count': len(rows),
            'sha256': _sha256(path),
        }
    except BaseException as exc:
        result['errors'].append('BC observations save: ' + repr(exc))


def _check_trace(out, result):
    reasons = []
    trace_path = Path(out) / 'success_trace.npz'
    if not trace_path.is_file():
        return False, ['missing success_trace.npz']
    try:
        with np.load(trace_path, allow_pickle=False) as data:
            required = {'initial', 'local_points', 'vertices', 'steps',
                        'absolute_steps', 'sim_time_s', 'holding',
                        'attachment_enabled', 'gripper_open'}
            missing = sorted(required - set(data.files))
            if missing:
                return False, ['success_trace.npz missing arrays: ' + ', '.join(missing)]
            initial = np.asarray(data['initial'], dtype=np.float64)
            local_points = np.asarray(data['local_points'], dtype=np.float64)
            vertices = np.asarray(data['vertices'], dtype=np.float64)
            steps = np.asarray(data['steps'])
            absolute = np.asarray(data['absolute_steps'])
            times = np.asarray(data['sim_time_s'], dtype=np.float64)
            holding = np.asarray(data['holding'])
            enabled = np.asarray(data['attachment_enabled'])
            opened = np.asarray(data['gripper_open'])
    except BaseException as exc:
        return False, ['cannot read success_trace.npz: ' + repr(exc)]

    if initial.shape != (441, 3) or not np.isfinite(initial).all():
        reasons.append('trace initial is not finite (441,3)')
    if local_points.shape != (441, 3) or not np.isfinite(local_points).all():
        reasons.append('trace local_points is not finite (441,3)')
    if vertices.shape != (331, 441, 3) or not np.isfinite(vertices).all():
        reasons.append('trace vertices is not finite (331,441,3)')
    if steps.shape != (331,) or not np.array_equal(steps, np.arange(331)):
        reasons.append('trace steps are not exactly 0..330')
    if holding.shape != (331,) or holding.any():
        reasons.append('trace holding is not all-false')
    if enabled.shape != (331, 3) or enabled.any():
        reasons.append('trace attachment_enabled is not all-false')
    if opened.shape != (331,) or not opened.all():
        reasons.append('trace gripper_open is not all-true')

    clock = result.get('release_clock') or {}
    if not clock:
        reasons.append('missing original release_clock')
    else:
        zero = clock.get('absolute_step')
        start = clock.get('sim_time_s')
        dt = clock.get('dt_s')
        try:
            zero_i = int(zero)
        except (TypeError, ValueError):
            zero_i = None
        if zero_i is None:
            reasons.append('release_clock absolute_step is invalid')
        else:
            if absolute.shape != (331,) or not np.array_equal(
                    absolute, zero_i + np.arange(331)):
                reasons.append('absolute_steps do not match release_clock origin')
        if start is None or not np.isfinite(float(start)):
            reasons.append('release_clock sim_time_s is invalid')
        else:
            expected = float(start) + np.arange(331) / 60.0
            if times.shape != (331,) or not np.allclose(
                    times, expected, atol=1e-5, rtol=0):
                reasons.append('sim_time_s does not match 60 Hz release clock')
        if dt is None or abs(float(dt) - 1.0 / 60.0) > 1e-12:
            reasons.append('release_clock dt_s is not 1/60')
        if float(clock.get('upward_displacement_m', 0.0)) < .01:
            reasons.append('retreat upward displacement < 1 cm')
        if not np.isfinite(float(clock.get('yaw_rad', float('nan')))):
            reasons.append('release_clock yaw_rad is not finite')
    return len(reasons) == 0, reasons


def _check_evidence(rt, out, result):
    reasons = []
    evidence_dir = Path(out) / 'evidence'
    for name in ('summary.json', 'manifest.json', 'timeline.jsonl',
                 'episode.mp4'):
        if not (evidence_dir / name).is_file():
            reasons.append('missing evidence/' + name)
    if reasons:
        return False, reasons, None
    try:
        summary = json.loads((evidence_dir / 'summary.json').read_text())
    except BaseException as exc:
        return False, ['cannot read evidence summary: ' + repr(exc)], None
    if summary.get('synthetic') is not False:
        reasons.append('evidence summary synthetic is not false')
    if summary.get('errors'):
        reasons.append('evidence summary reports errors: %r' % summary.get('errors'))
    try:
        capture = rt.audit(evidence_dir)
    except BaseException as exc:
        return False, ['evidence audit failed: ' + repr(exc)], None
    if capture.get('evidence_complete') is not True:
        failed = [k for k, v in (capture.get('checks') or {}).items() if not v]
        reasons.append('evidence audit incomplete: ' + ', '.join(failed))
    def _as_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    if _as_int(capture.get('attempted_public_actions'), -1) != len(result['actions']):
        reasons.append('evidence attempted_public_actions != action count')
    if _as_int(summary.get('execute_calls'), -1) != len(result['actions']):
        reasons.append('evidence execute_calls != action count')
    hook = result.get('step_hook') or {}
    if hook.get('observation_errors'):
        reasons.append('step hook observation errors: %r'
                       % hook.get('observation_errors'))
    if _as_int(hook.get('step_calls'), -1) != _as_int(summary.get('observed_steps'), -2):
        reasons.append('step hook calls != evidence observed_steps')
    if _as_int(hook.get('records'), -1) != _as_int(hook.get('step_calls'), -2):
        reasons.append('step hook records != step calls')
    return len(reasons) == 0, reasons, capture


def _evaluate_verdict(rt, out, result, budget):
    reasons = []
    meta_path = Path(out) / 'success_meta.json'
    trace_path = Path(out) / 'success_trace.npz'
    adapter = {
        'status': 'incomplete',
        'success': None,
        'accepted': False,
        'error': 'missing success_meta.json or success_trace.npz',
    }
    if meta_path.is_file() and trace_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            with np.load(trace_path, allow_pickle=False) as data:
                arrays = {key: data[key] for key in data.files}
            adapter = rt.physical_verdict(meta, arrays)
        except BaseException as exc:
            adapter = {
                'status': 'incomplete',
                'success': None,
                'accepted': False,
                'error': repr(exc),
            }
            reasons.append('adapter failed: ' + repr(exc))
    else:
        reasons.append('missing success_meta.json or success_trace.npz')

    terminal = result.get('terminal_release') or {}
    executed_target = terminal.get('executed_target')
    policy_target = terminal.get('policy_target')
    target_preserved = bool(
        executed_target is not None and policy_target is not None
        and np.allclose(np.asarray(executed_target, dtype=float),
                        np.asarray(policy_target, dtype=float),
                        atol=1e-5, rtol=0))
    yaw_preserved = False
    try:
        yaw_preserved = bool(abs(_wrap_angle(
            float(terminal.get('executed_yaw', 0.0))
            - float(terminal.get('policy_yaw', 0.0)))) < 1e-6)
    except (TypeError, ValueError):
        yaw_preserved = False
    terminal['target_preserved'] = target_preserved
    terminal['yaw_preserved'] = yaw_preserved
    expert_target_consistency = {
        'policy_target_equals_released_ee_plus_015': terminal.get(
            'expert_target_consistency'),
        'required_target': terminal.get('expert_target_required'),
        'policy_target': terminal.get('policy_target'),
        'distance_m': terminal.get('expert_target_distance_m'),
        'atol_m': terminal.get('expert_target_atol_m'),
        'reasons': list(terminal.get('expert_target_reasons') or []),
        'note': ('expert action identity/consistency field; it is not a '
                 'Stage 6 BC success gate'),
    }
    result['expert_target_consistency'] = expert_target_consistency
    terminal_ok = bool(
        terminal.get('policy_open') is True
        and terminal.get('terminal_ok') is True
        and terminal.get('target_override') is False
        and terminal.get('model_target_preserved') is True
        and terminal.get('release_action_label') == 'bc_release_open'
        and terminal.get('physical_retreat_ok') is True
        and terminal.get('detached_ok') is True
        and terminal.get('fold_slot_ok')
        and terminal.get('fold_reference_ok')
        and terminal.get('held_check_ok')
        and target_preserved and yaw_preserved
        and terminal.get('release_clock')
        and int(terminal.get('trace_frames', 0)) == 331)
    if not terminal_ok:
        reasons.append('terminal release/retreat condition missing')
        reasons.extend(str(r) for r in (terminal.get('reasons') or []))

    trace_ok, trace_reasons = _check_trace(out, result)
    reasons.extend(trace_reasons)
    clock_keys = ('clock', 'sim_time_s', 'absolute_steps', 'dt_s',
                  'displacement')
    clock_ok = bool(result.get('release_clock')) and not any(
        any(key in reason for key in clock_keys) for reason in trace_reasons)
    evidence_ok, evidence_reasons, capture = _check_evidence(rt, out, result)
    reasons.extend(evidence_reasons)

    hook = result.get('step_hook') or {}
    step_hook_ok = bool(
        hook.get('step_calls')
        and hook.get('step_calls') == hook.get('records')
        and not hook.get('observation_errors'))
    if not step_hook_ok:
        reasons.append('step hook count/readback condition missing')

    labels = [str(action.get('label', '')) for action in result['actions']]
    no_expert_actions = bool(labels) and all(
        label.startswith('bc_') for label in labels)
    if not no_expert_actions:
        reasons.append('non-BC action label found (expert action injection?)')

    action_count = len(result['actions'])
    budget_ok = bool(0 < action_count <= int(budget))
    if not budget_ok:
        reasons.append('action count outside BC budget')
    no_runtime_error = bool(result.get('errors') == [])
    if not no_runtime_error:
        reasons.append('runtime errors recorded')

    success = bool(
        adapter.get('accepted') is True
        and terminal_ok
        and trace_ok
        and clock_ok
        and evidence_ok
        and step_hook_ok
        and no_expert_actions
        and budget_ok
        and no_runtime_error)
    if (no_runtime_error and adapter.get('status') == 'rejected'
            and terminal_ok and trace_ok and clock_ok and evidence_ok
            and step_hook_ok and no_expert_actions and budget_ok):
        status = 'rejected'
    elif not no_runtime_error:
        status = 'execution_error'
    elif success:
        status = 'accepted'
    else:
        status = 'incomplete'

    result['adapter'] = adapter
    result['evidence_checks'] = None if capture is None else capture.get('checks')
    result['terminal_ok'] = terminal_ok
    result['trace_ok'] = trace_ok
    result['clock_ok'] = clock_ok
    result['evidence_ok'] = evidence_ok
    result['step_hook_ok'] = step_hook_ok
    result['no_expert_actions'] = no_expert_actions
    result['budget_ok'] = budget_ok
    result['no_runtime_error'] = no_runtime_error
    result['status'] = status
    result['success'] = success
    result['passed'] = success
    result['reasons'] = list(dict.fromkeys(reasons))
    result['verdict'] = {
        'protocol': 'stage6-bc-single-v1',
        'status': status,
        'success': success,
        'adapter': adapter,
        'terminal_ok': terminal_ok,
        'trace_ok': trace_ok,
        'clock_ok': result['clock_ok'],
        'evidence_ok': evidence_ok,
        'step_hook_ok': step_hook_ok,
        'no_expert_actions': no_expert_actions,
        'budget_ok': budget_ok,
        'no_runtime_error': no_runtime_error,
        'action_count': action_count,
        'budget': int(budget),
        'expert_target_consistency': expert_target_consistency,
        'expert_target_note': ('expert target identity is reported separately '
                               'and is not part of the Stage 6 success gate'),
        'reasons': result['reasons'],
        'note': ('Stage 6 BC acceptance is the frozen physics evaluator plus '
                 'terminal/evidence conditions; it is not a formal Day4 '
                 'expert-protocol success.'),
    }


def _finalize(rt, out, result, case, budget, hook, evidence, obs_rows):
    _save_observations(out, obs_rows, result)
    result['action_count'] = len(result['actions'])
    result['action_labels'] = [
        str(action.get('label', '')) for action in result['actions']]
    result['recovery_count'] = int(result.get('bc_recovery_releases', 0))
    result.setdefault('budget', {})
    result['budget']['used'] = len(result['actions'])
    result['budget']['within_limit'] = bool(
        len(result['actions']) <= int(budget))

    if hook is not None:
        try:
            hook.save_npz(Path(out) / 'step_hook.npz')
            result['step_hook'] = hook.summary()
            hook.save_json(Path(out) / 'step_hook.json')
        except BaseException as exc:
            result['errors'].append('StepHook save: ' + repr(exc))
            result['step_hook'] = hook.summary()
        try:
            hook.close()
        except BaseException as exc:
            result['errors'].append('StepHook close: ' + repr(exc))

    if evidence is not None:
        try:
            result['evidence'] = evidence.finish(result)
        except BaseException as exc:
            result['errors'].append('Evidence finalization: ' + repr(exc))
            result['passed'] = False

    if case is not None and result.get('release_clock'):
        try:
            rt.finish_metadata(out, result, case, 'single')
        except BaseException as exc:
            result['errors'].append('Metadata finalization: ' + repr(exc))

    trace_path = Path(out) / 'success_trace.npz'
    if trace_path.is_file():
        result['success_trace'] = {
            'path': 'success_trace.npz',
            'sha256': _sha256(trace_path),
        }
    final_path = Path(out) / 'final.npz'
    if final_path.is_file():
        result['final_npz'] = {
            'path': 'final.npz',
            'sha256': _sha256(final_path),
        }

    try:
        _evaluate_verdict(rt, out, result, budget)
    except BaseException as exc:
        result['errors'].append('Verdict finalization: ' + repr(exc))
        result['status'] = 'execution_error'
        result['success'] = False
        result['passed'] = False
        result['reasons'] = [repr(exc)]
        result['verdict'] = {
            'protocol': 'stage6-bc-single-v1',
            'status': 'execution_error',
            'success': False,
            'error': repr(exc),
            'reasons': [repr(exc)],
        }

    _write_json(Path(out) / 'result.json', result)
    _write_json(Path(out) / 'bc-verdict.json', result.get('verdict', {}))
    if not result.get('success'):
        failure = {
            'protocol': 'stage6-bc-single-v1',
            'status': result.get('status'),
            'success': False,
            'reasons': result.get('reasons', []),
            'errors': result.get('errors', []),
            'adapter': result.get('adapter'),
            'terminal_release': result.get('terminal_release'),
            'terminal_reasons': (result.get('terminal_release') or {}).get('reasons'),
            'partial_trace': result.get('partial_trace'),
            'evidence_checks': result.get('evidence_checks'),
            'step_hook': result.get('step_hook'),
            'budget': result.get('budget'),
            'last_action': (result['actions'][-1] if result['actions'] else None),
        }
        _write_json(Path(out) / 'failure.json', failure)


# ----------------------------------------------------------------------
# entry
# ----------------------------------------------------------------------
def _parse_args():
    parser = argparse.ArgumentParser(
        description='Stage 6 minimal single-step BC closed-loop entry')
    parser.add_argument('--initial-dir', type=Path, required=True,
                        help='passed Stage 4/5 initial case directory')
    parser.add_argument('--checkpoint', type=Path, default=None,
                        help='Stage 5 reduced single best.pt')
    parser.add_argument('--stats', type=Path, default=None,
                        help='train-only stats.json (or its directory)')
    parser.add_argument('--app-dir', type=Path, default=None,
                        help='frozen Stage 5 app directory')
    parser.add_argument('--repo-root', type=Path, default=None,
                        help='garmentlab-action-chunk-demo checkout')
    parser.add_argument('--out-root', type=Path, default=None,
                        help='parent directory for the new episode output')
    parser.add_argument('--out-dir', type=Path, default=None,
                        help='exact new output directory (must not exist)')
    parser.add_argument('--max-actions', type=int, default=None,
                        help='optional debug cap; cannot exceed the level budget')
    parser.add_argument('--label', default='day4-a5-bc-single',
                        help='output directory prefix')
    parser.add_argument('--skip-identity-check', action='store_true',
                        help='allow a different checkpoint/stats byte identity')
    parser.add_argument('--policy', choices=('bc', 'h4'), default='bc',
                        help='single-step BC or H=4 chunk policy')
    parser.add_argument('--execute-k', type=int, choices=(1, 2, 4), default=4,
                        help='H4 chunk actions executed before re-observing')
    parser.add_argument('--policy-device', choices=('cpu', 'cuda'), default='cpu',
                        help='policy forward device; Stage 8 timing uses cuda')
    return parser.parse_args()


def _collect_code_files(rt):
    paths = [
        HERE / 'a5_bc_single.py',
        HERE / 'h4_policy.py',
        HERE / 'h4_runner.py',
        HERE / 'step_hook.py',
        HERE / 'bc_eval_adapter.py',
        rt.training / 'bc_policy.py',
        rt.training / 'train_bc.py',
        rt.app / 'a5_l1.py',
        rt.app / 'a5_recovery.py',
        rt.app / 'a5_capture.py',
        rt.app / 'a5_entry.py',
        rt.app / 'stage4_success_v1.py',
        rt.app / 'stage4-success-v1.json',
        rt.app / 'l1_yaw_fold_geometry.py',
        rt.app / 'episode_evidence.py',
        rt.app / 'pfs1_observation_v2.py',
        rt.app / 'a5-manifest.json',
    ]
    files = {}
    for path in paths:
        path = Path(path)
        if path.is_file():
            files[str(path.resolve())] = _sha256(path)
    return files


def main():
    args = _parse_args()
    os.environ.setdefault('GARMENTLAB_ATTACHMENT_OVERLAP', '0.005')
    os.environ.setdefault('GARMENTLAB_DISABLED_ATTACHMENT_PROBE', '0')

    rt = load_runtime(args)
    init_dir = Path(args.initial_dir).resolve()
    try:
        init = json.loads((init_dir / 'result.json').read_text())
    except BaseException as exc:
        raise SystemExit('Cannot read initial result.json: ' + repr(exc))
    if init.get('passed') is not True:
        raise SystemExit('Initial state did not pass: ' + str(init_dir))
    case = init.get('initial_case')
    if not isinstance(case, dict):
        raise SystemExit('Initial result.json has no initial_case')
    level = case.get('level')
    if level not in ('flat', 'perturbed', 'crumpled'):
        raise SystemExit('Unknown initial level: %r' % (level,))
    if level not in rt.LEVEL_BUDGET:
        raise SystemExit('No BC budget for level: %r' % (level,))

    level_limit = int(rt.LEVEL_BUDGET[level])
    if args.max_actions is not None and not (1 <= args.max_actions <= level_limit):
        raise SystemExit('--max-actions must be within [1, %d] for %s'
                         % (level_limit, level))
    budget = int(args.max_actions if args.max_actions is not None else level_limit)

    checkpoint = resolve_checkpoint(args.checkpoint)
    stats = resolve_stats(args.stats)
    checkpoint_sha = _sha256(checkpoint)
    stats_sha = _sha256(stats)
    if not args.skip_identity_check:
        if checkpoint_sha != EXPECTED_CHECKPOINT_SHA256:
            raise SystemExit(
                'Checkpoint identity mismatch: %s != expected %s; use '
                '--skip-identity-check only for a reviewed replacement'
                % (checkpoint_sha, EXPECTED_CHECKPOINT_SHA256))
        if stats_sha != EXPECTED_STATS_SHA256:
            raise SystemExit(
                'Stats identity mismatch: %s != expected %s; use '
                '--skip-identity-check only for a reviewed replacement'
                % (stats_sha, EXPECTED_STATS_SHA256))

    candidate = json.loads((Path(rt.app) / 'a5-candidate.json').read_text())
    spec = candidate['tasks'][level]
    task = str(spec['task'])
    edge = str(spec['edge'])
    width_m = 0.2
    overhang_m = 0.02 if level == 'flat' else 0.0

    if args.out_dir is not None:
        out = Path(args.out_dir).resolve()
        if out.exists():
            raise SystemExit('Output directory already exists: ' + str(out))
        out.mkdir(parents=False)
    else:
        out_root = Path(
            args.out_root if args.out_root is not None
            else os.environ.get('STAGE6_OUT_ROOT', DEFAULT_OUT)).resolve()
        out_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        out = out_root / (str(args.label) + '-' + stamp)
        out.mkdir()

    code_files = _collect_code_files(rt)
    result = {
        'probe_version': 'stage6-bc-single-v1',
        'scope': ('Stage 6 minimal single-step BC closed-loop; no formal '
                  'Day4 success claim'),
        'utc': datetime.now(timezone.utc).isoformat(),
        'passed': False,
        'success': False,
        'status': 'running',
        'formal_day4_success': False,
        'fold_success_accepted': False,
        'initial_dir': str(init_dir),
        'initial_case': case,
        'initial_files': {
            name: _sha256(init_dir / name)
            for name in ('result.json', 'initial_geometry.npz')
            if (init_dir / name).is_file()
        },
        'initial_authorization': {
            'stage4_authorize_initial': False,
            'reason': ('Stage 6 uses passed val/unused initial cases; the frozen '
                       'Stage 4 dev/formal seed registry is not applicable'),
            'passed_flag': bool(init.get('passed')),
        },
        'execution_mode': 'single',
        'level': level,
        'task': task,
        'edge': edge,
        'width_m': width_m,
        'overhang_m': overhang_m,
        'budget': {
            'level_limit': level_limit,
            'requested': int(args.max_actions if args.max_actions is not None
                             else level_limit),
            'used': 0,
        },
        'actions': [],
        'events': [],
        'errors': [],
        'code_files': code_files,
        'policy': {
            'checkpoint': str(checkpoint),
            'checkpoint_sha256': checkpoint_sha,
            'stats': str(stats),
            'stats_sha256': stats_sha,
            'mode': 'single',
            'obs_dim': 1340,
            'device': args.policy_device,
            'source': ('Stage 5 reduced 50/10/10 single best.pt + '
                       'train-only stats.json'),
        },
    }

    backend = None
    evidence = None
    hook = None
    obs_rows = []
    initial = None
    local_points = None
    try:
        with _material_patch(rt, out, level):
            backend = _build_backend(rt, level, case, out)
            rt.start_with_square(backend, out, .0001)
            rt.pfs1.record_material_stage(
                backend, out, 'after_reset',
                expected_scale=0.0 if level == 'flat' else 1.0)
            evidence = rt.attach_evidence(backend, out, __file__, code_files)

        hook = rt.StepHook(backend).install()
        initial = _load_initial(rt, backend, init_dir, level, out)
        local_points = _load_local_points(out)
        if args.policy == 'h4':
            from h4_runner import run_policy_h4
            policy = rt.H4Policy(checkpoint, stats,
                                 device=args.policy_device)
            result['policy'].update({
                'kind': 'h4_chunk',
                'checkpoint_used': True,
                'checkpoint': str(checkpoint),
                'checkpoint_sha256': checkpoint_sha,
                'stats': str(stats),
                'stats_sha256': stats_sha,
                'horizon': 4,
                'execute_k': int(args.execute_k),
                'device': args.policy_device,
                'epoch': int(policy.epoch),
            })
            obs_rows, budget = run_policy_h4(
                rt, backend, out, result, evidence, case, level, args,
                local_points, policy, initial, obs_rows=obs_rows)
        else:
            policy = rt.BCPolicy(Path(checkpoint).parent, Path(stats).parent,
                                 device=args.policy_device)
            result['policy']['kind'] = 'learned_bc'
            result['policy']['checkpoint_used'] = True
            obs_rows, budget = _run_policy(
                rt, backend, out, result, evidence, case, level, args,
                local_points, policy, initial, obs_rows=obs_rows)
    except BaseException as exc:
        result['errors'].append(repr(exc))
        traceback.print_exc()
        # Fail-closed evidence: if the episode stopped before the terminal
        # release window, keep a one-frame partial trace of the actual state.
        try:
            if (backend is not None and initial is not None
                    and not (Path(out) / 'success_trace.npz').is_file()
                    and not (Path(out) / 'partial_trace.npz').is_file()):
                fold = result.get('fold_reference') or {}
                pick_index = fold.get('pick_index')
                yaw = fold.get('yaw_rad')
                if pick_index is None:
                    try:
                        slot = _expected_fold_slot(backend._env.control, level)
                        pick_index = int(slot.pick_index)
                    except BaseException:
                        pick_index = 0
                if yaw is None:
                    yaw = float(case.get('yaw_rad', 0.0))
                _save_partial_trace(
                    rt, backend, out, result, initial, pick_index, yaw,
                    ['episode stopped before terminal release: ' + repr(exc)])
        except BaseException as save_exc:
            result['errors'].append('Partial trace save: ' + repr(save_exc))
    finally:
        try:
            _finalize(rt, out, result, case, budget, hook, evidence, obs_rows)
        except BaseException as exc:
            result['errors'].append('Finalize: ' + repr(exc))
            traceback.print_exc()
            try:
                _write_json(Path(out) / 'result.json', result)
            except BaseException:
                pass
        # Print before closing the SimulationApp: close() can terminate the
        # process before any later print is flushed.
        print('RESULT_FILE', Path(out) / 'result.json', flush=True)
        print('DOWNLOAD_DIR', out, flush=True)
        if result.get('verdict'):
            print('BC_VERDICT', json.dumps(
                _json_safe(result['verdict']), default=_json_default,
                allow_nan=False), flush=True)
        if backend is not None:
            try:
                backend.stop()
            except BaseException as exc:
                print('STOP_ERROR', repr(exc), flush=True)

    if result.get('success'):
        raise SystemExit(0)
    if result.get('status') == 'rejected':
        raise SystemExit(1)
    raise SystemExit(3)


if __name__ == '__main__':
    main()
