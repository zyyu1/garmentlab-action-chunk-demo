"""Point rc8b a5-candidate.json development entries at the regenerated initials."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE / 'app'
NEW = HERE.parent / 'results' / 'RC8B_INITIALS_20261105'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

new_dirs = {}
for d in NEW.iterdir():
    if d.is_dir():
        r = json.loads((d / 'result.json').read_text())
        new_dirs[r['initial_case']['seed']] = d

policy_path = APP / 'a5-candidate.json'
policy = json.loads(policy_path.read_text())
for seed, d in sorted(new_dirs.items()):
    entry = policy['development'][str(seed)]
    entry['initial'] = d.name
    entry['files'] = {'result.json': sha(d / 'result.json'),
                      'initial_geometry.npz': sha(d / 'initial_geometry.npz')}
    print(seed, d.name, entry['files'])
policy_path.write_text(json.dumps(policy, indent=2) + '\n', encoding='utf-8')
print('updated', policy_path)
