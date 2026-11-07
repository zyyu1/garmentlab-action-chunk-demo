import json
from datetime import datetime, timezone
from pathlib import Path

p = Path('/root/autodl-tmp/stage5-formal-state-v1/attempts.jsonl')
rec = {
    'state': 'note',
    'seed': 6131,
    'level': 'flat',
    'utc': datetime.now(timezone.utc).isoformat(),
    'note': 'manual termination after >65 min hang; original started and partial evidence preserved; '
            'NOT triggered by the new episode_timeout mechanism',
    'reason': 'manual_stop_hung_episode',
}
with p.open('a', encoding='utf-8') as f:
    f.write(json.dumps(rec) + '\n')
print('NOTE_6131_APPENDED')
