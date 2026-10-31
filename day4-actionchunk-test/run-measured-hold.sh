#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
log=$(mktemp /root/autodl-tmp/day4-measured-hold-run-XXXXXXXX.log)
printf 'RUN_LOG %s\n' "$log"
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 \
GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
GARMENTLAB_ANCHOR_ALIGNMENT=aligned \
"$python_bin" -X faulthandler -u day4-aligned-measured-hold-test.py --allow-root 2>&1 | tee "$log"
"$python_bin" - "$log" <<'PY'
import json
import sys
from pathlib import Path
from compare_measured_hold import compare
log = Path(sys.argv[1])
lines = log.read_text(errors='replace').splitlines()
if 'ALIGNED_MEASURED_HOLD_TRACE_OK' not in lines:
    raise RuntimeError('Missing final success marker; process exit code alone is insufficient')
paths = [line[len('RESULT_FILE '):] for line in lines if line.startswith('RESULT_FILE ')]
if len(paths) != 1:
    raise RuntimeError('Expected exactly one result path')
run = Path(paths[0]).parent
compare(run, '/root/autodl-tmp/day4-aligned-lift-hold-20261024-230123-728994')
(run / 'runner.log').write_bytes(log.read_bytes())
print('DOWNLOAD_DIR', run, flush=True)
PY
