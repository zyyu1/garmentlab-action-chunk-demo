"""Deployment adapter: point frozen a5_entry at the source-inherited release receipt.

The frozen entry resolves E_RELEASE.json inside app/; the source-inherited freeze
stores it at the candidate root.  This adapter changes only that lookup path and
leaves all simulation/control/evaluation code untouched.
"""
import sys
from pathlib import Path

CAND = Path('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2')
APP = Path('/root/autodl-tmp/stage4-minimum-hold120/app_overlay')
sys.path.insert(0, str(APP))
import a5_entry  # noqa: E402

a5_entry.RELEASE = CAND / 'E_RELEASE.json'
a5_entry.main()
