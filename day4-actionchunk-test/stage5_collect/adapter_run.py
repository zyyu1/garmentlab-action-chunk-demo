"""Stage 5 deployment adapter (app/candidate overridable for trial overlays)."""
import os
import sys
from pathlib import Path

CAND = Path(os.environ.get('STAGE5_CANDIDATE',
                           '/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2'))
APP = Path(os.environ.get('STAGE5_APP',
                          '/root/autodl-tmp/stage4-minimum-hold120/app_overlay'))
sys.path.insert(0, str(APP))
import a5_entry  # noqa: E402

a5_entry.RELEASE = CAND / 'E_RELEASE.json'
a5_entry.main()
