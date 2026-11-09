"""Freeze the Stage 8 seed list and paired single/H4 manifest.

Reads the actual initial directories and hashes; records Stage 4/5 expert
attempts, final split membership and Stage 6/7 debug history. No simulation.
"""
from __future__ import annotations

import hashlib
import json
import os
import glob
import datetime
from pathlib import Path

ROOT = Path('/root/autodl-tmp')
RUNNER = ROOT / 'stage5-trial' / 'stage6' / 'a5_bc_single.py'
H4_POLICY = ROOT / 'stage5-trial' / 'stage6' / 'h4_policy.py'
H4_RUNNER = ROOT / 'stage5-trial' / 'stage6' / 'h4_runner.py'
STEP_HOOK = ROOT / 'stage5-trial' / 'stage6' / 'step_hook.py'
BC_POLICY = ROOT / 'stage5-trial' / 'training' / 'bc_policy.py'
BATCH_DRIVER = ROOT / 'stage5-trial' / 'stage8' / 'batch_run.py'
SINGLE_CKPT = ROOT / 'stage5-trial' / 'holdingfix-20261108' / 'diagnostics' / 'budget500' / 'runtime_recheck' / 'best.pt'
SINGLE_STATS = ROOT / 'stage5-trial' / 'holdingfix-20261108' / 'data' / 'stats.json'
H4_CKPT = ROOT / 'stage5-trial' / 'holdingfix-20261108' / 'h4fix-20261108' / 'runs' / 'h4_budget500' / 'best_val.pt'
H4_STATS = ROOT / 'stage5-trial' / 'holdingfix-20261108' / 'h4fix-20261108' / 'stats.json'
OUT_FORMAL = ROOT / 'stage8_frozen' / 'STAGE8_FROZEN_MANIFEST.json'
OUT_DRY = ROOT / 'stage8_frozen' / 'STAGE8_DRYRUN_MANIFEST.json'

SINGLE_CKPT_SHA = 'ade6013141cfa3b114fe6583602da4b14486b96d736ffe5bbfd104cc3e517208'
SINGLE_STATS_SHA = 'cbc4d711b2341b7ab786ca345ccb490bb32de1ebf93fb1eacc59de22d61a9ae9'
H4_CKPT_SHA = 'ff8c694516eb8940e089aeb0a380daab6da0d84e9ab53aeaa6cd302c9a6c21d5'
H4_STATS_SHA = 'fe5df5c45fb29f0c96d38a7d6cae8b8f19464c51884ae6631bdaa3dc16d553fb'

CANDIDATES = {
    'flat': list(range(4110, 4120)) + list(range(6100, 6110)),
    'perturbed': list(range(4215, 4230)) + [6300, 6301, 6305, 6310, 6311],
    'crumpled': list(range(4313, 4320)) + [6500, 6501, 6503, 6506, 6509,
                                          6510, 6511, 6512, 6513, 6514, 6515,
                                          6518, 6519],
}
STAGE4 = {'flat': set(range(4110, 4118)),
          'perturbed': set(range(4210, 4216)),
          'crumpled': set(range(4310, 4317))}
DEBUG = {'flat': {6120, 6121, 6122, 6148, 6151},
         'perturbed': set(range(4210, 4215)),
         'crumpled': {6504, 6507, 4310, 4311, 4312}}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def find_initial(level, seed):
    for p in glob.glob(str(ROOT / 'day4-square-initial*')):
        rp = os.path.join(p, 'result.json')
        if not os.path.isfile(rp):
            continue
        try:
            d = json.loads(Path(rp).read_text(encoding='utf-8'))
        except Exception:
            continue
        c = d.get('initial_case') or {}
        if (c.get('level') == level and int(c.get('seed', -1)) == seed
                and d.get('passed') is True):
            return Path(p)
    return None


def main():
    final_rows = [json.loads(l) for l in (
        ROOT / 'stage5-trial' / 'final' / 'episodes.jsonl').read_text(
            encoding='utf-8').splitlines() if l.strip()]
    splits = {(r['level'], int(r['seed'])): r['split'] for r in final_rows}
    attempt_rows = [json.loads(l) for l in (
        ROOT / 'stage5-formal-state-v1' / 'attempts.jsonl').read_text(
            encoding='utf-8').splitlines() if l.strip()]
    attempts = {}
    for r in attempt_rows:
        if r.get('seed') is None:
            continue
        attempts.setdefault((r.get('level'), int(r['seed'])), []).append(
            r.get('state'))
    seeds = []
    for level, ordered in CANDIDATES.items():
        if len(ordered) != 20:
            raise SystemExit('%s candidate count %d' % (level, len(ordered)))
        for order, seed in enumerate(ordered, 1):
            initial = find_initial(level, seed)
            if initial is None:
                raise SystemExit('missing passed initial %s %s' % (level, seed))
            states = attempts.get((level, seed), [])
            split = splits.get((level, seed), 'unused')
            debug = seed in DEBUG[level]
            train_val = split in ('train', 'val')
            if train_val or debug:
                raise SystemExit('candidate overlaps train/val or debug: %s %s'
                                 % (level, seed))
            seeds.append({
                'level': level, 'seed': seed, 'order': order,
                'initial_dir': str(initial),
                'initial_result_sha256': sha(initial / 'result.json'),
                'initial_geometry_sha256': sha(initial / 'initial_geometry.npz'),
                'initial_png_sha256': sha(initial / 'initial.png'),
                'stage4_expert_used': seed in STAGE4[level],
                'stage5_expert_attempted': bool(states),
                'stage5_expert_states': states,
                'stage5_final_split': split,
                'stage6_7_debug': debug,
                'candidate_origin': ('new_stage8_generated' if 4220 <= seed <= 4229
                                     else 'existing_initial'),
                'history_note': (
                    ('Stage4 used; ' if seed in STAGE4[level] else '')
                    + ('Stage5 expert attempted ' + ','.join(states) + '; '
                       if states else '')
                    + ('Stage5 final ' + split if split != 'unused'
                       else 'not in final 70')),
            })
    if len(seeds) != 60:
        raise SystemExit('expected 60 seeds, got %d' % len(seeds))
    for level in CANDIDATES:
        if sum(1 for s in seeds if s['level'] == level) != 20:
            raise SystemExit('level count mismatch: ' + level)
    if sha(SINGLE_CKPT) != SINGLE_CKPT_SHA or sha(SINGLE_STATS) != SINGLE_STATS_SHA:
        raise SystemExit('single candidate hash mismatch')
    if sha(H4_CKPT) != H4_CKPT_SHA or sha(H4_STATS) != H4_STATS_SHA:
        raise SystemExit('H4 candidate hash mismatch')
    single_stats = json.loads(SINGLE_STATS.read_text(encoding='utf-8'))
    h4_stats = json.loads(H4_STATS.read_text(encoding='utf-8'))
    norm_equal = {}
    for key in ('obs_mean', 'obs_std', 'cont_mean', 'cont_std'):
        a = single_stats[key]
        b = h4_stats[key]
        norm_equal[key] = a == b
    if not all(norm_equal.values()):
        raise SystemExit('normalization arrays differ')
    policies = {
        'single': {
            'checkpoint': str(SINGLE_CKPT), 'checkpoint_sha256': SINGLE_CKPT_SHA,
            'stats': str(SINGLE_STATS), 'stats_sha256': SINGLE_STATS_SHA,
            'execute_k': 1, 'horizon': 1, 'updates': 2000,
        },
        'h4': {
            'checkpoint': str(H4_CKPT), 'checkpoint_sha256': H4_CKPT_SHA,
            'stats': str(H4_STATS), 'stats_sha256': H4_STATS_SHA,
            'execute_k': 4, 'horizon': 4, 'updates': 500,
        },
    }
    code = {
        'runner': {'path': str(RUNNER), 'sha256': sha(RUNNER)},
        'h4_policy': {'path': str(H4_POLICY), 'sha256': sha(H4_POLICY)},
        'h4_runner': {'path': str(H4_RUNNER), 'sha256': sha(H4_RUNNER)},
        'step_hook': {'path': str(STEP_HOOK), 'sha256': sha(STEP_HOOK)},
        'bc_policy': {'path': str(BC_POLICY), 'sha256': sha(BC_POLICY)},
        'batch_driver': {'path': str(BATCH_DRIVER), 'sha256': sha(BATCH_DRIVER)},
    }
    core = {
        'stage': 8, 'frozen': True,
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'candidate_source': 'Stage 8 offline plan; seed ascending, no result-based selection',
        'policies': policies, 'code': code,
        'normalization_arrays_equal': norm_equal,
        'execution': {
            'backend': 'same single Backend/initialization',
            'budgets': {'flat': 7, 'perturbed': 12, 'crumpled': 12},
            'terminal': 'same Stage 6 terminal and 331-frame window',
            'wait_protocol': 'same existing single/H4 wait protocol; no H4-specific settle/hold',
            'h4_execute_k': 4, 'extra_ablation': False,
            'timing': {'device': 'cuda', 'boundary': 'synchronized policy forward only',
                       'exclude': ['initialization', 'model loading', 'Isaac step', 'video write'],
                       'first_call': 'separate column'},
        },
        'seeds': seeds,
        'cases': [
            {'run_id': 'stage8-%s-%d-%s' % (s['level'], s['seed'], policy),
             'policy': policy, 'level': s['level'], 'seed': s['seed'],
             'initial_dir': s['initial_dir'],
             'initial_result_sha256': s['initial_result_sha256'],
             'initial_geometry_sha256': s['initial_geometry_sha256'],
             'execute_k': policies[policy]['execute_k']}
            for s in seeds for policy in ('single', 'h4')
        ],
    }
    core_bytes = json.dumps(core, sort_keys=True, separators=(',', ':')).encode()
    core['manifest_core_sha256'] = hashlib.sha256(core_bytes).hexdigest()
    OUT_FORMAL.parent.mkdir(parents=True, exist_ok=True)
    OUT_FORMAL.write_text(json.dumps(core, indent=2, ensure_ascii=False) + '\n',
                          encoding='utf-8')
    dry_seeds = []
    dry_exact = {
        6120: ROOT / 'day4-square-initial-20261107-070155-602415',
        6121: ROOT / 'day4-square-initial-20261107-072355-812558',
    }
    for seed in (6120, 6121):
        initial = dry_exact.get(seed) or find_initial('flat', seed)
        if initial is None or not Path(initial).is_dir():
            raise SystemExit('missing dry initial %d' % seed)
        dry_seeds.append({
            'level': 'flat', 'seed': seed, 'initial_dir': str(initial),
            'initial_result_sha256': sha(initial / 'result.json'),
            'initial_geometry_sha256': sha(initial / 'initial_geometry.npz'),
            'stage6_7_debug': True,
        })
    dry = {
        'stage': 8, 'kind': 'paired_pipeline_dry_run_only', 'frozen': True,
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'not_formal_matrix': True,
        'policies': policies, 'code': code,
        'seeds': dry_seeds,
        'cases': [
            {'run_id': 'stage8-dry-%d-%s' % (s['seed'], policy),
             'policy': policy, 'level': s['level'], 'seed': s['seed'],
             'initial_dir': s['initial_dir'],
             'initial_result_sha256': s['initial_result_sha256'],
             'initial_geometry_sha256': s['initial_geometry_sha256'],
             'execute_k': policies[policy]['execute_k']}
            for s in dry_seeds for policy in ('single', 'h4')
        ],
    }
    dry['manifest_core_sha256'] = hashlib.sha256(
        json.dumps(dry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    OUT_DRY.write_text(json.dumps(dry, indent=2, ensure_ascii=False) + '\n',
                       encoding='utf-8')
    print('FROZEN_SEEDS', len(seeds), 'CASES', len(core['cases']))
    print('FORMAL', OUT_FORMAL, core['manifest_core_sha256'])
    print('DRY', OUT_DRY, dry['manifest_core_sha256'])


if __name__ == '__main__':
    main()
