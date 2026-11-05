import sys
from pathlib import Path

CAND = Path('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2')
sys.path.insert(0, str(CAND / 'app'))
import a5_entry

a5_entry.RELEASE = CAND / 'E_RELEASE.json'
try:
    a5_entry.authorize_initial(Path('/root/autodl-tmp/day4-square-initial-20261105-231810-103925'),
                               'formal', 'single', 'l1')
    print('AUTHORIZE_OK')
except Exception as exc:
    import traceback
    traceback.print_exc()
    raise SystemExit(7)
