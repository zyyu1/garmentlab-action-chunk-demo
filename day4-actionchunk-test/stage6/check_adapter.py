"""Offline checks: accepted stays accepted; rejected stays rejected; over-budget/error reject."""
import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, '/root/autodl-tmp/stage5-trial/app')
sys.path.insert(0, '/root/autodl-tmp/stage5-trial/stage6')
from bc_eval_adapter import physical_verdict  # noqa: E402

S = Path('/root/autodl-tmp/stage5-formal-state-v1')
demos = [json.loads(l) for l in (S / 'demonstrations.jsonl').read_text().splitlines() if l.strip()]
rec = [d for d in demos if d['level'] == 'flat'][0]
d = Path(rec['result_dir'])
meta = json.loads((d / 'success_meta.json').read_text())
with np.load(d / 'success_trace.npz', allow_pickle=True) as z:
    data = {k: z[k] for k in z.files}

base = physical_verdict(meta, data)
print('accepted_trace:', base['accepted'], base['physics_ok'], base['budget_ok'])

# rejected trace: same episode but final window replaced by the initial flat state
bad = copy.deepcopy(data)
bad['vertices'] = np.repeat((np.asarray(bad['vertices'][0]) + np.array([0.3, 0.0, 0.0]))[None], 331, axis=0)
rej = physical_verdict(meta, bad)
print('rejected_trace:', rej['accepted'], rej['physics_ok'], rej['failed_geometry_frames'][:3] if rej['failed_geometry_frames'] else None)

# over budget
m2 = copy.deepcopy(meta); m2['action_count'] = 8
print('over_budget:', physical_verdict(m2, data)['accepted'])

# runtime error
m3 = copy.deepcopy(meta); m3['errors'] = ['synthetic']
print('runtime_error:', physical_verdict(m3, data)['accepted'])
print('CHECKS_DONE')
