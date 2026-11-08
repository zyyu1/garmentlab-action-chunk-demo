"""Offline checks for the H4 L1 policy and chunk scheduler (no Isaac)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STAGE5 = Path('/root/autodl-tmp/stage5-trial')
TRAIN = STAGE5 / 'training'
H4 = STAGE5 / 'holdingfix-20261108' / 'h4fix-20261108'
CKPT = H4 / 'runs' / 'h4_budget500' / 'best_val.pt'
H4_STATS = H4 / 'stats.json'
SINGLE_STATS = STAGE5 / 'holdingfix-20261108' / 'data' / 'stats.json'
CKPT_SHA = 'ff8c694516eb8940e089aeb0a380daab6da0d84e9ab53aeaa6cd302c9a6c21d5'
H4_STATS_SHA = 'fe5df5c45fb29f0c96d38a7d6cae8b8f19464c51884ae6631bdaa3dc16d553fb'
OBS = STAGE5 / 'obs-formal' / 'day4-a5-rc2-l1-20261107-070512-123007'
OUT = H4 / 'diagnostics' / 'h4_l1_offline_check.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def schedule(predictions, budget, execute_k, terminal_at=None, fail_at=None):
    """Pure scheduler mirroring the H4 runner's budget/discard order."""
    calls = []
    action = 0
    while action < budget:
        remaining = budget - action
        limit = min(execute_k, remaining, 4)
        executed = []
        discarded = []
        stop = None
        for j in range(limit):
            if fail_at == (len(calls), j):
                stop = 'action_error'
                break
            executed.append(j)
            if terminal_at == (len(calls), j):
                stop = 'terminal'
                break
        if stop == 'terminal':
            discarded = [k for k in range(executed[-1] + 1, 4)]
        elif stop == 'action_error':
            discarded = [k for k in range(len(executed), 4)]
        else:
            discarded = [k for k in range(limit, 4)]
        calls.append({'executed': executed, 'discarded': discarded,
                      'stop': stop})
        action += len(executed)
        if stop == 'terminal' or stop == 'action_error':
            break
    return calls


def main():
    for path in (str(TRAIN), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from h4_policy import H4Policy

    if sha(CKPT) != CKPT_SHA:
        raise SystemExit('H4 checkpoint hash mismatch')
    if sha(H4_STATS) != H4_STATS_SHA:
        raise SystemExit('H4 stats hash mismatch')
    single_stats = json.loads(SINGLE_STATS.read_text(encoding='utf-8'))
    h4_stats = json.loads(H4_STATS.read_text(encoding='utf-8'))
    stats_equal = {}
    for key in ('obs_mean', 'obs_std', 'cont_mean', 'cont_std'):
        a = np.asarray(single_stats[key], dtype=float)
        b = np.asarray(h4_stats[key], dtype=float)
        stats_equal[key] = {
            'equal': bool(np.array_equal(a, b)),
            'max_abs_diff': float(np.abs(a - b).max()),
            'shape': list(a.shape),
        }
    if not all(item['equal'] for item in stats_equal.values()):
        raise SystemExit('single/H4 normalization arrays differ')

    policy = H4Policy(CKPT, H4_STATS)
    with np.load(OBS / 'action_001_obs.npz', allow_pickle=False) as z:
        meta = json.loads((OBS / 'action_001_obs.json').read_text(
            encoding='utf-8'))
        obs = policy.build_obs(z['vertices'], z['ee'], z['quat'],
                               z['joints'], meta['holding'])
    chunk = policy.predict_chunk(obs)
    if len(chunk['actions']) != 4:
        raise SystemExit('H4 policy did not return 4 actions')
    if chunk['cont_shape'] != [1, 4, 4] or chunk['gripper_logits_shape'] != [1, 4, 3]:
        raise SystemExit('H4 output shapes differ')
    for action in chunk['actions']:
        if not np.isfinite(action['xyz']).all() or not np.isfinite(action['yaw']):
            raise SystemExit('nonfinite H4 action')
        if action['gripper'] not in (0, 1, 2):
            raise SystemExit('invalid H4 gripper')

    cases = {}
    for execute_k in (1, 2, 4):
        calls = schedule([None] * 4, 7, execute_k)
        cases[str(execute_k)] = {
            'calls': len(calls),
            'executed': sum(len(c['executed']) for c in calls),
            'discarded': sum(len(c['discarded']) for c in calls),
            'schedule': calls,
        }
    fail = schedule([None] * 4, 7, 4, fail_at=(1, 1))
    term = schedule([None] * 4, 7, 4, terminal_at=(1, 1))
    checks = {
        'checkpoint': str(CKPT),
        'checkpoint_sha256': sha(CKPT),
        'stats': str(H4_STATS),
        'stats_sha256': sha(H4_STATS),
        'stats_normalization_equal_to_single': stats_equal,
        'stats_hash_note': ('hash differs only because H4 count metadata is '
                            'present; normalization arrays are byte-equal'),
        'holding_normalization': h4_stats.get('holding_normalization'),
        'obs_holding': bool(meta['holding']),
        'output_shapes': {
            'cont': chunk['cont_shape'],
            'gripper_logits': chunk['gripper_logits_shape'],
        },
        'predicted_actions': chunk['actions'],
        'inference_ms_raw': chunk['inference_ms'],
        'execute_k_schedules': cases,
        'failure_stop': fail,
        'terminal_stop': term,
        'budget': 7,
        'checks': {
            'four_actions': True,
            'finite': True,
            'budget_truncation_k4': (
                cases['4']['executed'] == 7
                and cases['4']['calls'] == 2
                and cases['4']['discarded'] == 1),
            'execute_k1': (
                cases['1']['executed'] == 7 and cases['1']['calls'] == 7
                and cases['1']['discarded'] == 21),
            'execute_k2': (
                cases['2']['executed'] == 7 and cases['2']['calls'] == 4),
            'failure_stops': (
                len(fail) == 2 and fail[1]['stop'] == 'action_error'
                and fail[1]['executed'] == [0]),
            'terminal_stops': (
                len(term) == 2 and term[1]['stop'] == 'terminal'
                and term[1]['executed'] == [0, 1]),
        },
        'test_evaluated': False,
        'isaac_started': False,
    }
    if not all(checks['checks'].values()):
        raise SystemExit('H4 offline schedule check failed: %r'
                         % checks['checks'])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(checks, indent=2, allow_nan=False) + '\n',
                   encoding='utf-8')
    print('H4_L1_OFFLINE_CHECK_OK')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
