"""Recover historical pre-action holding for the 70 Stage 5 demos.

No simulation.  Holding is read from the actual evidence timeline:
  * call 1: last ``state`` row before ``action_begin`` call 1;
  * call c>1: the ``action_end`` record of call c-1, cross-checked against the
    last ``state`` row before ``action_begin`` call c and result.json's
    post-previous-action holding.
The saved action_XXX_obs.json ``holding`` values are known to be false for all
historical rows and are recorded but never used as the source.

If any action cannot be aligned unambiguously, the script writes a coverage
report and exits 2 without creating a dataset/stats version.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
HOLDING_INDEX = 1339
TRAIN = Path('/root/autodl-tmp/stage5-trial/training')
DEFAULT_EPISODES = Path('/root/autodl-tmp/stage5-trial/final/episodes.jsonl')
DEFAULT_DATASET = TRAIN / 'final' / 'dataset_single.npz'
DEFAULT_OUT = Path('/root/autodl-tmp/stage5-trial/holdingfix-20261108')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def parse_timeline(path):
    begins = defaultdict(list)
    ends = defaultdict(list)
    states = []
    for line_no, line in enumerate(
            Path(path).read_text(encoding='utf-8').splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        row['_line_no'] = line_no
        kind = row.get('kind')
        if kind == 'action_begin':
            begins[int(row['call_id'])].append(row)
        elif kind == 'action_end':
            ends[int(row['call_id'])].append(row)
        elif kind == 'state':
            states.append(row)
    for key, values in list(begins.items()) + list(ends.items()):
        if len(values) != 1:
            raise ValueError('duplicate call_id %r in %s' % (key, path))
    return begins, ends, states


def last_state_before(states, begin):
    begin_step = int(begin.get('observed_step', -1))
    begin_mono = int(begin.get('monotonic_ns', 0))
    begin_time = float(begin.get('sim_time_s', -1.0))
    if begin_step < 0:
        return None
    candidates = [
        row for row in states
        if int(row.get('observed_step', -1)) <= begin_step
        and int(row.get('monotonic_ns', -1)) < begin_mono
        and float(row.get('sim_time_s', -1)) <= begin_time + 1e-6
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda row: int(row['monotonic_ns']))


def source_record(row):
    return {
        'file_kind': 'evidence/timeline.jsonl',
        'line_no': int(row['_line_no']),
        'kind': row.get('kind'),
        'call_id': row.get('call_id'),
        'observed_step': row.get('observed_step'),
        'sim_time_s': row.get('sim_time_s'),
        'backend_step': row.get('backend_step'),
        'holding': row.get('holding'),
        'attached': row.get('attached'),
        'logical_attached': row.get('logical_attached'),
        'enabled_slots': row.get('enabled_slots'),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--episodes', type=Path, default=DEFAULT_EPISODES)
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    episodes = [json.loads(line) for line in
                args.episodes.read_text(encoding='utf-8').splitlines()
                if line.strip()]
    data = np.load(args.dataset, allow_pickle=True)
    arrays = {key: data[key] for key in data.files}
    if len(episodes) != 70:
        raise SystemExit('Expected 70 episodes, got %d' % len(episodes))
    if len(arrays['seed']) != 590:
        raise SystemExit('Expected 590 single samples, got %d'
                         % len(arrays['seed']))

    episode_keys = [(str(e['level']), int(e['seed'])) for e in episodes]
    n_by_key = {(str(e['level']), int(e['seed'])): int(e['single_samples'])
                for e in episodes}
    if len(set(episode_keys)) != len(episode_keys):
        raise SystemExit('Duplicate episode level/seed')
    if sum(int(e['single_samples']) for e in episodes) != len(arrays['seed']):
        raise SystemExit('Episode sample count does not sum to dataset size')

    groups = {}
    for key in episode_keys:
        indices = np.where(
            (arrays['level'] == key[0]) & (arrays['seed'] == key[1]))[0]
        if len(indices) == 0:
            raise SystemExit('No dataset rows for %r' % (key,))
        if not np.array_equal(indices, np.arange(indices.min(),
                                                 indices.max() + 1)):
            raise SystemExit('Dataset rows are not contiguous for %r' % (key,))
        groups[key] = [int(i) for i in indices]

    rows = []
    missing = []
    ambiguous = []
    episode_reports = []
    for episode in episodes:
        level = str(episode['level'])
        seed = int(episode['seed'])
        key = (level, seed)
        result_dir = Path(episode['result_dir'])
        result_path = result_dir / 'result.json'
        timeline_path = result_dir / 'evidence' / 'timeline.jsonl'
        obs_dir = Path(episode['obs_dir'])
        n_expected = int(episode['single_samples'])
        dataset_indices = groups[key]
        episode_issues = []
        if not result_path.is_file():
            episode_issues.append('missing result.json')
            result = {}
        else:
            try:
                result = load_json(result_path)
            except Exception as exc:
                episode_issues.append('result.json parse: ' + repr(exc))
                result = {}
        actions = result.get('actions') or []
        if len(dataset_indices) != n_expected:
            episode_issues.append(
                'dataset rows %d != single_samples %d'
                % (len(dataset_indices), n_expected))
        if len(actions) != n_expected:
            episode_issues.append(
                'result actions %d != single_samples %d'
                % (len(actions), n_expected))
        if not timeline_path.is_file():
            episode_issues.append('missing evidence/timeline.jsonl')
            begins = ends = {}
            states = []
        else:
            try:
                begins, ends, states = parse_timeline(timeline_path)
            except Exception as exc:
                episode_issues.append('timeline parse: ' + repr(exc))
                begins = ends = {}
                states = []

        result_hash = sha(result_path) if result_path.is_file() else None
        timeline_hash = sha(timeline_path) if timeline_path.is_file() else None
        episode_report = {
            'level': level,
            'seed': seed,
            'result_dir': str(result_dir),
            'obs_dir': str(obs_dir),
            'single_samples': n_expected,
            'result_sha256': result_hash,
            'timeline_sha256': timeline_hash,
            'issues': list(episode_issues),
        }
        episode_reports.append(episode_report)

        for call_id in range(1, n_expected + 1):
            dataset_index = dataset_indices[call_id - 1]
            begin = (begins.get(call_id) or [None])[0]
            end = (ends.get(call_id) or [None])[0]
            status = 'ok'
            reasons = []
            primary = None
            state_check = None
            alignment = {}
            result_prev_holding = None
            saved_json_holding = None
            saved_json = None
            obs_match = None
            action_match = None
            holding = None
            if begin is None:
                status = 'missing'
                reasons.append('missing action_begin call_id=%d' % call_id)
                begin = {}
            if end is None:
                status = 'missing'
                reasons.append('missing action_end call_id=%d' % call_id)
                end = {}

            if call_id == 1:
                state = last_state_before(states, begin) if begin else None
                if state is None:
                    status = 'missing'
                    reasons.append('no state before action_begin call_id=1')
                else:
                    primary = state
                    state_check = state
                    holding = state.get('holding')
                    same_step = (int(state.get('observed_step', -1))
                                 == int(begin.get('observed_step', -2)))
                    same_time = abs(
                        float(state.get('sim_time_s', -1))
                        - float(begin.get('sim_time_s', -2))) <= 1e-6
                    alignment = {
                        'state_before_action_begin': True,
                        'state_observed_step': state.get('observed_step'),
                        'begin_observed_step': begin.get('observed_step'),
                        'state_sim_time_s': state.get('sim_time_s'),
                        'begin_sim_time_s': begin.get('sim_time_s'),
                        'same_step_as_begin': bool(same_step),
                        'same_time_as_begin': bool(same_time),
                        'state_monotonic_lt_begin': int(
                            state['monotonic_ns']) < int(begin['monotonic_ns']),
                    }
                    if not (same_step and same_time):
                        status = 'ambiguous'
                        reasons.append('pre-action state is not at the same '
                                       'step/time as action_begin')
            else:
                prev_end = (ends.get(call_id - 1) or [None])[0]
                state = last_state_before(states, begin) if begin else None
                if prev_end is None:
                    status = 'missing'
                    reasons.append('missing previous action_end call_id=%d'
                                   % (call_id - 1))
                else:
                    prev_holding = prev_end.get('holding')
                    begin_step = int(begin.get('observed_step', -2))
                    begin_time = float(begin.get('sim_time_s', -2))
                    prev_step = int(prev_end.get('observed_step', -3))
                    prev_time = float(prev_end.get('sim_time_s', -3))
                    state_after_prev = bool(
                        state is not None
                        and int(state.get('monotonic_ns', -1))
                        >= int(prev_end.get('monotonic_ns', 0))
                        and int(state.get('observed_step', -1)) == begin_step
                        and abs(float(state.get('sim_time_s', -1))
                                - begin_time) <= 1e-6)
                    if state_after_prev:
                        # A settle/hold may insert steps after the previous
                        # action_end (L2/L3 calls 6 and 12).  The last state
                        # before action_begin is then the actual pre-action
                        # state; use it and cross-check the previous end.
                        primary = state
                        state_check = state
                        holding = state.get('holding')
                        primary_kind = 'state_before_begin'
                        ordered = (int(prev_end.get('monotonic_ns', 0))
                                   <= int(state.get('monotonic_ns', 0))
                                   <= int(begin.get('monotonic_ns', 0)))
                        if not ordered:
                            status = 'ambiguous'
                            reasons.append('previous action_end is not before '
                                           'the pre-action state/begin')
                        if prev_holding != holding:
                            status = 'ambiguous'
                            reasons.append('pre-action state holding differs '
                                           'from previous action_end')
                    else:
                        # Normal immediate transition: the previous action_end
                        # is the last state before action_begin.
                        primary = prev_end
                        holding = prev_holding
                        primary_kind = 'previous_action_end'
                        if not (prev_step == begin_step
                                and abs(prev_time - begin_time) <= 1e-6
                                and int(prev_end.get('monotonic_ns', 0))
                                <= int(begin.get('monotonic_ns', 0))):
                            status = 'ambiguous'
                            reasons.append('no pre-action state between '
                                           'previous action_end and begin')
                    alignment = {
                        'primary_source_kind': primary_kind,
                        'state_before_begin_after_previous_end':
                            bool(state_after_prev),
                        'state_observed_step': (None if state is None
                                                else state.get('observed_step')),
                        'state_sim_time_s': (None if state is None
                                             else state.get('sim_time_s')),
                        'begin_observed_step': begin.get('observed_step'),
                        'begin_sim_time_s': begin.get('sim_time_s'),
                        'previous_action_end_call_id': call_id - 1,
                        'previous_end_observed_step': prev_end.get(
                            'observed_step'),
                        'previous_end_sim_time_s': prev_end.get('sim_time_s'),
                        'gap_steps_previous_to_begin':
                            int(begin.get('observed_step', -1)) - prev_step,
                        'gap_sim_time_previous_to_begin':
                            begin_time - prev_time,
                        'state_matches_previous_end_holding':
                            bool(state is not None
                                 and state.get('holding') == prev_holding),
                    }
                    result_prev = (actions[call_id - 2]
                                   if len(actions) >= call_id - 1 else None)
                    if result_prev is None:
                        status = 'missing'
                        reasons.append('missing result action %d'
                                       % (call_id - 1))
                    else:
                        result_prev_holding = result_prev.get('holding')
                        if result_prev_holding != holding:
                            status = 'ambiguous'
                            reasons.append('result post-previous holding '
                                           'differs from pre-action state')

            if not isinstance(holding, bool):
                status = 'missing' if status == 'ok' else status
                reasons.append('holding is not a bool: %r' % (holding,))

            # Action / observation identity checks.
            result_action = actions[call_id - 1] if len(actions) >= call_id else None
            dataset_action = np.asarray(arrays['action'][dataset_index],
                                        dtype=float)
            saved_json_path = obs_dir / ('action_%03d_obs.json' % call_id)
            saved_npz_path = obs_dir / ('action_%03d_obs.npz' % call_id)
            if result_action is None:
                status = 'missing'
                reasons.append('missing result action %d' % call_id)
            else:
                target = np.asarray(result_action.get('target_pose', []),
                                    dtype=float)
                command = int(result_action.get('command', -1))
                action_match = bool(
                    target.shape == (4,)
                    and np.allclose(dataset_action[:4], target, atol=1e-5,
                                    rtol=0)
                    and int(dataset_action[4]) == command)
                if not action_match:
                    status = 'ambiguous'
                    reasons.append('dataset action differs from result action')
            if saved_json_path.is_file():
                saved_json = load_json(saved_json_path)
                saved_json_holding = saved_json.get('holding')
                if int(saved_json.get('call_id', -1)) != call_id:
                    status = 'ambiguous'
                    reasons.append('saved obs call_id mismatch')
                saved_target = np.asarray(
                    (saved_json.get('targets') or [[None]])[0], dtype=float)
                saved_command = int((saved_json.get('commands') or [-1])[0])
                if not (np.allclose(dataset_action[:4], saved_target,
                                    atol=1e-5, rtol=0)
                        and int(dataset_action[4]) == saved_command):
                    status = 'ambiguous'
                    reasons.append('dataset action differs from saved obs')
            else:
                status = 'missing'
                reasons.append('missing saved action observation json')

            if saved_npz_path.is_file():
                try:
                    with np.load(saved_npz_path, allow_pickle=False) as z:
                        diffs = {
                            'vertices_max_abs_m': float(np.abs(
                                arrays['obs_vertices'][dataset_index]
                                - z['vertices']).max()),
                            'ee_max_abs_m': float(np.abs(
                                arrays['obs_ee'][dataset_index] - z['ee']).max()),
                            'quat_max_abs': float(np.abs(
                                arrays['obs_quat'][dataset_index]
                                - z['quat']).max()),
                            'joints_max_abs': float(np.abs(
                                arrays['obs_joints'][dataset_index]
                                - z['joints']).max()),
                        }
                    obs_match = max(diffs.values()) <= 1e-6
                    if not obs_match:
                        status = 'ambiguous'
                        reasons.append('dataset observation differs from saved '
                                       'obs npz: %r' % diffs)
                except Exception as exc:
                    status = 'ambiguous'
                    reasons.append('saved obs npz read: ' + repr(exc))
            else:
                status = 'missing'
                reasons.append('missing saved action observation npz')

            row = {
                'level': level,
                'seed': seed,
                'result_dir': str(result_dir),
                'obs_dir': str(obs_dir),
                'call_id': call_id,
                'action_index': call_id - 1,
                'dataset_index': dataset_index,
                'status': status,
                'holding': None if not isinstance(holding, bool) else holding,
                'reasons': reasons,
                'primary_source': (None if primary is None
                                   else source_record(primary)),
                'state_check': (None if state_check is None
                                else source_record(state_check)),
                'result_post_previous_holding': result_prev_holding,
                'saved_json_holding_historical': saved_json_holding,
                'saved_json_holding_used': False,
                'alignment': alignment,
                'action_match': action_match,
                'obs_match': obs_match,
                'result_sha256': result_hash,
                'timeline_sha256': timeline_hash,
            }
            rows.append(row)
            if status == 'missing':
                missing.append(row)
            elif status == 'ambiguous':
                ambiguous.append(row)

    coverage = {
        'episodes_expected': 70,
        'episodes_checked': len(episode_reports),
        'episodes_with_issues': [
            r for r in episode_reports if r['issues']],
        'actions_expected': 590,
        'actions_checked': len(rows),
        'actions_ok': sum(row['status'] == 'ok' for row in rows),
        'actions_missing': len(missing),
        'actions_ambiguous': len(ambiguous),
        'missing': [
            {k: row[k] for k in ('level', 'seed', 'call_id', 'dataset_index',
                                 'reasons')} for row in missing],
        'ambiguous': [
            {k: row[k] for k in ('level', 'seed', 'call_id', 'dataset_index',
                                 'reasons')} for row in ambiguous],
    }
    out = args.out
    (out / 'recovery').mkdir(parents=True, exist_ok=True)
    (out / 'recovery' / 'holding_recovery.jsonl').write_text(
        ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows),
        encoding='utf-8')
    (out / 'recovery' / 'holding_recovery_summary.json').write_text(
        json.dumps(coverage, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    (out / 'recovery' / 'episode_reports.json').write_text(
        json.dumps(episode_reports, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print(json.dumps({k: v for k, v in coverage.items()
                      if k not in ('missing', 'ambiguous')}, indent=2))
    if coverage['actions_ok'] != coverage['actions_expected']:
        print('RECOVERY_INCOMPLETE', coverage['actions_ok'],
              '/', coverage['actions_expected'])
        for row in (missing + ambiguous)[:20]:
            print('RECOVERY_BAD', row['level'], row['seed'], row['call_id'],
                  row['status'], row['reasons'])
        raise SystemExit(2)

    # Complete: build the revised single dataset.
    holding = np.zeros(len(arrays['seed']), dtype=np.float32)
    for row in rows:
        holding[int(row['dataset_index'])] = float(row['holding'])
    if not np.isfinite(holding).all() or len(holding) != 590:
        raise SystemExit('Invalid recovered holding array')
    new_arrays = {key: np.array(value, copy=True) for key, value in arrays.items()}
    new_arrays['obs_holding'] = holding
    for key in arrays:
        if key == 'obs_holding':
            continue
        if not np.array_equal(arrays[key], new_arrays[key]):
            raise SystemExit('Unexpected dataset change in ' + key)

    data_dir = out / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = data_dir / 'dataset_single.npz'
    np.savez_compressed(dataset_path, **new_arrays)

    if str(TRAIN) not in sys.path:
        sys.path.insert(0, str(TRAIN))
    from train_bc import obs_matrix
    X = obs_matrix(new_arrays)
    train_mask = new_arrays['split'] == 'train'
    obs_mean = X[train_mask].mean(0)
    obs_std = X[train_mask].std(0) + 1e-6
    obs_mean[HOLDING_INDEX] = 0.0
    obs_std[HOLDING_INDEX] = 1.0
    cont = new_arrays['action'][:, :4]
    cont_mean = cont[train_mask].mean(0)
    cont_std = cont[train_mask].std(0) + 1e-6
    original_stats = load_json(TRAIN / 'final' / 'stats.json')
    dataset_sha = sha(dataset_path)
    recovery_path = out / 'recovery' / 'holding_recovery.jsonl'
    episodes_sha = sha(args.episodes)
    original_dataset_sha = sha(args.dataset)
    stats = {
        'obs_dim': 1340,
        'obs_mean': obs_mean.tolist(),
        'obs_std': obs_std.tolist(),
        'cont_mean': cont_mean.tolist(),
        'cont_std': cont_std.tolist(),
        'gripper_classes': sorted(int(v) for v in np.unique(
            new_arrays['action'][:, 4])),
        'single_samples': int(len(X)),
        'h4_chunks': int(original_stats['h4_chunks']),
        'h4_mask_ones': int(original_stats['h4_mask_ones']),
        'h4_mask_total': int(original_stats['h4_mask_total']),
        'episodes': 70,
        'episode_names': sorted(
            '%s-%d' % (str(level), int(seed))
            for level, seed in episode_keys),
        'splits': {
            split: int((new_arrays['split'] == split).sum())
            for split in ('train', 'val', 'test')
        },
        'levels': {
            level: int((new_arrays['level'] == level).sum())
            for level in sorted(set(new_arrays['level'].tolist()))
        },
        'holding_normalization': 'identity',
        'holding_index': HOLDING_INDEX,
        'holding_mean': 0.0,
        'holding_std': 1.0,
        'source_dataset_sha256': original_dataset_sha,
        'source_episodes_sha256': episodes_sha,
        'holding_recovery_sha256': sha(recovery_path),
        'dataset_sha256': dataset_sha,
        'recovery': {
            'actions_ok': coverage['actions_ok'],
            'actions_expected': coverage['actions_expected'],
            'episodes_ok': 70,
        },
    }
    stats_path = data_dir / 'stats.json'
    stats_path.write_text(json.dumps(stats, indent=2, allow_nan=False) + '\n',
                          encoding='utf-8')
    config = {
        'label': 'Stage 5 holdingfix 20261108',
        'input_dim': 1340,
        'holding_normalization': 'identity',
        'holding_index': HOLDING_INDEX,
        'holding_mean': 0.0,
        'holding_std': 1.0,
        'source': {
            'original_dataset_sha256': original_dataset_sha,
            'episodes_sha256': episodes_sha,
            'holding_recovery_sha256': stats['holding_recovery_sha256'],
            'dataset_sha256': dataset_sha,
            'stats_sha256': sha(stats_path),
        },
        'training': {
            'mode': 'single',
            'architecture': 'MLP 512 -> 512 (GELU + LayerNorm)',
            'epochs': 100,
            'early_stop': 15,
            'batch': 128,
            'lr': 1e-3,
            'weight_decay': 1e-4,
            'seed': 0,
            'selection': 'best validation total loss; test never used for selection',
        },
        'splits': stats['splits'],
    }
    config_path = out / 'config.json'
    config_path.write_text(json.dumps(config, indent=2, allow_nan=False) + '\n',
                           encoding='utf-8')
    identity = {
        'original_dataset': str(args.dataset),
        'original_dataset_sha256': original_dataset_sha,
        'episodes': str(args.episodes),
        'episodes_sha256': episodes_sha,
        'holding_recovery': str(recovery_path),
        'holding_recovery_sha256': stats['holding_recovery_sha256'],
        'new_dataset': str(dataset_path),
        'new_dataset_sha256': dataset_sha,
        'new_stats': str(stats_path),
        'new_stats_sha256': sha(stats_path),
        'config': str(config_path),
        'config_sha256': sha(config_path),
    }
    (out / 'dataset_identity.json').write_text(
        json.dumps(identity, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')

    # Validation, not just non-zero.
    by_command = {}
    for command in (0, 1, 2):
        mask = new_arrays['action'][:, 4] == command
        by_command[str(command)] = {
            'n': int(mask.sum()),
            'holding_true': int((holding[mask] > 0).sum()),
        }
    by_call = {}
    for call_id in range(1, 13):
        mask = np.asarray([row['call_id'] == call_id for row in rows])
        if mask.any():
            by_call[str(call_id)] = {
                'n': int(mask.sum()),
                'holding_true': int(sum(
                    bool(row['holding']) for row in rows if row['call_id'] == call_id)),
            }
    validation = {
        'holding_true_total': int((holding > 0).sum()),
        'holding_false_total': int((holding == 0).sum()),
        'by_command': by_command,
        'by_call_id': by_call,
        'first_action_false': int(sum(
            not bool(row['holding']) for row in rows
            if row['call_id'] == 1)),
        'last_action_true': int(sum(
            bool(row['holding']) for row in rows
            if row['call_id'] == n_by_key[(row['level'], row['seed'])])),
        'previous_close_implies_next_true': int(sum(
            bool(rows[i]['holding']) for i in range(1, len(rows))
            if rows[i]['level'] == rows[i - 1]['level']
            and rows[i]['seed'] == rows[i - 1]['seed']
            and rows[i]['call_id'] == rows[i - 1]['call_id'] + 1
            and int(new_arrays['action'][rows[i - 1]['dataset_index'], 4]) == 1)),
        'previous_close_count': int(sum(
            int(new_arrays['action'][rows[i - 1]['dataset_index'], 4]) == 1
            for i in range(1, len(rows))
            if rows[i]['level'] == rows[i - 1]['level']
            and rows[i]['seed'] == rows[i - 1]['seed']
            and rows[i]['call_id'] == rows[i - 1]['call_id'] + 1)),
        'command1_holding_true': int(by_command['1']['holding_true']),
        'dataset_action_unchanged': bool(np.array_equal(
            arrays['action'], new_arrays['action'])),
        'dataset_split_unchanged': bool(np.array_equal(
            arrays['split'], new_arrays['split'])),
        'dataset_seed_level_unchanged': bool(
            np.array_equal(arrays['seed'], new_arrays['seed'])
            and np.array_equal(arrays['level'], new_arrays['level'])),
        'other_obs_arrays_unchanged': all(
            np.array_equal(arrays[key], new_arrays[key])
            for key in arrays if key != 'obs_holding'),
        'holding_normalization': 'identity',
        'holding_index': HOLDING_INDEX,
        'holding_mean': 0.0,
        'holding_std': 1.0,
    }
    (out / 'recovery' / 'holding_validation.json').write_text(
        json.dumps(validation, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print(json.dumps({
        'RECOVERY_COMPLETE': True,
        'actions_ok': coverage['actions_ok'],
        'dataset': str(dataset_path),
        'stats': str(stats_path),
        'config': str(config_path),
        'validation': validation,
        'identity': identity,
    }, indent=2))


if __name__ == '__main__':
    main()
