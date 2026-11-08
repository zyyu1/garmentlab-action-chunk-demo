#!/usr/bin/env bash
# One L1 development-evaluation random run. No retry.
set -euo pipefail

SEED="$1"
INIT="$2"
DEMO="$3"
OBS="$4"
PY=/root/autodl-tmp/envs/isaac40/bin/python
ROOT=/root/autodl-tmp
STAGE5="$ROOT/stage5-trial"
REPO="$ROOT/garmentlab-action-chunk-demo"
APP="$STAGE5/app"
BIND="$STAGE5/holdingfix-20261108/diagnostics/budget500/runtime_recheck"
CKPT_SRC="$STAGE5/holdingfix-20261108/diagnostics/budget500/best_val.pt"
STATS_SRC="$STAGE5/holdingfix-20261108/data/stats.json"
CKPT="$BIND/best.pt"
STATS="$BIND/stats.json"
MANIFEST="$ROOT/stage6_runs/evals/l1_dev_budget500_20261108/manifest.json"
PRECHECK="$ROOT/stage6_runs/evals/l1_dev_budget500_20261108/precheck.json"
OUTROOT="$ROOT/stage6_runs/results"
ATTEMPT_ROOT="$ROOT/stage6_runs/attempts"
STAMP=$(date -u +%Y%m%d-%H%M%S)
ATTEMPT="$ATTEMPT_ROOT/l1dev-random-$SEED-$STAMP"
LABEL="day4-a5-l1dev-random-$SEED"
EXPECTED_CKPT=ade6013141cfa3b114fe6583602da4b14486b96d736ffe5bbfd104cc3e517208
EXPECTED_STATS=cbc4d711b2341b7ab786ca345ccb490bb32de1ebf93fb1eacc59de22d61a9ae9

mkdir -p "$ATTEMPT" "$OUTROOT"
echo "$ATTEMPT" > "$ATTEMPT_ROOT/LATEST_L1DEV_RANDOM_$SEED"

"$PY" - "$MANIFEST" "$SEED" "$INIT" "$DEMO" "$OBS" "$CKPT" "$STATS" \
  "$CKPT_SRC" "$STATS_SRC" "$EXPECTED_CKPT" "$EXPECTED_STATS" <<'PY'
import hashlib, json, sys
(manifest_path, seed, initial, demo, obs, bind_ckpt, bind_stats,
 ckpt_src, stats_src, exp_ckpt, exp_stats) = sys.argv[1:12]
seed = int(seed)
manifest = json.load(open(manifest_path, encoding='utf-8'))
case = [c for c in manifest['cases'] if int(c['seed']) == seed]
assert len(case) == 1, (seed, len(case))
case = case[0]
assert case['initial_dir'] == initial, (case['initial_dir'], initial)
assert case['demo_result_dir'] == demo, (case['demo_result_dir'], demo)
assert case['obs_dir'] == obs, (case['obs_dir'], obs)
def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()
assert sha(initial + '/result.json') == case['initial_result_json_sha256']
assert sha(initial + '/initial_geometry.npz') == case['initial_geometry_npz_sha256']
assert sha(bind_ckpt) == sha(ckpt_src) == exp_ckpt
assert sha(bind_stats) == sha(stats_src) == exp_stats
json.dump({'case': case, 'checkpoint_sha256': exp_ckpt,
           'stats_sha256': exp_stats}, sys.stdout)
PY

"$PY" - "$ATTEMPT" "$SEED" "$INIT" "$DEMO" "$OBS" "$CKPT" "$CKPT_SRC" \
  "$STATS" "$STATS_SRC" <<'PY'
import datetime, hashlib, json, os, sys
(attempt, seed, initial, demo, obs, bind_ckpt, ckpt_src, bind_stats,
 stats_src) = sys.argv[1:10]
def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()
payload = {
    'purpose': 'development_evaluation_l1',
    'policy': 'random',
    'seed': int(seed),
    'level': 'flat',
    'split': 'val',
    'max_actions': 7,
    'initial_dir': initial,
    'demo_result_dir': demo,
    'obs_dir': obs,
    'checkpoint': bind_ckpt,
    'checkpoint_source': ckpt_src,
    'checkpoint_sha256': sha(bind_ckpt),
    'checkpoint_source_sha256': sha(ckpt_src),
    'checkpoint_epoch': 498,
    'stats': bind_stats,
    'stats_source': stats_src,
    'stats_sha256': sha(bind_stats),
    'stats_source_sha256': sha(stats_src),
    'initial_result_json_sha256': sha(os.path.join(initial, 'result.json')),
    'initial_geometry_npz_sha256': sha(os.path.join(initial, 'initial_geometry.npz')),
    'runner_sha256': sha('/root/autodl-tmp/stage5-trial/stage6/a5_bc_single.py'),
    'random_policy_sha256': sha('/root/autodl-tmp/stage5-trial/stage6/random_policy.py'),
    'step_hook_sha256': sha('/root/autodl-tmp/stage5-trial/stage6/step_hook.py'),
    'random': {
        'base_seed': 0,
        'episode_seed': int(seed),
        'rng': 'numpy.random.default_rng([0, episode_seed])',
        'draw_order_per_action': ['dx', 'dy', 'dz', 'dyaw', 'gripper'],
        'xyz': 'current actual EE xyz + U(-0.05,0.05) per axis',
        'yaw': ('current actual EE yaw + U(-0.2,0.2) rad; '
                'R.from_euler("xyz",[pi,0,yaw]) convention'),
        'gripper': '0/1/2 equal probability',
        'checkpoint_used': False,
        'no_expert_target': True,
        'no_prepared_region_snap': True,
    },
    'command': ('/root/autodl-tmp/envs/isaac40/bin/python -u '
                '/root/autodl-tmp/stage5-trial/stage6/a5_bc_single.py '
                '--initial-dir ' + initial +
                ' --checkpoint ' + bind_ckpt +
                ' --stats ' + bind_stats +
                ' --app-dir /root/autodl-tmp/stage5-trial/app '
                '--repo-root /root/autodl-tmp/garmentlab-action-chunk-demo '
                '--out-root /root/autodl-tmp/stage6_runs/results '
                '--label ' + 'day4-a5-l1dev-random-' + seed +
                ' --policy random --random-base-seed 0 '
                '--skip-identity-check'),
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
  --policy random \
  --random-base-seed 0 \
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

"$PY" - "$ATTEMPT" "$CODE" "$DOWNLOAD" "$SEED" <<'PY'
import datetime, hashlib, json, os, sys
attempt, code, result_dir, seed = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
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
    'purpose': 'development_evaluation_l1',
    'policy': 'random',
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
print(json.dumps({'seed': int(seed), 'attempt_dir': attempt,
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
