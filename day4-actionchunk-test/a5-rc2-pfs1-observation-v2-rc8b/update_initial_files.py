"""Update the two initial-generation file manifests after protocol/entry edits.

Each manifest lists its generator script and its runner; rewrite both entries
and reject any other drift.
"""
import hashlib
import json
from pathlib import Path

app = Path(__file__).resolve().parent / 'app'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

jobs = [
    ('square-initial-files.json',
     ['day4-square-initial.py', 'run-square-initial.sh']),
    ('square-initial-stripfold-files.json',
     ['day4-square-initial-stripfold.py', 'run-square-initial-stripfold.sh']),
]
for manifest_name, names in jobs:
    path = app / manifest_name
    data = json.loads(path.read_text())
    changed = [name for name, want in data.items() if sha(app / name) != want]
    assert set(changed) <= set(names), (manifest_name, changed)
    for name in names:
        data[name] = sha(app / name)
        print(manifest_name, name, data[name])
    with path.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps(data, indent=2, sort_keys=True) + '\n')
