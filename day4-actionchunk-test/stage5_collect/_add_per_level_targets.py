from pathlib import Path

p = Path('collect_demos.py')
s = p.read_text(encoding='utf-8')

old = "        target = int(self.cfg['target_per_level'])"
new = "        default_target = int(self.cfg['target_per_level'])"
assert old in s, 'target init not found'
s = s.replace(old, new, 1)

old2 = "            attempts = sum(1 for s in seeds[level] if _episode_started(s, done))"
new2 = old2 + "\n            target = int((self.cfg.get('targets') or {}).get(level, default_target))"
assert old2 in s, 'attempts line not found'
s = s.replace(old2, new2, 1)

old3 = "                'stop': 'target' if len(accepted) >= target else ('cap' if attempts >= cap else 'seeds_exhausted'),"
new3 = old3 + "\n                'target': target,"
assert old3 in s, 'summary stop line not found'
s = s.replace(old3, new3, 1)

p.write_text(s, encoding='utf-8')
print('targets_patched')
