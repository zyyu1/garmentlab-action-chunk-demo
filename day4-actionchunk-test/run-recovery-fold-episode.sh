#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
initial_dir=${1:?Usage: [RECOVERY_FOLD_EXECUTION=single|arc4] run-recovery-fold-episode.sh /root/autodl-tmp/day4-square-initial-stripfold-... [left|right]}
fold_edge=${2:-left}
case "$fold_edge" in left|right) ;; *) echo "fold_edge must be left or right" >&2; exit 2;; esac
execution=${RECOVERY_FOLD_EXECUTION:-single}
case "$execution" in single|arc4) ;; *) echo "RECOVERY_FOLD_EXECUTION must be single or arc4" >&2; exit 2;; esac
"$python_bin" - "$initial_dir" "$fold_edge" <<'PY'
import sys,json,hashlib
from pathlib import Path
initial=Path(sys.argv[1]);fold_edge=sys.argv[2]
assert (initial/'result.json').exists(),'Initial result missing'
r=json.loads((initial/'result.json').read_text())
assert r.get('passed'),'Initial state did not pass'
assert r.get('initial_case',{}).get('strips'),'Initial state has no strips'
for name,digest in json.loads(Path('square-recovery-fold-files.json').read_text()).items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
print('RECOVERY_FOLD_PREFLIGHT_OK',r['initial_case']['seed'],r['initial_case']['level'],
      'fold_edge='+fold_edge,flush=True)
PY
log=$(mktemp /root/autodl-tmp/day4-recovery-fold-log-XXXXXXXX.log)
set +e
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
"$python_bin" -u day4-recovery-fold-episode.py --initial-dir "$initial_dir" \
    --fold-edge "$fold_edge" --execution "$execution" --allow-root 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e
"$python_bin" - "$log" "$fold_edge" "$execution" <<'PY'
import sys,json
import numpy as np
from pathlib import Path
import cv2
log=Path(sys.argv[1]);fold_edge=sys.argv[2];execution=sys.argv[3]
paths=[s[12:] for s in log.read_text(errors='replace').splitlines() if s.startswith('RESULT_FILE ')]
assert len(paths)==1,'Missing result; retain '+str(log)
p=Path(paths[0]);(p.parent/'runner.log').write_bytes(log.read_bytes())
r=json.loads(p.read_text());print('DOWNLOAD_DIR',p.parent,flush=True)
assert r['passed'],r['errors']
assert r['action_count']==12,r['action_count']
assert r['fold_edge']==fold_edge,(r['fold_edge'],fold_edge)
assert r['execution_mode']==execution,(r['execution_mode'],execution)
assert sum(r['call_horizons'])==r['action_count']==12,r['call_horizons']
assert len(r['chunks'])==(0 if execution=='single' else 1),r['chunks']
fold_targets=next(x for x in r['records'] if x['label']=='fold_targets')
for c in r['chunks']:
    rows=[a for a in r['actions'] if a.get('chunk_label')==c['label']]
    assert c['labels']==['fold_arc45','fold_arc90','fold_arc135','fold_place'],c['labels']
    assert c['horizon']==len(rows)==4,c['horizon']
    assert [a['target_pose'] for a in rows]==c['targets'],'chunk target mismatch'
    assert np.allclose([t[:3] for t in c['targets']],fold_targets['ee_targets'],
                       atol=0,rtol=0),'chunk targets differ from fold_targets'
    assert c['response']['executed_steps']==4,c['response']
im=cv2.imread(str(p.parent/'final.png'))
assert im is not None and im.shape==(480,640,3)
print('RECOVERY_FOLD_SAVED',r['initial_case']['seed'],r['initial_case']['level'],
      'fold_edge='+r['fold_edge'],'execution='+r['execution_mode'],flush=True)
PY
if [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then exit 1; fi
