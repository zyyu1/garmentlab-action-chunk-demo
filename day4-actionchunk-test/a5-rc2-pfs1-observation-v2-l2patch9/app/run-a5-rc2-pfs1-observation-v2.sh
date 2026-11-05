#!/usr/bin/env bash
# l2patch9: one 4202 single with the fixed nine-point z patch initial.
set -euo pipefail

app_dir=/root/autodl-tmp/a5-rc2-pfs1-observation-v2-l2patch9/app
cd "$app_dir"
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
runs=/root/autodl-tmp/a5-rc2-pfs1-observation-v2-l2patch9-runs

if [ "$#" -ne 0 ]; then echo "L2PATCH9_ARGS_ERROR" >&2; exit 2; fi
mkdir -p "$runs"
if [ "${L2PATCH9_ALLOW_RERUN:-0}" != "1" ] && [ -e "$runs/completed" ]; then
  echo "L2PATCH9_ALREADY_RUN" >&2; exit 6
fi
mkdir "$runs/run.lock" 2>/dev/null || { echo "L2PATCH9_LOCKED" >&2; exit 6; }
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
assert (app / 'a5-rc2-pfs1-observation-v2-l2patch9-files.json').read_bytes() == \
       (app / 'a5-manifest.json').read_bytes(), 'manifest alias out of sync'

parent_path = version_dir / 'parent-rc8b-manifest.json'
assert sha(parent_path) == 'cce573ddd626715b15818467290152a4c68502bafc9595b11780fe1dd601bc8e'
parent = json.loads(parent_path.read_text())
assert set(parent) == set(manifest)
changed = {'a5-candidate.json', 'a5-rc2-pfs1-observation-v2.json',
           'run-a5-rc2-pfs1-observation-v2.sh'}
drift = [n for n in parent if n not in changed and manifest[n] != parent[n]]
assert not drift, ('rc8b identity drift', drift)
assert len([n for n in parent if n not in changed]) == 60
for n in changed:
    assert manifest[n] != parent[n]

config = json.loads((app / 'a5-rc2-pfs1-observation-v2.json').read_text())
assert config['revision'] == 'diagnostic-l2-nine-point-z-patch'
assert config['kind'] == 'diagnostic_single_case_patch'
assert config['diagnostic_of'] == 'a5-rc2-pfs1-observation-v2-rc8b'
assert config['parent_manifest_sha256'] == sha(parent_path)
assert config['run']['lock'] == 'a5-rc2-pfs1-observation-v2-l2patch9-runs'
assert config['patch']['indices'] == [69, 70, 71, 90, 91, 92, 111, 112, 113]
assert config['patch']['initial_diagnostic'] is True

policy = json.loads((app / 'a5-candidate.json').read_text())
item = policy['development']['4202']
assert item['modes'] == ['single']
initial = root / item['initial']
assert initial.is_dir()
for name, want in item['files'].items():
    assert sha(initial / name) == want
res = json.loads((initial / 'result.json').read_text())
assert res.get('initial_diagnostic') is True
assert res.get('diagnostic_control') == 'nine_point_z_patch'
proto = res.get('protocol') or {}
assert proto.get('version') == 'diagnostic-l2-nine-point-z-patch-v1'
assert proto.get('kind') == 'derived_control'
assert proto.get('is_task_scoped_generated') is False
assert proto.get('initial_diagnostic') is True
assert res['loaded_state']['velocities_restored'] is False
assert res['patch']['indices'] == [69, 70, 71, 90, 91, 92, 111, 112, 113]

audit = json.loads((initial / 'patch_audit.json').read_text())
assert audit['changed_count'] == 9
assert audit['changed_indices'] == [69, 70, 71, 90, 91, 92, 111, 112, 113]
assert audit['only_z_changed'] is True and audit['xy_unchanged'] is True
assert audit['other_vertices_unchanged'] is True
assert audit['before_applied_flat_unchanged'] is True
assert audit['derived_hashes']['result.json'] == sha(initial / 'result.json')
assert audit['derived_hashes']['initial_geometry.npz'] == sha(initial / 'initial_geometry.npz')
assert audit['patch_definition_sha256'] == config['patch_definition_sha256']
assert audit['max_abs_edge_length_change_mm'] <= 0.2
assert audit['max_abs_adjacent_dz_change_mm'] <= 0.3
assert audit['no_smoothing_or_extra_motion'] is True

source = root / res['protocol']['source_initial']
with np.load(initial / 'initial_geometry.npz') as a, np.load(source / 'initial_geometry.npz') as b:
    assert np.array_equal(a['flat_settled'], b['flat_settled'])
    assert np.array_equal(a['before'], b['before'])
    assert np.array_equal(a['applied'], b['applied'])
    assert np.array_equal(a['final'][:, :2], b['final'][:, :2])
    diff = np.abs(a['final'][:, 2] - b['final'][:, 2])
    changed_idx = [int(i) for i in np.where(diff > 0)[0]]
    assert changed_idx == [69, 70, 71, 90, 91, 92, 111, 112, 113], changed_idx
    for i in changed_idx:
        assert abs(a['final'][i, 2] - res['patch']['z_derived_m'][str(i)]) < 1e-12

journal = root / 'a5-rc2-pfs1-observation-v2-l2patch9-runs/journal'
if journal.is_dir():
    assert not any(journal.iterdir())
attempts = root / 'a5-rc2-pfs1-observation-v2-l2patch9-runs/attempts.jsonl'
if attempts.is_file():
    assert not attempts.read_text().strip()
print('L2PATCH9_PREFLIGHT_OK', len(manifest),
      hashlib.sha256((app / 'a5-manifest.json').read_bytes()).hexdigest(), initial.name, flush=True)
PY

if [ "${L2PATCH9_PREFLIGHT_ONLY:-0}" = "1" ]; then echo "L2PATCH9_PREFLIGHT_ONLY_OK"; exit 0; fi

initial=$("$python_bin" - <<'PY'
import json
from pathlib import Path
print('/root/autodl-tmp/' + json.loads(Path('a5-candidate.json').read_text())['development']['4202']['initial'])
PY
)
log=$runs/4202-single.log
echo "L2PATCH9_START seed=4202 mode=single initial=${initial}" | tee -a "$runs/batch.log"
"$python_bin" - "$runs/attempts.jsonl" "$initial" <<'PY'
import hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
rec = {'state': 'started', 'utc': datetime.now(timezone.utc).isoformat(),
       'seed': 4202, 'mode': 'single', 'initial': sys.argv[2],
       'manifest_sha256': hashlib.sha256(Path('a5-manifest.json').read_bytes()).hexdigest()}
with Path(sys.argv[1]).open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n'); fh.flush(); os.fsync(fh.fileno())
PY

set +e
"$python_bin" -u a5_entry.py run --initial "$initial" --mode single --split dev --journal "$runs/journal" 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}"); set -e
entry_status=${statuses[0]}
result_dir=$(sed -n 's/^DOWNLOAD_DIR //p' "$log" | tail -1)
if [ -z "$result_dir" ] || [ ! -d "$result_dir" ]; then echo "L2PATCH9_NO_RESULT" >&2; exit 3; fi

audit_status=0
"$python_bin" ../audit_l2patch9_case.py --run "$result_dir" --seed 4202 --mode single \
  --out "$runs/semantics.json" || audit_status=$?
if [ "$audit_status" -ne 0 ]; then echo "L2PATCH9_AUDIT_FAILED $result_dir" >&2; exit 3; fi

verdict=$("$python_bin" - "$result_dir" <<'PY'
import json, sys
from pathlib import Path
v = json.loads((Path(sys.argv[1]) / 'a5-verdict.json').read_text())
print('%s %s' % (v.get('status'), v.get('success')))
PY
)
"$python_bin" - "$runs/attempts.jsonl" "$result_dir" "$verdict" "$runs/batch.jsonl" "$runs/completed" <<'PY'
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
rec = {'state': 'finished', 'utc': datetime.now(timezone.utc).isoformat(), 'seed': 4202,
       'mode': 'single', 'result_dir': sys.argv[2], 'verdict': sys.argv[3]}
with Path(sys.argv[1]).open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n'); fh.flush(); os.fsync(fh.fileno())
Path(sys.argv[4]).write_text(json.dumps(rec, sort_keys=True) + '\n', encoding='utf-8')
Path(sys.argv[5]).write_text(sys.argv[2] + '\n', encoding='utf-8')
print('L2PATCH9_COMPLETE', sys.argv[2], sys.argv[3], flush=True)
PY
