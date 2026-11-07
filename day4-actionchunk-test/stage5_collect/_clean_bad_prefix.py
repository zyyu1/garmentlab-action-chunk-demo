import json
from datetime import datetime, timezone
from pathlib import Path

p = Path('/root/autodl-tmp/stage5-formal-state-v1/attempts.jsonl')
rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
bad = [r for r in rows if str(r.get('initial', '')).startswith('R ')]
keep = [r for r in rows if not str(r.get('initial', '')).startswith('R ')]
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
arch = p.with_name('attempts.bad-prefix-%s.jsonl' % stamp)
arch.write_text('\n'.join(json.dumps(r) for r in bad) + ('\n' if bad else ''), encoding='utf-8')
p.write_text('\n'.join(json.dumps(r) for r in keep) + ('\n' if keep else ''), encoding='utf-8')
print('CLEANED', len(rows), 'keep', len(keep), 'archived', len(bad), 'archive', arch)
