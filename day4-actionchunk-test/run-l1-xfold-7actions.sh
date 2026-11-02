#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
"$python_bin" - <<'PY'
import json,hashlib
from pathlib import Path
for name,digest in json.loads(Path('square-l1-xfold-7actions-files.json').read_text()).items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
print('L1_XFOLD_7ACTIONS_PREFLIGHT_OK',flush=True)
PY
log=$(mktemp /root/autodl-tmp/day4-l1-xfold-7actions-log-XXXXXXXX.log)
set +e
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
"$python_bin" -u day4-l1-xfold-7actions.py --allow-root 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e
"$python_bin" - "$log" <<'PY'
import sys,json
from pathlib import Path
import cv2
log=Path(sys.argv[1])
paths=[s[12:] for s in log.read_text(errors='replace').splitlines() if s.startswith('RESULT_FILE ')]
assert len(paths)==1,'Missing result; retain '+str(log)
p=Path(paths[0]);(p.parent/'runner.log').write_bytes(log.read_bytes())
r=json.loads(p.read_text());print('DOWNLOAD_DIR',p.parent,flush=True)
assert r['passed'],r['errors']
assert r['action_count']==7,r['action_count']
im=cv2.imread(str(p.parent/'final.png'))
assert im is not None and im.shape==(480,640,3)
print('L1_XFOLD_7ACTIONS_SAVED',flush=True)
PY
if [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then exit 1; fi
