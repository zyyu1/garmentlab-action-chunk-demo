#!/usr/bin/env bash
# Diagnostic-only entry for the RC2 release-window recording.
# Usage: bash run-a5-rc2-drift-diag.sh [seed] [single|arc4]
set -euo pipefail
cd /root/autodl-tmp/a5-rc2-drift-diag/app
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
seed=${1:-4202}
mode=${2:-single}

"$python_bin" - "$seed" <<'PY'
import hashlib, json, sys
from pathlib import Path
seed = int(sys.argv[1])
manifest = json.loads(Path('a5-rc2-drift-diag-v1-files.json').read_text())
bad = []
for name, want in manifest.items():
    p = Path(name)
    if not p.is_file():
        bad.append((name, 'missing'))
        continue
    if hashlib.sha256(p.read_bytes()).hexdigest() != want:
        bad.append((name, 'mismatch'))
assert not bad, bad
base = hashlib.sha256(Path('a5-manifest.json').read_bytes()).hexdigest()
assert base == '39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d', base
config = json.loads(Path('a5-rc2-drift-diag-v1.json').read_text())
assert config['base_manifest_sha256'] == base
assert seed in (config['subject']['seed'], config['revalidation']['seed'])
print('DIAG_MANIFEST_OK', len(manifest), base, seed)
PY

initial=$("$python_bin" - "$seed" <<'PY'
import json, sys
from pathlib import Path
seed = str(sys.argv[1])
policy = json.loads(Path('a5-candidate.json').read_text())
print('/root/autodl-tmp/' + policy['development'][seed]['initial'])
PY
)

log=$(mktemp /root/autodl-tmp/a5-rc2-drift-diag-log-XXXXXXXX.log)
set +e
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
  "$python_bin" -u a5_recovery_diag.py --initial-dir "$initial" \
  --fold-edge right --execution "$mode" --split dev --allow-root 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e

result_dir=$(sed -n 's/^DOWNLOAD_DIR //p' "$log" | tail -1)
if [ -z "$result_dir" ]; then
  echo 'DIAG_ABORT no DOWNLOAD_DIR; retain log '"$log" >&2
  exit 4
fi
"$python_bin" - "$result_dir" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
r = json.loads((p / 'result.json').read_text())
print('DIAG_RUN', r.get('probe_version'), 'passed', r.get('passed'),
      'errors', r.get('errors'))
print('DIAG_EVIDENCE',
      (p / 'evidence' / 'release_diag.npz').is_file(),
      (p / 'evidence' / 'release_diag.json').is_file())
print('DIAG_CONTACT', (p / 'contact_report.json').is_file())
PY

assess_status=0
"$python_bin" a5_diag_assess.py "$result_dir" || assess_status=$?
if [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then exit 1; fi
exit "$assess_status"
