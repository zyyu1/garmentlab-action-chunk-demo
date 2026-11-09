#!/usr/bin/env bash
# Generate only the remaining 4227-4229; do not regenerate completed 4220-4226.
set -euo pipefail
APP=/root/autodl-tmp/stage5-trial/app
PY=/root/autodl-tmp/envs/isaac40/bin/python
OUT=/root/autodl-tmp/stage8_initial_generation_20261109
mkdir -p "$OUT"
for seed in 4227 4228 4229; do
  echo "=== GENERATE $seed ==="
  log="$OUT/generate-$seed.log"
  started=$(date -u +%Y-%m-%dT%H:%M:%S+00:00)
  set +e
  (cd "$APP" && bash run-square-initial-stripfold.sh "$seed") > "$log" 2>&1
  status=$?
  set -e
  dir=$(grep '^DOWNLOAD_DIR ' "$log" | tail -1 | awk '{print $2}' || true)
  if [ "$status" -ne 0 ] || [ -z "${dir:-}" ] || [ ! -f "$dir/result.json" ]; then
    "$PY" - "$OUT" "$seed" "$status" "$dir" "$started" <<'PY'
import json, sys, datetime
out, seed, status, d, started = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
open(out + '/attempts.jsonl', 'a', encoding='utf-8').write(json.dumps({
    'seed': seed, 'state': 'failed', 'exit_code': status, 'dir': d or None,
    'started_utc': started, 'finished_utc': datetime.datetime.now(
        datetime.timezone.utc).isoformat(),
    'error': 'generation command/result missing'}, allow_nan=False) + '\n')
PY
    echo "GENERATION_FAILED $seed status=$status"
    exit 1
  fi
  set +e
  "$PY" - "$OUT" "$seed" "$status" "$dir" "$started" <<'PY'
import hashlib, json, os, sys, datetime
out, seed, status, d, started = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
r = json.load(open(os.path.join(d, 'result.json'), encoding='utf-8'))
c = r.get('initial_case') or {}
p = r.get('protocol') or {}
checks = {
    'passed': r.get('passed') is True,
    'level': c.get('level') == 'perturbed',
    'seed': int(c.get('seed', -1)) == seed,
    'task': p.get('task') == 'B_nominal',
    'protocol_version': p.get('version') == 'stage4-initial-v2-task-scoped',
    'friction_readback': abs(float(p.get('particle_friction_scale_readback', -1)) - 1.0) < 1e-12,
    'has_strips': bool(c.get('strips')),
    'has_geometry': os.path.isfile(os.path.join(d, 'initial_geometry.npz')),
    'has_resolved_task': bool(p.get('task')),
}
row = {'seed': seed, 'state': 'accepted' if all(checks.values()) else 'invalid',
       'exit_code': status, 'dir': d, 'started_utc': started,
       'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'result_sha256': sha(os.path.join(d, 'result.json')),
       'geometry_sha256': sha(os.path.join(d, 'initial_geometry.npz')),
       'initial_png_sha256': sha(os.path.join(d, 'initial.png')) if os.path.isfile(os.path.join(d, 'initial.png')) else None,
       'protocol': p, 'initial_case': c, 'checks': checks}
open(out + '/attempts.jsonl', 'a', encoding='utf-8').write(json.dumps(row, allow_nan=False) + '\n')
print('INITIAL_IDENTITY_CHECKED', seed, all(checks.values()), flush=True)
sys.exit(0 if all(checks.values()) else 2)
PY
  chk=$?
  set -e
  if [ "$chk" -ne 0 ]; then
    echo "INITIAL_IDENTITY_CHECK_FAILED $seed"
    exit 1
  fi
done
echo "REMAINING_4227_4229_GENERATED"
