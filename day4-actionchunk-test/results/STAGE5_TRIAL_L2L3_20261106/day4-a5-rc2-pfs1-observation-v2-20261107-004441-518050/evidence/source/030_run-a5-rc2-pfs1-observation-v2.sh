#!/usr/bin/env bash
# a5-rc8b-recovery-hold120-rc7: seven-case development RC.
# L1 pfs=0, no recovery hold. L2/L3 pfs=1, recovery hold 120 steps after the
# original 240-step settle, then re-observe and compute fold pick/yaw.
# One manifest, one ledger, one attempt per slot, sequential, no retry.
set -euo pipefail

app_dir=/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7/app
cd "$app_dir"
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
runs=/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-runs

if [ "$#" -ne 0 ]; then echo "HOLD120RC7_ARGS_ERROR" >&2; exit 2; fi
mkdir -p "$runs"
if [ "${HOLD120RC7_ALLOW_RERUN:-0}" != "1" ] && [ -e "$runs/completed" ]; then
  echo "HOLD120RC7_ALREADY_RUN" >&2; exit 6
fi
mkdir "$runs/batch.lock" 2>/dev/null || { echo "HOLD120RC7_LOCKED" >&2; exit 6; }
trap 'rmdir "$runs/batch.lock" 2>/dev/null || true' EXIT

# --- preflight ---------------------------------------------------------
"$python_bin" - <<'PY'
import hashlib, json
from pathlib import Path

app = Path('.').resolve(); root = Path('/root/autodl-tmp')
version_dir = app.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

manifest = json.loads((app / 'a5-manifest.json').read_text())
bad = [n for n, w in manifest.items() if not (app / n).is_file() or sha(app / n) != w]
assert not bad, bad
assert len(manifest) == 63
assert (app / 'a5-rc8b-recovery-hold120-rc7-files.json').read_bytes() ==        (app / 'a5-manifest.json').read_bytes(), 'manifest alias out of sync'

parent_rc8b_path = version_dir / 'parent-rc8b-manifest.json'
assert sha(parent_rc8b_path) == 'cce573ddd626715b15818467290152a4c68502bafc9595b11780fe1dd601bc8e'
parent_rc8b = json.loads(parent_rc8b_path.read_text())
changed_rc8b = {'a5_recovery.py', 'a5-rc2-pfs1-observation-v2.json',
                'run-a5-rc2-pfs1-observation-v2.sh'}
assert {n for n in parent_rc8b if manifest[n] != parent_rc8b[n]} == changed_rc8b
assert len([n for n in parent_rc8b if n not in changed_rc8b]) == 60

parent_r2_path = version_dir / 'parent-r2-manifest.json'
assert sha(parent_r2_path) == '60733a6b4d93b7b76cbea9b22f2db9849562a420f7cf412e50e1ecd8aecb2bbc'
parent_r2 = json.loads(parent_r2_path.read_text())
changed_r2 = {'a5-rc2-pfs1-observation-v2.json', 'run-a5-rc2-pfs1-observation-v2.sh'}
assert {n for n in parent_r2 if manifest[n] != parent_r2[n]} == changed_r2
assert len([n for n in parent_r2 if n not in changed_r2]) == 61
assert manifest['a5_recovery.py'] == parent_r2['a5_recovery.py']

config = json.loads((app / 'a5-rc2-pfs1-observation-v2.json').read_text())
assert config['revision'] == 'final-candidate-hold120-rc7'
assert config['final_candidate'] is True
assert config['physics_scope']['tasks']['flat']['particle_friction_scale'] == 0.0
assert config['physics_scope']['tasks']['perturbed']['particle_friction_scale'] == 1.0
assert config['physics_scope']['tasks']['crumpled']['particle_friction_scale'] == 1.0
assert config['physics_scope']['applies_to'] == ['initial generation', 'reset', 'rollout']
assert config['initial_protocol']['version'] == 'stage4-initial-v2-task-scoped'
assert config['initial_protocol']['old_initial_fallback'] == 'forbidden'
assert config['hold_scope']['flat'].startswith('not_applicable')
assert '120' in config['hold_scope']['perturbed'] and '120' in config['hold_scope']['crumpled']
assert config['recovery_hold']['steps'] == 120
assert abs(config['recovery_hold']['dt_s'] - 1 / 60) < 1e-12
assert config['run']['one_attempt_per_slot'] is True and config['run']['retry'] is False
assert abs(config['run']['pair_target_atol'] - 1e-6) < 1e-15
assert config['run']['lock'] == 'a5-rc8b-recovery-hold120-rc7-runs'
matrix = config['matrix']
assert len(matrix) == 7
assert [(m['seed'], m['mode']) for m in matrix] ==        [(4100, 'single'), (4100, 'arc4'), (4202, 'single'), (4202, 'arc4'),
        (4302, 'single'), (4302, 'arc4'), (4201, 'single')]

recovery = (app / 'a5_recovery.py').read_text()
l1 = (app / 'a5_l1.py').read_text()
formal = (app / 'run-stage4-formal-batch.sh').read_text()
assert 'def run_recovery_hold' in recovery and 'steps=120' in recovery
assert recovery.count('b._env.step()') == 1
assert "k['particle_friction_scale'] = 1." in recovery
assert "kwargs['particle_friction_scale'] = 0." in l1
assert 'cd "$(dirname "$0")"' in formal or 'cd "$here"' in formal
assert 'bash "$here/$runner"' in formal
for bad in ('hold_open_for_steps', 'internal_delay', 'release_order', 'preopen'):
    assert bad not in recovery

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
    assert initial.is_dir()
    for name, want in item['files'].items():
        assert sha(initial / name) == want
    res = json.loads((initial / 'result.json').read_text())
    assert res.get('passed') is True
    case = res['initial_case']
    assert case['seed'] == m['seed'] and case['level'] == m['level']
    assert sum(row == case for row in plan) == 1
    expected_scale, expected_task, script, files_json = spec[m['level']]
    proto = res.get('protocol') or {}
    assert proto.get('version') == 'stage4-initial-v2-task-scoped'
    assert (proto.get('task'), proto.get('level'), proto.get('seed')) ==            (expected_task, m['level'], m['seed'])
    for key in ('particle_friction_scale_expected', 'particle_friction_scale_readback'):
        assert abs(float(proto.get(key, -1)) - expected_scale) <= 1e-6
    binding = proto.get('material_binding') or {}
    assert binding.get('particle_material') == '/World/Garment/particleMaterial'
    assert bool(binding.get('particle_system'))
    gen = proto.get('generator') or {}
    assert gen.get('script') == script and gen.get('script_sha256') == sha(app / script)
    assert gen.get('files_manifest') == files_json and            gen.get('files_manifest_sha256') == sha(app / files_json)

journal = root / 'a5-rc8b-recovery-hold120-rc7-runs/journal'
if journal.is_dir():
    assert not any(journal.iterdir())
attempts = root / 'a5-rc8b-recovery-hold120-rc7-runs/attempts.jsonl'
if attempts.is_file():
    assert not attempts.read_text().strip()
print('HOLD120RC7_PREFLIGHT_OK', len(manifest),
      hashlib.sha256((app / 'a5-manifest.json').read_bytes()).hexdigest(),
      'cases', len(matrix), flush=True)
PY

if [ "${HOLD120RC7_PREFLIGHT_ONLY:-0}" = "1" ]; then echo "HOLD120RC7_PREFLIGHT_ONLY_OK"; exit 0; fi

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
hold120rc7_rejections=0
hold120rc7_accepted=0

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
  echo "HOLD120RC7_START slot=${slot} seed=${seed} mode=${mode} initial=${initial}" | tee -a "$runs/batch.log"
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
    echo "HOLD120RC7_QUEUE_PAUSED slot=${slot} reason=no_result_dir" | tee -a "$runs/batch.log"
    exit 3
  fi

  pair_args=()
  single_dir_file=$runs/pair-single-$seed.txt
  if [ "$mode" = "arc4" ]; then
    if [ ! -f "$single_dir_file" ]; then
      record "$slot" "$seed" "$mode" paused "{\"reason\": \"missing_single_before_arc4\", \"result_dir\": \"$result_dir\"}"
      echo "HOLD120RC7_QUEUE_PAUSED slot=${slot} reason=missing_single" | tee -a "$runs/batch.log"
      exit 3
    fi
    pair_args=(--single-dir "$(cat "$single_dir_file")")
  fi

  audit_status=0
  "$python_bin" ../audit_hold120_case.py --run "$result_dir" --seed "$seed" --mode "$mode" \
    "${pair_args[@]}" --out "$runs/slot${slot}-semantics.json" || audit_status=$?
  if [ "$audit_status" -ne 0 ]; then
    record "$slot" "$seed" "$mode" paused "{\"reason\": \"audit_failed\", \"run\": \"$result_dir\"}"
    echo "HOLD120RC7_QUEUE_PAUSED slot=${slot} reason=audit_failed run=$result_dir" | tee -a "$runs/batch.log"
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
    hold120rc7_accepted=$((hold120rc7_accepted + 1))
    decision=accepted
  elif [ "$case_status" = "rejected" ]; then
    hold120rc7_rejections=$((hold120rc7_rejections + 1))
    decision=frozen_failure
  else
    record "$slot" "$seed" "$mode" paused "{\"reason\": \"incomplete_verdict\", \"verdict\": \"$verdict_status\", \"run\": \"$result_dir\"}"
    echo "HOLD120RC7_QUEUE_PAUSED slot=${slot} reason=incomplete_verdict" | tee -a "$runs/batch.log"
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
  echo "HOLD120RC7_CASE_DONE slot=${slot} seed=${seed} mode=${mode} decision=${decision} run=${result_dir}" | tee -a "$runs/batch.log"
done

"$python_bin" - "$runs" "$hold120rc7_accepted" "$hold120rc7_rejections" <<'PY'
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
print('HOLD120RC7_BATCH_COMPLETE', json.dumps(summary['cases']), flush=True)
raise SystemExit(0 if accepted >= 6 else 5)
PY
