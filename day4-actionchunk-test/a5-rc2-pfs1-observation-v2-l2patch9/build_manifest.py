import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
app = root / 'app'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
parent = json.loads((root / 'parent-rc8b-manifest.json').read_text())
new = {n: sha(app / n) for n in parent}
assert len(new) == 63
expected = {'a5-candidate.json', 'a5-rc2-pfs1-observation-v2.json',
            'run-a5-rc2-pfs1-observation-v2.sh'}
changed = sorted(n for n in parent if new[n] != parent[n])
print('changed', changed, 'identical', 63 - len(changed))
assert set(changed) == expected
text = json.dumps(new, indent=2, sort_keys=True) + '\n'
for fn in ('a5-manifest.json', 'a5-rc2-pfs1-observation-v2-l2patch9-files.json'):
    (app / fn).write_text(text, encoding='utf-8', newline='\n')
print('manifest sha', hashlib.sha256(text.encode()).hexdigest())
for n in sorted(expected):
    print(n, new[n])
