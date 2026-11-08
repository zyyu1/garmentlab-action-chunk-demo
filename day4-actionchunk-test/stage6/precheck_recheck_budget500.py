"""Minimal pre-run checks for the budget500 L1 development recheck."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
STAGE5 = Path('/root/autodl-tmp/stage5-trial')
TRAIN = STAGE5 / 'training'
DEFAULT_CKPT = (STAGE5 / 'holdingfix-20261108' / 'diagnostics'
                / 'budget500' / 'best_val.pt')
DEFAULT_STATS = STAGE5 / 'holdingfix-20261108' / 'data' / 'stats.json'
DEFAULT_INITIAL = Path('/root/autodl-tmp/day4-square-initial-20261107-070155-602415')
DEFAULT_OBS = (STAGE5 / 'obs-formal'
               / 'day4-a5-rc2-l1-20261107-070512-123007')
DEFAULT_OUT = Path('/root/autodl-tmp/stage6_recheck_precheck.json')
EXPECTED_CKPT = 'ade6013141cfa3b114fe6583602da4b14486b96d736ffe5bbfd104cc3e517208'
EXPECTED_STATS = 'cbc4d711b2341b7ab786ca345ccb490bb32de1ebf93fb1eacc59de22d61a9ae9'
EXPECTED_RUNNER = '562386eec41826c818febbf930c7107f39b9d2ebafcc92de4b45be76c5205a7d'
EXPECTED_HOOK = '50aca4767d965871df80df06a233b438c17a45b6b88cb21275bd6eb2f7eb9b85'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', type=Path, default=DEFAULT_CKPT)
    parser.add_argument('--stats', type=Path, default=DEFAULT_STATS)
    parser.add_argument('--initial', type=Path, default=DEFAULT_INITIAL)
    parser.add_argument('--obs-dir', type=Path, default=DEFAULT_OBS)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    for path in (str(TRAIN), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from bc_policy import BCPolicy

    ckpt_hash = sha(args.checkpoint)
    stats_hash = sha(args.stats)
    runner_hash = sha(STAGE5 / 'stage6' / 'a5_bc_single.py')
    hook_hash = sha(STAGE5 / 'stage6' / 'step_hook.py')
    if ckpt_hash != EXPECTED_CKPT:
        raise SystemExit('checkpoint hash mismatch: ' + ckpt_hash)
    if stats_hash != EXPECTED_STATS:
        raise SystemExit('stats hash mismatch: ' + stats_hash)
    if runner_hash != EXPECTED_RUNNER:
        raise SystemExit('runner hash mismatch: ' + runner_hash)
    if hook_hash != EXPECTED_HOOK:
        raise SystemExit('step_hook hash mismatch: ' + hook_hash)

    ckpt = torch.load(args.checkpoint, map_location='cpu')
    stats = json.loads(args.stats.read_text(encoding='utf-8'))
    if int(ckpt['epoch']) != 498:
        raise SystemExit('expected epoch 498, got %r' % ckpt.get('epoch'))
    if ckpt['mode'] != 'single' or int(ckpt['in_dim']) != 1340:
        raise SystemExit('unexpected checkpoint architecture')
    if stats.get('holding_normalization') != 'identity':
        raise SystemExit('stats is not holdingfix identity')
    if abs(float(stats['obs_mean'][1339])) > 1e-12 or abs(
            float(stats['obs_std'][1339]) - 1.0) > 1e-12:
        raise SystemExit('holding stats are not identity')

    policy = BCPolicy(args.checkpoint.parent, args.stats.parent)
    if policy.holding_normalization != 'identity':
        raise SystemExit('BCPolicy did not load identity holding stats')
    obs_meta = json.loads(
        (args.obs_dir / 'action_002_obs.json').read_text(encoding='utf-8'))
    with np.load(args.obs_dir / 'action_002_obs.npz',
                 allow_pickle=False) as z:
        obs = policy.build_obs(z['vertices'], z['ee'], z['quat'], z['joints'],
                               obs_meta['holding'])
    if obs.shape != (1340,) or not np.isfinite(obs).all():
        raise SystemExit('invalid 1340-dim observation')
    prediction = policy.predict(obs)
    if not all(np.isfinite(prediction['xyz'])):
        raise SystemExit('non-finite prediction')

    initial_result = json.loads(
        (args.initial / 'result.json').read_text(encoding='utf-8'))
    if not (args.initial / 'initial_geometry.npz').is_file():
        raise SystemExit('missing initial_geometry.npz')
    episode = [json.loads(line) for line in
               (STAGE5 / 'final' / 'episodes.jsonl').read_text(
                   encoding='utf-8').splitlines() if line.strip()]
    row = [r for r in episode if int(r.get('seed', -1)) == 6120]
    if len(row) != 1 or row[0]['level'] != 'flat' or row[0]['split'] != 'val':
        raise SystemExit('6120 episode row is not flat/val')

    runner_text = (STAGE5 / 'stage6' / 'a5_bc_single.py').read_text(
        encoding='utf-8')
    required_markers = ('obs_rows', 'bc_observations.npz',
                        'partial_trace.npz', 'expert_target_consistency',
                        'DOWNLOAD_DIR')
    missing = [marker for marker in required_markers if marker not in runner_text]
    if missing:
        raise SystemExit('runner missing markers: %r' % missing)

    report = {
        'purpose': 'development_recheck_new_checkpoint_precheck',
        'checkpoint': str(args.checkpoint),
        'checkpoint_sha256': ckpt_hash,
        'checkpoint_epoch': int(ckpt['epoch']),
        'checkpoint_val_total': ckpt.get('val_total'),
        'checkpoint_mode': ckpt['mode'],
        'checkpoint_in_dim': int(ckpt['in_dim']),
        'checkpoint_hidden': int(ckpt['hidden']),
        'stats': str(args.stats),
        'stats_sha256': stats_hash,
        'holding_normalization': policy.holding_normalization,
        'holding_index': 1339,
        'holding_mean': float(stats['obs_mean'][1339]),
        'holding_std': float(stats['obs_std'][1339]),
        'obs_holding_input': bool(obs_meta['holding']),
        'obs_shape': list(obs.shape),
        'obs_finite': bool(np.isfinite(obs).all()),
        'prediction_action_002': prediction,
        'initial_dir': str(args.initial),
        'initial_result_json_sha256': sha(args.initial / 'result.json'),
        'initial_geometry_npz_sha256': sha(
            args.initial / 'initial_geometry.npz'),
        'initial_passed': initial_result.get('passed'),
        'episode_row': row[0],
        'runner_sha256': runner_hash,
        'step_hook_sha256': hook_hash,
        'runner_markers': list(required_markers),
        'torch_version': torch.__version__,
        'cuda_available': bool(torch.cuda.is_available()),
    }
    args.output.write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print('RECHECK_PRECHECK_OK')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
