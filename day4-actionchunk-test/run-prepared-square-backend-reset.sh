#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
cycles=${1:-10}
"$python_bin" - <<'PY'
import hashlib,json
from pathlib import Path
for name,digest in json.loads(Path('square-prepared-backend-reset-files.json').read_text()).items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:
        raise RuntimeError('File/dependency mismatch: '+name)
print('PREPARED_SQUARE_BACKEND_RESET_PREFLIGHT_OK',flush=True)
PY
run_log=$(mktemp /root/autodl-tmp/prepared-square-backend-reset-log-XXXXXXXX.log)
set +e
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
"$python_bin" -u day4-prepared-square-backend-reset.py --allow-root --cycles "$cycles" 2>&1 | tee "$run_log"
statuses=("${PIPESTATUS[@]}")
set -e
echo "PYTHON_EXIT=${statuses[0]} TEE_EXIT=${statuses[1]}"
"$python_bin" - "$run_log" <<'PY'
import json,sys
from pathlib import Path
log=Path(sys.argv[1]);lines=log.read_text(errors='replace').splitlines()
paths=[line[len('STEP5_RESULT_FILE '):] for line in lines if line.startswith('STEP5_RESULT_FILE ')]
if len(paths)!=1:raise RuntimeError('No unique result file; retain log '+str(log))
path=Path(paths[0]);(path.parent/'runner.log').write_bytes(log.read_bytes())
r=json.loads(path.read_text())
print('PREPARED_SQUARE_BACKEND_RESET_RESULT_VERIFIED',r.get('passed') is True,flush=True)
print('CYCLE_COUNT',r.get('cycle_count'),'ERRORS',r.get('errors'),flush=True)
for c in r.get('cycles',[]):
    print('CYCLE',c.get('cycle'),c.get('rollout'),
          'json_save_ok',c.get('json_save_ok'),
          'yaw_error',c.get('yaw_error_rad'),
          'reuse',None if 'regrasp' not in c else c['regrasp'].get('reuse_count'),
          'fold_iou',None if 'fold_metrics' not in c else c['fold_metrics'].get('particle_occupancy_iou'),
          flush=True)
print('DOWNLOAD_DIR',path.parent,flush=True)
if not r.get('passed'):raise SystemExit(2)
PY

if [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then exit 1; fi
