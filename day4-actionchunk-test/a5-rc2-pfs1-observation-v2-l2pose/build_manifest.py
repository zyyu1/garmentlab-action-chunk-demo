"""Build the l2pose diagnostic manifest against rc8b."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
app = root / 'app'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rc8b = json.loads((root / 'parent-rc8b-manifest.json').read_text())
new = {n: sha(app / n) for n in rc8b}
assert len(new) == 63
expected = {'a5-candidate.json', 'a5-rc2-pfs1-observation-v2.json',
            'run-a5-rc2-pfs1-observation-v2.sh'}
changed = sorted(n for n in rc8b if new[n] != rc8b[n])
print('changed', changed)
assert set(changed) == expected, changed
print('identical', 63 - len(changed))
text = json.dumps(new, indent=2, sort_keys=True) + '\n'
for name in ('a5-manifest.json', 'a5-rc2-pfs1-observation-v2-l2pose-files.json'):
    with (app / name).open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
print('manifest sha', hashlib.sha256(text.encode()).hexdigest())
for n in sorted(expected):
    print(n, new[n])
