#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
"$python_bin" - <<'PY'
from pathlib import Path
import hashlib,json
for name,expected in json.loads(Path('l1-hem-files.json').read_text()).items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Uploaded/dependency version mismatch: '+name)
print('L1_FOLD_PREFLIGHT_OK',flush=True)
PY
log=$(mktemp /root/autodl-tmp/day4-l1-fold-log-XXXXXXXX.log)
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
"$python_bin" -X faulthandler -u day4-l1-hem-fold.py --allow-root 2>&1 | tee "$log"
"$python_bin" - "$log" <<'PY'
from pathlib import Path
import json,sys,cv2
log=Path(sys.argv[1]);lines=log.read_text(errors='replace').splitlines()
paths=[line[len('RESULT_FILE '):] for line in lines if line.startswith('RESULT_FILE ')]
if len(paths)!=1:raise RuntimeError('Expected one result file')
path=Path(paths[0]);r=json.loads(path.read_text())
(path.parent/'runner.log').write_bytes(log.read_bytes())
if 'L1_FOLD_PILOT_PIPELINE_COMPLETED' not in lines or r['pipeline_completed'] is not True:
    raise RuntimeError('Pilot incomplete; download saved failure data')
assert r.get('expert_version')=='hem-v12-pitch-arc-probe'
cap=cv2.VideoCapture(str(path.parent/'episode.mp4'))
ok,frame=cap.read();cap.release()
if not ok or frame.shape[:2]!=(480,640):raise RuntimeError('Saved video cannot be decoded')
print('L1_FOLD_PILOT_ARTIFACTS_OK',flush=True)
print('PROVISIONAL_FOLD_SUCCESS',r['provisional_fold_success'],flush=True)
print('FORMAL_DAY4_ACCEPTANCE',False,flush=True)
print('FOLD_METRICS',json.dumps(r['fold_metrics']),flush=True)
print('DOWNLOAD_DIR',path.parent,flush=True)
PY
