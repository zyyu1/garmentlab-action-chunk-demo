#!/usr/bin/env bash
# a5-rc2-pfs1: one registered 4202 single particle-inter-friction sensitivity run.
# There is no retry loop.  A completed marker blocks a second attempt unless
# PFS1_ALLOW_RERUN=1 is set explicitly after review.
set -euo pipefail

app_dir=/root/autodl-tmp/a5-rc2-pfs1/app
cd "$app_dir"
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
seed=${1:-4202}
mode=${2:-single}

if [ "$seed" != "4202" ] || [ "$mode" != "single" ]; then
  echo "PFS1_SCOPE_ERROR only 4202 single is registered; got seed=${seed} mode=${mode}" >&2
  exit 2
fi

runs=/root/autodl-tmp/a5-rc2-pfs1-runs
mkdir -p "$runs"
if [ "${PFS1_ALLOW_RERUN:-0}" != "1" ] && [ -e "$runs/completed" ]; then
  echo "PFS1_ALREADY_RUN $runs/completed; review evidence before any rerun" >&2
  exit 6
fi
mkdir "$runs/run.lock" 2>/dev/null || { echo "PFS1_LOCKED $runs/run.lock" >&2; exit 6; }
trap 'rmdir "$runs/run.lock" 2>/dev/null || true' EXIT

initial=$("$python_bin" - "$seed" <<'PY'
import json, sys
from pathlib import Path
seed = str(sys.argv[1])
policy = json.loads(Path('a5-candidate.json').read_text())
print('/root/autodl-tmp/' + policy['development'][seed]['initial'])
PY
)

# --- offline preflight: deployment manifest, parent, initial identity, scope ---
"$python_bin" - "$seed" "$mode" <<'PY'
import hashlib, json, sys
from pathlib import Path

seed = int(sys.argv[1])
mode = sys.argv[2]
app = Path('.').resolve()
version = app.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

manifest = json.loads((app / 'a5-rc2-pfs1-files.json').read_text())
bad = []
for name, want in manifest.items():
    p = app / name
    if not p.is_file():
        bad.append((name, 'missing'))
    elif hashlib.sha256(p.read_bytes()).hexdigest() != want:
        bad.append((name, 'mismatch'))
assert not bad, bad
assert len(manifest) == 63, len(manifest)

parent_manifest = json.loads((version / 'parent-a5-manifest.json').read_text())
assert hashlib.sha256((version / 'parent-a5-manifest.json').read_bytes()).hexdigest() == \
       '39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d'
base = json.loads((app / 'a5-manifest.json').read_text())
for name, want in parent_manifest.items():
    if name in ('a5_recovery.py', 'a5_capture.py'):
        continue
    assert base.get(name) == want, ('parent/base identity mismatch', name)

config = json.loads((app / 'a5-rc2-pfs1.json').read_text())
assert config['version'] == 'a5-rc2-pfs1'
assert config['parent_manifest_sha256'] == \
       '39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d'
assert config['subject']['seed'] == seed == 4202
assert config['subject']['mode'] == mode == 'single'
assert config['change']['old_value'] == 0.0 and config['change']['new_value'] == 1.0
assert config['change']['explicitly_not_ground_friction'] is True

recovery = (app / 'a5_recovery.py').read_text()
capture = (app / 'a5_capture.py').read_text()
assert "k['particle_friction_scale'] = 1." in recovery
assert 'particle_friction_scale' in recovery
for bad_marker in ('hold_open_for_steps', 'internal_delay', 'release_order', 'preopen'):
    assert bad_marker not in recovery, ('D1/D2-C residue', bad_marker)
for bad_marker in ('release_order', 'preopen', 'suppressed_open'):
    assert bad_marker not in capture, ('D2-C residue', bad_marker)
assert 'pfs1_observation' in recovery and 'pfs1_observation' in capture

policy = json.loads((app / 'a5-candidate.json').read_text())
item = policy['development'][str(seed)]
assert mode in item['modes']
initial = Path('/root/autodl-tmp') / item['initial']
assert str(initial) == config['initial']['dir_remote'], (str(initial), config['initial']['dir_remote'])
assert item['files'] == config['initial']['hashes']
for name, want in config['initial']['hashes'].items():
    have = hashlib.sha256((initial / name).read_bytes()).hexdigest()
    assert have == want, (name, have, want)
initial_result = json.loads((initial / 'result.json').read_text())
assert initial_result.get('passed') is True
case = initial_result['initial_case']
assert case['seed'] == seed and case['level'] == 'perturbed'
plan = json.loads((app / 'square-initial-plan.json').read_text())['episodes']
assert sum(row == case for row in plan) == 1, 'Initial case differs from plan'
print('PFS1_PREFLIGHT_OK', len(manifest), config['parent_manifest_sha256'], str(initial), flush=True)
PY

if [ "${PFS1_PREFLIGHT_ONLY:-0}" = "1" ]; then
  echo "PFS1_PREFLIGHT_ONLY_OK $initial"
  exit 0
fi

# --- attempt ledger: record before any GPU work ---
attempt_log=$runs/attempts.jsonl
"$python_bin" - "$attempt_log" "$seed" "$mode" "$initial" <<'PY'
import hashlib, json, os, socket, sys
from datetime import datetime, timezone
from pathlib import Path

log, seed, mode, initial = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
rec = {
    'state': 'started',
    'utc': datetime.now(timezone.utc).isoformat(),
    'version': 'a5-rc2-pfs1',
    'seed': seed,
    'mode': mode,
    'host': socket.gethostname(),
    'pid': os.getpid(),
    'cwd': str(Path.cwd()),
    'manifest_sha256': hashlib.sha256(Path('a5-rc2-pfs1-files.json').read_bytes()).hexdigest(),
    'config_sha256': hashlib.sha256(Path('a5-rc2-pfs1.json').read_bytes()).hexdigest(),
    'initial': initial,
}
with log.open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n')
    fh.flush()
    os.fsync(fh.fileno())
PY

existing=$(mktemp)
ls -d /root/autodl-tmp/day4-a5-rc2-pfs1-* 2>/dev/null > "$existing" || true
log=$(mktemp /root/autodl-tmp/a5-rc2-pfs1-log-XXXXXXXX.log)

set +e
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
  "$python_bin" -u a5_entry.py run --initial "$initial" --mode "$mode" \
  --split dev --journal "$runs/journal" 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e
entry_status=${statuses[0]}

result_dir=$(sed -n 's/^DOWNLOAD_DIR //p' "$log" | tail -1)
new_dirs=$(mktemp)
ls -d /root/autodl-tmp/day4-a5-rc2-pfs1-* 2>/dev/null | grep -vxF -f "$existing" > "$new_dirs" || true
if [ -z "$result_dir" ]; then
  new_count=$(grep -c . "$new_dirs" || true)
  if [ "$new_count" -eq 1 ]; then
    result_dir=$(cat "$new_dirs")
  fi
fi
if [ -z "$result_dir" ] || [ ! -d "$result_dir" ]; then
  echo 'PFS1_ABORT no result directory; retain log '"$log" >&2
  echo 'PFS1_LOG_RETAINED '"$log" >&2
  exit 4
fi
cp "$log" "$result_dir/runner.log"
echo "PFS1_LOG $result_dir/runner.log"

# --- post-run identity, quality, evidence and observation inventory ---
post_status=0
"$python_bin" - "$result_dir" "$entry_status" "$attempt_log" "$runs/completed" <<'PY' || post_status=$?
import hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

d = Path(sys.argv[1])
entry_status = int(sys.argv[2])
attempt_log = Path(sys.argv[3])
marker = Path(sys.argv[4])
app = Path('.').resolve()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
r = json.loads((d / 'result.json').read_text())
verdict_path = d / 'a5-verdict.json'
verdict = json.loads(verdict_path.read_text()) if verdict_path.is_file() else {}
config = json.loads(Path('a5-rc2-pfs1.json').read_text())
assert Path(r['initial_dir']).resolve() == Path(config['initial']['dir_remote']).resolve()
assert r.get('execution_mode') == 'single'
assert r.get('fold_edge') == 'right'
assert r.get('action_count') == 12, r.get('action_count')
assert sum(r.get('call_horizons') or []) == 12, r.get('call_horizons')
assert r.get('action_labels', [])[-1:] == ['release_retreat'], r.get('action_labels')
assert r.get('passed') is True, r.get('errors')
assert (d / 'success_trace.npz').is_file()
assert (d / 'success_meta.json').is_file()
assert (d / 'evidence' / 'summary.json').is_file()

required_stages = ['initial_loaded', 'after_recovery', 'pre_release', 'release_boundary']
stage_index = json.loads((d / 'pfs1_stage_index.json').read_text())
stage_labels = [x['label'] for x in stage_index]
for label in required_stages:
    assert label in stage_labels, ('missing stage', label)
    assert (d / 'pfs1_stages' / (label + '.npz')).is_file(), label
for name in ('pfs1_release_steps.npz', 'pfs1_release_steps.json',
             'pfs1_first_0_5s.npz', 'pfs1_formal_210_330.npz',
             'pfs1_release_clock.json'):
    assert (d / name).is_file(), name
step_meta = json.loads((d / 'pfs1_release_steps.json').read_text())
assert step_meta['velocity_missing_count'] == 0, step_meta
clock = json.loads((d / 'pfs1_release_clock.json').read_text())
assert clock.get('sampling_error_steps') is not None, clock
assert clock.get('release_boundary', {}).get('attachment_enabled_any') is False, clock

quality = verdict.get('criteria') or verdict.get('quality') or {}
quality_status = quality.get('status') if isinstance(quality, dict) else None
evidence_checks = verdict.get('evidence_checks') or {}
evidence_complete = bool(evidence_checks) and all(evidence_checks.values())
observation_complete = True

def info(path):
    return {'present': path.is_file(),
            'bytes': path.stat().st_size if path.is_file() else None,
            'sha256': sha(path) if path.is_file() else None}

evidence = {name: info(d / name) for name in
            ('result.json', 'success_trace.npz', 'success_meta.json', 'final.png',
             'runner.log', 'contact_report.json', 'pre_release_hold.npz',
             'pfs1_stage_index.json', 'pfs1_release_steps.npz',
             'pfs1_release_steps.json', 'pfs1_first_0_5s.npz',
             'pfs1_formal_210_330.npz', 'pfs1_release_clock.json',
             'evidence/summary.json', 'evidence/timeline.jsonl',
             'evidence/manifest.json')}
valid = (entry_status in (0, 1) and r.get('passed') is True
         and quality_status in ('accepted', 'rejected')
         and evidence_complete and observation_complete)
rec = {
    'state': 'finished',
    'utc': datetime.now(timezone.utc).isoformat(),
    'version': 'a5-rc2-pfs1',
    'seed': 4202,
    'mode': 'single',
    'result_dir': str(d),
    'runner_exit': verdict.get('runner_exit'),
    'entry_assess_exit': entry_status,
    'quality_status': quality_status,
    'evidence_complete': evidence_complete,
    'observation_complete': observation_complete,
    'episode_passed': r.get('passed'),
    'errors': r.get('errors'),
    'action_count': r.get('action_count'),
    'call_horizons': r.get('call_horizons'),
    'release_clock': clock,
    'stage_labels': stage_labels,
    'pfs1_release_steps': step_meta,
    'evidence': evidence,
}
(d / 'pfs1_run_ledger.json').write_text(json.dumps(rec, indent=2, allow_nan=False) + '\n')
with attempt_log.open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n')
    fh.flush()
    os.fsync(fh.fileno())
marker.write_text(str(d) + '\n', encoding='utf-8')
print('PFS1_LEDGER', d / 'pfs1_run_ledger.json', flush=True)
if not valid:
    raise SystemExit(5)
PY

if [ "$post_status" -eq 5 ]; then
  echo "PFS1_INVALID_OR_INCOMPLETE $result_dir" >&2
  exit 5
fi
if [ "$post_status" -ne 0 ]; then
  echo "PFS1_POSTCHECK_FAILED status=$post_status; evidence retained in $result_dir" >&2
  exit 1
fi
echo "PFS1_SINGLE_RUN_COMPLETE $result_dir"
