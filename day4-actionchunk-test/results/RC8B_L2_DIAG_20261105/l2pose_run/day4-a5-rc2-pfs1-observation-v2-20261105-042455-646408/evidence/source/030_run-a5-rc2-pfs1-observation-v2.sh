#!/usr/bin/env bash
# l2pose diagnostic: one 4202 single with the pose-matched derived initial.
# Rollout sources are byte-identical to rc8b; only the registered initial and
# orchestration differ.  No retry, no expansion, no freeze.
set -euo pipefail

app_dir=/root/autodl-tmp/a5-rc2-pfs1-observation-v2-l2pose/app
cd "$app_dir"
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
runs=/root/autodl-tmp/a5-rc2-pfs1-observation-v2-l2pose-runs

if [ "$#" -ne 0 ]; then
  echo "L2POSE_ARGS_ERROR this diagnostic takes no arguments" >&2
  exit 2
fi
mkdir -p "$runs"
if [ "${L2POSE_ALLOW_RERUN:-0}" != "1" ] && [ -e "$runs/completed" ]; then
  echo "L2POSE_ALREADY_RUN $runs/completed" >&2
  exit 6
fi
mkdir "$runs/run.lock" 2>/dev/null || { echo "L2POSE_LOCKED $runs/run.lock" >&2; exit 6; }
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
assert (app / 'a5-rc2-pfs1-observation-v2-l2pose-files.json').read_bytes() == \
       (app / 'a5-manifest.json').read_bytes(), 'manifest alias out of sync'

rc8b_path = version_dir / 'parent-rc8b-manifest.json'
assert sha(rc8b_path) == 'cce573ddd626715b15818467290152a4c68502bafc9595b11780fe1dd601bc8e'
rc8b = json.loads(rc8b_path.read_text())
assert set(rc8b) == set(manifest)
changed = {'a5-candidate.json', 'a5-rc2-pfs1-observation-v2.json',
           'run-a5-rc2-pfs1-observation-v2.sh'}
drift = [n for n in rc8b if n not in changed and manifest[n] != rc8b[n]]
assert not drift, ('rc8b rollout drift', drift)
assert len([n for n in rc8b if n not in changed]) == 60
for n in changed:
    assert manifest[n] != rc8b[n], ('changed file did not change', n)

config = json.loads((app / 'a5-rc2-pfs1-observation-v2.json').read_text())
assert config['revision'] == 'diagnostic-l2-pose-control'
assert config['kind'] == 'diagnostic_single_case_control'
assert config['parent_manifest_sha256'] == sha(rc8b_path)
assert config['case'] == {'seed': 4202, 'level': 'perturbed', 'task': 'B_nominal',
                          'mode': 'single', 'actions': 12, 'fold_edge': 'right', 'split': 'dev'}
assert config['physics_scope']['particle_friction_scale'] == 1.0
assert config['run']['one_attempt'] is True and config['run']['retry'] is False
assert config['diagnostic_initial']['is_task_scoped_generated'] is False

policy = json.loads((app / 'a5-candidate.json').read_text())
item = policy['development']['4202']
assert item['modes'] == ['single']
initial = root / item['initial']
assert initial.is_dir(), str(initial)
for name, want in item['files'].items():
    assert sha(initial / name) == want, ('initial hash mismatch', name)
res = json.loads((initial / 'result.json').read_text())
assert res.get('passed') is True
assert res.get('diagnostic_control') == 'pose_matched_old_geometry'
assert res['initial_case']['seed'] == 4202 and res['initial_case']['level'] == 'perturbed'
proto = res.get('protocol') or {}
assert proto.get('version') == 'diagnostic-l2-pose-control-v1'
assert proto.get('kind') == 'derived_control'
assert proto.get('is_task_scoped_generated') is False
assert res['loaded_state']['velocities_restored'] is False

audit = json.loads((initial / 'transform_audit.json').read_text())
assert audit['derived_hashes']['result.json'] == sha(initial / 'result.json')
assert audit['derived_hashes']['initial_geometry.npz'] == sha(initial / 'initial_geometry.npz')
assert abs(audit['transform']['rotation_deg'] - 0.256377) < 1e-5
assert abs(audit['transform']['translation_m'][0] * 1000 - (-1.9414)) < 1e-3
assert abs(audit['transform']['translation_m'][1] * 1000 - 2.7075) < 1e-3
assert audit['internal_pairwise_distance_max_abs_diff_m'] <= 1e-9
assert audit['alignment_residual_vs_new_p95_mm'] <= 0.1
assert audit['alignment_residual_vs_new_max_mm'] <= 0.5
assert audit['flat_settled_equal_new'] is True
assert audit['z_unchanged'] is True

ref = root / proto['pose_reference_initial']
with np.load(initial / 'initial_geometry.npz') as a, np.load(ref / 'initial_geometry.npz') as b:
    assert np.array_equal(a['flat_settled'], b['flat_settled']), 'flat_settled differs from new initial'
    assert not np.array_equal(a['final'], b['final']), 'final was not transformed'

journal = root / 'a5-rc2-pfs1-observation-v2-l2pose-runs/journal'
if journal.is_dir():
    assert not any(journal.iterdir()), 'diagnostic journal is not empty'
attempts = root / 'a5-rc2-pfs1-observation-v2-l2pose-runs/attempts.jsonl'
if attempts.is_file():
    assert not attempts.read_text().strip(), 'diagnostic ledger is not empty'
print('L2POSE_PREFLIGHT_OK', len(manifest),
      hashlib.sha256((app / 'a5-manifest.json').read_bytes()).hexdigest(),
      'initial', initial.name, flush=True)
PY

if [ "${L2POSE_PREFLIGHT_ONLY:-0}" = "1" ]; then
  echo "L2POSE_PREFLIGHT_ONLY_OK"
  exit 0
fi

initial=$("$python_bin" - <<'PY'
import json
from pathlib import Path
print('/root/autodl-tmp/' + json.loads(Path('a5-candidate.json').read_text())['development']['4202']['initial'])
PY
)
log=$runs/4202-single.log
echo "L2POSE_START seed=4202 mode=single initial=${initial}" | tee -a "$runs/batch.log"
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
"$python_bin" -u a5_entry.py run --initial "$initial" --mode single --split dev \
  --journal "$runs/journal" 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e
entry_status=${statuses[0]}
result_dir=$(sed -n 's/^DOWNLOAD_DIR //p' "$log" | tail -1)
if [ -z "$result_dir" ] || [ ! -d "$result_dir" ]; then
  echo "L2POSE_NO_RESULT entry_status=$entry_status" >&2
  exit 3
fi

audit_status=0
"$python_bin" ../audit_l2pose_case.py --run "$result_dir" --seed 4202 --mode single \
  --out "$runs/semantics.json" || audit_status=$?
if [ "$audit_status" -ne 0 ]; then
  echo "L2POSE_AUDIT_FAILED $result_dir" >&2
  exit 3
fi

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
log = Path(sys.argv[1]); run = sys.argv[2]; verdict = sys.argv[3]
rec = {'state': 'finished', 'utc': datetime.now(timezone.utc).isoformat(), 'seed': 4202,
       'mode': 'single', 'result_dir': run, 'verdict': verdict}
with log.open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n'); fh.flush(); os.fsync(fh.fileno())
Path(sys.argv[4]).write_text(json.dumps(rec, sort_keys=True) + '\n', encoding='utf-8')
Path(sys.argv[5]).write_text(run + '\n', encoding='utf-8')
print('L2POSE_SINGLE_COMPLETE', run, verdict, flush=True)
PY
