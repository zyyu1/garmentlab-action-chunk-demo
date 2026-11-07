import json
from datetime import datetime, timezone
from pathlib import Path

p = Path('/root/autodl-tmp/stage5-formal-state-v1/attempts.jsonl')
now = datetime.now(timezone.utc).isoformat()
seeds_missing_obs = [6103, 6106, 6107, 6110, 6111, 6112, 6113, 6115, 6116]
with p.open('a', encoding='utf-8') as f:
    for s in seeds_missing_obs:
        f.write(json.dumps({
            'state': 'note', 'seed': s, 'level': 'flat', 'utc': now,
            'note': 'accepted but missing pre-action observations; NOT includable as demonstration',
            'reason': 'obs_overwritten_or_overlay_disabled',
        }) + '\n')
    f.write(json.dumps({
        'state': 'note', 'seed': 6117, 'level': 'flat', 'utc': now,
        'note': 'started then interrupted by manual stop; unsettled; skipped, not rerun',
        'reason': 'started_without_verdict',
    }) + '\n')
print('EVENTS_APPENDED', len(seeds_missing_obs) + 1)
