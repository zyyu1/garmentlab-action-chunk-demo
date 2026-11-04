"""Build the rc8 task-scoped manifest.

Base file set is identical to v2 (63 entries).  Four entries change relative to
v2 and to rc7: a5_l1.py (L1 0.0), pfs1_observation_v2.py (per-task expected
scale), the registration JSON and the batch runner.
"""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
app = root / 'app'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

v2 = json.loads((root / 'parent-v2-manifest.json').read_text())
rc7 = json.loads((root / 'parent-rc7-manifest.json').read_text())
new = {name: sha(app / name) for name in v2}
assert len(new) == 63

changed_v2 = sorted(n for n in v2 if new[n] != v2[n])
changed_rc7 = sorted(n for n in rc7 if new[n] != rc7[n])
expected = sorted(['a5_l1.py', 'pfs1_observation_v2.py',
                   'a5-rc2-pfs1-observation-v2.json',
                   'run-a5-rc2-pfs1-observation-v2.sh'])
print('changed vs v2:', changed_v2)
print('changed vs rc7:', changed_rc7)
assert changed_v2 == expected, changed_v2
assert changed_rc7 == expected, changed_rc7
print('identical vs v2:', 63 - len(changed_v2))

text = json.dumps(new, indent=2, sort_keys=True) + '\n'
for name in ('a5-manifest.json', 'a5-rc2-pfs1-observation-v2-rc8-files.json'):
    with (app / name).open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
print('manifest sha256:', hashlib.sha256(text.encode()).hexdigest())
print('a5_l1.py:', new['a5_l1.py'])
print('pfs1_observation_v2.py:', new['pfs1_observation_v2.py'])
print('config:', new['a5-rc2-pfs1-observation-v2.json'])
print('runner:', new['run-a5-rc2-pfs1-observation-v2.sh'])
