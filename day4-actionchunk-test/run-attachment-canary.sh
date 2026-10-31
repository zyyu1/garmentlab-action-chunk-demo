#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
"$python_bin" - <<'PY'
import hashlib,json
from pathlib import Path
for name,digest in json.loads(Path('attachment-canary-files.json').read_text()).items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
print('ATTACHMENT_CANARY_PREFLIGHT_OK',flush=True)
PY
output=$(mktemp -d /root/autodl-tmp/day4-attachment-canary-XXXXXXXX)
cp attachment-canary-files.json run-attachment-canary.sh evaluate-attachment-canary.py "$output/"
echo "DOWNLOAD_DIR $output"
for case_name in rigid disabled enabled; do
    set +e
    "$python_bin" -u day4-attachment-canary.py --case "$case_name" --output "$output" --allow-root 2>&1 | tee "$output/$case_name.log"
    statuses=("${PIPESTATUS[@]}")
    set -e
    if [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then
        echo "ATTACHMENT_CANARY_RUN_FAILED $case_name"
        echo "DOWNLOAD_DIR $output"
        exit 1
    fi
    set +e
    "$python_bin" evaluate-attachment-canary.py "$output" "$case_name" 2>&1 | tee "$output/$case_name-assessment.log"
    statuses=("${PIPESTATUS[@]}")
    set -e
    if [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then
        echo "ATTACHMENT_CANARY_GATE_STOP $case_name"
        echo "DOWNLOAD_DIR $output"
        exit 2
    fi
done
echo 'ATTACHMENT_CANARY_CAPABILITY_PASSED'
echo "DOWNLOAD_DIR $output"
