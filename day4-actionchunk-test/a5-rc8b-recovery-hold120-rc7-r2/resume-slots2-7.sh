#!/usr/bin/env bash
# Controlled resume for hold120 rc7: slots 2-7 only; slot1 is inherited.
set -euo pipefail
app_dir=/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2/app
cd "$app_dir"
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
runs=/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2-resume

if [ "$#" -ne 0 ]; then echo "HOLD120RC7R2_ARGS_ERROR" >&2; exit 2; fi
mkdir -p "$runs"
if [ "${HOLD120RC7R2_ALLOW_RERUN:-0}" != "1" ] && [ -e "$runs/completed" ]; then
  echo "HOLD120RC7R2_ALREADY_RUN" >&2; exit 6
fi
mkdir "$runs/resume.lock" 2>/dev/null || { echo "HOLD120RC7R2_LOCKED" >&2; exit 6; }
trap 'rmdir "$runs/resume.lock" 2>/dev/null || true' EXIT

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
assert (app / 'a5-rc8b-recovery-hold120-rc7-r2-files.json').read_bytes() ==        (app / 'a5-manifest.json').read_bytes(), 'manifest alias out of sync'

parent_path = version_dir / 'parent-rc7-manifest.json'
assert sha(parent_path) == '41db790f256396e07df079e511090d14a9852c1f55197afa36ea847a9403c2df'
parent = json.loads(parent_path.read_text())
changed = {n for n in parent if manifest[n] != parent[n]}
assert changed == {'a5-rc2-pfs1-observation-v2.json'}, changed
assert len([n for n in parent if n not in changed]) == 62
assert manifest['a5_recovery.py'] == parent['a5_recovery.py']

config = json.loads((app / 'a5-rc2-pfs1-observation-v2.json').read_text())
assert config['revision'] == 'final-candidate-hold120-rc7-r2'
assert config['parent_manifest_sha256'] == sha(parent_path)
assert config['resume']['slots'] == [2, 3, 4, 5, 6, 7]
assert config['resume']['slot1_reused'] is True and config['resume']['slot1_rerun'] is False
assert config['run']['lock'] == 'a5-rc8b-recovery-hold120-rc7-r2-resume'
assert config['recovery_hold']['steps'] == 120
assert abs(config['recovery_hold']['dt_s'] - 1 / 60) < 1e-12
assert config['run']['pair_target_atol'] == 1e-6
assert config['hold_scope']['flat'].startswith('not_applicable')

inh = json.loads((version_dir / 'inheritance.json').read_text())
assert inh['scope'] == 'slot1_only'
assert inh['parent']['manifest_sha256'] == sha(parent_path)
assert inh['revised']['manifest_sha256'] == sha(app / 'a5-manifest.json')
assert inh['audit']['revised_sha256'] == sha(version_dir / 'audit_hold120_case.py')
assert inh['slot1']['quality'] == 'accepted'
assert inh['resume']['slots'] == [2, 3, 4, 5, 6, 7]

orig = root / 'a5-rc8b-recovery-hold120-rc7-runs'
assert not (orig / 'completed').exists(), 'original batch already completed'
recs = [json.loads(l) for l in (orig / 'attempts.jsonl').read_text().splitlines() if l.strip()]
assert len(recs) == 2, recs
assert [r['state'] for r in recs] == ['started', 'paused']
assert all(int(r['slot']) == 1 for r in recs)
slot1 = Path(config['resume']['slot1_result'])
if not slot1.is_absolute():
    slot1 = root / slot1
assert slot1.is_dir(), str(slot1)
v = json.loads((slot1 / 'a5-verdict.json').read_text())
assert v.get('status') == 'accepted'
assert (orig / 'slot1-postaudit.json').is_file()

resume_journal = root / 'a5-rc8b-recovery-hold120-rc7-r2-resume/journal'
if resume_journal.is_dir():
    assert not any(resume_journal.iterdir())
resume_attempts = root / 'a5-rc8b-recovery-hold120-rc7-r2-resume/attempts.jsonl'
if resume_attempts.is_file():
    assert not resume_attempts.read_text().strip()
print('HOLD120RC7R2_PREFLIGHT_OK', len(manifest),
      hashlib.sha256((app / 'a5-manifest.json').read_bytes()).hexdigest(),
      'resume', config['resume']['slots'], flush=True)
PY

if [ "${HOLD120RC7R2_PREFLIGHT_ONLY:-0}" = "1" ]; then echo "HOLD120RC7R2_PREFLIGHT_ONLY_OK"; exit 0; fi

# slot1 is inherited; slot2 arc4 pairs against it.
echo "/root/autodl-tmp/day4-a5-rc2-l1-20261105-081311-735952" > "$runs/pair-single-4100.txt"

CASES=(
  "2 4100 arc4"
  "3 4202 single"
  "4 4202 arc4"
  "5 4302 single"
  "6 4302 arc4"
  "7 4201 single"
)

attempt_log=$runs/attempts.jsonl
: > "$runs/batch.jsonl"
hold120rc7r2_rejections=0
hold120rc7r2_accepted=0

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
  echo "HOLD120RC7R2_START slot=${slot} seed=${seed} mode=${mode} initial=${initial}" | tee -a "$runs/batch.log"
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
    echo "HOLD120RC7R2_QUEUE_PAUSED slot=${slot} reason=no_result_dir" | tee -a "$runs/batch.log"
    exit 3
  fi

  pair_args=()
  single_dir_file=$runs/pair-single-$seed.txt
  if [ "$mode" = "arc4" ]; then
    if [ ! -f "$single_dir_file" ]; then
      record "$slot" "$seed" "$mode" paused "{\"reason\": \"missing_single_before_arc4\", \"result_dir\": \"$result_dir\"}"
      echo "HOLD120RC7R2_QUEUE_PAUSED slot=${slot} reason=missing_single" | tee -a "$runs/batch.log"
      exit 3
    fi
    pair_args=(--single-dir "$(cat "$single_dir_file")")
  fi

  audit_status=0
  "$python_bin" ../audit_hold120_case.py --run "$result_dir" --seed "$seed" --mode "$mode" \
    "${pair_args[@]}" --out "$runs/slot${slot}-semantics.json" || audit_status=$?
  if [ "$audit_status" -ne 0 ]; then
    record "$slot" "$seed" "$mode" paused "{\"reason\": \"audit_failed\", \"run\": \"$result_dir\"}"
    echo "HOLD120RC7R2_QUEUE_PAUSED slot=${slot} reason=audit_failed run=$result_dir" | tee -a "$runs/batch.log"
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
    hold120rc7r2_accepted=$((hold120rc7r2_accepted + 1))
    decision=accepted
  elif [ "$case_status" = "rejected" ]; then
    hold120rc7r2_rejections=$((hold120rc7r2_rejections + 1))
    decision=frozen_failure
  else
    record "$slot" "$seed" "$mode" paused "{\"reason\": \"incomplete_verdict\", \"verdict\": \"$verdict_status\", \"run\": \"$result_dir\"}"
    echo "HOLD120RC7R2_QUEUE_PAUSED slot=${slot} reason=incomplete_verdict" | tee -a "$runs/batch.log"
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
  echo "HOLD120RC7R2_CASE_DONE slot=${slot} seed=${seed} mode=${mode} decision=${decision} run=${result_dir}" | tee -a "$runs/batch.log"
done

"$python_bin" - "$runs" "$hold120rc7r2_accepted" "$hold120rc7r2_rejections" <<'PY'
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
print('HOLD120RC7R2_BATCH_COMPLETE', json.dumps(summary['cases']), flush=True)
raise SystemExit(0 if accepted >= 6 else 5)
PY
