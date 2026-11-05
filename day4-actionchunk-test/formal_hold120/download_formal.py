"""Archive a formal hold120 state directory and all referenced result dirs."""
import argparse
import json
import tarfile
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--state', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
a = ap.parse_args()
root = Path('/root/autodl-tmp')
paths = set()
for line in (a.state / 'attempts.jsonl').read_text().splitlines():
    if not line.strip():
        continue
    rec = json.loads(line)
    d = rec.get('result_dir')
    if d and Path(d).is_dir():
        paths.add(Path(d))
with tarfile.open(a.out, 'w:gz') as tar:
    tar.add(a.state, arcname=a.state.name)
    for p in sorted(paths):
        tar.add(p, arcname=p.name)
print('FORMAL_ARCHIVE', len(paths), 'result dirs', a.out)
