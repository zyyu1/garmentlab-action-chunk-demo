"""Real-torch preflight for the fixed L1 val seed 6120.

Run on the GPU host with:
  /root/autodl-tmp/envs/isaac40/bin/python stage6/check_6120_real.py

This is the real-model check, not the fake-torch offline unit test.  It:
  * verifies 6120 in the final Stage 5 episodes.jsonl is level=flat / split=val;
  * verifies the referenced initial case, task protocol and material settings;
  * records the full SHA256 of initial result.json, initial_geometry.npz,
    checkpoint and stats;
  * loads the real Stage 5 single checkpoint + train-only stats and runs one
    real forward pass on 6120's saved action_001 observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
TRAINING = Path('/root/autodl-tmp/stage5-trial/training')
APP = Path('/root/autodl-tmp/stage5-trial/app')
DEFAULT_RESULT = Path(
    '/root/autodl-tmp/day4-a5-rc2-l1-20261107-070512-123007')
DEFAULT_OBS = Path(
    '/root/autodl-tmp/stage5-trial/obs-formal/'
    'day4-a5-rc2-l1-20261107-070512-123007')
DEFAULT_EPISODES = Path('/root/autodl-tmp/stage5-trial/final/episodes.jsonl')
DEFAULT_CHECKPOINT = TRAINING / 'runs' / 'single' / 'best.pt'
DEFAULT_STATS = TRAINING / 'final' / 'stats.json'
EXPECTED_CHECKPOINT = (
    '5bff9e671c54b5240b93fefb5c67507987553153bad4b5ca0a5bb92d20e48ad6')
EXPECTED_STATS = (
    '8f1788d11803be7e22729758cf071f68d49ec5bae80aa387a3327112fcae746a')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--result-dir', type=Path, default=DEFAULT_RESULT)
    parser.add_argument('--obs-dir', type=Path, default=DEFAULT_OBS)
    parser.add_argument('--episodes', type=Path, default=DEFAULT_EPISODES)
    parser.add_argument('--checkpoint', type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument('--stats', type=Path, default=DEFAULT_STATS)
    parser.add_argument('--output', type=Path, default=Path(
        '/root/autodl-tmp/stage6_6120_real_check.json'))
    args = parser.parse_args()

    for path in (HERE, TRAINING, APP):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    rows = [json.loads(line) for line in
            Path(args.episodes).read_text(encoding='utf-8').splitlines()
            if line.strip()]
    matches = [row for row in rows if int(row.get('seed', -1)) == 6120]
    if len(matches) != 1:
        raise SystemExit('Expected exactly one 6120 episode row, got %d'
                         % len(matches))
    episode = matches[0]
    if (episode.get('level') != 'flat' or episode.get('split') != 'val'):
        raise SystemExit('6120 is not flat/val in final episodes.jsonl: %r'
                         % episode)
    if Path(episode['result_dir']) != args.result_dir:
        raise SystemExit('6120 result_dir mismatch: %r' % episode['result_dir'])
    if Path(episode['obs_dir']) != args.obs_dir:
        raise SystemExit('6120 obs_dir mismatch: %r' % episode['obs_dir'])

    result_path = args.result_dir / 'result.json'
    result = load_json(result_path)
    initial_dir = Path(result['initial_dir'])
    initial_path = initial_dir / 'result.json'
    geometry_path = initial_dir / 'initial_geometry.npz'
    initial = load_json(initial_path)
    case = result['initial_case']
    initial_case = initial['initial_case']

    if result.get('passed') is not True or initial.get('passed') is not True:
        raise SystemExit('6120 result/initial did not pass')
    if (int(case['seed']), case['level']) != (6120, 'flat'):
        raise SystemExit('6120 result initial_case mismatch: %r' % case)
    if (int(initial_case['seed']), initial_case['level']) != (6120, 'flat'):
        raise SystemExit('6120 initial_case mismatch: %r' % initial_case)
    protocol = initial.get('protocol') or {}
    if protocol.get('task') != 'A_l1_overfold':
        raise SystemExit('Unexpected task protocol: %r' % protocol.get('task'))
    if protocol.get('particle_friction_scale_expected') != 0.0:
        raise SystemExit('Unexpected L1 particle friction scale expectation')
    material = initial.get('material_readback') or {}
    if not (abs(float(material.get('friction', -1)) - .3) <= 1e-5
            and abs(float(material.get('particle_friction_scale', -1))) <= 1e-6):
        raise SystemExit('Unexpected L1 material readback: %r' % material)
    if 'particle friction scale 0' not in str(initial.get('physics_profile', '')):
        raise SystemExit('L1 physics profile does not state particle friction scale 0')

    with np.load(geometry_path, allow_pickle=False) as data:
        if 'settled' not in data.files:
            raise SystemExit('initial_geometry.npz missing settled')
        settled = np.asarray(data['settled'], dtype=np.float64)
    if settled.shape != (441, 3) or not np.isfinite(settled).all():
        raise SystemExit('Invalid settled geometry: %r' % (settled.shape,))

    hashes = {
        'initial_result_json': sha256(initial_path),
        'initial_geometry_npz': sha256(geometry_path),
        'checkpoint': sha256(args.checkpoint),
        'stats': sha256(args.stats),
    }
    if hashes['checkpoint'] != EXPECTED_CHECKPOINT:
        raise SystemExit('Checkpoint hash mismatch: ' + hashes['checkpoint'])
    if hashes['stats'] != EXPECTED_STATS:
        raise SystemExit('Stats hash mismatch: ' + hashes['stats'])

    from bc_policy import BCPolicy
    policy = BCPolicy(args.checkpoint.parent, args.stats.parent)

    obs_npz = args.obs_dir / 'action_001_obs.npz'
    obs_json = load_json(args.obs_dir / 'action_001_obs.json')
    with np.load(obs_npz, allow_pickle=False) as data:
        obs = policy.build_obs(
            data['vertices'], data['ee'], data['quat'], data['joints'],
            obs_json['holding'])
    if obs.shape != (1340,) or not np.isfinite(obs).all():
        raise SystemExit('Invalid 1340-dim observation: %r' % (obs.shape,))

    prediction = policy.predict(obs)
    xyz = np.asarray(prediction['xyz'], dtype=np.float64)
    yaw = float(prediction['yaw'])
    gripper = int(prediction['gripper'])
    if xyz.shape != (3,) or not np.isfinite(xyz).all():
        raise SystemExit('Non-finite policy XYZ: %r' % (xyz,))
    if not np.isfinite(yaw):
        raise SystemExit('Non-finite policy yaw')
    if gripper not in (0, 1, 2):
        raise SystemExit('Invalid gripper class: %r' % gripper)
    expert = obs_json.get('targets', [None])[0]
    expert_command = (obs_json.get('commands') or [None])[0]

    report = {
        'scope': 'real torch forward on 6120 saved action_001 observation',
        'episode': episode,
        'initial_dir': str(initial_dir),
        'initial_case': initial_case,
        'protocol': {
            'task': protocol.get('task'),
            'level': protocol.get('level'),
            'seed': protocol.get('seed'),
            'particle_friction_scale_expected':
                protocol.get('particle_friction_scale_expected'),
        },
        'material_readback': material,
        'initial_geometry_keys': ['settled'],
        'initial_geometry_shape': list(settled.shape),
        'sha256': hashes,
        'checkpoint': str(args.checkpoint),
        'stats': str(args.stats),
        'torch': {
            'version': torch.__version__,
            'cuda_available': bool(torch.cuda.is_available()),
            'device': 'cpu',
        },
        'obs_path': str(obs_npz),
        'obs_shape': list(obs.shape),
        'obs_finite': bool(np.isfinite(obs).all()),
        'holding': bool(obs_json['holding']),
        'prediction': {
            'xyz': xyz.tolist(),
            'yaw': yaw,
            'gripper': gripper,
        },
        'prediction_finite': bool(np.isfinite(xyz).all() and np.isfinite(yaw)),
        'expert_target': expert,
        'expert_command': expert_command,
        'gripper_mapping_ok': gripper in (0, 1, 2),
    }
    args.output.write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print('REAL_TORCH_FORWARD_OK')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
