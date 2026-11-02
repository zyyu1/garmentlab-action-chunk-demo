#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
initial_dir=${1:?Usage: run-strip-recovery-smoke.sh /root/autodl-tmp/day4-square-initial-stripfold-...}
"$python_bin" - "$initial_dir" <<'PY'
import sys,json,hashlib
from pathlib import Path
initial=Path(sys.argv[1])
assert (initial/'result.json').exists(), 'Initial result missing'
r=json.loads((initial/'result.json').read_text())
assert r.get('passed'), 'Initial state did not pass'
assert r.get('initial_case',{}).get('strips'), 'Initial state has no strips'
for name,digest in json.loads(Path('square-strip-recovery-files.json').read_text()).items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
print('STRIP_RECOVERY_PREFLIGHT_OK',r['initial_case']['seed'],r['initial_case']['level'],flush=True)
PY
log=$(mktemp /root/autodl-tmp/day4-strip-recovery-log-XXXXXXXX.log)
set +e
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
"$python_bin" -u day4-strip-recovery-smoke.py --initial-dir "$initial_dir" --allow-root 2>&1 | tee "$log"
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
assert r['recovery_metrics']['action_count']==5,r['recovery_metrics']
im=cv2.imread(str(p.parent/'recovered.png'))
assert im is not None and im.shape==(480,640,3)
print('STRIP_RECOVERY_SAVED',r['initial_case']['seed'],r['initial_case']['level'],flush=True)
PY
if [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then exit 1; fi
