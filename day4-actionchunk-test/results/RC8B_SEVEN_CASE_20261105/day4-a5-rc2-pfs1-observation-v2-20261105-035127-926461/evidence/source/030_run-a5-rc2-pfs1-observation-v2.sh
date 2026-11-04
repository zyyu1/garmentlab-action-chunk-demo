#!/usr/bin/env bash
# a5-rc2-pfs1-observation-v2-rc8b: seven-case RC batch runner.
# Task protocol: L1 flat particleFrictionScale=0.0, L2/L3=1.0, applied to
# initial generation, reset and rollout.  Initial results carry a protocol
# block (task/material binding/scale/generator); old initials are rejected.
# One manifest, one batch ledger, one attempt per slot, sequential, no retry.
#
# Exit codes: 0 queue complete; 2 usage/scope; 3 queue paused (retain scene);
#             4 preflight mismatch (nothing started); 5 completed but not all
#             six positives accepted; 6 locked.
set -euo pipefail

app_dir=/root/autodl-tmp/a5-rc2-pfs1-observation-v2-rc8b/app
cd "$app_dir"
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
runs=/root/autodl-tmp/a5-rc2-pfs1-observation-v2-rc8b-runs

if [ "$#" -ne 0 ]; then
  echo "RC8B_ARGS_ERROR this batch takes no arguments" >&2
  exit 2
fi
mkdir -p "$runs"
if [ "${RC8B_ALLOW_RERUN:-0}" != "1" ] && [ -e "$runs/completed" ]; then
  echo "RC8B_ALREADY_RUN $runs/completed; review evidence before any rerun" >&2
  exit 6
fi
mkdir "$runs/batch.lock" 2>/dev/null || { echo "RC8B_LOCKED $runs/batch.lock" >&2; exit 6; }
trap 'rmdir "$runs/batch.lock" 2>/dev/null || true' EXIT

# --- preflight: identity, task protocol, initial protocol, matrix, ledger ---
"$python_bin" - <<'PY'
import hashlib, json
from pathlib import Path

app = Path('.').resolve()
version_dir = app.parent
root = Path('/root/autodl-tmp')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

manifest = json.loads((app / 'a5-manifest.json').read_text())
bad = []
for name, want in manifest.items():
    p = app / name
    if not p.is_file():
        bad.append((name, 'missing'))
    elif sha(p) != want:
        bad.append((name, 'mismatch'))
assert not bad, bad
assert len(manifest) == 63, len(manifest)
assert (app / 'a5-rc2-pfs1-observation-v2-rc8b-files.json').read_bytes() == \
       (app / 'a5-manifest.json').read_bytes(), 'manifest alias out of sync'

parent_v2 = version_dir / 'parent-v2-manifest.json'
assert sha(parent_v2) == 'd97bf349dc8a7813ab274da52c4a16c69a11b9135717a6851abbd6192cf3b73f'
v2 = json.loads(parent_v2.read_text())
parent_rc8 = version_dir / 'parent-rc8-manifest.json'
assert sha(parent_rc8) == '6893001070f6bfc24307927cafe95bb83001524edcb35804a4aaf57479f457aa'
rc8 = json.loads(parent_rc8.read_text())
assert set(v2) == set(rc8) == set(manifest)

changed_vs_rc8 = {
    'day4-square-initial.py',
    'day4-square-initial-stripfold.py',
    'square-initial-files.json',
    'square-initial-stripfold-files.json',
    'stage4_batch_preflight.py',
    'run-stage4-formal-batch.sh',
    'run-square-initial.sh',
    'run-square-initial-stripfold.sh',
    'a5-candidate.json',
    'a5-rc2-pfs1-observation-v2.json',
    'run-a5-rc2-pfs1-observation-v2.sh',
}
drift = [n for n in rc8 if n not in changed_vs_rc8 and manifest[n] != rc8[n]]
assert not drift, ('rc8 identity drift', drift)
assert len([n for n in rc8 if n not in changed_vs_rc8]) == 52
for n in changed_vs_rc8:
    assert manifest[n] != rc8[n], ('changed file did not change', n)

config = json.loads((app / 'a5-rc2-pfs1-observation-v2.json').read_text())
assert config['revision'] == 'final-candidate-rc8b-task-scoped-initials'
assert config['final_candidate'] is True
assert config['physics_scope']['decision'] == 'task_scoped'
assert config['physics_scope']['applies_to'] == ['initial generation', 'reset', 'rollout']
assert config['physics_scope']['tasks']['flat']['particle_friction_scale'] == 0.0
assert config['physics_scope']['tasks']['perturbed']['particle_friction_scale'] == 1.0
assert config['physics_scope']['tasks']['crumpled']['particle_friction_scale'] == 1.0
assert config['physics_scope']['uniform_physics_claim'] is False
assert config['initial_protocol']['version'] == 'stage4-initial-v2-task-scoped'
assert config['initial_protocol']['old_initial_fallback'] == 'forbidden'
assert config['run']['one_attempt_per_slot'] is True
assert config['run']['retry'] is False
assert abs(config['run']['pair_target_atol'] - 1e-6) < 1e-15
matrix = config['matrix']
assert len(matrix) == 7
assert [(m['seed'], m['mode']) for m in matrix] == \
       [(4100, 'single'), (4100, 'arc4'), (4202, 'single'), (4202, 'arc4'),
        (4302, 'single'), (4302, 'arc4'), (4201, 'single')]

l1 = (app / 'a5_l1.py').read_text()
recovery = (app / 'a5_recovery.py').read_text()
obs = (app / 'pfs1_observation_v2.py').read_text()
strip = (app / 'day4-square-initial-stripfold.py').read_text()
flat = (app / 'day4-square-initial.py').read_text()
formal = (app / 'run-stage4-formal-batch.sh').read_text()
assert "kwargs['particle_friction_scale'] = 0." in l1
assert l1.count('expected_scale=0.0') == 4
assert "k['particle_friction_scale'] = 1." in recovery
assert 'expected_scale=1.0' not in recovery
assert 'def capture_material_object(mat, out, label, expected_scale=' in obs
assert 'def record_material_stage(backend, out, label, expected_scale=' in obs
assert "kwargs['particle_friction_scale'] = 1." in strip
assert "kwargs['particle_friction_scale']=0." in flat
assert "stage4-initial-v2-task-scoped" in strip and "stage4-initial-v2-task-scoped" in flat
assert 'cd "$(dirname "$0")"' in formal or 'cd "$here"' in formal
assert 'bash "$here/$runner"' in formal
for bad_marker in ('hold_open_for_steps', 'internal_delay', 'release_order', 'preopen'):
    assert bad_marker not in recovery

spec = {'flat': (0.0, 'A_l1_overfold', 'day4-square-initial.py', 'square-initial-files.json'),
        'perturbed': (1.0, 'B_nominal', 'day4-square-initial-stripfold.py',
                      'square-initial-stripfold-files.json'),
        'crumpled': (1.0, 'B_nominal', 'day4-square-initial-stripfold.py',
                     'square-initial-stripfold-files.json')}
policy = json.loads((app / 'a5-candidate.json').read_text())['development']
plan = json.loads((app / 'square-initial-plan.json').read_text())['episodes']
for m in matrix:
    item = policy[str(m['seed'])]
    assert m['mode'] in item['modes']
    initial = root / item['initial']
    assert initial.is_dir(), ('initial missing', str(initial))
    for name, want in item['files'].items():
        assert sha(initial / name) == want, ('initial hash mismatch', name)
    res = json.loads((initial / 'result.json').read_text())
    assert res.get('passed') is True
    case = res['initial_case']
    assert case['seed'] == m['seed'] and case['level'] == m['level']
    assert sum(row == case for row in plan) == 1
    expected_scale, expected_task, script, files_json = spec[m['level']]
    proto = res.get('protocol') or {}
    assert proto.get('version') == 'stage4-initial-v2-task-scoped', ('old initial', str(initial))
    assert (proto.get('task'), proto.get('level'), proto.get('seed')) == \
           (expected_task, m['level'], m['seed'])
    for key in ('particle_friction_scale_expected', 'particle_friction_scale_readback'):
        assert abs(float(proto.get(key, -1)) - expected_scale) <= 1e-6, (key, str(initial))
    binding = proto.get('material_binding') or {}
    assert binding.get('particle_material') == '/World/Garment/particleMaterial'
    assert bool(binding.get('particle_system'))
    gen = proto.get('generator') or {}
    assert gen.get('script') == script and gen.get('script_sha256') == sha(app / script)
    assert gen.get('files_manifest') == files_json and \
           gen.get('files_manifest_sha256') == sha(app / files_json)

journal = root / 'a5-rc2-pfs1-observation-v2-rc8b-runs/journal'
if journal.is_dir():
    assert not any(journal.iterdir()), 'batch journal is not empty'
attempts = root / 'a5-rc2-pfs1-observation-v2-rc8b-runs/attempts.jsonl'
if attempts.is_file():
    assert not attempts.read_text().strip(), 'batch attempt ledger is not empty'
print('RC8B_PREFLIGHT_OK', len(manifest),
      hashlib.sha256((app / 'a5-manifest.json').read_bytes()).hexdigest(),
      'cases', len(matrix), flush=True)
PY

if [ "${RC8B_PREFLIGHT_ONLY:-0}" = "1" ]; then
  echo "RC8B_PREFLIGHT_ONLY_OK"
  exit 0
fi

CASES=(
  "1 4100 single"
  "2 4100 arc4"
  "3 4202 single"
  "4 4202 arc4"
  "5 4302 single"
  "6 4302 arc4"
  "7 4201 single"
)

attempt_log=$runs/attempts.jsonl
: > "$runs/batch.jsonl"
rc8b_rejections=0
rc8b_accepted=0

record() {
  "$python_bin" - "$attempt_log" "$1" "$2" "$3" "$4" "$5" <<'PY'
import hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
log = Path(sys.argv[1]); slot = int(sys.argv[2]); seed = int(sys.argv[3]); mode = sys.argv[4]
state = sys.argv[5]; extra = json.loads(sys.argv[6])
rec = {'state': state, 'utc': datetime.now(timezone.utc).isoformat(),
       'slot': slot, 'seed': seed, 'mode': mode,
       'manifest_sha256': hashlib.sha256(Path('a5-manifest.json').read_bytes()).hexdigest()}
rec.update(extra)
with log.open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n')
    fh.flush(); os.fsync(fh.fileno())
PY
}

for entry in "${CASES[@]}"; do
  read -r slot seed mode <<< "$entry"
  initial=$("$python_bin" - "$seed" <<'PY'
import json, sys
from pathlib import Path
print('/root/autodl-tmp/' + json.loads(Path('a5-candidate.json').read_text())['development'][sys.argv[1]]['initial'])
PY
)
  log=$runs/slot${slot}-${seed}-${mode}.log
  echo "RC8B_START slot=${slot} seed=${seed} mode=${mode} initial=${initial}" | tee -a "$runs/batch.log"
  record "$slot" "$seed" "$mode" started "{\"initial\": \"$initial\"}"

  set +e
  "$python_bin" -u a5_entry.py run --initial "$initial" --mode "$mode" \
    --split dev --journal "$runs/journal" 2>&1 | tee "$log"
  statuses=("${PIPESTATUS[@]}")
  set -e
  entry_status=${statuses[0]}
  result_dir=$(sed -n 's/^DOWNLOAD_DIR //p' "$log" | tail -1)

  if [ -z "$result_dir" ] || [ ! -d "$result_dir" ]; then
    record "$slot" "$seed" "$mode" paused "{\"reason\": \"no_result_dir\", \"entry_status\": $entry_status}"
    echo "RC8B_QUEUE_PAUSED slot=${slot} reason=no_result_dir" | tee -a "$runs/batch.log"
    exit 3
  fi

  pair_args=()
  single_dir_file=$runs/pair-single-$seed.txt
  if [ "$mode" = "arc4" ]; then
    if [ ! -f "$single_dir_file" ]; then
      record "$slot" "$seed" "$mode" paused "{\"reason\": \"missing_single_before_arc4\", \"result_dir\": \"$result_dir\"}"
      echo "RC8B_QUEUE_PAUSED slot=${slot} reason=missing_single" | tee -a "$runs/batch.log"
      exit 3
    fi
    pair_args=(--single-dir "$(cat "$single_dir_file")")
  fi

  audit_status=0
  "$python_bin" ../audit_rc8b_case.py --run "$result_dir" --seed "$seed" --mode "$mode" \
    "${pair_args[@]}" --out "$runs/slot${slot}-semantics.json" || audit_status=$?
  if [ "$audit_status" -ne 0 ]; then
    record "$slot" "$seed" "$mode" paused "{\"reason\": \"audit_failed\", \"run\": \"$result_dir\"}"
    echo "RC8B_QUEUE_PAUSED slot=${slot} reason=audit_failed run=$result_dir" | tee -a "$runs/batch.log"
    exit 3
  fi

  verdict_status=$("$python_bin" - "$result_dir" <<'PY'
import json, sys
from pathlib import Path
v = json.loads((Path(sys.argv[1]) / 'a5-verdict.json').read_text())
print('%s %s' % (v.get('status'), v.get('success')))
PY
)
  case_status=${verdict_status%% *}
  if [ "$mode" = "single" ]; then
    echo "$result_dir" > "$single_dir_file"
  fi

  if [ "$case_status" = "accepted" ]; then
    rc8b_accepted=$((rc8b_accepted + 1))
    decision=accepted
  elif [ "$case_status" = "rejected" ]; then
    rc8b_rejections=$((rc8b_rejections + 1))
    decision=frozen_failure
  else
    record "$slot" "$seed" "$mode" paused "{\"reason\": \"incomplete_verdict\", \"verdict\": \"$verdict_status\", \"run\": \"$result_dir\"}"
    echo "RC8B_QUEUE_PAUSED slot=${slot} reason=incomplete_verdict" | tee -a "$runs/batch.log"
    exit 3
  fi

  record "$slot" "$seed" "$mode" finished "{\"decision\": \"$decision\", \"verdict\": \"$verdict_status\", \"run\": \"$result_dir\"}"
  "$python_bin" - "$runs/batch.jsonl" "$slot" "$seed" "$mode" "$decision" "$result_dir" "$runs/slot${slot}-semantics.json" <<'PY'
import json, sys
from pathlib import Path
out, slot, seed, mode, decision, run, sem = sys.argv[1:8]
with Path(out).open('a', encoding='utf-8') as fh:
    fh.write(json.dumps({'slot': int(slot), 'seed': int(seed), 'mode': mode,
                         'decision': decision, 'run': run,
                         'semantics': json.loads(Path(sem).read_text())}, sort_keys=True) + '\n')
PY
  echo "RC8B_CASE_DONE slot=${slot} seed=${seed} mode=${mode} decision=${decision} run=${result_dir}" | tee -a "$runs/batch.log"
done

"$python_bin" - "$runs" "$rc8b_accepted" "$rc8b_rejections" <<'PY'
import json, sys
from pathlib import Path
runs = Path(sys.argv[1]); accepted = int(sys.argv[2]); rejected = int(sys.argv[3])
rows = [json.loads(l) for l in (runs / 'batch.jsonl').read_text().splitlines() if l.strip()]
summary = {
    'slots': len(rows), 'accepted': accepted, 'rejected_complete': rejected,
    'all_six_positives_accepted': accepted >= 6,
    'positive_expectation_met': accepted >= 6,
    'cases': [{k: r[k] for k in ('slot', 'seed', 'mode', 'decision', 'run')} for r in rows],
}
(runs / 'batch_summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
(runs / 'completed').write_text('queue complete; accepted=%d rejected_complete=%d\n' % (accepted, rejected))
print('RC8B_BATCH_COMPLETE', json.dumps(summary['cases']), flush=True)
raise SystemExit(0 if accepted >= 6 else 5)
PY
