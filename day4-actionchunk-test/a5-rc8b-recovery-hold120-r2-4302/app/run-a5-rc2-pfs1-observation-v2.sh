#!/usr/bin/env bash
# recovery-hold120: one 4302 single; 120-step recovery hold is inside a5_recovery.
set -euo pipefail

app_dir=/root/autodl-tmp/a5-rc8b-recovery-hold120-r2-4302/app
cd "$app_dir"
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
runs=/root/autodl-tmp/a5-rc8b-recovery-hold120-r2-4302-runs

if [ "$#" -ne 0 ]; then echo "HOLD4302_ARGS_ERROR" >&2; exit 2; fi
mkdir -p "$runs"
if [ "${HOLD4302_ALLOW_RERUN:-0}" != "1" ] && [ -e "$runs/completed" ]; then
  echo "HOLD4302_ALREADY_RUN" >&2; exit 6
fi
mkdir "$runs/run.lock" 2>/dev/null || { echo "HOLD4302_LOCKED" >&2; exit 6; }
trap 'rmdir "$runs/run.lock" 2>/dev/null || true' EXIT

"$python_bin" - <<'PY'
import hashlib, json
from pathlib import Path
import numpy as np

app = Path('.').resolve(); root = Path('/root/autodl-tmp')
version_dir = app.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

manifest = json.loads((app / 'a5-manifest.json').read_text())
bad = [n for n, w in manifest.items() if not (app / n).is_file() or sha(app / n) != w]
assert not bad, bad
assert len(manifest) == 63
assert (app / 'a5-rc8b-recovery-hold120-r2-4302-files.json').read_bytes() == \
       (app / 'a5-manifest.json').read_bytes(), 'manifest alias out of sync'

parent_path = version_dir / 'parent-r2-manifest.json'
assert sha(parent_path) == '60733a6b4d93b7b76cbea9b22f2db9849562a420f7cf412e50e1ecd8aecb2bbc'
parent = json.loads(parent_path.read_text())
assert set(parent) == set(manifest)
expected = {'a5-rc2-pfs1-observation-v2.json', 'run-a5-rc2-pfs1-observation-v2.sh'}
changed = {n for n in parent if manifest[n] != parent[n]}
assert changed == expected, changed
assert len([n for n in parent if n not in changed]) == 61

config = json.loads((app / 'a5-rc2-pfs1-observation-v2.json').read_text())
assert config['revision'] == 'diagnostic-recovery-hold120-r2-4302'
assert config['kind'] == 'diagnostic_single_case_recovery_hold_auditfix'
assert config['parent_manifest_sha256'] == sha(parent_path)
assert config['case']['seed'] == 4302 and config['case']['mode'] == 'single'
assert config['scope_lock'] == {'seeds': [4302], 'modes': ['single']}
assert config['recovery_hold']['steps'] == 120
assert abs(config['recovery_hold']['dt_s'] - 1 / 60) < 1e-12
assert abs(config['recovery_hold']['duration_s'] - 2.0) < 1e-12
assert config['run']['lock'] == 'a5-rc8b-recovery-hold120-r2-4302-runs'
assert config['run']['one_attempt'] is True and config['run']['retry'] is False
assert manifest['a5_recovery.py'] == parent['a5_recovery.py']
assert manifest['a5_recovery.py'] == sha(app / 'a5_recovery.py')
assert manifest['a5_capture.py'] == parent['a5_capture.py']
assert manifest['pfs1_observation_v2.py'] == parent['pfs1_observation_v2.py']
assert manifest['stage4_success_v1.py'] == parent['stage4_success_v1.py']

policy = json.loads((app / 'a5-candidate.json').read_text())
item = policy['development']['4302']
assert 'single' in item['modes']
initial = root / item['initial']
assert initial.is_dir()
for name, want in item['files'].items():
    assert sha(initial / name) == want
res = json.loads((initial / 'result.json').read_text())
proto = res.get('protocol') or {}
binding = proto.get('material_binding') or {}
gen = proto.get('generator') or {}
assert proto.get('version') == 'stage4-initial-v2-task-scoped'
assert (proto.get('task'), proto.get('level'), proto.get('seed')) == ('B_nominal', 'crumpled', 4302)
assert abs(float(proto['particle_friction_scale_expected']) - 1.0) <= 1e-6
assert abs(float(proto['particle_friction_scale_readback']) - 1.0) <= 1e-6
assert binding.get('particle_material') == '/World/Garment/particleMaterial'
assert binding.get('particle_system')
assert gen.get('script') == 'day4-square-initial-stripfold.py'
assert gen.get('script_sha256') == sha(app / 'day4-square-initial-stripfold.py')
assert gen.get('files_manifest') == 'square-initial-stripfold-files.json'
assert gen.get('files_manifest_sha256') == sha(app / 'square-initial-stripfold-files.json')

journal = root / 'a5-rc8b-recovery-hold120-r2-4302-runs/journal'
if journal.is_dir():
    assert not any(journal.iterdir())
attempts = root / 'a5-rc8b-recovery-hold120-r2-4302-runs/attempts.jsonl'
if attempts.is_file():
    assert not attempts.read_text().strip()
print('HOLD4302_PREFLIGHT_OK', len(manifest),
      hashlib.sha256((app / 'a5-manifest.json').read_bytes()).hexdigest(),
      'recovery_sha', manifest['a5_recovery.py'], flush=True)
PY

if [ "${HOLD4302_PREFLIGHT_ONLY:-0}" = "1" ]; then echo "HOLD4302_PREFLIGHT_ONLY_OK"; exit 0; fi

initial=$("$python_bin" - <<'PY'
import json
from pathlib import Path
print('/root/autodl-tmp/' + json.loads(Path('a5-candidate.json').read_text())['development']['4302']['initial'])
PY
)
log=$runs/4302-single.log
echo "HOLD4302_START seed=4302 mode=single initial=${initial}" | tee -a "$runs/batch.log"
"$python_bin" - "$runs/attempts.jsonl" "$initial" <<'PY'
import hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
rec = {'state': 'started', 'utc': datetime.now(timezone.utc).isoformat(),
       'seed': 4302, 'mode': 'single', 'initial': sys.argv[2],
       'manifest_sha256': hashlib.sha256(Path('a5-manifest.json').read_bytes()).hexdigest()}
with Path(sys.argv[1]).open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n'); fh.flush(); os.fsync(fh.fileno())
PY

set +e
"$python_bin" -u a5_entry.py run --initial "$initial" --mode single --split dev --journal "$runs/journal" 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}"); set -e
entry_status=${statuses[0]}
echo "HOLD4302_ENTRY_EXIT ${entry_status}" | tee -a "$runs/batch.log"
result_dir=$(sed -n 's/^DOWNLOAD_DIR //p' "$log" | tail -1)
if [ -z "$result_dir" ] || [ ! -d "$result_dir" ]; then echo "HOLD4302_NO_RESULT" >&2; exit 3; fi

audit_status=0
"$python_bin" ../audit_hold120_case.py --run "$result_dir" --seed 4302 --mode single \
  --out "$runs/semantics.json" || audit_status=$?
if [ "$audit_status" -ne 0 ]; then echo "HOLD4302_AUDIT_FAILED $result_dir" >&2; exit 3; fi

verdict=$("$python_bin" - "$result_dir" <<'PY'
import json, sys
from pathlib import Path
v = json.loads((Path(sys.argv[1]) / 'a5-verdict.json').read_text())
print('%s %s' % (v.get('status'), v.get('success')))
PY
)
"$python_bin" - "$runs/attempts.jsonl" "$result_dir" "$verdict" "$runs/batch.jsonl" "$runs/completed" "$entry_status" <<'PY'
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
rec = {'state': 'finished', 'utc': datetime.now(timezone.utc).isoformat(), 'seed': 4302,
       'mode': 'single', 'result_dir': sys.argv[2], 'verdict': sys.argv[3],
       'entry_exit': int(sys.argv[6])}
with Path(sys.argv[1]).open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n'); fh.flush(); os.fsync(fh.fileno())
Path(sys.argv[4]).write_text(json.dumps(rec, sort_keys=True) + '\n', encoding='utf-8')
Path(sys.argv[5]).write_text(sys.argv[2] + '\n', encoding='utf-8')
print('HOLD4302_COMPLETE', sys.argv[2], sys.argv[3], 'entry_exit', sys.argv[6], flush=True)
PY
