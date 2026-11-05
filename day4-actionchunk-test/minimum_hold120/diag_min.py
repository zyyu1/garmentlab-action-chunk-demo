import json
from pathlib import Path

root = Path('/root/autodl-tmp')
init = root / 'day4-square-initial-20261105-231449-197286'
a = json.loads((init / 'result.json').read_text())['initial_case']
h = json.loads((root / 'a5-rc8b-recovery-hold120-rc7-r2/app/stage4-heldout-seeds.json').read_text())['heldout']
row = [x for x in h if x['seed'] == 4110][0]
print('INIT_KEYS', sorted(a))
print('HELD_KEYS', sorted(row))
print('INIT', json.dumps(a, sort_keys=True))
print('HELD', json.dumps(row, sort_keys=True))
print('EQUAL', a == row, 'IN', a in h)
print('DIFF', {k: (a.get(k), row.get(k)) for k in set(a) | set(row) if a.get(k) != row.get(k)})
