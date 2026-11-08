"""Rebuild the corrected H=4 dataset from the corrected single dataset.

Every chunk input is the 1340-dim pre-action observation at the chunk start;
targets are at most four following actions; padding is excluded from loss.
No cross-episode chunks and no future observation are used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

STAGE5 = Path('/root/autodl-tmp/stage5-trial')
DEFAULT_SINGLE = STAGE5 / 'holdingfix-20261108' / 'data' / 'dataset_single.npz'
DEFAULT_OLD_H4 = STAGE5 / 'training' / 'final' / 'dataset_h4.npz'
DEFAULT_OUT = STAGE5 / 'holdingfix-20261108' / 'h4fix-20261108'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--single', type=Path, default=DEFAULT_SINGLE)
    parser.add_argument('--old-h4', type=Path, default=DEFAULT_OLD_H4)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    single = np.load(args.single, allow_pickle=True)
    old = np.load(args.old_h4, allow_pickle=True)
    arrays = {key: single[key].copy() for key in single.files}
    n_single = len(arrays['seed'])
    if n_single != 590:
        raise SystemExit('expected 590 single rows, got %d' % n_single)

    # Group single rows by episode, preserving the dataset order.
    groups = {}
    for index, (level, seed) in enumerate(zip(arrays['level'], arrays['seed'])):
        groups.setdefault((str(level), int(seed)), []).append(index)
    if len(groups) != 70:
        raise SystemExit('expected 70 episodes, got %d' % len(groups))
    for key, indices in groups.items():
        if len(indices) not in (7, 12):
            raise SystemExit('unexpected episode length %r: %d'
                             % (key, len(indices)))
        if indices != list(range(indices[0], indices[-1] + 1)):
            raise SystemExit('episode rows are not contiguous for %r' % (key,))

    rows = []
    for (level, seed), indices in groups.items():
        n = len(indices)
        split = str(arrays['split'][indices[0]])
        if any(str(arrays['split'][i]) != split for i in indices):
            raise SystemExit('split mismatch inside %r' % ((level, seed),))
        for start in range(0, n, 4):
            valid = min(4, n - start)
            if valid <= 0:
                continue
            index = indices[start]
            action = np.zeros((4, 5), dtype=np.float64)
            phase = np.full(4, 'PAD', dtype='<U8')
            mask = np.zeros(4, dtype=np.int8)
            for k in range(valid):
                source = indices[start + k]
                action[k] = arrays['action'][source]
                phase[k] = arrays['phase'][source]
                mask[k] = 1
            rows.append({
                'level': level,
                'seed': seed,
                'split': split,
                'start': start,
                'valid': valid,
                'obs_vertices_start': arrays['obs_vertices'][index],
                'obs_ee_start': arrays['obs_ee'][index],
                'obs_quat_start': arrays['obs_quat'][index],
                'obs_joints_start': arrays['obs_joints'][index],
                'obs_holding': float(arrays['obs_holding'][index]),
                'obs_holding_start': float(arrays['obs_holding'][index]),
                'action': action,
                'phase': phase,
                'mask': mask,
                'source_index': index,
            })

    h4 = {
        'obs_vertices_start': np.stack([r['obs_vertices_start'] for r in rows]),
        'obs_ee_start': np.stack([r['obs_ee_start'] for r in rows]),
        'obs_quat_start': np.stack([r['obs_quat_start'] for r in rows]),
        'obs_joints_start': np.stack([r['obs_joints_start'] for r in rows]),
        'action': np.stack([r['action'] for r in rows]),
        'phase': np.stack([r['phase'] for r in rows]),
        'mask': np.stack([r['mask'] for r in rows]),
        'chunk_start_index': np.asarray([r['start'] for r in rows], dtype=np.int64),
        'seed': np.asarray([r['seed'] for r in rows], dtype=np.int64),
        'level': np.asarray([r['level'] for r in rows], dtype='<U9'),
        'split': np.asarray([r['split'] for r in rows], dtype='<U5'),
        'obs_holding': np.asarray([r['obs_holding'] for r in rows], dtype=np.float32),
        'obs_holding_start': np.asarray(
            [r['obs_holding_start'] for r in rows], dtype=np.float32),
    }
    if len(rows) != 160:
        raise SystemExit('expected 160 chunks, got %d' % len(rows))
    if int(h4['mask'].sum()) != 590:
        raise SystemExit('expected 590 valid actions, got %d'
                         % int(h4['mask'].sum()))
    if int(h4['mask'].size - h4['mask'].sum()) != 50:
        raise SystemExit('expected 50 padding slots')

    # Exact structural checks against the corrected single data.
    max_obs_diff = 0.0
    max_action_diff = 0.0
    for i, row in enumerate(rows):
        source = row['source_index']
        for key, target in (
                ('obs_vertices_start', 'obs_vertices'),
                ('obs_ee_start', 'obs_ee'),
                ('obs_quat_start', 'obs_quat'),
                ('obs_joints_start', 'obs_joints')):
            max_obs_diff = max(max_obs_diff, float(np.abs(
                h4[key][i] - arrays[target][source]).max()))
        for k in range(row['valid']):
            max_action_diff = max(max_action_diff, float(np.abs(
                h4['action'][i, k] - arrays['action'][
                    groups[(row['level'], row['seed'])][row['start'] + k]]).max()))
        if row['start'] + row['valid'] > len(groups[(row['level'], row['seed'])]):
            raise SystemExit('chunk crosses episode boundary')
    if max_obs_diff > 1e-9:
        raise SystemExit('chunk start observation differs from single: %r'
                         % max_obs_diff)
    if max_action_diff > 1e-9:
        raise SystemExit('chunk target differs from single: %r' % max_action_diff)

    # Old H4 structural fields should match; only holding/metadata changes.
    old_structural_equal = {
        key: bool(np.array_equal(old[key], h4[key]))
        for key in ('action', 'mask', 'chunk_start_index', 'seed', 'level',
                    'split', 'phase')
    }

    dataset_h4_path = args.out / 'dataset_h4.npz'
    np.savez_compressed(dataset_h4_path, **h4)
    # Keep a byte-identical reference copy of the shared single data.
    dataset_single_path = args.out / 'dataset_single.npz'
    if dataset_single_path.resolve() != args.single.resolve():
        np.savez_compressed(dataset_single_path, **arrays)

    stats = json.loads((STAGE5 / 'holdingfix-20261108' / 'data' /
                        'stats.json').read_text(encoding='utf-8'))
    stats.update({
        'h4_chunks': int(len(rows)),
        'h4_mask_ones': int(h4['mask'].sum()),
        'h4_mask_total': int(h4['mask'].size),
        'h4_holding': 'corrected single holding at chunk start',
        'h4_source_dataset_sha256': sha(dataset_h4_path),
        'h4_old_dataset_sha256': sha(args.old_h4),
        'h4_single_dataset_sha256': sha(args.single),
        'h4_checks': {
            'chunks': int(len(rows)),
            'valid_actions': int(h4['mask'].sum()),
            'padding': int(h4['mask'].size - h4['mask'].sum()),
            'max_start_obs_diff': max_obs_diff,
            'max_action_diff': max_action_diff,
            'old_structural_equal': old_structural_equal,
        },
    })
    (args.out / 'stats.json').write_text(
        json.dumps(stats, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    config = {
        'label': 'holdingfix H4 rebuild 20261108',
        'input_dim': 1340,
        'horizon': 4,
        'holding_normalization': 'identity',
        'holding_index': 1339,
        'source_single': str(args.single),
        'source_single_sha256': sha(args.single),
        'old_h4': str(args.old_h4),
        'old_h4_sha256': sha(args.old_h4),
        'new_h4': str(dataset_h4_path),
        'new_h4_sha256': sha(dataset_h4_path),
        'stats_sha256': sha(args.out / 'stats.json'),
        'chunks': int(len(rows)),
        'valid_actions': int(h4['mask'].sum()),
        'padding': int(h4['mask'].size - h4['mask'].sum()),
    }
    (args.out / 'config.json').write_text(
        json.dumps(config, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    identity = {
        'new_h4': str(dataset_h4_path),
        'new_h4_sha256': sha(dataset_h4_path),
        'new_stats': str(args.out / 'stats.json'),
        'new_stats_sha256': sha(args.out / 'stats.json'),
        'source_single': str(args.single),
        'source_single_sha256': sha(args.single),
        'old_h4': str(args.old_h4),
        'old_h4_sha256': sha(args.old_h4),
    }
    (args.out / 'dataset_identity.json').write_text(
        json.dumps(identity, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    checks = {
        'chunks': int(len(rows)),
        'valid_actions': int(h4['mask'].sum()),
        'padding': int(h4['mask'].size - h4['mask'].sum()),
        'chunks_by_level': {
            level: int((h4['level'] == level).sum())
            for level in sorted(set(h4['level'].tolist()))
        },
        'valid_by_level': {
            level: int(h4['mask'][h4['level'] == level].sum())
            for level in sorted(set(h4['level'].tolist()))
        },
        'chunks_by_split': {
            split: int((h4['split'] == split).sum())
            for split in ('train', 'val', 'test')
        },
        'valid_by_split': {
            split: int(h4['mask'][h4['split'] == split].sum())
            for split in ('train', 'val', 'test')
        },
        'max_start_obs_diff': max_obs_diff,
        'max_action_diff': max_action_diff,
        'no_cross_episode': True,
        'no_future_observation': True,
        'old_structural_equal': old_structural_equal,
        'holding_true': int((h4['obs_holding'] > 0).sum()),
        'holding_false': int((h4['obs_holding'] == 0).sum()),
        'identity': identity,
    }
    (args.out / 'h4_data_check.json').write_text(
        json.dumps(checks, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print('H4_REBUILD_OK')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
