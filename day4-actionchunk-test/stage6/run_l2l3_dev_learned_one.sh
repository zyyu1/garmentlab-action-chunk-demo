#!/usr/bin/env bash
# One L2/L3 development-evaluation learned run. No retry.
set -euo pipefail

LEVEL="$1"
SEED="$2"
INIT="$3"
PY=/root/autodl-tmp/envs/isaac40/bin/python
ROOT=/root/autodl-tmp
STAGE5="$ROOT/stage5-trial"
REPO="$ROOT/garmentlab-action-chunk-demo"
APP="$STAGE5/app"
BIND="$STAGE5/holdingfix-20261108/diagnostics/budget500/runtime_recheck"
CKPT="$BIND/best.pt"
STATS="$BIND/stats.json"
MANIFEST="$ROOT/stage6_runs/evals/l2l3_dev_budget500_20261108/manifest.json"
PRECHECK="$ROOT/stage6_runs/evals/l2l3_dev_budget500_20261108/precheck.json"
OUTROOT="$ROOT/stage6_runs/results"
ATTEMPT_ROOT="$ROOT/stage6_runs/attempts"
STAMP=$(date -u +%Y%m%d-%H%M%S)
ATTEMPT="$ATTEMPT_ROOT/l2l3dev-learned-$LEVEL-$SEED-$STAMP"
LABEL="day4-a5-l2l3dev-learned-$LEVEL-$SEED"

mkdir -p "$ATTEMPT" "$OUTROOT"
echo "$ATTEMPT" > "$ATTEMPT_ROOT/LATEST_L2L3DEV_LEARNED_${LEVEL}_$SEED"

"$PY" - "$MANIFEST" "$LEVEL" "$SEED" "$INIT" "$CKPT" "$STATS" <<'PY'
import hashlib, json, sys
manifest_path, level, seed, initial, bind_ckpt, bind_stats = sys.argv[1:7]
seed = int(seed)
manifest = json.load(open(manifest_path, encoding='utf-8'))
case = [c for c in manifest['cases']
        if c['level'] == level and int(c['seed']) == seed]
assert len(case) == 1, (level, seed, len(case))
case = case[0]
assert case['initial_dir'] == initial, (case['initial_dir'], initial)
def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()
assert sha(initial + '/result.json') == case['initial_result_json_sha256']
assert sha(initial + '/initial_geometry.npz') == case['initial_geometry_npz_sha256']
assert sha(bind_ckpt) == manifest['model']['checkpoint_sha256']
assert sha(bind_stats) == manifest['model']['stats_sha256']
json.dump({'case': case}, sys.stdout)
PY

"$PY" - "$ATTEMPT" "$LEVEL" "$SEED" "$INIT" "$CKPT" "$STATS" <<'PY'
import datetime, hashlib, json, os, sys
attempt, level, seed, initial, bind_ckpt, bind_stats = sys.argv[1:7]
def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()
payload = {
    'purpose': 'development_evaluation_l2_l3',
    'policy': 'learned_budget500_best_val',
    'level': level,
    'seed': int(seed),
    'initial_dir': initial,
    'max_actions': 12,
    'checkpoint': bind_ckpt,
    'checkpoint_sha256': sha(bind_ckpt),
    'checkpoint_epoch': 498,
    'stats': bind_stats,
    'stats_sha256': sha(bind_stats),
    'initial_result_json_sha256': sha(os.path.join(initial, 'result.json')),
    'initial_geometry_npz_sha256': sha(os.path.join(initial, 'initial_geometry.npz')),
    'runner_sha256': sha('/root/autodl-tmp/stage5-trial/stage6/a5_bc_single.py'),
    'step_hook_sha256': sha('/root/autodl-tmp/stage5-trial/stage6/step_hook.py'),
    'command': ('/root/autodl-tmp/envs/isaac40/bin/python -u '
                '/root/autodl-tmp/stage5-trial/stage6/a5_bc_single.py '
                '--initial-dir ' + initial +
                ' --checkpoint ' + bind_ckpt +
                ' --stats ' + bind_stats +
                ' --app-dir /root/autodl-tmp/stage5-trial/app '
                '--repo-root /root/autodl-tmp/garmentlab-action-chunk-demo '
                '--out-root /root/autodl-tmp/stage6_runs/results '
                '--label day4-a5-l2l3dev-learned-' + level + '-' + seed +
                ' --skip-identity-check'),
    'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'automatic_retry': False,
    'identity_check_skipped_for_reviewed_replacement': True,
}
open(os.path.join(attempt, 'started.json'), 'w', encoding='utf-8').write(
    json.dumps(payload, indent=2, allow_nan=False) + '\n')
print('ATTEMPT_STARTED', attempt)
PY

if [ -f "$PRECHECK" ]; then
  cp "$PRECHECK" "$ATTEMPT/precheck.json"
fi

set +e
"$PY" -u "$STAGE5/stage6/a5_bc_single.py" \
  --initial-dir "$INIT" \
  --checkpoint "$CKPT" \
  --stats "$STATS" \
  --app-dir "$APP" \
  --repo-root "$REPO" \
  --out-root "$OUTROOT" \
  --label "$LABEL" \
  --skip-identity-check \
  > "$ATTEMPT/runner.log" 2>&1
CODE=$?
set -e

DOWNLOAD=$(grep '^DOWNLOAD_DIR ' "$ATTEMPT/runner.log" | tail -1 | awk '{print $2}' || true)
if [ -z "${DOWNLOAD:-}" ]; then
  echo "NO_DOWNLOAD_DIR" >&2
  DOWNLOAD=$(ls -dt "$OUTROOT"/"$LABEL"-* 2>/dev/null | head -1 || true)
  if [ -n "${DOWNLOAD:-}" ]; then
    echo "NO_DOWNLOAD_DIR_FALLBACK $DOWNLOAD" >&2
  fi
fi

"$PY" - "$ATTEMPT" "$CODE" "$DOWNLOAD" "$LEVEL" "$SEED" <<'PY'
import datetime, hashlib, json, os, sys
attempt, code, result_dir, level, seed = sys.argv[1:6]
def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()
def load(path):
    try:
        return json.load(open(path, encoding='utf-8'))
    except Exception:
        return None
verdict = load(os.path.join(result_dir, 'bc-verdict.json')) if result_dir else None
result = load(os.path.join(result_dir, 'result.json')) if result_dir else None
artifacts = {}
if result_dir and os.path.isdir(result_dir):
    for name in ('result.json', 'bc-verdict.json', 'failure.json',
                 'success_trace.npz', 'partial_trace.npz',
                 'success_meta.json', 'step_hook.npz', 'step_hook.json',
                 'bc_observations.npz', 'final.npz', 'fold_initial.npz'):
        path = os.path.join(result_dir, name)
        artifacts[name] = {'exists': os.path.isfile(path),
                           'sha256': sha(path) if os.path.isfile(path) else None,
                           'bytes': os.path.getsize(path) if os.path.isfile(path) else None}
payload = {
    'purpose': 'development_evaluation_l2_l3',
    'policy': 'learned_budget500_best_val',
    'level': level,
    'seed': int(seed),
    'attempt_dir': attempt,
    'process_exit_code': code,
    'effective_exit_code': (0 if (verdict or {}).get('status') == 'accepted'
                            else 1 if (verdict or {}).get('status') == 'rejected'
                            else 3),
    'result_dir': result_dir or None,
    'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': None if verdict is None else verdict.get('status'),
    'success': None if verdict is None else verdict.get('success'),
    'action_count': None if result is None else result.get('action_count'),
    'bc_verdict': verdict,
    'result_summary': None if result is None else {
        'status': result.get('status'),
        'success': result.get('success'),
        'action_count': result.get('action_count'),
        'target_override_any': any(a.get('target_override') is not False
                                   for a in result.get('actions', [])),
        'terminal_release': result.get('terminal_release'),
        'reasons': result.get('reasons'),
        'errors': result.get('errors'),
    },
    'artifacts': artifacts,
    'automatic_retry': False,
}
open(os.path.join(attempt, 'finished.json'), 'w', encoding='utf-8').write(
    json.dumps(payload, indent=2, allow_nan=False) + '\n')
print(json.dumps({'level': level, 'seed': int(seed), 'attempt_dir': attempt,
                  'process_exit_code': code,
                  'effective_exit_code': payload['effective_exit_code'],
                  'result_dir': result_dir or None,
                  'status': payload['status'],
                  'success': payload['success'],
                  'action_count': payload['action_count']}, indent=2))
PY

echo "ATTEMPT_DIR $ATTEMPT"
echo "RESULT_DIR ${DOWNLOAD:-<none>}"
echo "PROCESS_EXIT_CODE $CODE"
EFFECTIVE=$("$PY" -c "import json;print(json.load(open('$ATTEMPT/finished.json'))['effective_exit_code'])" 2>/dev/null || echo 3)
echo "EFFECTIVE_EXIT_CODE $EFFECTIVE"
exit "$EFFECTIVE"
