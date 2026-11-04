"""Build the rc8b manifest against rc8."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
app = root / 'app'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rc8 = json.loads((root / 'parent-rc8-manifest.json').read_text())
new = {n: sha(app / n) for n in rc8}
assert len(new) == 63
expected = {
    'day4-square-initial.py',
    'day4-square-initial-stripfold.py',
    'square-initial-files.json',
    'square-initial-stripfold-files.json',
    'stage4_batch_preflight.py',
    'run-stage4-formal-batch.sh',
    'run-square-initial.sh',
    'run-square-initial-stripfold.sh',
    'a5-candidate.json',
    'a5-rc2-pfs1-observation-v2.json',
    'run-a5-rc2-pfs1-observation-v2.sh',
}
changed = sorted(n for n in rc8 if new[n] != rc8[n])
print('changed', changed)
assert set(changed) == expected, changed
print('identical', 63 - len(changed))
text = json.dumps(new, indent=2, sort_keys=True) + '\n'
for name in ('a5-manifest.json', 'a5-rc2-pfs1-observation-v2-rc8b-files.json'):
    with (app / name).open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
print('manifest sha', hashlib.sha256(text.encode()).hexdigest())
for n in sorted(expected):
    print(n, new[n])
