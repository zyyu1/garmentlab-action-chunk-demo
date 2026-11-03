#!/usr/bin/env bash
# New C development protocol, not the frozen 7/12 action experiment.
set -euo pipefail
cd /root/autodl-tmp
python_bin=${ISAAC_PYTHON:-/root/autodl-tmp/envs/isaac40/bin/python}
mode=${1:?usage: run-c-evidence.sh l1|recovery <initial-dir> [runner options]}
initial=${2:?initial directory required}
shift 2
case "$mode" in
  l1) runner=day4-c-l1-xfold-yaw-aware.py ;;
  recovery) runner=day4-c-recovery-fold-episode.py ;;
  *) exit 2 ;;
esac
log=$(mktemp /root/autodl-tmp/day4-c-evidence-XXXXXXXX.log)
set +e
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
"$python_bin" -u "$runner" --initial-dir "$initial" --allow-root --retention-evidence "$@" 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e
"$python_bin" - "$log" <<'PY'
import json,sys
from pathlib import Path
from audit_episode_evidence import audit
log=Path(sys.argv[1])
paths=[line[12:] for line in log.read_text(errors='replace').splitlines() if line.startswith('RESULT_FILE ')]
assert len(paths)==1, 'Startup failed: retain '+str(log)
p=Path(paths[0]); (p.parent/'runner.log').write_bytes(log.read_bytes())
print('DOWNLOAD_DIR', p.parent, flush=True)
r=json.loads(p.read_text())
report=audit(p.parent/'evidence')
(p.parent/'evidence_audit.json').write_text(json.dumps(report,indent=2))
assert report['evidence_complete'], report
assert r['passed'], r['errors']
print('C_EVIDENCE_COMPLETE; formal_success=False; budget_passed='+str(report['action_budget_passed']))
PY
if [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then exit 1; fi
