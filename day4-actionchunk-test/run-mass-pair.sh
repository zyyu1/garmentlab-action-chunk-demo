#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
"$python_bin" - <<'PY'
import hashlib,json
from pathlib import Path
manifest=json.loads(Path('mass-pair-files.json').read_text())
for name, expected in manifest.items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Wrong uploaded file: '+name)
print('MASS_PAIR_PREFLIGHT_OK',flush=True)
PY
pair_root=$(mktemp -d /root/autodl-tmp/day4-mass-pair-XXXXXXXX)
printf 'PAIR_RUN_DIR %s\n' "$pair_root"
for mode in baseline light; do
    log="$pair_root/$mode.log"
    GARMENTLAB_ATTACHMENT_OVERLAP=0.005 \
    GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
    GARMENTLAB_ANCHOR_ALIGNMENT=aligned \
    GARMENTLAB_MASS_MODE="$mode" \
    GARMENTLAB_MASS_OUTPUT_ROOT="$pair_root" \
    "$python_bin" -X faulthandler -u day4-mass-sensitivity-test.py --allow-root 2>&1 | tee "$log"
    "$python_bin" - "$log" "$mode" "$pair_root" <<'PY'
import sys
from pathlib import Path
from compare_mass_pair import verify
log, mode, root=Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3])
lines=log.read_text(errors='replace').splitlines()
if 'MASS_SENSITIVITY_RUN_OK' not in lines:
    raise RuntimeError('Missing success marker for '+mode+'; keep full run for diagnosis')
paths=[line[len('RESULT_FILE '):] for line in lines if line.startswith('RESULT_FILE ')]
if len(paths)!=1:
    raise RuntimeError('Expected one result path')
run=Path(paths[0]).parent
verify(run,mode)
(root/(mode+'-path.txt')).write_text(str(run))
print('MASS_BRANCH_VERIFIED',mode,flush=True)
PY
done
"$python_bin" - "$pair_root" <<'PY'
import sys
from pathlib import Path
from compare_mass_pair import compare
root=Path(sys.argv[1])
compare((root/'baseline-path.txt').read_text(),(root/'light-path.txt').read_text(),root/'comparison.json')
print('DOWNLOAD_DIR',root,flush=True)
PY
