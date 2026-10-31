#!/usr/bin/env bash
# Two fresh, sequential processes. Stop on failure, missing marker or bad JSON.
set -u
set -o pipefail
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
test_file=/root/autodl-tmp/day4-anchor-alignment-test.py
pair_root="$(mktemp -d /root/autodl-tmp/day4-anchor-pair-run-XXXXXXXX)"
printf 'PAIR_RUN_DIR %s\n' "$pair_root"
for mode in baseline aligned; do
    run_log="$pair_root/$mode.log"
    printf 'START_MODE %s\n' "$mode"
    GARMENTLAB_ATTACHMENT_OVERLAP=0.005 \
    GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
    GARMENTLAB_ANCHOR_ALIGNMENT="$mode" \
    "$python_bin" -X faulthandler -u "$test_file" --allow-root 2>&1 | tee "$run_log"
    run_status=("${PIPESTATUS[@]}")
    printf 'MODE=%s PYTHON_EXIT=%s TEE_EXIT=%s\n' "$mode" "${run_status[0]}" "${run_status[1]}" | tee -a "$run_log"
    if (( run_status[0] != 0 || run_status[1] != 0 )); then
        printf 'PAIR_STOPPED: process or logging failure in %s\n' "$mode"
        exit 1
    fi
    "$python_bin" - "$run_log" "$mode" "$pair_root" <<'PY'
import json
from pathlib import Path
import sys
log, mode, pair_root = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
lines = log.read_text(errors='replace').splitlines()
if 'ANCHOR_ALIGNMENT_CONTROL_OK ' + mode not in lines:
    raise RuntimeError('Missing final success marker: ' + mode)
paths = [line[len('RESULT_FILE '):] for line in lines if line.startswith('RESULT_FILE ')]
if len(paths) != 1:
    raise RuntimeError('Expected one result path')
path = Path(paths[0])
r = json.loads(path.read_text())
if r.get('passed') is not True or r.get('experiment_mode') != mode:
    raise RuntimeError('Result JSON did not pass')
m = r['alignment_metrics']
if not m.get('usd_readback_ok') or not all(m['arrays_after_first_step'].values()):
    raise RuntimeError('Anchor write/readback/persistence checks failed')
if m['usd_points1_written'] != (mode == 'aligned'):
    raise RuntimeError('Wrong intervention mode')
(pair_root/(mode+'-result-path.txt')).write_text(str(path))
print('MODE_RESULT_VERIFIED', mode, path, flush=True)
PY
    if (( $? != 0 )); then
        printf 'PAIR_STOPPED: result audit failed in %s\n' "$mode"
        exit 1
    fi
done

"$python_bin" - "$pair_root" <<'PY'
import json
from pathlib import Path
import sys
import numpy as np
root = Path(sys.argv[1])
paths = {mode: Path((root/(mode+'-result-path.txt')).read_text()) for mode in ('baseline','aligned')}
results = {mode: json.loads(path.read_text()) for mode,path in paths.items()}
with np.load(paths['baseline'].parent/'alignment_operation.npz', allow_pickle=False) as a, np.load(paths['aligned'].parent/'alignment_operation.npz', allow_pickle=False) as b:
    checks = {k: bool(np.array_equal(a[k], b[k])) for k in
              ('anchor_indices', 'points0', 'points1_original', 'vertices_before',
               'block_position', 'block_quaternion', 'block_scale')}
summary = {'result_paths': {k: str(v) for k,v in paths.items()},
           'pre_intervention_exact_match_checks': checks,
           'pre_intervention_exact_match': all(checks.values()),
           'activation': {k: v['alignment_metrics']['activation'] for k,v in results.items()},
           'grasp_lift_release': {k: {name: v[name] for name in
               ('cloth_rise','follow_error','cloth_drop','release_block_drift')} for k,v in results.items()},
           'note': 'Both pipelines completed; judge improvement from paired data, not this marker.'}
(root/'comparison.json').write_text(json.dumps(summary, indent=2))
print('PAIR_COMPARISON', json.dumps(summary), flush=True)
if not all(checks.values()):
    raise RuntimeError('Pre-intervention states differ; do not treat as a clean matched-state control')
print('ANCHOR_ALIGNMENT_PAIR_COMPLETED', root, flush=True)
PY
