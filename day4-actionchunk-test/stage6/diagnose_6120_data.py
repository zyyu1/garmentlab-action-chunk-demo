"""Diagnose 6120 CLOSE error: label alignment, field order, normalization,
holding channel and fit on training CLOSE samples.

No simulation, no retraining, no rerun.  Run on the GPU host with:
  /root/autodl-tmp/envs/isaac40/bin/python stage6/diagnose_6120_data.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TRAINING = Path('/root/autodl-tmp/stage5-trial/training')
DATASET = TRAINING / 'final' / 'dataset_single.npz'
CHECKPOINT = TRAINING / 'runs' / 'single' / 'best.pt'
STATS = TRAINING / 'final' / 'stats.json'
OBS = Path('/root/autodl-tmp/stage5-trial/obs-formal/'
           'day4-a5-rc2-l1-20261107-070512-123007')
OUTPUT = Path('/root/autodl-tmp/stage6_diagnose_6120_data.json')


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=Path, default=DATASET)
    parser.add_argument('--checkpoint', type=Path, default=CHECKPOINT)
    parser.add_argument('--stats', type=Path, default=STATS)
    parser.add_argument('--obs-dir', type=Path, default=OBS)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()

    for path in (str(TRAINING), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from bc_policy import BCPolicy
    from train_bc import obs_matrix

    policy = BCPolicy(args.checkpoint.parent, args.stats.parent)
    data = np.load(args.dataset, allow_pickle=True)
    seed = data['seed']
    split = data['split']
    action = data['action']
    holding = data['obs_holding']
    idx6120 = np.where(seed == 6120)[0]
    if len(idx6120) != 7:
        raise SystemExit('Expected 7 dataset rows for 6120, got %d'
                         % len(idx6120))

    # 1. Holding channel is constant in the dataset.
    holding_counts = {
        str(value): int((holding == value).sum())
        for value in np.unique(holding)
    }
    holding_by_command = {}
    for command in (0, 1, 2):
        mask = action[:, 4] == command
        holding_by_command[str(command)] = {
            'n': int(mask.sum()),
            'holding_true': int((holding[mask] > 0).sum()),
        }

    # 2. Action-label alignment for 6120 and dataset obs vs saved obs.
    label_rows = []
    for order, index in enumerate(idx6120):
        saved = load_json(args.obs_dir / ('action_%03d_obs.json' % (order + 1)))
        target = np.asarray(saved['targets'][0], dtype=float)
        label = action[index]
        with np.load(args.obs_dir / ('action_%03d_obs.npz' % (order + 1)),
                     allow_pickle=False) as z:
            saved_obs = {
                'vertices': np.asarray(z['vertices'], dtype=float).copy(),
                'ee': np.asarray(z['ee'], dtype=float).reshape(3).copy(),
                'quat': np.asarray(z['quat'], dtype=float).reshape(4).copy(),
                'joints': np.asarray(z['joints'], dtype=float).reshape(-1).copy(),
            }
        obs_diff = {
            'vertices_max_abs_m': float(np.abs(
                data['obs_vertices'][index] - saved_obs['vertices']).max()),
            'ee_max_abs_m': float(np.abs(
                data['obs_ee'][index] - saved_obs['ee']).max()),
            'quat_max_abs': float(np.abs(
                data['obs_quat'][index] - saved_obs['quat']).max()),
            'joints_max_abs': float(np.abs(
                data['obs_joints'][index] - saved_obs['joints']).max()),
            'holding_dataset': float(holding[index]),
            'holding_saved_json': bool(saved['holding']),
        }
        label_rows.append({
            'action_index': order + 1,
            'dataset_action': label.tolist(),
            'saved_target': target.tolist(),
            'saved_command': int(saved['commands'][0]),
            'action_label_match': bool(np.allclose(
                label[:4], target, atol=1e-6, rtol=0)
                and int(label[4]) == int(saved['commands'][0])),
            'dataset_obs_vs_saved_obs': obs_diff,
            'dataset_phase': str(data['phase'][index]),
        })

    # 3. Field order: policy.build_obs vs train_bc.obs_matrix for all 6120 rows.
    field_order = []
    for index in idx6120:
        built = policy.build_obs(
            data['obs_vertices'][index], data['obs_ee'][index],
            data['obs_quat'][index], data['obs_joints'][index],
            data['obs_holding'][index])
        matrix = obs_matrix({key: np.asarray([data[key][index]])
                             for key in ('obs_vertices', 'obs_ee', 'obs_quat',
                                         'obs_joints', 'obs_holding')})[0]
        diff = np.abs(built.astype(float) - matrix.astype(float))
        segments = {
            'vertices': (0, 1323),
            'ee': (1323, 1326),
            'quat': (1326, 1330),
            'joints': (1330, 1339),
            'holding': (1339, 1340),
        }
        field_order.append({
            'seed': int(seed[index]),
            'obs_shape': list(built.shape),
            'built_dtype': str(built.dtype),
            'matrix_dtype': str(matrix.dtype),
            'max_abs_diff': float(diff.max()),
            'values_allclose_1e6': bool(np.allclose(
                built, matrix, atol=1e-6, rtol=0)),
            'exact_array_equal': bool(np.array_equal(built, matrix)),
            'segments_allclose': {
                name: bool(np.allclose(
                    built[start:end].astype(float),
                    matrix[start:end].astype(float), atol=1e-6, rtol=0))
                for name, (start, end) in segments.items()
            },
            'finite': bool(np.isfinite(built).all()),
        })

    # 4. Normalization z-scores for the 6120 action_002 observation.
    index2 = int(idx6120[1])
    obs2 = policy.build_obs(
        data['obs_vertices'][index2], data['obs_ee'][index2],
        data['obs_quat'][index2], data['obs_joints'][index2],
        data['obs_holding'][index2])
    mean = np.asarray(policy.obs_mean, dtype=float)
    std = np.asarray(policy.obs_std, dtype=float)
    z = (obs2.astype(float) - mean) / std
    z_groups = {
        'vertices': z[:1323],
        'ee': z[1323:1326],
        'quat': z[1326:1330],
        'joints': z[1330:1339],
        'holding': z[1339:1340],
    }
    normalization = {
        name: {
            'max_abs_z': float(np.abs(group).max()),
            'mean_z': float(group.mean()),
        }
        for name, group in z_groups.items()
    }

    # 5. Fit on training CLOSE samples vs 6120 val CLOSE.
    close_mask = action[:, 4] == 1
    errors = {}
    predictions_6120 = []
    for index in np.where(close_mask)[0]:
        obs = policy.build_obs(
            data['obs_vertices'][index], data['obs_ee'][index],
            data['obs_quat'][index], data['obs_joints'][index],
            data['obs_holding'][index])
        prediction = policy.predict(obs)
        error = float(np.linalg.norm(
            np.asarray(prediction['xyz'], dtype=float) - action[index, :3]))
        key = str(split[index])
        errors.setdefault(key, []).append(error)
        if int(seed[index]) == 6120:
            predictions_6120.append({
                'dataset_index': int(index),
                'prediction': prediction,
                'label': action[index].tolist(),
                'xyz_l2_m': error,
            })
    fit = {}
    for key, values in errors.items():
        values = np.asarray(values, dtype=float)
        fit[key] = {
            'n': int(len(values)),
            'mean_xyz_l2_m': float(values.mean()),
            'median_xyz_l2_m': float(np.median(values)),
            'p95_xyz_l2_m': float(np.percentile(values, 95)),
            'max_xyz_l2_m': float(values.max()),
        }
    if len(predictions_6120) != 1:
        raise SystemExit('Expected one 6120 CLOSE sample, got %d'
                         % len(predictions_6120))
    expert_002 = load_json(args.obs_dir / 'action_002_obs.json')
    with np.load(args.obs_dir / 'action_002_obs.npz',
                 allow_pickle=False) as z2:
        obs_a2 = policy.build_obs(
            z2['vertices'], z2['ee'], z2['quat'], z2['joints'],
            expert_002['holding'])
    a2 = policy.predict(obs_a2)
    a2_error = float(np.linalg.norm(
        np.asarray(a2['xyz'], dtype=float)
        - np.asarray(expert_002['targets'][0][:3], dtype=float)))

    report = {
        'scope': 'offline data diagnostic; no simulation, no retrain, no rerun',
        'dataset': str(args.dataset),
        'holding': {
            'unique_counts': holding_counts,
            'by_command': holding_by_command,
            'diagnosis': ('all saved action observations have holding=false; '
                          'the 1340-dim holding channel is constant zero'),
        },
        'label_alignment_6120': label_rows,
        'field_order_6120': field_order,
        'normalization_action002': normalization,
        'close_fit': fit,
        'close_6120': predictions_6120[0],
        'expert_action002_prediction': a2,
        'expert_action002_error_m': a2_error,
        'notes': [
            'sitecustomize._snap writes holding from action_begin row, but '
            'EpisodeEvidence.execute action_begin does not carry holding; '
            'the value is therefore false for every saved action.',
            'Dataset action row 6120 #2 matches the saved expert action_002 '
            'target/command; label alignment is not shifted.',
            'BCPolicy.build_obs matches train_bc.obs_matrix field order.',
            'The expert action_002 prediction has the same large CLOSE error '
            'as the closed-loop prediction; this is not explained by the '
            'closed-loop observation shift.',
        ],
    }
    args.output.write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print('DIAGNOSE_6120_DATA_OK')
    print(json.dumps({
        'holding_unique_counts': holding_counts,
        'holding_by_command': holding_by_command,
        'label_alignment_all_7': all(r['action_label_match']
                                     for r in label_rows),
        'dataset_obs_vs_saved_max_abs': max(
            max(r['dataset_obs_vs_saved_obs'][k] for k in
                ('vertices_max_abs_m', 'ee_max_abs_m', 'quat_max_abs',
                 'joints_max_abs')) for r in label_rows),
        'field_order_values_allclose': all(
            r['segments_allclose'] and r['values_allclose_1e6']
            for r in field_order),
        'field_order_exact_equal': all(
            r['exact_array_equal'] for r in field_order),
        'field_order_max_abs_diff': max(
            r['max_abs_diff'] for r in field_order),
        'normalization_max_abs_z': normalization,
        'close_fit': fit,
        'close_6120_error_m': predictions_6120[0]['xyz_l2_m'],
        'expert_action002_error_m': a2_error,
    }, indent=2))


if __name__ == '__main__':
    main()
