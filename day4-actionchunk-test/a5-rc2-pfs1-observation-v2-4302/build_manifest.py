"""Build the 4302-extension manifest from the fixed v2 manifest.

Reads parent-v2-manifest.json, recomputes SHA256 for every entry relative to
app/, asserts that exactly the two registration/orchestration entries differ,
then writes the new manifest plus its a5-manifest.json alias.
"""
import hashlib
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent
app = root / 'app'
parent = json.loads((root / 'parent-v2-manifest.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

changed_expected = {
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
for name in ('a5-rc2-pfs1-observation-v2-4302-files.json', 'a5-manifest.json'):
    with (app / name).open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
print('new manifest sha256:', hashlib.sha256(text.encode()).hexdigest())
print('config sha256:', new['a5-rc2-pfs1-observation-v2.json'])
print('runner sha256:', new['run-a5-rc2-pfs1-observation-v2.sh'])
