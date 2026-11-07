import json
from datetime import datetime, timezone
from pathlib import Path

p = Path('/root/autodl-tmp/stage5-formal-state-v1/attempts.jsonl')
rec = {
    'state': 'note',
    'seed': 6101,
    'level': 'flat',
    'utc': datetime.now(timezone.utc).isoformat(),
    'note': 'initial_generation_failed preserved; no rollout started; retry allowed after manifest fix',
    'demo_manifest_sha256': '432273a11328913ba7832786aed95decfbd77897b6289b9b37eaa315655cc5cb',
    'initial_files_sha256': 'd48e7a1e84ac106f338f6245d8e5ddf41605626bc60ec7438f958cce998ef57a',
    'initial_plan_sha256': 'b3076929633968fe0a228fcb65b1ea5b2463a8d614345a9541c23f5f4226f698',
}
with p.open('a', encoding='utf-8') as f:
    f.write(json.dumps(rec) + '\n')
print('NOTE_APPENDED')
