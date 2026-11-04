#!/usr/bin/env bash
# a5-rc2-pfs1-observation-v2: one registered 4202 single observation revalidation.
# Physics/control are inherited unchanged from a5-rc2-pfs1.  This runner uses a
# NEW manifest and a NEW one-shot lock; it does not reuse the pfs1 marker.
# There is no retry loop.  A completed marker blocks a second attempt unless
# PFS1_OBS_V2_ALLOW_RERUN=1 is set explicitly after review.
set -euo pipefail

app_dir=/root/autodl-tmp/a5-rc2-pfs1-observation-v2/app
cd "$app_dir"
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
seed=${1:-4202}
mode=${2:-single}
version=a5-rc2-pfs1-observation-v2
manifest_name=a5-rc2-pfs1-observation-v2-files.json
config_name=a5-rc2-pfs1-observation-v2.json

if [ "$seed" != "4202" ] || [ "$mode" != "single" ]; then
  echo "PFS1_V2_SCOPE_ERROR only 4202 single is registered; got seed=${seed} mode=${mode}" >&2
  exit 2
fi

runs=/root/autodl-tmp/a5-rc2-pfs1-observation-v2-runs
mkdir -p "$runs"
if [ "${PFS1_OBS_V2_ALLOW_RERUN:-0}" != "1" ] && [ -e "$runs/completed" ]; then
  echo "PFS1_V2_ALREADY_RUN $runs/completed; review evidence before any rerun" >&2
  exit 6
fi
mkdir "$runs/run.lock" 2>/dev/null || { echo "PFS1_V2_LOCKED $runs/run.lock" >&2; exit 6; }
trap 'rmdir "$runs/run.lock" 2>/dev/null || true' EXIT

initial=$("$python_bin" - "$seed" <<'PY'
import json, sys
from pathlib import Path
seed = str(sys.argv[1])
policy = json.loads(Path('a5-candidate.json').read_text())
print('/root/autodl-tmp/' + policy['development'][seed]['initial'])
PY
)

# --- offline preflight: deployment manifest, parent pfs1, initial identity, scope ---
"$python_bin" - "$seed" "$mode" <<'PY'
import hashlib, json, sys
from pathlib import Path

seed = int(sys.argv[1])
mode = sys.argv[2]
app = Path('.').resolve()
version_dir = app.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

manifest = json.loads((app / 'a5-rc2-pfs1-observation-v2-files.json').read_text())
bad = []
for name, want in manifest.items():
    p = app / name
    if not p.is_file():
        bad.append((name, 'missing'))
    elif hashlib.sha256(p.read_bytes()).hexdigest() != want:
        bad.append((name, 'mismatch'))
assert not bad, bad
assert len(manifest) == 63, len(manifest)

parent_manifest_path = version_dir / 'parent-pfs1-manifest.json'
assert sha(parent_manifest_path) == \
       'bad4b59a0baecd08bd814bc98cfc28e7a0197fb9fed2effd21282ef40563c51b', \
       sha(parent_manifest_path)
parent_manifest = json.loads(parent_manifest_path.read_text())
base = json.loads((app / 'a5-manifest.json').read_text())
parent_specific = {'pfs1_observation.py', 'a5-rc2-pfs1.json', 'run-a5-rc2-pfs1.sh'}
changed = {'a5_recovery.py', 'a5_capture.py'}
unchanged = [name for name in parent_manifest
             if name not in parent_specific and name not in changed]
assert len(unchanged) == 58, len(unchanged)
for name in unchanged:
    assert base.get(name) == parent_manifest[name], ('parent/base identity mismatch', name)

config = json.loads((app / 'a5-rc2-pfs1-observation-v2.json').read_text())
assert config['version'] == 'a5-rc2-pfs1-observation-v2'
assert config['parent_manifest_sha256'] == \
       'bad4b59a0baecd08bd814bc98cfc28e7a0197fb9fed2effd21282ef40563c51b'
assert config['physical_invariance']['unchanged_from_pfs1'] is True
assert config['physical_invariance']['particle_friction_scale'] == 1.0
assert config['physical_invariance']['friction'] == 0.3
assert config['subject']['seed'] == seed == 4202
assert config['subject']['mode'] == mode == 'single'
assert config['run']['one_shot'] is True
assert config['observation_revision']['velocity_policy']['raw_api_validated'] is False
assert config['observation_revision']['semantic_validity']['raw_readback_is_not_semantic_pass'] is True
assert config['observation_revision']['contact_capability']['required_for_acceptance'] is False

recovery = (app / 'a5_recovery.py').read_text()
capture = (app / 'a5_capture.py').read_text()
assert "k['particle_friction_scale'] = 1." in recovery
assert 'pfs1_observation_v2' in recovery and 'pfs1_observation_v2' in capture
for bad_marker in ('hold_open_for_steps', 'internal_delay', 'release_order', 'preopen'):
    assert bad_marker not in recovery, ('D1/D2-C residue', bad_marker)
for bad_marker in ('release_order', 'preopen', 'suppressed_open'):
    assert bad_marker not in capture, ('D2-C residue', bad_marker)
for required in ('after_construction', 'after_reset', 'after_initial_settle',
                 'after_recovery', 'pre_release'):
    assert required in recovery, ('material stage hook missing', required)
assert 'fd_velocities' in (app / 'pfs1_observation_v2.py').read_text()
assert 'ClothPrimView.get_velocities' in (app / 'pfs1_observation_v2.py').read_text()

policy = json.loads((app / 'a5-candidate.json').read_text())
item = policy['development'][str(seed)]
assert mode in item['modes']
initial = Path('/root/autodl-tmp') / item['initial']
assert str(initial) == config['initial']['dir_remote'], (str(initial), config['initial']['dir_remote'])
assert item['files'] == config['initial']['hashes']
for name, want in config['initial']['hashes'].items():
    have = hashlib.sha256((initial / name).read_bytes()).hexdigest()
    assert have == want, (name, have, want)

# New one-shot lock: an unfinished attempt for THIS manifest blocks a retry.
attempts_path = Path('/root/autodl-tmp/a5-rc2-pfs1-observation-v2-runs/attempts.jsonl')
current_manifest = hashlib.sha256((app / 'a5-rc2-pfs1-observation-v2-files.json').read_bytes()).hexdigest()
if attempts_path.is_file():
    attempts = [json.loads(line) for line in attempts_path.read_text().splitlines() if line.strip()]
    started_current = [r for r in attempts if r.get('state') == 'started'
                       and r.get('manifest_sha256') == current_manifest]
    finished_current = [r for r in attempts if r.get('state') == 'finished'
                        and r.get('manifest_sha256') == current_manifest]
    assert not (started_current and not finished_current), \
        'unfinished attempt exists for the current v2 manifest; inspect the ledger'

initial_result = json.loads((initial / 'result.json').read_text())
assert initial_result.get('passed') is True
case = initial_result['initial_case']
assert case['seed'] == seed and case['level'] == 'perturbed'
plan = json.loads((app / 'square-initial-plan.json').read_text())['episodes']
assert sum(row == case for row in plan) == 1, 'Initial case differs from plan'
print('PFS1_V2_PREFLIGHT_OK', len(manifest), config['parent_manifest_sha256'], str(initial), flush=True)
PY

if [ "${PFS1_OBS_V2_PREFLIGHT_ONLY:-0}" = "1" ]; then
  echo "PFS1_V2_PREFLIGHT_ONLY_OK $initial"
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
    'version': 'a5-rc2-pfs1-observation-v2',
    'seed': seed,
    'mode': mode,
    'host': socket.gethostname(),
    'pid': os.getpid(),
    'cwd': str(Path.cwd()),
    'manifest_sha256': hashlib.sha256(Path('a5-rc2-pfs1-observation-v2-files.json').read_bytes()).hexdigest(),
    'config_sha256': hashlib.sha256(Path('a5-rc2-pfs1-observation-v2.json').read_bytes()).hexdigest(),
    'initial': initial,
}
with log.open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n')
    fh.flush()
    os.fsync(fh.fileno())
PY

existing=$(mktemp)
ls -d /root/autodl-tmp/day4-a5-rc2-pfs1-observation-v2-* 2>/dev/null > "$existing" || true
log=$(mktemp /root/autodl-tmp/a5-rc2-pfs1-observation-v2-log-XXXXXXXX.log)

set +e
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
  "$python_bin" -u a5_entry.py run --initial "$initial" --mode "$mode" \
  --split dev --journal "$runs/journal" 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e
entry_status=${statuses[0]}

result_dir=$(sed -n 's/^DOWNLOAD_DIR //p' "$log" | tail -1)
new_dirs=$(mktemp)
ls -d /root/autodl-tmp/day4-a5-rc2-pfs1-observation-v2-* 2>/dev/null | grep -vxF -f "$existing" > "$new_dirs" || true
if [ -z "$result_dir" ]; then
  new_count=$(grep -c . "$new_dirs" || true)
  if [ "$new_count" -eq 1 ]; then
    result_dir=$(cat "$new_dirs")
  fi
fi
if [ -z "$result_dir" ] || [ ! -d "$result_dir" ]; then
  echo 'PFS1_V2_ABORT no result directory; retain log '"$log" >&2
  echo 'PFS1_V2_LOG_RETAINED '"$log" >&2
  exit 4
fi
cp "$log" "$result_dir/runner.log"
echo "PFS1_V2_LOG $result_dir/runner.log"

# --- post-run: separate file completeness, observation semantics, quality ---
post_status=0
"$python_bin" - "$result_dir" "$entry_status" "$attempt_log" "$runs/completed" <<'PY' || post_status=$?
import hashlib, json, math, sys
from datetime import datetime, timezone
from pathlib import Path

d = Path(sys.argv[1])
entry_status = int(sys.argv[2])
attempt_log = Path(sys.argv[3])
marker = Path(sys.argv[4])
app = Path('.').resolve()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

required = [
    'result.json', 'a5-verdict.json', 'success_trace.npz', 'success_meta.json', 'final.png',
    'pre_release_hold.npz', 'pfs1_stage_index.json',
    'pfs1_release_steps.npz', 'pfs1_release_steps.json',
    'pfs1_first_0_5s.npz', 'pfs1_first_0_5s.json',
    'pfs1_formal_210_330.npz', 'pfs1_formal_210_330.json',
    'pfs1_release_clock.json', 'material_readbacks.json',
    'contact_capability.json', 'evidence/summary.json',
    'evidence/timeline.jsonl', 'evidence/manifest.json',
]
file_presence = {name: (d / name).is_file() for name in required}
file_complete = all(file_presence.values())

def read_json(path, default=None):
    p = d / path
    if not p.is_file():
        return default
    return json.loads(p.read_text())

result = read_json('result.json', {})
verdict = read_json('a5-verdict.json', {})
criteria = verdict.get('criteria') or {}
quality_status = criteria.get('status')
quality_accepted = quality_status == 'accepted'
episode_passed = result.get('passed') is True

stage_index = read_json('pfs1_stage_index.json', [])
stage_labels = [x.get('label') for x in stage_index if isinstance(x, dict)]
required_stages = ['initial_loaded', 'after_recovery', 'pre_release', 'release_boundary']
stage_files_ok = all(label in stage_labels and (d / 'pfs1_stages' / (label + '.npz')).is_file()
                     for label in required_stages)
file_complete = bool(file_complete and stage_files_ok)

# --- observation semantic checks ---
release_meta = read_json('pfs1_release_steps.json', {})
first_meta = read_json('pfs1_first_0_5s.json', {})
formal_meta = read_json('pfs1_formal_210_330.json', {})
fd_policy_ok = all(
    isinstance(meta.get('fd_method'), str) and meta.get('fd_method')
    and isinstance(meta.get('fd_time_source'), str) and meta.get('fd_time_source')
    for meta in (release_meta, first_meta, formal_meta)
)
fd_valid = int(release_meta.get('fd_velocity_valid_count') or 0) > 0
raw_unvalidated = (release_meta.get('readback_velocity_validated') is False
                   and all(x.get('readback_velocity_validated') is False for x in stage_index))
# Single-frame stages intentionally have no finite-difference velocity; the
# per-step release record must provide valid FD samples.

mat = read_json('material_readbacks.json', {})
mat_stages = mat.get('stages') or {}
mat_required = ['after_construction', 'after_reset', 'after_initial_settle',
                'after_recovery', 'pre_release']
mat_present = all(x in mat_stages for x in mat_required)

def call_value(x):
    if isinstance(x, dict) and x.get('ok') is True:
        return x.get('value')
    return None

def close(a, b, tol):
    return isinstance(a, (int, float)) and abs(float(a) - b) <= tol

mat_values_ok = True
mat_binding_ok = True
mat_self_ok = True
mat_nonparticle_ok = True
mat_solver_boundary = True
for label, rec in mat_stages.items():
    if not isinstance(rec, dict):
        mat_values_ok = False; continue
    if label == 'after_construction':
        # Recorded as construction-time evidence.  The live reset/recovery/
        # pre-release stages below are the enforced value gates.
        continue
    pm = rec.get('particle_material') or {}
    friction = call_value(pm.get('friction'))
    scale = call_value(pm.get('particle_friction_scale'))
    pm_path = pm.get('prim_path')
    targets = rec.get('binding_targets') or []
    mat_values_ok = mat_values_ok and close(friction, 0.3, 1e-5) and close(scale, 1.0, 1e-6)
    mat_binding_ok = mat_binding_ok and bool(pm_path) and pm_path in targets
    mat_self_ok = mat_self_ok and rec.get('self_collision_value') is True
    mat_nonparticle_ok = mat_nonparticle_ok and rec.get('non_particle_collision_value') is True
    mat_solver_boundary = mat_solver_boundary and \
        ('unverified' in str(rec.get('solver_effective', '')))

contact = read_json('contact_capability.json', {})
contact_ok = (contact.get('cloth_ground_force_impulse') is False
              and contact.get('required_for_acceptance') is False
              and bool(contact.get('reason')))
clock = read_json('pfs1_release_clock.json', {})
clock_ok = (isinstance(clock, dict)
            and bool(clock.get('t0_definition'))
            and isinstance(clock.get('sampling_error_steps'), int)
            and (clock.get('release_boundary') or {}).get('attachment_enabled_any') is False)
semantic_checks = {
    'fd_policy_recorded': bool(fd_policy_ok),
    'fd_velocity_valid_present': bool(fd_valid),
    'raw_readback_marked_unvalidated': bool(raw_unvalidated),
    'material_stages_present': bool(mat_present),
    'material_values_match': bool(mat_values_ok),
    'material_binding_match': bool(mat_binding_ok),
    'self_collision_true': bool(mat_self_ok),
    'non_particle_collision_true': bool(mat_nonparticle_ok),
    'solver_effective_boundary_recorded': bool(mat_solver_boundary),
    'contact_capability_recorded': bool(contact_ok),
    'release_clock_boundary_recorded': bool(clock_ok),
    'quality_status_recorded': quality_status in ('accepted', 'rejected'),
}
observation_semantics_valid = all(semantic_checks.values())
overall_valid = bool(file_complete and observation_semantics_valid and quality_accepted and episode_passed)
semantics = {
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'file_completeness': {'complete': bool(file_complete), 'presence': file_presence,
                          'stage_labels': stage_labels, 'required_stages': required_stages},
    'observation_semantics': {'valid': bool(observation_semantics_valid),
                              'checks': semantic_checks,
                              'release_meta': release_meta,
                              'material_status': mat.get('solver_effective'),
                              'contact_capability': contact},
    'quality': {'status': quality_status, 'accepted': bool(quality_accepted),
                'episode_passed': bool(episode_passed)},
    'overall_pass': bool(overall_valid),
    'note': 'File completeness, observation semantics and quality are separate; raw velocity readback is not a semantic pass.',
}
(d / 'pfs1_semantics.json').write_text(json.dumps(semantics, indent=2, allow_nan=False) + '\n')

files = {name: {'present': (d / name).is_file(),
                'bytes': (d / name).stat().st_size if (d / name).is_file() else None,
                'sha256': sha(d / name) if (d / name).is_file() else None}
         for name in required}
rec = {
    'state': 'finished',
    'utc': datetime.now(timezone.utc).isoformat(),
    'version': 'a5-rc2-pfs1-observation-v2',
    'manifest_sha256': hashlib.sha256((app / 'a5-rc2-pfs1-observation-v2-files.json').read_bytes()).hexdigest(),
    'config_sha256': hashlib.sha256((app / 'a5-rc2-pfs1-observation-v2.json').read_bytes()).hexdigest(),
    'seed': 4202,
    'mode': 'single',
    'result_dir': str(d),
    'entry_assess_exit': entry_status,
    'file_complete': bool(file_complete),
    'observation_semantics_valid': bool(observation_semantics_valid),
    'quality_status': quality_status,
    'quality_accepted': bool(quality_accepted),
    'episode_passed': bool(episode_passed),
    'overall_valid': bool(overall_valid),
    'semantic_checks': semantic_checks,
    'errors': result.get('errors'),
    'action_count': result.get('action_count'),
    'call_horizons': result.get('call_horizons'),
    'material_readback': str(d / 'material_readbacks.json'),
    'contact_capability': str(d / 'contact_capability.json'),
    'files': files,
}
(d / 'pfs1_observation_v2_ledger.json').write_text(json.dumps(rec, indent=2, allow_nan=False) + '\n')
with attempt_log.open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(rec, sort_keys=True) + '\n')
    fh.flush()
marker.write_text(str(d) + '\n', encoding='utf-8')
print('PFS1_V2_LEDGER', d / 'pfs1_observation_v2_ledger.json', flush=True)
print('PFS1_V2_SEMANTICS', json.dumps(semantic_checks, sort_keys=True), flush=True)
if not overall_valid:
    raise SystemExit(5)
PY

if [ "$post_status" -eq 5 ]; then
  echo "PFS1_V2_NOT_OVERALL_PASS $result_dir" >&2
  exit 5
fi
if [ "$post_status" -ne 0 ]; then
  echo "PFS1_V2_POSTCHECK_FAILED status=$post_status; evidence retained in $result_dir" >&2
  exit 1
fi
echo "PFS1_V2_SINGLE_RUN_COMPLETE $result_dir"
