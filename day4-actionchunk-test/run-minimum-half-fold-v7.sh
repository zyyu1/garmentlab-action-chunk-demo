#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
"$python_bin" - <<'PY'
import hashlib,json
from pathlib import Path
for name,digest in json.loads(Path('minimum-half-fold-v7-files.json').read_text()).items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:
        raise RuntimeError('File/dependency mismatch: '+name)
print('MINIMUM_HALF_FOLD_PILOT_PREFLIGHT_OK',flush=True)
PY
run_log=$(mktemp /root/autodl-tmp/day4-minimum-half-fold-log-XXXXXXXX.log)
set +e
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
"$python_bin" -u day4-minimum-half-fold-v7.py --allow-root 2>&1 | tee "$run_log"
statuses=("${PIPESTATUS[@]}")
set -e
echo "PYTHON_EXIT=${statuses[0]} TEE_EXIT=${statuses[1]}"
"$python_bin" - "$run_log" <<'PY'
import json,sys
from pathlib import Path
log=Path(sys.argv[1]);lines=log.read_text(errors='replace').splitlines()
paths=[line[len('RESULT_FILE '):] for line in lines if line.startswith('RESULT_FILE ')]
if len(paths)!=1:raise RuntimeError('No unique result file; retain log '+str(log))
path=Path(paths[0]);(path.parent/'runner.log').write_bytes(log.read_bytes())
r=json.loads(path.read_text())
if r.get('passed') is True:
    import cv2
    cap=cv2.VideoCapture(str(path.parent/'episode.mp4'))
    ok,frame=cap.read();cap.release()
    if not ok or frame.shape[:2]!=(480,640):raise RuntimeError('Saved fold video cannot be decoded; retain full result')
    print('MINIMUM_HALF_FOLD_VIDEO_DECODE_OK',flush=True)
print('MINIMUM_HALF_FOLD_PILOT_RESULT_VERIFIED',r.get('passed') is True,flush=True)
print('DOWNLOAD_DIR',path.parent,flush=True)
PY
