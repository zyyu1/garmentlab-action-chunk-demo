import json
from pathlib import Path

root = Path('/root/autodl-tmp')
seeds = set(range(4110, 4130)) | set(range(4210, 4230)) | set(range(4310, 4330))
found = {}
for d in root.glob('day4-square-initial*'):
    p = d / 'result.json'
    if not p.is_file():
        continue
    try:
        r = json.loads(p.read_text())
        c = r.get('initial_case', {})
        s = c.get('seed')
        if s in seeds:
            found.setdefault(s, []).append(str(d))
    except Exception:
        pass
print('FOUND_HELDOUT_INITIALS', len(found))
for s in sorted(found):
    print(s, found[s][0])
