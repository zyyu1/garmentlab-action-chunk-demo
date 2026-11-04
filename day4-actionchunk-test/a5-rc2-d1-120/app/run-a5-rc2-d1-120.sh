#!/usr/bin/env bash
# D1-120 step 6: one registered diagnostic run (seed 4202, single only).
#
# One invocation = one attempt.  There is no retry loop.  A failed episode is
# kept as diagnostic evidence: result.json, runner.log, video, release_diag
# and the run ledger are never deleted or overwritten.  D1_ALLOW_RERUN=1 is
# required for any second attempt, and only after the first one is reviewed.
#
# Usage: bash run-a5-rc2-d1-120.sh [4202] [single]
set -euo pipefail

app_dir=/root/autodl-tmp/a5-rc2-d1-120/app
cd "$app_dir"
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
seed=${1:-4202}
mode=${2:-single}

if [ "$seed" != "4202" ] || [ "$mode" != "single" ]; then
  echo "D1_SCOPE_ERROR only 4202 single is registered; got seed=${seed} mode=${mode}" >&2
  exit 2
fi

runs=/root/autodl-tmp/a5-rc2-d1-120-runs
mkdir -p "$runs"
if [ "${D1_ALLOW_RERUN:-0}" != "1" ] && [ -e "$runs/completed" ]; then
  echo "D1_ALREADY_RUN $runs/completed; review evidence before any rerun" >&2
  exit 6
fi
mkdir "$runs/run.lock" 2>/dev/null || { echo "D1_LOCKED $runs/run.lock" >&2; exit 6; }
trap 'rmdir "$runs/run.lock" 2>/dev/null || true' EXIT

initial=$("$python_bin" - "$seed" <<'PY'
import json, sys
from pathlib import Path
seed = str(sys.argv[1])
policy = json.loads(Path('a5-candidate.json').read_text())
print('/root/autodl-tmp/' + policy['development'][seed]['initial'])
PY
)

# --- offline preflight: manifest, registered delay, initial identity --------
"$python_bin" - "$seed" "$mode" <<'PY'
import hashlib, json, sys
from pathlib import Path

seed = int(sys.argv[1])
mode = sys.argv[2]
manifest = json.loads(Path('a5-rc2-d1-120-files.json').read_text())
bad = []
for name, want in manifest.items():
    p = Path(name)
    if not p.is_file():
        bad.append((name, 'missing'))
    elif hashlib.sha256(p.read_bytes()).hexdigest() != want:
        bad.append((name, 'mismatch'))
assert not bad, bad

base = hashlib.sha256(Path('a5-manifest.json').read_bytes()).hexdigest()
assert base == '39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d', base

config = json.loads(Path('a5-rc2-d1-120.json').read_text())
assert config['version'] == 'a5-rc2-d1-120'
assert config['base_manifest_sha256'] == base
assert seed == config['subject']['seed'] == 4202
assert config['subject']['mode'] == 'single'
delay = config['delay']
assert delay['steps'] == 120
assert abs(float(delay['dt_s']) - 1 / 60) < 1e-12
assert abs(float(delay['duration_s']) - 2.0) < 1e-12
assert delay['counted_as_public_action'] is False
assert config['events'] == ['ungrasp_return', 'delay_begin', 'delay_end',
                            'retreat_begin', 'retreat_end']

policy = json.loads(Path('a5-candidate.json').read_text())
item = policy['development'][str(seed)]
assert mode in item['modes']
initial = Path('/root/autodl-tmp') / item['initial']
assert initial == Path(config['initial']['dir_remote']), (
    str(initial), config['initial']['dir_remote'])
assert item['files'] == config['initial']['hashes']
for name, want in config['initial']['hashes'].items():
    have = hashlib.sha256((initial / name).read_bytes()).hexdigest()
    assert have == want, (name, have, want)

initial_result = json.loads((initial / 'result.json').read_text())
assert initial_result.get('passed') is True
case = initial_result['initial_case']
assert case['seed'] == seed
assert case['level'] == 'perturbed'
plan = json.loads(Path('square-initial-plan.json').read_text())['episodes']
assert sum(row == case for row in plan) == 1, 'Initial case differs from plan'

print('D1_PREFLIGHT_OK', len(manifest), base, str(initial), flush=True)
PY

if [ "${D1_PREFLIGHT_ONLY:-0}" = "1" ]; then
  echo "D1_PREFLIGHT_ONLY_OK $initial"
  exit 0
fi

# --- attempt ledger: record the start before any GPU work -------------------
attempt_log=$runs/attempts.jsonl
"$python_bin" - "$attempt_log" "$seed" "$mode" <<'PY'
import hashlib, json, os, socket, sys
from datetime import datetime, timezone
from pathlib import Path

log, seed, mode = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
rec = {
    'state': 'started',
    'utc': datetime.now(timezone.utc).isoformat(),
    'version': 'a5-rc2-d1-120',
    'seed': seed,
    'mode': mode,
    'host': socket.gethostname(),
    'pid': os.getpid(),
    'cwd': str(Path.cwd()),
    'manifest_sha256': hashlib.sha256(
        Path('a5-rc2-d1-120-files.json').read_bytes()).hexdigest(),
    'config_sha256': hashlib.sha256(
        Path('a5-rc2-d1-120.json').read_bytes()).hexdigest(),
    'initial': json.loads(Path('a5-candidate.json').read_text())[
        'development'][str(seed)]['initial'],
}
with log.open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n')
    fh.flush()
    os.fsync(fh.fileno())
PY

# Snapshot existing result directories so a crash still leaves a locatable log.
existing=$(mktemp)
ls -d /root/autodl-tmp/day4-a5-rc2-d1-120-* 2>/dev/null > "$existing" || true
log=$(mktemp /root/autodl-tmp/a5-rc2-d1-120-log-XXXXXXXX.log)

set +e
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
  "$python_bin" -u a5_recovery_diag.py --initial-dir "$initial" \
  --fold-edge right --execution "$mode" --split dev --allow-root 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e
sim_status=${statuses[0]}

# Resolve the new result directory.  DOWNLOAD_DIR is authoritative; the
# set-difference fallback keeps the log with the run even if the process died
# before printing it.
result_dir=$(sed -n 's/^DOWNLOAD_DIR //p' "$log" | tail -1)
new_dirs=$(mktemp)
ls -d /root/autodl-tmp/day4-a5-rc2-d1-120-* 2>/dev/null \
  | grep -vxF -f "$existing" > "$new_dirs" || true
if [ -z "$result_dir" ]; then
  new_count=$(grep -c . "$new_dirs" || true)
  if [ "$new_count" -eq 1 ]; then
    result_dir=$(cat "$new_dirs")
  fi
fi
if [ -z "$result_dir" ] || [ ! -d "$result_dir" ]; then
  echo 'D1_ABORT no result directory; retain log '"$log" >&2
  echo 'D1_LOG_RETAINED '"$log" >&2
  exit 4
fi
cp "$log" "$result_dir/runner.log"
echo "D1_LOG $result_dir/runner.log"

# --- post-run identity and evidence inventory -------------------------------
post_status=0
"$python_bin" - "$result_dir" "$initial" "$mode" <<'PY' || post_status=$?
import json, sys
from pathlib import Path

d, initial, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
r = json.loads((d / 'result.json').read_text())
assert r.get('probe_version') == 'a5-rc2-d1-120', r.get('probe_version')
assert Path(r.get('initial_dir', '')).resolve() == initial.resolve(), (
    r.get('initial_dir'), str(initial))
assert r.get('execution_mode') == mode == 'single'
assert r.get('fold_edge') == 'right'
print('D1_RUN', r.get('probe_version'), 'passed', r.get('passed'),
      'errors', r.get('errors'), flush=True)

if r.get('action_count') is not None:
    assert r['action_count'] == 12, r['action_count']
    assert sum(r.get('call_horizons') or []) == 12, r.get('call_horizons')
    assert r.get('action_labels', [])[-1:] == ['release_retreat'], r.get('action_labels')

delay = r.get('internal_delay')
if delay is not None:
    assert delay.get('requested_steps') == 120, delay
    assert delay.get('elapsed_steps') == 120, delay
    assert delay.get('end_step', 0) - delay.get('start_step', 0) == 120, delay
    assert abs(float(delay.get('elapsed_sim_time_s', 0)) - 2.0) <= 1e-6, delay
    assert delay.get('public_action') is False, delay
    assert delay.get('public_action_index') == 12, delay
    assert delay.get('public_action_label') == 'release_retreat', delay
    assert delay.get('control_calls') == 0 and delay.get('target_changes') == 0, delay
    assert delay.get('cloth_position_reset') is False, delay
    assert delay.get('cloth_velocity_reset') is False, delay
elif r.get('passed') is True:
    raise AssertionError('passed run has no internal_delay record')

names = ['success_trace.npz', 'success_meta.json', 'final.png',
         'evidence/release_diag.npz', 'evidence/release_diag.json',
         'evidence/release_diag_events.csv', 'evidence/summary.json',
         'evidence/episode.mp4', 'evidence/timeline.jsonl',
         'evidence/manifest.json', 'contact_report.json']
missing = []
for name in names:
    p = d / name
    print('D1_FILE', name, p.is_file(),
          p.stat().st_size if p.is_file() else -1, flush=True)
    if not p.is_file():
        missing.append(name)
if r.get('passed') is True:
    assert not missing, missing
else:
    print('D1_EVIDENCE_INCOMPLETE', missing, flush=True)
    raise SystemExit(3)
PY

# --- diagnostic ledger + one-shot marker ------------------------------------
assess_status=0
"$python_bin" a5_diag_assess.py "$result_dir" || assess_status=$?

"$python_bin" - "$result_dir" "$attempt_log" "$runs/completed" "$sim_status" "$assess_status" <<'PY'
import hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

d = Path(sys.argv[1])
attempt_log = Path(sys.argv[2])
marker = Path(sys.argv[3])
sim_status, assess_status = int(sys.argv[4]), int(sys.argv[5])
result_path = d / 'result.json'
r = json.loads(result_path.read_text()) if result_path.is_file() else {}
case = r.get('initial_case') or {}


def info(path):
    return {'present': path.is_file(), 'bytes': path.stat().st_size if path.is_file() else None,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None}


evidence = {name: info(d / name) for name in
            ('result.json', 'success_trace.npz', 'success_meta.json', 'final.png',
             'runner.log', 'contact_report.json',
             'evidence/release_diag.npz', 'evidence/release_diag.json',
             'evidence/release_diag_events.csv', 'evidence/summary.json',
             'evidence/episode.mp4', 'evidence/timeline.jsonl',
             'evidence/manifest.json', 'diag-verdict.json')}
rec = {
    'state': 'finished',
    'utc': datetime.now(timezone.utc).isoformat(),
    'version': 'a5-rc2-d1-120',
    'seed': case.get('seed'),
    'level': case.get('level'),
    'mode': r.get('execution_mode'),
    'result_dir': str(d),
    'sim_process_status': sim_status,
    'assess_status': assess_status,
    'episode_passed': r.get('passed'),
    'errors': r.get('errors'),
    'action_count': r.get('action_count'),
    'call_horizons': r.get('call_horizons'),
    'internal_delay': r.get('internal_delay'),
    'evidence': evidence,
}
(d / 'run_ledger.json').write_text(json.dumps(rec, indent=2) + '\n', encoding='utf-8')
with attempt_log.open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n')
    fh.flush()
    os.fsync(fh.fileno())
marker.write_text(str(d) + '\n', encoding='utf-8')
print('D1_LEDGER', d / 'run_ledger.json', flush=True)
print('D1_ATTEMPTS', attempt_log, flush=True)
PY

if [ "$post_status" -eq 3 ]; then
  echo "D1_EPISODE_FAILED evidence retained in $result_dir" >&2
  exit 1
fi
if [ "$post_status" -ne 0 ]; then
  echo "D1_POSTCHECK_FAILED status=$post_status; evidence retained in $result_dir" >&2
  exit 1
fi
if [ "$assess_status" -ne 0 ]; then
  echo "D1_DIAGNOSTIC_INCOMPLETE assess_status=$assess_status; see $result_dir/diag-verdict.json" >&2
  exit 5
fi
echo "D1_SINGLE_RUN_COMPLETE $result_dir"
