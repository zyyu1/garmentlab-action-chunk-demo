"""Offline real-torch comparison: expert action_002 obs vs 6120 rollout obs.

A: run BCPolicy on 6120's saved expert action_002 pre-execution observation.
B: the rollout's second prediction is taken from runner.log; its full 1340-dim
   closed-loop input was not saved (bc_observations.npz missing) and StepHook
   has no joint_positions, so B is NOT re-run.  Only the recoverable partial
   fields (vertices/EE/quat/holding) are compared.

Run on the GPU host:
  /root/autodl-tmp/envs/isaac40/bin/python stage6/compare_6120_observations.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
TRAINING = Path('/root/autodl-tmp/stage5-trial/training')
DEFAULT_RESULT = Path(
    '/root/autodl-tmp/stage6_runs/results/day4-a5-bc-single-20261109-015433-798440')
DEFAULT_ATTEMPT = Path(
    '/root/autodl-tmp/stage6_runs/attempts/6120-single-20261108-175431')
DEFAULT_OBS = Path(
    '/root/autodl-tmp/stage5-trial/obs-formal/'
    'day4-a5-rc2-l1-20261107-070512-123007')
DEFAULT_CHECKPOINT = TRAINING / 'runs' / 'single' / 'best.pt'
DEFAULT_STATS = TRAINING / 'final' / 'stats.json'
DEFAULT_OUTPUT = Path('/root/autodl-tmp/stage6_compare_6120.json')
PICKS = {'right_230': 230, 'left_210': 210, 'hem_10': 10}
MAX_REGION_DISTANCE = 0.03


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def wrap(value):
    return float(np.arctan2(np.sin(value), np.cos(value)))


def run_policy(policy, npz_path, json_path):
    meta = load_json(json_path)
    with np.load(npz_path, allow_pickle=False) as data:
        vertices = np.asarray(data['vertices'], dtype=float).copy()
        ee = np.asarray(data['ee'], dtype=float).reshape(3).copy()
        quat = np.asarray(data['quat'], dtype=float).reshape(4).copy()
        joints = np.asarray(data['joints'], dtype=float).reshape(-1).copy()
    obs = policy.build_obs(vertices, ee, quat, joints, meta['holding'])
    if obs.shape != (1340,) or not np.isfinite(obs).all():
        raise SystemExit('Invalid 1340-dim observation: %r' % (obs.shape,))
    prediction = policy.predict(obs)
    return {
        'obs_npz': str(npz_path),
        'obs_json': str(json_path),
        'obs_shape': list(obs.shape),
        'obs_finite': bool(np.isfinite(obs).all()),
        'holding': bool(meta['holding']),
        'vertices': vertices,
        'ee': ee,
        'quat': quat,
        'joints': joints,
        'prediction': prediction,
        'label': {
            'target': meta.get('targets', [None])[0],
            'command': (meta.get('commands') or [None])[0],
        },
    }


def target_errors(prediction, label):
    target = np.asarray(label['target'], dtype=float)
    xyz = np.asarray(prediction['xyz'], dtype=float)
    yaw = float(prediction['yaw'])
    return {
        'xyz_abs_axis_m': np.abs(xyz - target[:3]).tolist(),
        'xyz_l2_m': float(np.linalg.norm(xyz - target[:3])),
        'yaw_abs_wrapped_rad': abs(wrap(yaw - float(target[3]))),
        'gripper_match': int(prediction['gripper']) == int(label['command']),
        'expert_target': target.tolist(),
        'expert_command': int(label['command']),
    }


def region_distances(target, vertices):
    target = np.asarray(target, dtype=float).reshape(3)
    rows = {}
    for name, index in PICKS.items():
        point = np.asarray(vertices[index], dtype=float)
        rows[name] = {
            'pick_index': index,
            'vertex': point.tolist(),
            'distance_m': float(np.linalg.norm(point - target)),
        }
    nearest = min(rows.items(), key=lambda item: item[1]['distance_m'])
    return {
        'target': target.tolist(),
        'max_distance_m': MAX_REGION_DISTANCE,
        'regions': rows,
        'nearest': nearest[0],
        'nearest_distance_m': nearest[1]['distance_m'],
        'within_max_distance': bool(
            nearest[1]['distance_m'] < MAX_REGION_DISTANCE),
    }


def parse_runner_log(path):
    obs = {}
    pred = {}
    for line in Path(path).read_text(encoding='utf-8',
                                      errors='replace').splitlines():
        match = re.match(r'BC_OBS (\d+) (\{.*\})$', line)
        if match:
            obs[int(match.group(1))] = json.loads(match.group(2))
            continue
        match = re.match(r'BC_PREDICT (\d+) (\{.*\})$', line)
        if match:
            pred[int(match.group(1))] = json.loads(match.group(2))
    return obs, pred


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--result-dir', type=Path, default=DEFAULT_RESULT)
    parser.add_argument('--attempt-dir', type=Path, default=DEFAULT_ATTEMPT)
    parser.add_argument('--obs-dir', type=Path, default=DEFAULT_OBS)
    parser.add_argument('--checkpoint', type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument('--stats', type=Path, default=DEFAULT_STATS)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    for path in (HERE, TRAINING):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from bc_policy import BCPolicy

    policy = BCPolicy(args.checkpoint.parent, args.stats.parent)
    expert_001 = run_policy(
        policy, args.obs_dir / 'action_001_obs.npz',
        args.obs_dir / 'action_001_obs.json')
    expert_002 = run_policy(
        policy, args.obs_dir / 'action_002_obs.npz',
        args.obs_dir / 'action_002_obs.json')

    result = load_json(args.result_dir / 'result.json')
    started = load_json(args.attempt_dir / 'started.json')
    prior_action0 = result['actions'][0]
    action0_consistency = {
        'prior_action0_policy_target': prior_action0.get('policy', {}).get(
            'xyz'),
        'prior_action0_target_pose': prior_action0.get('target_pose'),
        'real_action001_prediction': expert_001['prediction'],
        'target_match': bool(np.allclose(
            np.asarray(expert_001['prediction']['xyz'], dtype=float),
            np.asarray(prior_action0['target_pose'][:3], dtype=float),
            atol=1e-6, rtol=0)),
        'yaw_match': bool(abs(wrap(
            float(expert_001['prediction']['yaw'])
            - float(prior_action0['target_pose'][3]))) < 1e-6),
        'gripper_match': bool(
            int(expert_001['prediction']['gripper'])
            == int(prior_action0['command'])),
    }

    obs_log, pred_log = parse_runner_log(args.attempt_dir / 'runner.log')
    closed_obs = obs_log.get(1)
    closed_prediction = pred_log.get(1)
    if closed_obs is None or closed_prediction is None:
        raise SystemExit('runner.log lacks BC_OBS/BC_PREDICT 1')

    with np.load(args.result_dir / 'step_hook.npz', allow_pickle=False) as z:
        step = np.asarray(z['absolute_step'])
        times = np.asarray(z['sim_time_s'])
        candidates = np.where(
            (step == int(closed_obs['absolute_step']))
            & (np.abs(times - float(closed_obs['sim_time_s'])) <= 1e-6))[0]
        if len(candidates) != 1:
            raise SystemExit('Expected one StepHook frame for closed-loop obs, '
                             'got %d' % len(candidates))
        index = int(candidates[0])
        closed_partial = {
            'step_hook_index': index,
            'absolute_step': int(step[index]),
            'sim_time_s': float(times[index]),
            'vertices': np.asarray(z['vertices'][index], dtype=float),
            'ee': np.asarray(z['ee_m'][index], dtype=float).reshape(3),
            'quat': np.asarray(z['ee_quaternion_wxyz'][index],
                              dtype=float).reshape(4),
            'holding': bool(z['holding'][index]),
            'gripper_state': int(z['gripper_state'][index]),
            'gripper_open': bool(z['gripper_open'][index]),
        }

    bc_obs_path = args.result_dir / 'bc_observations.npz'
    full_closed = None
    if bc_obs_path.is_file():
        with np.load(bc_obs_path, allow_pickle=False) as z:
            if 'obs' in z.files and len(z['obs']) > 1:
                full_closed = np.asarray(z['obs'][1], dtype=np.float32)

    # A2 vs B partial input differences.
    vertex_l2 = np.linalg.norm(
        expert_002['vertices'] - closed_partial['vertices'], axis=1)
    quat_a = expert_002['quat']
    quat_b = closed_partial['quat']
    quat_sign = min(np.linalg.norm(quat_a - quat_b),
                    np.linalg.norm(quat_a + quat_b))
    dot = abs(float(np.clip(np.dot(quat_a, quat_b), -1.0, 1.0)))
    input_differences = {
        'vertices_mean_l2_m': float(vertex_l2.mean()),
        'vertices_max_l2_m': float(vertex_l2.max()),
        'vertices_centroid_l2_m': float(np.linalg.norm(
            expert_002['vertices'].mean(axis=0)
            - closed_partial['vertices'].mean(axis=0))),
        'ee_l2_m': float(np.linalg.norm(expert_002['ee']
                                        - closed_partial['ee'])),
        'ee_delta_m': (closed_partial['ee'] - expert_002['ee']).tolist(),
        'quat_sign_invariant_l2': float(quat_sign),
        'quat_angle_rad': float(2.0 * np.arccos(np.clip(dot, -1.0, 1.0))),
        'joints': {
            'available': False,
            'reason': ('StepHook has no joint_positions and '
                       'bc_observations.npz is missing; cannot compare 9 joints'),
        },
        'holding': {
            'expert': expert_002['holding'],
            'closed_partial': closed_partial['holding'],
            'equal': expert_002['holding'] == closed_partial['holding'],
        },
        'full_1340_recoverable': bool(full_closed is not None),
    }

    a2_errors = target_errors(expert_002['prediction'],
                              expert_002['label'])
    b_errors = target_errors(closed_prediction,
                             {'target': expert_002['label']['target'],
                              'command': expert_002['label']['command']})
    a2_regions = region_distances(expert_002['prediction']['xyz'],
                                  expert_002['vertices'])
    b_regions = region_distances(closed_prediction['xyz'],
                                 closed_partial['vertices'])

    expert_error = a2_errors['xyz_l2_m']
    closed_error = b_errors['xyz_l2_m']
    if expert_error > MAX_REGION_DISTANCE and closed_error > MAX_REGION_DISTANCE:
        interpretation = ('both expert-observation and closed-loop predictions '
                          'show a large CLOSE error; prioritize fit, field order, '
                          'normalization and label alignment before attributing '
                          'to closed-loop drift')
    elif expert_error <= MAX_REGION_DISTANCE < closed_error:
        interpretation = ('expert-observation prediction is close but the '
                          'closed-loop prediction deviates; this is consistent '
                          'with post-execution observation change and error '
                          'growth, not a specific mechanism claim')
    else:
        interpretation = 'mixed/unexpected error pattern; inspect values'
    report = {
        'scope': 'offline real-torch comparison; no simulation, no rerun',
        'run_identity': {
            'result_dir': str(args.result_dir),
            'attempt_dir': str(args.attempt_dir),
            'run_runner_sha256': started.get('runner_sha256'),
            'current_runner_sha256': sha(Path(
                '/root/autodl-tmp/stage5-trial/stage6/a5_bc_single.py')),
            'checkpoint_sha256': sha(args.checkpoint),
            'stats_sha256': sha(args.stats),
            'torch': torch.__version__,
            'cuda_available': bool(torch.cuda.is_available()),
        },
        'expert_action_001': {
            'prediction': expert_001['prediction'],
            'label': expert_001['label'],
            'errors': target_errors(expert_001['prediction'],
                                    expert_001['label']),
        },
        'expert_action_002': {
            'prediction': expert_002['prediction'],
            'label': expert_002['label'],
            'errors': a2_errors,
            'regions': a2_regions,
        },
        'closed_loop_action_002': {
            'prediction_source': ('runner.log BC_PREDICT 1; actual rollout '
                                  'real-torch output, not re-run'),
            'prediction': closed_prediction,
            'obs_summary_from_log': closed_obs,
            'partial_obs_from_step_hook': {
                'absolute_step': closed_partial['absolute_step'],
                'sim_time_s': closed_partial['sim_time_s'],
                'holding': closed_partial['holding'],
                'gripper_state': closed_partial['gripper_state'],
                'gripper_open': closed_partial['gripper_open'],
                'frame_matches_obs_step_and_time': True,
            },
            'full_1340_recoverable': bool(full_closed is not None),
            'missing_fields': ([] if full_closed is not None else
                               ['obs 1340 (bc_observations.npz missing)',
                                'joints 9 (StepHook does not record joints)']),
            'errors': b_errors,
            'regions': b_regions,
        },
        'action_001_consistency': action0_consistency,
        'input_differences_a2_vs_b_partial': input_differences,
        'error_interpretation': {
            'expert_obs_close_error_m': expert_error,
            'closed_loop_close_error_m': closed_error,
            'max_region_distance_m': MAX_REGION_DISTANCE,
            'interpretation': interpretation,
            'mechanism_claim': False,
        },
        'notes': [
            'B was not re-run because its full 1340-dim input is not saved.',
            'No expert joints were substituted and no simulation data was added.',
            'The closed-loop prediction is the real rollout output from '
            'runner.log, not a recomputation.',
        ],
    }
    args.output.write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print('COMPARE_6120_OK')
    print(json.dumps({
        'expert_002_prediction': expert_002['prediction'],
        'present_002_prediction': closed_prediction,
        'expert_002_xyz_error_m': a2_errors['xyz_l2_m'],
        'closed_loop_xyz_error_m': b_errors['xyz_l2_m'],
        'expert_002_nearest_region_m': a2_regions['nearest_distance_m'],
        'closed_loop_nearest_region_m': b_regions['nearest_distance_m'],
        'joints_comparable': False,
        'full_closed_1340': bool(full_closed is not None),
        'action_001_matches_first_run': action0_consistency['target_match'],
        'interpretation': interpretation,
    }, indent=2))


if __name__ == '__main__':
    main()
