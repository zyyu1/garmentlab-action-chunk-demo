"""Freeze the L1 development-evaluation manifest before any new run."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

STAGE5 = Path('/root/autodl-tmp/stage5-trial')
EPISODES = STAGE5 / 'final' / 'episodes.jsonl'
CKPT = STAGE5 / 'holdingfix-20261108' / 'diagnostics' / 'budget500' / 'best_val.pt'
STATS = STAGE5 / 'holdingfix-20261108' / 'data' / 'stats.json'
RUNNER = STAGE5 / 'stage6' / 'a5_bc_single.py'
EXISTING_6120_RESULT = Path(
    '/root/autodl-tmp/stage6_runs/results/'
    'day4-a5-bc-recheck-budget500-20261109-030302-075279')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path(
        '/root/autodl-tmp/stage6_runs/evals/l1_dev_budget500_20261108'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in EPISODES.read_text(
        encoding='utf-8').splitlines() if line.strip()]
    flat_val = sorted((r for r in rows
                       if r['level'] == 'flat' and r['split'] == 'val'),
                      key=lambda r: int(r['seed']))
    seeds = [int(r['seed']) for r in flat_val]
    if 6120 not in seeds:
        raise SystemExit('6120 not in flat/val list')
    extras = [seed for seed in seeds if seed != 6120][:4]
    if len(extras) != 4:
        raise SystemExit('Need four extra flat/val seeds')
    selected = [6120] + extras
    cases = []
    for seed in selected:
        row = [r for r in flat_val if int(r['seed']) == seed][0]
        result_dir = Path(row['result_dir'])
        result = json.loads((result_dir / 'result.json').read_text(
            encoding='utf-8'))
        initial = Path(result['initial_dir'])
        if not (initial / 'result.json').is_file():
            raise SystemExit('missing initial result for %d' % seed)
        if not (initial / 'initial_geometry.npz').is_file():
            raise SystemExit('missing initial geometry for %d' % seed)
        initial_result = json.loads((initial / 'result.json').read_text(
            encoding='utf-8'))
        if initial_result.get('passed') is not True:
            raise SystemExit('initial not passed for %d' % seed)
        cases.append({
            'seed': seed,
            'level': 'flat',
            'split': 'val',
            'demo_result_dir': str(result_dir),
            'obs_dir': row['obs_dir'],
            'initial_dir': str(initial),
            'initial_result_json_sha256': sha(initial / 'result.json'),
            'initial_geometry_npz_sha256': sha(
                initial / 'initial_geometry.npz'),
            'initial_passed': True,
            'single_samples': int(row['single_samples']),
        })
    manifest = {
        'purpose': 'development_evaluation_l1',
        'not_independent_test': True,
        'model': {
            'checkpoint_source': str(CKPT),
            'checkpoint_sha256': sha(CKPT),
            'checkpoint_epoch': 498,
            'stats': str(STATS),
            'stats_sha256': sha(STATS),
            'runner': str(RUNNER),
            'runner_sha256': sha(RUNNER),
        },
        'seed_selection': {
            'source': str(EPISODES),
            'rule': ('flat/val seeds sorted ascending; include 6120; '
                     'take the first four other seeds; no train/test'),
            'all_flat_val_seeds': seeds,
            'selected': selected,
            'extra_excluding_6120': extras,
        },
        'cases': cases,
        'existing_learned_6120': {
            'result_dir': str(EXISTING_6120_RESULT),
            'status': 'execution_error',
            'action_count': 1,
            'close_distance_m': 0.040755392906330755,
            'reused_not_rerun': True,
        },
        'random_policy': {
            'base_seed': 0,
            'per_episode_rng': ('numpy.random.default_rng([0, seed]) '
                                '(SeedSequence([0, seed]), PCG64)'),
            'draw_order_per_action': ['dx', 'dy', 'dz', 'dyaw', 'gripper'],
            'xyz': 'current actual EE xyz + U(-0.05, 0.05) each axis',
            'yaw': ('current actual EE yaw + U(-0.2, 0.2) rad; yaw from '
                    'the EE quaternion with the Backend orientation '
                    'convention R.from_euler("xyz",[pi,0,yaw])'),
            'gripper': 'integers 0/1/2 with equal probability',
            'no_expert_target': True,
            'no_prepared_region_snap': True,
        },
        'scope': {
            'retrain': False,
            'new_collection': False,
            'l2_l3': False,
            'rerun_learned_6120': False,
            'runs_per_case': 1,
        },
    }
    (args.out / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print('L1_DEV_MANIFEST_OK')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
