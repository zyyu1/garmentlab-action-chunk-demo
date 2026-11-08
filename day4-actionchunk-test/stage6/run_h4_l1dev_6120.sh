#!/usr/bin/env bash
# One Stage 7 H4 L1 development run, seed 6120, execute_k=4. No retry.
set -euo pipefail

PY=/root/autodl-tmp/envs/isaac40/bin/python
ROOT=/root/autodl-tmp
STAGE5="$ROOT/stage5-trial"
REPO="$ROOT/garmentlab-action-chunk-demo"
APP="$STAGE5/app"
INITIAL="$ROOT/day4-square-initial-20261107-070155-602415"
CKPT="$STAGE5/holdingfix-20261108/h4fix-20261108/runs/h4_budget500/best_val.pt"
STATS="$STAGE5/holdingfix-20261108/h4fix-20261108/stats.json"
OUTROOT="$ROOT/stage6_runs/results"
ATTEMPT_ROOT="$ROOT/stage6_runs/attempts"
PRECHECK="$STAGE5/holdingfix-20261108/h4fix-20261108/diagnostics/h4_l1_offline_check.json"
STAMP=$(date -u +%Y%m%d-%H%M%S)
ATTEMPT="$ATTEMPT_ROOT/h4-l1dev-6120-$STAMP"
LABEL=day4-a5-h4-l1dev-6120
EXPECTED_CKPT=ff8c694516eb8940e089aeb0a380daab6da0d84e9ab53aeaa6cd302c9a6c21d5
EXPECTED_STATS=fe5df5c45fb29f0c96d38a7d6cae8b8f19464c51884ae6631bdaa3dc16d553fb
EXPECTED_RUNNER=488711adb25f1258bf9b11df7b9f0db9d4596215391f9429490cfc5e129f6be2

mkdir -p "$ATTEMPT" "$OUTROOT"
echo "$ATTEMPT" > "$ATTEMPT_ROOT/LATEST_H4_L1DEV"

"$PY" - "$CKPT" "$STATS" "$INITIAL" "$EXPECTED_CKPT" "$EXPECTED_STATS" "$EXPECTED_RUNNER" <<'PY'
import hashlib, json, sys
ckpt, stats, initial, exp_ckpt, exp_stats, exp_runner = sys.argv[1:7]
def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()
assert sha(ckpt) == exp_ckpt, sha(ckpt)
assert sha(stats) == exp_stats, sha(stats)
assert sha('/root/autodl-tmp/stage5-trial/stage6/a5_bc_single.py') == exp_runner
assert sha('/root/autodl-tmp/stage5-trial/stage6/h4_policy.py') == '4c96c29d2356bd087ebb78e1efa3b929547896ebd0105b84bf0471ce4ed7d718'
assert sha('/root/autodl-tmp/stage5-trial/stage6/h4_runner.py') == '27b895f28b8b11b310b1bab78a617232221fa9729988f0d7f42065d6bd65d274'
for name in ('result.json', 'initial_geometry.npz'):
    assert open(initial + '/' + name, 'rb').read(4)
PY

"$PY" - "$ATTEMPT" "$CKPT" "$STATS" "$INITIAL" <<'PY'
import datetime, hashlib, json, os, sys
attempt, ckpt, stats, initial = sys.argv[1:5]
def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()
payload = {
    'purpose': 'development_evaluation_l1_h4',
    'policy': 'h4_budget500_best_val',
    'level': 'flat',
    'seed': 6120,
    'initial_dir': initial,
    'checkpoint': ckpt,
    'checkpoint_sha256': sha(ckpt),
    'checkpoint_epoch': 389,
    'stats': stats,
    'stats_sha256': sha(stats),
    'stats_normalization': 'identical arrays to single; hash differs only H4 metadata',
    'initial_result_json_sha256': sha(initial + '/result.json'),
    'initial_geometry_npz_sha256': sha(initial + '/initial_geometry.npz'),
    'runner_sha256': sha('/root/autodl-tmp/stage5-trial/stage6/a5_bc_single.py'),
    'h4_policy_sha256': sha('/root/autodl-tmp/stage5-trial/stage6/h4_policy.py'),
    'h4_runner_sha256': sha('/root/autodl-tmp/stage5-trial/stage6/h4_runner.py'),
    'step_hook_sha256': sha('/root/autodl-tmp/stage5-trial/stage6/step_hook.py'),
    'horizon': 4,
    'execute_k': 4,
    'budget': 7,
    'command': ('/root/autodl-tmp/envs/isaac40/bin/python -u '
                '/root/autodl-tmp/stage5-trial/stage6/a5_bc_single.py '
                '--initial-dir ' + initial +
                ' --checkpoint ' + ckpt +
                ' --stats ' + stats +
                ' --app-dir /root/autodl-tmp/stage5-trial/app '
                '--repo-root /root/autodl-tmp/garmentlab-action-chunk-demo '
                '--out-root /root/autodl-tmp/stage6_runs/results '
                '--label day4-a5-h4-l1dev-6120 '
                '--policy h4 --execute-k 4 --skip-identity-check'),
    'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'automatic_retry': False,
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
  --initial-dir "$INITIAL" \
  --checkpoint "$CKPT" \
  --stats "$STATS" \
  --app-dir "$APP" \
  --repo-root "$REPO" \
  --out-root "$OUTROOT" \
  --label "$LABEL" \
  --policy h4 \
  --execute-k 4 \
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

"$PY" - "$ATTEMPT" "$CODE" "$DOWNLOAD" <<'PY'
import datetime, hashlib, json, os, sys
attempt, code, result_dir = sys.argv[1], int(sys.argv[2]), sys.argv[3]
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
    'purpose': 'development_evaluation_l1_h4',
    'policy': 'h4_budget500_best_val',
    'seed': 6120,
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
        'policy_calls': result.get('policy_calls'),
        'terminal_release': result.get('terminal_release'),
        'reasons': result.get('reasons'),
        'errors': result.get('errors'),
    },
    'artifacts': artifacts,
    'automatic_retry': False,
}
open(os.path.join(attempt, 'finished.json'), 'w', encoding='utf-8').write(
    json.dumps(payload, indent=2, allow_nan=False) + '\n')
print(json.dumps({'attempt_dir': attempt, 'process_exit_code': code,
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
