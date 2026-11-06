"""Hash-only preflight for the zerovel overlay; starts no simulation."""
import os
import sys

APP = '/root/autodl-tmp/stage4-4112-zerovel/app'
sys.path.insert(0, APP)
os.chdir(APP)
import a5_entry  # noqa: E402

a5_entry.preflight()
print('PREFLIGHT_OK')
