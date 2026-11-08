"""Necessary prechecks for the fixed L1 development evaluation."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
STAGE5 = Path('/root/autodl-tmp/stage5-trial')
TRAIN = STAGE5 / 'training'
MANIFEST = (STAGE5 / '..' / 'stage6_runs' / 'evals'
            / 'l1_dev_budget500_20261108' / 'manifest.json').resolve()
DEFAULT_OUT = (STAGE5 / '..' / 'stage6_runs' / 'evals'
               / 'l1_dev_budget500_20261108' / 'precheck.json').resolve()
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

    # Verify the skip flag only bypasses the two byte-identity constants.
    runner_text = Path(model['runner']).read_text(encoding='utf-8')
    tree = ast.parse(runner_text)
    skip_blocks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = ast.unparse(node.test) if hasattr(ast, 'unparse') else ''
            if 'skip_identity_check' in test:
                skip_blocks.append({
                    'line': node.lineno,
                    'test': test,
                    'body': [ast.unparse(stmt) if hasattr(ast, 'unparse')
                             else type(stmt).__name__ for stmt in node.body],
                })
    if len(skip_blocks) != 1:
        raise SystemExit('unexpected skip_identity_check blocks: %r'
                         % skip_blocks)
    block_text = ' '.join(skip_blocks[0]['body'])
    if ('EXPECTED_CHECKPOINT_SHA256' not in block_text
            or 'EXPECTED_STATS_SHA256' not in block_text):
        raise SystemExit('skip block is not limited to checkpoint/stats')

    for path in (str(TRAIN), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from bc_policy import BCPolicy
    bind_dir = Path(model['checkpoint_source']).parent / 'runtime_recheck'
    policy = BCPolicy(bind_dir, Path(model['stats']).parent)
    if policy.holding_normalization != 'identity':
        raise SystemExit('holding normalization is not identity')
    if abs(float(policy.obs_mean[1339])) > 1e-12 or abs(
            float(policy.obs_std[1339]) - 1.0) > 1e-12:
        raise SystemExit('holding stats are not identity')

    cases = []
    for case in manifest['cases']:
        seed = int(case['seed'])
        initial = Path(case['initial_dir'])
        if not (initial / 'result.json').is_file():
            raise SystemExit('missing initial result for %d' % seed)
        if not (initial / 'initial_geometry.npz').is_file():
            raise SystemExit('missing initial geometry for %d' % seed)
        if sha(initial / 'result.json') != case['initial_result_json_sha256']:
            raise SystemExit('initial result hash mismatch for %d' % seed)
        if sha(initial / 'initial_geometry.npz') != case['initial_geometry_npz_sha256']:
            raise SystemExit('initial geometry hash mismatch for %d' % seed)
        if json.loads((initial / 'result.json').read_text(
                encoding='utf-8')).get('passed') is not True:
            raise SystemExit('initial not passed for %d' % seed)
        obs_dir = Path(case['obs_dir'])
        with np.load(obs_dir / 'action_001_obs.npz',
                     allow_pickle=False) as z:
            meta = json.loads((obs_dir / 'action_001_obs.json').read_text(
                encoding='utf-8'))
            obs = policy.build_obs(z['vertices'], z['ee'], z['quat'],
                                   z['joints'], meta['holding'])
        if obs.shape != (1340,) or not np.isfinite(obs).all():
            raise SystemExit('invalid obs for %d' % seed)
        prediction = policy.predict(obs)
        if not all(np.isfinite(prediction['xyz'])):
            raise SystemExit('nonfinite prediction for %d' % seed)
        cases.append({
            'seed': seed,
            'level': case['level'],
            'split': case['split'],
            'initial_dir': str(initial),
            'initial_result_json_sha256': sha(initial / 'result.json'),
            'initial_geometry_npz_sha256': sha(
                initial / 'initial_geometry.npz'),
            'initial_passed': True,
            'obs_holding': bool(meta['holding']),
            'obs_shape': list(obs.shape),
            'prediction_action_001': prediction,
        })

    report = {
        'purpose': 'l1_development_evaluation_precheck',
        'manifest': str(args.manifest),
        'model': model,
        'skip_identity_check': {
            'blocks': skip_blocks,
            'scope': 'only EXPECTED_CHECKPOINT_SHA256 and '
                     'EXPECTED_STATS_SHA256 byte-identity constants',
        },
        'holding_normalization': 'identity',
        'holding_index': 1339,
        'holding_mean': 0.0,
        'holding_std': 1.0,
        'cases': cases,
        'torch_version': torch.__version__,
        'cuda_available': bool(torch.cuda.is_available()),
    }
    args.out.write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print('L1_DEV_PRECHECK_OK')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
