#!/usr/bin/env bash
# One Stage 6 L1 development recheck with budget500 best_val.
# No retry, no expert backfill, no target snapping, no threshold change.
set -euo pipefail

PY=/root/autodl-tmp/envs/isaac40/bin/python
ROOT=/root/autodl-tmp
STAGE5="$ROOT/stage5-trial"
REPO="$ROOT/garmentlab-action-chunk-demo"
APP="$STAGE5/app"
RESULT="$ROOT/day4-a5-rc2-l1-20261107-070512-123007"
OBS="$STAGE5/obs-formal/day4-a5-rc2-l1-20261107-070512-123007"
EPISODES="$STAGE5/final/episodes.jsonl"
BIND="$STAGE5/holdingfix-20261108/diagnostics/budget500/runtime_recheck"
CKPT_SRC="$STAGE5/holdingfix-20261108/diagnostics/budget500/best_val.pt"
STATS_SRC="$STAGE5/holdingfix-20261108/data/stats.json"
CKPT="$BIND/best.pt"
STATS="$BIND/stats.json"
OUTROOT="$ROOT/stage6_runs/results"
ATTEMPT_ROOT="$ROOT/stage6_runs/attempts"
STAMP=$(date -u +%Y%m%d-%H%M%S)
ATTEMPT="$ATTEMPT_ROOT/6120-recheck-budget500-$STAMP"
LABEL=day4-a5-bc-recheck-budget500
PURPOSE=development_recheck_new_checkpoint
EXPECTED_CKPT=ade6013141cfa3b114fe6583602da4b14486b96d736ffe5bbfd104cc3e517208
EXPECTED_STATS=cbc4d711b2341b7ab786ca345ccb490bb32de1ebf93fb1eacc59de22d61a9ae9

mkdir -p "$ATTEMPT" "$OUTROOT"
echo "$ATTEMPT" > "$ATTEMPT_ROOT/LATEST_6120_RECHECK"

# Runtime binding must be byte-identical to the registered source; never use
# the old formal checkpoint/stats.
"$PY" - "$CKPT" "$STATS" "$CKPT_SRC" "$STATS_SRC" "$EXPECTED_CKPT" "$EXPECTED_STATS" <<'PY'
import hashlib, sys
bind_ckpt, bind_stats, src_ckpt, src_stats, exp_ckpt, exp_stats = sys.argv[1:7]
def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()
a, b = sha(bind_ckpt), sha(src_ckpt)
c, d = sha(bind_stats), sha(src_stats)
assert a == b == exp_ckpt, (a, b, exp_ckpt)
assert c == d == exp_stats, (c, d, exp_stats)
print('RUNTIME_BINDING_OK', a, c)
PY

# 1. Final Stage 5 episode row must still be flat / val.
"$PY" - "$EPISODES" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding='utf-8')
        if line.strip()]
match = [row for row in rows if int(row.get('seed', -1)) == 6120]
assert len(match) == 1, len(match)
row = match[0]
assert row['level'] == 'flat' and row['split'] == 'val', row
assert row['result_dir'] == '/root/autodl-tmp/day4-a5-rc2-l1-20261107-070512-123007'
assert row['obs_dir'] == '/root/autodl-tmp/stage5-trial/obs-formal/day4-a5-rc2-l1-20261107-070512-123007'
print('EPISODE_ROW_OK', row['result_dir'])
PY

INIT=$("$PY" -c "import json;print(json.load(open('$RESULT/result.json'))['initial_dir'])")
test -f "$INIT/result.json"
test -f "$INIT/initial_geometry.npz"

# 2. Independent attempt record with full model/initial/runner hashes.
"$PY" - "$ATTEMPT" "$RESULT" "$INIT" "$CKPT" "$CKPT_SRC" "$STATS" "$STATS_SRC" "$EPISODES" <<'PY'
import datetime, hashlib, json, os, sys
(attempt, result, initial, bind_ckpt, ckpt_src, bind_stats, stats_src,
 episodes) = sys.argv[1:9]
def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()
rows = [json.loads(line) for line in open(episodes, encoding='utf-8')
        if line.strip()]
row = [r for r in rows if int(r.get('seed', -1)) == 6120][0]
payload = {
    'purpose': 'development_recheck_new_checkpoint',
    'seed': 6120,
    'level': 'flat',
    'split': 'val',
    'max_actions': 7,
    'result_dir': result,
    'initial_dir': initial,
    'obs_dir': '/root/autodl-tmp/stage5-trial/obs-formal/day4-a5-rc2-l1-20261107-070512-123007',
    'episode_row': row,
    'checkpoint': bind_ckpt,
    'checkpoint_source': ckpt_src,
    'checkpoint_sha256': sha(bind_ckpt),
    'checkpoint_source_sha256': sha(ckpt_src),
    'checkpoint_epoch': 498,
    'checkpoint_val_total': 0.024020773073634115,
    'stats': bind_stats,
    'stats_source': stats_src,
    'stats_sha256': sha(bind_stats),
    'stats_source_sha256': sha(stats_src),
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
                '--label day4-a5-bc-recheck-budget500 '
                '--skip-identity-check'),
    'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'automatic_retry': False,
    'identity_check_skipped_for_reviewed_replacement': True,
}
open(os.path.join(attempt, 'started.json'), 'w', encoding='utf-8').write(
    json.dumps(payload, indent=2, allow_nan=False) + '\n')
print('ATTEMPT_STARTED', attempt)
PY

if [ -f /root/autodl-tmp/stage6_recheck_precheck.json ]; then
  cp /root/autodl-tmp/stage6_recheck_precheck.json "$ATTEMPT/precheck.json"
fi

# 3. Run once. The runner creates a new label/timestamp result directory.
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

# 4. Independent finished record; no retry.
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
                 'bc_observations.npz', 'final.npz', 'fold_initial.npz',
                 'video.mp4'):
        path = os.path.join(result_dir, name)
        artifacts[name] = {'exists': os.path.isfile(path),
                           'sha256': sha(path) if os.path.isfile(path) else None,
                           'bytes': os.path.getsize(path) if os.path.isfile(path) else None}
payload = {
    'purpose': 'development_recheck_new_checkpoint',
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
