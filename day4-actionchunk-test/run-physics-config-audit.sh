#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
log=$(mktemp /root/autodl-tmp/day4-physics-config-run-XXXXXXXX.log)
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 \
GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
"$python_bin" -X faulthandler -u day4-physics-config-audit.py --allow-root 2>&1 | tee "$log"
"$python_bin" - "$log" <<'PY'
import json
import sys
from pathlib import Path
log = Path(sys.argv[1])
lines = log.read_text(errors='replace').splitlines()
if 'PHYSICS_CONFIG_AUDIT_OK' not in lines:
    raise RuntimeError('Missing audit success marker')
paths = [line[len('RESULT_FILE '):] for line in lines if line.startswith('RESULT_FILE ')]
if len(paths) != 1:
    raise RuntimeError('Expected one result path')
path = Path(paths[0])
r = json.loads(path.read_text())
assert r['passed'] is True and r['no_steps_during_capture'] is True and r['attachment_disabled'] is True
assert r['baseline_source_checks'] and all(r['baseline_source_checks'].values())
(path.parent / 'runner.log').write_bytes(log.read_bytes())
print('PHYSICS_CONFIG_RESULT_VERIFIED', flush=True)
print('DOWNLOAD_DIR', path.parent, flush=True)
PY
