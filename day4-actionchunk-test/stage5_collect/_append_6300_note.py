import json
from datetime import datetime, timezone
from pathlib import Path

p = Path('/root/autodl-tmp/stage5-formal-state-v1/attempts.jsonl')
rec = {
    'state': 'note',
    'seed': 6300,
    'level': 'perturbed',
    'utc': datetime.now(timezone.utc).isoformat(),
    'note': 'first initial_generation_failed preserved (NameError APP); stripfold demo generator fixed '
            '(STAGE5_APP env, default /root/autodl-tmp/stage5-trial/app); no rollout started; retry allowed',
    'reason': 'initial_generator_bug_fixed',
}
with p.open('a', encoding='utf-8') as f:
    f.write(json.dumps(rec) + '\n')
print('NOTE_6300_APPENDED')
