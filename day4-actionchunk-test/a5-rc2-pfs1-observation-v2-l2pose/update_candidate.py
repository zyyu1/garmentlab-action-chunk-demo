import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
app = root / 'app'
derived = root.parent / 'results' / 'RC8B_L2_DIAG_20261105' / 'day4-square-initial-stripfold-20261104-202215-l2posecontrol'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

policy_path = app / 'a5-candidate.json'
policy = json.loads(policy_path.read_text())
entry = policy['development']['4202']
entry['initial'] = derived.name
entry['files'] = {'result.json': sha(derived / 'result.json'),
                  'initial_geometry.npz': sha(derived / 'initial_geometry.npz')}
entry['modes'] = ['single']
policy_path.write_text(json.dumps(policy, indent=2) + '\n', encoding='utf-8')
print('updated', entry)
