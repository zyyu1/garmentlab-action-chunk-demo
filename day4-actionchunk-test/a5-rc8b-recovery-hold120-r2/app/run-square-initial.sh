#!/usr/bin/env bash
set -euo pipefail
# rc8b: run from this candidate's app directory, not the shared root.
cd "$(dirname "$0")"
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
seed=${1:-4100}
"$python_bin" - "$seed" <<'PY'
import sys,json,hashlib
from pathlib import Path
seed=int(sys.argv[1])
assert 4100<=seed<=4129, 'Only registered L1 seeds 4100..4109 (dev) and 4110..4129 (held-out) are enabled'
for name,digest in json.loads(Path('square-initial-files.json').read_text()).items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
plan=json.loads(Path('square-initial-plan.json').read_text())
assert hashlib.sha256(Path('square-difficulty.yaml').read_bytes()).hexdigest()==plan['config_sha256']
assert hashlib.sha256(Path('square_cloth_40cm.usda').read_bytes()).hexdigest()==plan['asset_sha256']
print('SQUARE_INITIAL_PREFLIGHT_OK',seed,flush=True)
PY
log=$(mktemp /root/autodl-tmp/day4-square-initial-log-XXXXXXXX.log)
set +e
SQUARE_INITIAL_SEED="$seed" GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 "$python_bin" -u day4-square-initial.py --allow-root 2>&1 | tee "$log"
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
im=cv2.imread(str(p.parent/'initial.png'))
assert im is not None and im.shape==(480,640,3)
print('L1_INITIAL_PILOT_SAVED',r['initial_case']['seed'],flush=True)
PY
if [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then exit 1; fi
