"""Build the rc7 final-candidate manifest from the fixed v2 manifest.

File set is identical to v2 (63 entries).  Exactly three entries change:
a5_l1.py (uniform particleFrictionScale=1.0 + passive observation hooks),
the registration JSON, and the batch runner.
"""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
app = root / 'app'
parent = json.loads((root / 'parent-v2-manifest.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

changed_expected = {
    'a5_l1.py',
    'a5-rc2-pfs1-observation-v2.json',
    'run-a5-rc2-pfs1-observation-v2.sh',
}
new = {}
for name in parent:
    p = app / name
    assert p.is_file(), ('missing', name)
    new[name] = sha(p)

diff = sorted(n for n in parent if new[n] != parent[n])
print('entries:', len(new))
print('changed:', diff)
print('identical:', len([n for n in parent if new[n] == parent[n]]))
assert set(diff) == changed_expected, diff
assert len(new) == 63

text = json.dumps(new, indent=2, sort_keys=True) + '\n'
for name in ('a5-manifest.json', 'a5-rc2-pfs1-observation-v2-rc7-files.json'):
    with (app / name).open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
print('manifest sha256:', hashlib.sha256(text.encode()).hexdigest())
print('a5_l1.py:', new['a5_l1.py'])
print('config:', new['a5-rc2-pfs1-observation-v2.json'])
print('runner:', new['run-a5-rc2-pfs1-observation-v2.sh'])
