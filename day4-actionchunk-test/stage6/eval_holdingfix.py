"""Offline metrics for the holding-fixed single BC model.

No simulation, no rollout, no retraining.  Run on the GPU host:
  /root/autodl-tmp/envs/isaac40/bin/python stage6/eval_holdingfix.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
STAGE5 = Path('/root/autodl-tmp/stage5-trial')
TRAIN = STAGE5 / 'training'
DEFAULT_DATA = STAGE5 / 'holdingfix-20261108' / 'data'
DEFAULT_RUN = STAGE5 / 'holdingfix-20261108' / 'runs' / 'single'
DEFAULT_RECOVERY = STAGE5 / 'holdingfix-20261108' / 'recovery'
DEFAULT_OBS = (STAGE5 / 'obs-formal'
               / 'day4-a5-rc2-l1-20261107-070512-123007')
DEFAULT_OUT = STAGE5 / 'holdingfix-20261108' / 'report'
PICKS = {'right_230': 230, 'left_210': 210, 'hem_10': 10}
MAX_REGION_DISTANCE = 0.03
HOLDING_INDEX = 1339


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def wrap(value):
    return float(np.arctan2(np.sin(value), np.cos(value)))


def split_metrics(pred_cont, pred_grip, target, split, mask):
    result = {}
    for name in ('train', 'val', 'test'):
        m = mask & (split == name)
        if not m.any():
            result[name] = {'n': 0}
            continue
        err = pred_cont[m, :3] - target[m, :3]
        result[name] = {
            'n': int(m.sum()),
            'xyz_coord_mae_m': float(np.abs(err).mean()),
            'xyz_euclidean_mae_m': float(np.linalg.norm(err, axis=1).mean()),
            'xyz_euclidean_median_m': float(np.median(
                np.linalg.norm(err, axis=1))),
            'xyz_euclidean_p95_m': float(np.percentile(
                np.linalg.norm(err, axis=1), 95)),
            'yaw_mae_rad': float(np.mean(np.abs(
                np.arctan2(np.sin(pred_cont[m, 3] - target[m, 3]),
                           np.cos(pred_cont[m, 3] - target[m, 3]))))),
            'gripper_accuracy': float((pred_grip[m] == target[m, 4]).mean()),
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--run', type=Path, default=DEFAULT_RUN)
    parser.add_argument('--recovery', type=Path, default=DEFAULT_RECOVERY)
    parser.add_argument('--obs-dir', type=Path, default=DEFAULT_OBS)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    for path in (str(TRAIN), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from bc_policy import BCPolicy
    from train_bc import obs_matrix

    data = np.load(args.data / 'dataset_single.npz', allow_pickle=True)
    arrays = {key: data[key] for key in data.files}
    stats = load_json(args.data / 'stats.json')
    policy = BCPolicy(args.run, args.data)
    if stats.get('holding_normalization') != 'identity':
        raise SystemExit('Expected identity holding normalization')
    if abs(float(stats['obs_mean'][HOLDING_INDEX])) > 1e-12:
        raise SystemExit('holding mean is not 0')
    if abs(float(stats['obs_std'][HOLDING_INDEX]) - 1.0) > 1e-12:
        raise SystemExit('holding std is not 1')

    # Input consistency: training matrix vs BCPolicy.build_obs, and identity
    # holding normalization on both paths.
    X_train = obs_matrix(arrays)
    policy_obs = np.stack([
        policy.build_obs(arrays['obs_vertices'][i], arrays['obs_ee'][i],
                         arrays['obs_quat'][i], arrays['obs_joints'][i],
                         arrays['obs_holding'][i])
        for i in range(len(arrays['seed']))
    ])
    mean = np.asarray(policy.obs_mean, dtype=np.float64)
    std = np.asarray(policy.obs_std, dtype=np.float64)
    X_norm = (X_train.astype(np.float64) - mean) / std
    P_norm = (policy_obs.astype(np.float64) - mean) / std
    input_consistency = {
        'n': int(len(X_train)),
        'raw_max_abs_diff': float(np.abs(
            X_train.astype(np.float64) - policy_obs.astype(np.float64)).max()),
        'raw_allclose_1e6': bool(np.allclose(
            X_train, policy_obs, atol=1e-6, rtol=0)),
        'normalized_max_abs_diff': float(np.abs(X_norm - P_norm).max()),
        'normalized_allclose_1e6': bool(np.allclose(
            X_norm, P_norm, atol=1e-6, rtol=0)),
        'holding_normalized_train_unique': np.unique(
            X_norm[:, HOLDING_INDEX]).tolist(),
        'holding_normalized_policy_unique': np.unique(
            P_norm[:, HOLDING_INDEX]).tolist(),
        'holding_raw_true': int((arrays['obs_holding'] > 0).sum()),
        'holding_raw_false': int((arrays['obs_holding'] == 0).sum()),
    }

    # Batched model output (same checkpoint/stats).
    X = P_norm.astype(np.float32)
    with torch.no_grad():
        pc, pg = policy.model(torch.tensor(X, dtype=torch.float32))
    pc = pc.numpy().astype(np.float64)
    pg = pg.numpy().astype(np.float64)
    c_mean = np.asarray(policy.c_mean, dtype=np.float64)
    c_std = np.asarray(policy.c_std, dtype=np.float64)
    pred_cont = pc * c_std + c_mean
    pred_grip = pg.argmax(axis=1)
    target = np.asarray(arrays['action'], dtype=np.float64)
    target_cont_norm = (target[:, :4] - c_mean) / c_std
    cont_mse_norm = float(((pc - target_cont_norm) ** 2).mean())
    log_probs = pg - pg.max(axis=1, keepdims=True)
    log_probs = log_probs - np.log(np.exp(log_probs).sum(axis=1, keepdims=True))
    grip_ce = float(-log_probs[np.arange(len(target)), target[:, 4].astype(int)].mean())
    split = arrays['split']
    all_mask = np.ones(len(target), dtype=bool)
    close_mask = target[:, 4] == 1
    metrics = {
        'all_actions': split_metrics(pred_cont, pred_grip, target, split,
                                     all_mask),
        'close_only': split_metrics(pred_cont, pred_grip, target, split,
                                    close_mask),
        'all_actions_overall': {
            'n': int(len(target)),
            'xyz_coord_mae_m': float(np.abs(
                pred_cont[:, :3] - target[:, :3]).mean()),
            'xyz_euclidean_mae_m': float(np.linalg.norm(
                pred_cont[:, :3] - target[:, :3], axis=1).mean()),
            'yaw_mae_rad': float(np.mean(np.abs(
                np.arctan2(np.sin(pred_cont[:, 3] - target[:, 3]),
                           np.cos(pred_cont[:, 3] - target[:, 3]))))),
            'gripper_accuracy': float((pred_grip == target[:, 4]).mean()),
            'cont_mse_normalized': cont_mse_norm,
            'grip_ce': grip_ce,
        },
        'close_overall': {
            'n': int(close_mask.sum()),
            'xyz_coord_mae_m': float(np.abs(
                pred_cont[close_mask, :3] - target[close_mask, :3]).mean()),
            'xyz_euclidean_mae_m': float(np.linalg.norm(
                pred_cont[close_mask, :3] - target[close_mask, :3],
                axis=1).mean()),
            'xyz_euclidean_median_m': float(np.median(np.linalg.norm(
                pred_cont[close_mask, :3] - target[close_mask, :3], axis=1))),
            'xyz_euclidean_p95_m': float(np.percentile(np.linalg.norm(
                pred_cont[close_mask, :3] - target[close_mask, :3], axis=1),
                95)),
        },
    }

    # 6120 expert action_002: new first prediction and prepared-region distance.
    with np.load(args.obs_dir / 'action_002_obs.npz',
                 allow_pickle=False) as z:
        obs_meta = load_json(args.obs_dir / 'action_002_obs.json')
        obs6120 = policy.build_obs(
            z['vertices'], z['ee'], z['quat'], z['joints'],
            obs_meta['holding'])
        vertices6120 = np.asarray(z['vertices'], dtype=np.float64).copy()
    prediction6120 = policy.predict(obs6120)
    target6120 = np.asarray(obs_meta['targets'][0], dtype=np.float64)
    regions = {}
    for name, index in PICKS.items():
        point = np.asarray(vertices6120[index], dtype=np.float64)
        regions[name] = {
            'pick_index': index,
            'vertex': point.tolist(),
            'distance_m': float(np.linalg.norm(
                point - np.asarray(prediction6120['xyz'], dtype=float))),
        }
    nearest = min(regions.items(), key=lambda item: item[1]['distance_m'])
    prediction6120_error = {
        'prediction': prediction6120,
        'expert_target': target6120.tolist(),
        'expert_command': int(obs_meta['commands'][0]),
        'gripper': int(prediction6120['gripper']),
        'xyz_l2_m': float(np.linalg.norm(
            np.asarray(prediction6120['xyz'], dtype=float) - target6120[:3])),
        'yaw_abs_wrapped_rad': abs(wrap(
            float(prediction6120['yaw']) - float(target6120[3]))),
        'gripper_match': int(prediction6120['gripper']) == int(obs_meta['commands'][0]),
        'nearest_region': nearest[0],
        'nearest_distance_m': nearest[1]['distance_m'],
        'max_distance_m': MAX_REGION_DISTANCE,
        'within_max_distance': bool(nearest[1]['distance_m'] < MAX_REGION_DISTANCE),
        'regions': regions,
        'split': 'val',
        'note': '6120 val debug record only; not independent generalization',
    }

    recovery_summary = load_json(
        args.recovery / 'holding_recovery_summary.json')
    recovery_validation = load_json(
        args.recovery / 'holding_validation.json')
    recovery_rows = [json.loads(line) for line in
                     (args.recovery / 'holding_recovery.jsonl')
                     .read_text(encoding='utf-8').splitlines() if line.strip()]
    source_counts = Counter()
    for row in recovery_rows:
        source = row.get('primary_source') or {}
        source_counts[str(source.get('kind'))] += 1
    holding_recovery = {
        'summary': recovery_summary,
        'validation': recovery_validation,
        'primary_source_kinds': dict(source_counts),
        'saved_json_holding_used_false': int(sum(
            row.get('saved_json_holding_used') is False
            for row in recovery_rows)),
        'saved_json_holding_false': int(sum(
            row.get('saved_json_holding_historical') is False
            for row in recovery_rows)),
    }

    old_metrics = load_json(TRAIN / 'runs' / 'single' / 'metrics.json')
    new_metrics = load_json(args.run / 'metrics.json')
    report = {
        'scope': 'offline evaluation only; no simulation/rollout/retraining',
        'data': str(args.data / 'dataset_single.npz'),
        'stats': str(args.data / 'stats.json'),
        'stats_sha256': hashlib.sha256(
            (args.data / 'stats.json').read_bytes()).hexdigest(),
        'checkpoint': str(args.run / 'best.pt'),
        'checkpoint_sha256': hashlib.sha256(
            (args.run / 'best.pt').read_bytes()).hexdigest(),
        'holding_normalization': {
            'mode': 'identity',
            'index': HOLDING_INDEX,
            'mean': 0.0,
            'std': 1.0,
        },
        'input_consistency': input_consistency,
        'holding_recovery': holding_recovery,
        'metrics': metrics,
        'old_model_metrics_reference': old_metrics,
        'new_model_metrics': new_metrics,
        '6120_action_002': prediction6120_error,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'offline_metrics.json').write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print('EVAL_HOLDINGFIX_OK')
    print(json.dumps({
        'input_consistency': input_consistency,
        'holding_recovery': {
            'actions_ok': recovery_summary.get('actions_ok'),
            'actions_expected': recovery_summary.get('actions_expected'),
            'source_kinds': dict(source_counts),
            'validation': recovery_validation,
        },
        'all_actions_overall': metrics['all_actions_overall'],
        'all_actions_by_split': metrics['all_actions'],
        'close_by_split': metrics['close_only'],
        '6120_action_002': prediction6120_error,
        'new_model_metrics': new_metrics,
    }, indent=2))


if __name__ == '__main__':
    main()
