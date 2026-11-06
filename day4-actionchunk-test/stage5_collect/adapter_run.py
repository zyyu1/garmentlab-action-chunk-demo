"""Stage 5 deployment adapter: point frozen a5_entry at the source-inherited receipt.

Same as minimum_hold120/adapter_run.py; kept local so the collector does not
depend on the minimum-acceptance state directory.
"""
import sys
from pathlib import Path

CAND = Path('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2')
APP = Path('/root/autodl-tmp/stage4-minimum-hold120/app_overlay')
sys.path.insert(0, str(APP))
import a5_entry  # noqa: E402

a5_entry.RELEASE = CAND / 'E_RELEASE.json'
a5_entry.main()
