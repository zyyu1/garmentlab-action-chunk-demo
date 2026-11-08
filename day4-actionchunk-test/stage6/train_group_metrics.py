"""Train-only grouping diagnostics for the holdingfix single model.

Tables:
  A. train, level x true command: n, XYZ Euclidean mean/median/P95, gripper acc.
  B. train CLOSE, by true action label (L1/L2 recovery/L2 fold/L3 recovery/L3 fold).
  C. predicted gripper distribution for the same CLOSE samples.

Action labels are used only for grouping.  They are not model inputs.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STAGE5 = Path('/root/autodl-tmp/stage5-trial')
TRAIN = STAGE5 / 'training'
DEFAULT_DATA = STAGE5 / 'holdingfix-20261108' / 'data'
DEFAULT_RUN = STAGE5 / 'holdingfix-20261108' / 'runs' / 'single'
DEFAULT_OUT = STAGE5 / 'holdingfix-20261108' / 'diagnostics'
CLOSE_LABELS = {
    ('flat', 'GRASP'): 'L1_grasp',
    ('perturbed', 'RECOVERY'): 'L2_recovery_grasp',
    ('perturbed', 'GRASP'): 'L2_fold_grasp',
    ('crumpled', 'RECOVERY'): 'L3_recovery_grasp',
    ('crumpled', 'GRASP'): 'L3_fold_grasp',
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def error_stats(errors):
    values = np.asarray(errors, dtype=np.float64)
    return {
        'n': int(len(values)),
        'xyz_euclidean_mean_m': float(values.mean()),
        'xyz_euclidean_median_m': float(np.median(values)),
        'xyz_euclidean_p95_m': float(np.percentile(values, 95)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--run', type=Path, default=DEFAULT_RUN)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    for path in (str(TRAIN), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from bc_policy import BCPolicy

    data = np.load(args.data / 'dataset_single.npz', allow_pickle=True)
    arrays = {key: data[key] for key in data.files}
    policy = BCPolicy(args.run, args.data)
    train = arrays['split'] == 'train'
    rows = []
    for index in np.where(train)[0]:
        prediction = policy.predict(policy.build_obs(
            arrays['obs_vertices'][index], arrays['obs_ee'][index],
            arrays['obs_quat'][index], arrays['obs_joints'][index],
            arrays['obs_holding'][index]))
        target = arrays['action'][index]
        rows.append({
            'dataset_index': int(index),
            'level': str(arrays['level'][index]),
            'seed': int(arrays['seed'][index]),
            'phase': str(arrays['phase'][index]),
            'command': int(target[4]),
            'pred_xyz': prediction['xyz'],
            'pred_yaw': prediction['yaw'],
            'pred_gripper': int(prediction['gripper']),
            'euclidean_m': float(np.linalg.norm(
                np.asarray(prediction['xyz'], dtype=float) - target[:3])),
            'coord_abs_mean_m': float(np.abs(
                np.asarray(prediction['xyz'], dtype=float) - target[:3]).mean()),
        })

    table_a = {}
    for level in sorted(set(row['level'] for row in rows)):
        for command in (0, 1, 2):
            subset = [row for row in rows
                      if row['level'] == level and row['command'] == command]
            if not subset:
                continue
            stats = error_stats([row['euclidean_m'] for row in subset])
            stats['gripper_accuracy'] = float(np.mean(
                [row['pred_gripper'] == command for row in subset]))
            table_a.setdefault(level, {})[str(command)] = stats

    close_rows = []
    for row in rows:
        if row['command'] != 1:
            continue
        label = CLOSE_LABELS.get((row['level'], row['phase']))
        if label is None:
            raise SystemExit('Unclassified CLOSE: %r' % (row,))
        row = dict(row)
        row['close_label'] = label
        close_rows.append(row)
    if len(close_rows) != 59:
        raise SystemExit('Expected 59 train CLOSE rows, got %d'
                         % len(close_rows))

    table_b = {}
    table_c = {}
    for label in CLOSE_LABELS.values():
        subset = [row for row in close_rows if row['close_label'] == label]
        if not subset:
            continue
        stats = error_stats([row['euclidean_m'] for row in subset])
        stats['gripper_accuracy'] = float(np.mean(
            [row['pred_gripper'] == 1 for row in subset]))
        stats['coord_abs_mean_m'] = float(np.mean(
            [row['coord_abs_mean_m'] for row in subset]))
        table_b[label] = stats
        counts = Counter(row['pred_gripper'] for row in subset)
        table_c[label] = {
            'n': len(subset),
            'true_gripper': 1,
            'pred_gripper_0': int(counts.get(0, 0)),
            'pred_gripper_1': int(counts.get(1, 0)),
            'pred_gripper_2': int(counts.get(2, 0)),
        }

    report = {
        'scope': 'train only; action labels are grouping variables only',
        'data': str(args.data / 'dataset_single.npz'),
        'stats': str(args.data / 'stats.json'),
        'checkpoint': str(args.run / 'best.pt'),
        'train_samples': int(train.sum()),
        'table_a_level_command': table_a,
        'table_b_close_by_label': table_b,
        'table_c_close_predicted_gripper': table_c,
        'notes': [
            'XYZ Euclidean = sqrt(dx^2+dy^2+dz^2); not Backend prepared-region distance.',
            'Error to expert target < 0.03 m is not the Backend prepared-region pass check.',
            'Labels are used only for analysis; model input remains 1340-dim.',
        ],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'train_tables.json').write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')

    lines = ['# Train-only grouping diagnostics', '',
             '## A. train by level x true command', '',
             '| level | command | n | XYZ Euclid mean | median | P95 | gripper acc |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for level in sorted(table_a):
        for command in ('0', '1', '2'):
            if command not in table_a[level]:
                continue
            s = table_a[level][command]
            lines.append('| %s | %s | %d | %.6f | %.6f | %.6f | %.4f |' % (
                level, command, s['n'], s['xyz_euclidean_mean_m'],
                s['xyz_euclidean_median_m'], s['xyz_euclidean_p95_m'],
                s['gripper_accuracy']))
    lines += ['', '## B. train CLOSE by true action label', '',
              '| label | n | XYZ Euclid mean | median | P95 | gripper acc |',
              '|---|---:|---:|---:|---:|---:|']
    for label in CLOSE_LABELS.values():
        if label not in table_b:
            continue
        s = table_b[label]
        lines.append('| %s | %d | %.6f | %.6f | %.6f | %.4f |' % (
            label, s['n'], s['xyz_euclidean_mean_m'],
            s['xyz_euclidean_median_m'], s['xyz_euclidean_p95_m'],
            s['gripper_accuracy']))
    lines += ['', '## C. predicted gripper on CLOSE', '',
              '| label | n | pred 0 | pred 1 | pred 2 |',
              '|---|---:|---:|---:|---:|']
    for label in CLOSE_LABELS.values():
        if label not in table_c:
            continue
        s = table_c[label]
        lines.append('| %s | %d | %d | %d | %d |' % (
            label, s['n'], s['pred_gripper_0'], s['pred_gripper_1'],
            s['pred_gripper_2']))
    lines += ['', 'Note: to-expert-target error is not the Backend prepared-region check.']
    (args.out / 'train_tables.md').write_text(
        '\n'.join(lines) + '\n', encoding='utf-8')
    print('TRAIN_TABLES_OK')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
