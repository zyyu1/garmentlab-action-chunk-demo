"""Necessary prechecks and static interface audit for L2/L3 dev evaluation."""
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
EVAL = Path('/root/autodl-tmp/stage6_runs/evals/l2l3_dev_budget500_20261108')
MANIFEST = EVAL / 'manifest.json'
DEFAULT_OUT = EVAL / 'precheck.json'
EXPECTED_CKPT = 'ade6013141cfa3b114fe6583602da4b14486b96d736ffe5bbfd104cc3e517208'
EXPECTED_STATS = 'cbc4d711b2341b7ab786ca345ccb490bb32de1ebf93fb1eacc59de22d61a9ae9'
EXPECTED_RUNNER = '562386eec41826c818febbf930c7107f39b9d2ebafcc92de4b45be76c5205a7d'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    model = manifest['model']
    if sha(model['checkpoint_source']) != EXPECTED_CKPT:
        raise SystemExit('checkpoint hash mismatch')
    if sha(model['stats']) != EXPECTED_STATS:
        raise SystemExit('stats hash mismatch')
    if sha(model['runner']) != EXPECTED_RUNNER:
        raise SystemExit('runner hash mismatch')

    for path in (str(TRAIN), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from bc_policy import BCPolicy
    from bc_eval_adapter import LEVEL_BUDGET
    bind_dir = Path(model['checkpoint_source']).parent / 'runtime_recheck'
    policy = BCPolicy(bind_dir, Path(model['stats']).parent)
    if policy.holding_normalization != 'identity':
        raise SystemExit('holding normalization is not identity')
    if LEVEL_BUDGET.get('perturbed') != 12 or LEVEL_BUDGET.get('crumpled') != 12:
        raise SystemExit('L2/L3 budget is not 12')

    cases = []
    for case in manifest['cases']:
        seed = int(case['seed'])
        level = case['level']
        initial = Path(case['initial_dir'])
        for name in ('result.json', 'initial_geometry.npz'):
            if not (initial / name).is_file():
                raise SystemExit('missing %s for %d' % (name, seed))
        if sha(initial / 'result.json') != case['initial_result_json_sha256']:
            raise SystemExit('initial result hash mismatch for %d' % seed)
        if sha(initial / 'initial_geometry.npz') != case['initial_geometry_npz_sha256']:
            raise SystemExit('initial geometry hash mismatch for %d' % seed)
        result = json.loads((initial / 'result.json').read_text(encoding='utf-8'))
        if result.get('passed') is not True:
            raise SystemExit('initial not passed for %d' % seed)
        if result.get('protocol', {}).get('task') != 'B_nominal':
            raise SystemExit('initial task is not B_nominal for %d' % seed)
        if not result.get('strip_records'):
            raise SystemExit('initial has no strip_records for %d' % seed)
        obs_dir = Path(case.get('obs_dir', '')) if case.get('obs_dir') else None
        # Unused heldout initials have no demo obs_dir; the prediction check
        # uses the model's own initial observation only when a demo obs exists.
        prediction = None
        if obs_dir is not None and (obs_dir / 'action_001_obs.npz').is_file():
            with np.load(obs_dir / 'action_001_obs.npz', allow_pickle=False) as z:
                meta = json.loads((obs_dir / 'action_001_obs.json').read_text(
                    encoding='utf-8'))
                obs = policy.build_obs(z['vertices'], z['ee'], z['quat'],
                                       z['joints'], meta['holding'])
            if obs.shape != (1340,) or not np.isfinite(obs).all():
                raise SystemExit('invalid obs for %d' % seed)
            prediction = policy.predict(obs)
        cases.append({
            'level': level,
            'seed': seed,
            'initial_dir': str(initial),
            'initial_result_passed': True,
            'task': 'B_nominal',
            'strips': result['initial_case'].get('strips'),
            'strip_records': len(result.get('strip_records') or []),
            'prediction_action_001': prediction,
        })

    runner_text = Path(model['runner']).read_text(encoding='utf-8')
    interface = {
        'level_budgets': LEVEL_BUDGET,
        'grasp_counting': (
            "required_grasps = 1 if level == 'flat' else 2"
            in runner_text
            and "if not before['engaged'] and after['engaged']:" in runner_text),
        'recovery_release_from_actual_transition': (
            "elif before['engaged'] and not after['engaged']:" in runner_text
            and 'bc_recovery_release' in runner_text),
        'repeated_close_not_new_grasp': (
            'bc_repeated_closes' in runner_text
            and 'bc_repeated_closes' in runner_text),
        'terminal_requires_actual_engaged_and_grasps': (
            "terminal = bool(before['engaged']" in runner_text
            and 'grasp_events >= required_grasps' in runner_text),
        'fold_reference_post_recovery': (
            'post_recovery_nonengaged' in runner_text
            and 'bc_fold_reference' in runner_text),
        'release_clock_331': (
            'release_clock' in runner_text and '331' in runner_text),
        'expert_target_not_gate': (
            'expert_target_consistency' in runner_text
            and 'physical_retreat_ok' in runner_text),
        'runner_initial_settle_30': '_settle(30)' in runner_text,
        'runner_has_expert_settle_240': '_settle(240)' in runner_text,
        'runner_has_expert_recovery_hold': 'run_recovery_hold' in runner_text,
        'settle_hold_note': manifest.get('settle_hold_note'),
    }
    if not interface['grasp_counting']:
        raise SystemExit('grasp counting interface missing')
    if not interface['recovery_release_from_actual_transition']:
        raise SystemExit('recovery release interface missing')
    if not interface['terminal_requires_actual_engaged_and_grasps']:
        raise SystemExit('terminal interface missing')
    if not interface['release_clock_331']:
        raise SystemExit('331 clock interface missing')
    if interface['runner_has_expert_settle_240'] or interface[
            'runner_has_expert_recovery_hold']:
        raise SystemExit('runner unexpectedly contains expert settle/hold')

    report = {
        'purpose': 'l2_l3_development_evaluation_precheck',
        'manifest': str(args.manifest),
        'model': model,
        'cases': cases,
        'interface': interface,
        'holding_normalization': 'identity',
        'holding_index': 1339,
        'torch_version': torch.__version__,
        'cuda_available': bool(torch.cuda.is_available()),
    }
    args.out.write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print('L2L3_DEV_PRECHECK_OK')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
