"""Offline check: reload checkpoint, build obs from a real episode, map action."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, '/root/autodl-tmp/stage5-trial/training')
from bc_policy import BCPolicy  # noqa: E402

T = Path('/root/autodl-tmp/stage5-trial')
S = Path('/root/autodl-tmp/stage5-formal-state-v1')

demos = [json.loads(l) for l in (S / 'demonstrations.jsonl').read_text().splitlines() if l.strip()]
rec = [d for d in demos if d['level'] == 'flat'][0]
obs_dir = T / 'obs-formal' / Path(rec['result_dir']).name
z = np.load(obs_dir / 'action_001_obs.npz', allow_pickle=True)
j = json.loads((obs_dir / 'action_001_obs.json').read_text())
print('obs keys', list(z.keys()), 'holding', j['holding'])

pol = BCPolicy(T / 'training' / 'runs' / 'single', T / 'training' / 'final')
obs = pol.build_obs(z['vertices'], z['ee'], z['quat'], z['joints'], j['holding'])
print('obs dim', obs.shape, 'dtype', obs.dtype, 'finite', bool(np.isfinite(obs).all()))
out = pol.predict(obs)
print('prediction', out)
ex = np.load(S / 'exports' / ('flat-%s' % rec['seed']) / 'single_step.npz', allow_pickle=True)
gt = ex['action'][0]
print('ground-truth action[0]', gt.tolist())
print('gripper class in', sorted(int(v) for v in np.unique(ex['action'][:, 4])))
print('CHECK_OK')
