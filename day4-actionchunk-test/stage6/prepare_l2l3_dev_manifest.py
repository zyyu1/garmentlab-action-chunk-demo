"""Freeze the L2/L3 development-evaluation initial-state manifest."""
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
ROOT = Path('/root/autodl-tmp')

L2_SEEDS = [4210, 4211, 4212, 4213, 4214]
L3_VAL_SEEDS = [6504, 6507]
L3_UNUSED_SEEDS = [4310, 4311, 4312]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def initial_dirs():
    found = {}
    for path in ROOT.glob('day4-square-initial-stripfold-*'):
        result_path = path / 'result.json'
        if not result_path.is_file():
            continue
        result = json.loads(result_path.read_text(encoding='utf-8'))
        case = result.get('initial_case') or {}
        level, seed = case.get('level'), case.get('seed')
        if level not in ('perturbed', 'crumpled') or seed is None:
            continue
        protocol = result.get('protocol') or {}
        if result.get('passed') is not True:
            continue
        if protocol.get('task') != 'B_nominal':
            continue
        key = (str(level), int(seed))
        found.setdefault(key, []).append((result_path.stat().st_mtime_ns, path))
    return found


def describe(path):
    result_path = path / 'result.json'
    geometry = path / 'initial_geometry.npz'
    result = json.loads(result_path.read_text(encoding='utf-8'))
    case = result['initial_case']
    protocol = result.get('protocol') or {}
    if not geometry.is_file():
        raise SystemExit('missing initial_geometry.npz: %s' % path)
    if not case.get('strips'):
        raise SystemExit('initial has no strips: %s' % path)
    if not result.get('strip_records'):
        raise SystemExit('initial has no strip_records: %s' % path)
    return {
        'level': str(case['level']),
        'seed': int(case['seed']),
        'initial_dir': str(path),
        'initial_result_json_sha256': sha(result_path),
        'initial_geometry_npz_sha256': sha(geometry),
        'initial_result_passed': True,
        'task': protocol.get('task'),
        'protocol_version': protocol.get('version'),
        'strips': case.get('strips'),
        'strip_records': len(result.get('strip_records') or []),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path(
        '/root/autodl-tmp/stage6_runs/evals/l2l3_dev_budget500_20261108'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in EPISODES.read_text(
        encoding='utf-8').splitlines() if line.strip()]
    perturbed = [r for r in rows if r['level'] == 'perturbed']
    crumpled = [r for r in rows if r['level'] == 'crumpled']
    if not any(r['split'] == 'val' for r in perturbed):
        l2_val_note = 'no final perturbed val episode; use unused heldout initials'
    else:
        l2_val_note = 'final perturbed val exists'
    l3_val_rows = {int(r['seed']): r for r in crumpled
                   if r['split'] == 'val'}
    if sorted(l3_val_rows) != L3_VAL_SEEDS:
        raise SystemExit('unexpected crumpled val seeds: %r'
                         % sorted(l3_val_rows))
    found = initial_dirs()

    def pick(level, seed, source):
        candidates = found.get((level, seed))
        if not candidates:
            raise SystemExit('no compliant initial for %s/%d' % (level, seed))
        candidates.sort()
        path = candidates[-1][1]
        record = describe(path)
        record['selection_source'] = source
        return record

    l2_cases = [pick('perturbed', seed, 'stage4_used_not_stage5_training')
                for seed in L2_SEEDS]
    l3_cases = []
    for seed in L3_VAL_SEEDS:
        row = l3_val_rows[seed]
        result = json.loads((Path(row['result_dir']) / 'result.json').read_text(
            encoding='utf-8'))
        path = Path(result['initial_dir'])
        record = describe(path)
        record['selection_source'] = 'existing_final_val_initial'
        record['demo_result_dir'] = row['result_dir']
        l3_cases.append(record)
    l3_cases.extend(pick('crumpled', seed, 'stage4_used_not_stage5_training')
                    for seed in L3_UNUSED_SEEDS)

    used_final = {(r['level'], int(r['seed'])) for r in rows}
    final_val_allowed = {('crumpled', seed) for seed in L3_VAL_SEEDS}
    selected = {(c['level'], c['seed']) for c in l2_cases + l3_cases}
    unexpected_used = (selected & used_final) - final_val_allowed
    if unexpected_used:
        raise SystemExit('selected unused seed is already a final demo: %r'
                         % unexpected_used)
    test_seeds = sorted(int(r['seed']) for r in rows
                        if r['split'] == 'test'
                        and r['level'] in ('perturbed', 'crumpled'))
    train_seeds = sorted(int(r['seed']) for r in rows
                         if r['split'] == 'train'
                         and r['level'] in ('perturbed', 'crumpled'))
    if {c['seed'] for c in l2_cases + l3_cases} & set(test_seeds):
        raise SystemExit('test seed selected')
    if {c['seed'] for c in l2_cases + l3_cases} & set(train_seeds):
        raise SystemExit('train seed selected')

    manifest = {
        'purpose': 'development_evaluation_l2_l3',
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
        'selection': {
            'rule': ('per level: existing final val seeds first; then unused '
                     'compliant heldout initials in ascending seed order; '
                     'exclude train, preserve test and prior strategy-debug seeds'),
            'initial_source_note': (
                '4210-4214 and 4310-4312 were used in Stage 4; they were not '
                'used for Stage 5 model training and are not claimed as fresh '
                'held-out states. 6504/6507 are existing final val initials.'),
            'l2_val_note': l2_val_note,
            'l2_seeds': L2_SEEDS,
            'l3_val_seeds': L3_VAL_SEEDS,
            'l3_unused_seeds': L3_UNUSED_SEEDS,
            'excluded_train': train_seeds,
            'preserved_test': test_seeds,
            'used_final': sorted([list(x) for x in used_final]),
        },
        'cases': l2_cases + l3_cases,
        'budgets': {'perturbed': 12, 'crumpled': 12},
        'scope': {
            'retrain': False,
            'new_collection': False,
            'rerun_l1': False,
            'random_baseline': False,
            'runs_per_case': 1,
        },
        'settle_hold_note': (
            'The learned runner uses only the initial _settle(30) and '
            'controller action execution; it does not insert the expert '
            'L2/L3 recovery _settle(240) or the 120-step recovery hold. '
            'No expert wait/repair is added in this evaluation.'),
    }
    (args.out / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print('L2L3_DEV_MANIFEST_OK')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
