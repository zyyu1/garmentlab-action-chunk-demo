#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
if [ "$#" -ne 1 ]; then
  echo "usage: [L1_XFOLD_EXECUTION=single|arc4] $0 <l1-initial-dir>" >&2
  exit 2
fi
execution=${L1_XFOLD_EXECUTION:-single}
case "$execution" in single|arc4) ;; *) echo "L1_XFOLD_EXECUTION must be single or arc4" >&2; exit 2;; esac
initial_dir=$1
if [ ! -f "$initial_dir/result.json" ] || [ ! -f "$initial_dir/initial_geometry.npz" ]; then
  echo "missing L1 initial files under $initial_dir" >&2
  exit 2
fi
"$python_bin" - <<'PY'
import json,hashlib
from pathlib import Path
for name,digest in json.loads(Path('square-l1-xfold-yaw-files.json').read_text()).items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
print('L1_XFOLD_YAW_PREFLIGHT_OK',flush=True)
PY
log=$(mktemp /root/autodl-tmp/day4-l1-xfold-yaw-log-XXXXXXXX.log)
set +e
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
"$python_bin" -u day4-l1-xfold-yaw-aware.py --initial-dir "$initial_dir" --allow-root \
  --overhang "${L1_XFOLD_OVERHANG:-0.0}" --execution "$execution" 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e
"$python_bin" - "$log" <<'PY'
import os,sys,json
from pathlib import Path
import cv2
log=Path(sys.argv[1])
paths=[s[12:] for s in log.read_text(errors='replace').splitlines() if s.startswith('RESULT_FILE ')]
assert len(paths)==1,'Missing result; retain '+str(log)
p=Path(paths[0]);(p.parent/'runner.log').write_bytes(log.read_bytes())
r=json.loads(p.read_text());print('DOWNLOAD_DIR',p.parent,flush=True)
assert r['passed'],r['errors']
assert r['action_count']==7,r['action_count']
expected_mode=os.environ.get('L1_XFOLD_EXECUTION','single')
assert r['execution_mode']==expected_mode,(r['execution_mode'],expected_mode)
assert sum(r['call_horizons'])==r['action_count']==7,r['call_horizons']
assert len(r['chunks'])==(0 if expected_mode=='single' else 1),r['chunks']
for c in r['chunks']:
    rows=[a for a in r['actions'] if a.get('chunk_label')==c['label']]
    assert c['labels']==['arc45','arc90','arc135','place'],c['labels']
    assert c['horizon']==len(rows)==4,c['horizon']
    assert [a['target_pose'] for a in rows]==c['targets'],'chunk target mismatch'
    assert c['response']['executed_steps']==4,c['response']
assert abs(r['fold_yaw_delta'])<=.02,r['fold_yaw_delta']
expected=float(os.environ.get('L1_XFOLD_OVERHANG','0.0'))
assert abs(r['fold_definition']['fold_overhang_m']-expected)<1e-12,r['fold_definition']
assert r['initial_files']['initial_geometry.npz'],r['initial_files']
m=r['fold_metrics']
assert m['moving_half_crossed_fraction']>=.5,m['moving_half_crossed_fraction']
assert 100<=m['moving_count']<=341,m['moving_count']
im=cv2.imread(str(p.parent/'final.png'))
assert im is not None and im.shape==(480,640,3)
print('L1_XFOLD_YAW_SAVED',flush=True)
PY
if [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then exit 1; fi
