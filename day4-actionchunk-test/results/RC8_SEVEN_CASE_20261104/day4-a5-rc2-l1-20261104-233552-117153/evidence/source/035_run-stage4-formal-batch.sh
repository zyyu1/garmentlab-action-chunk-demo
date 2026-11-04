#!/usr/bin/env bash
# Stage 4 formal batch driver (runs on the remote GPU host; do not run locally).
#
#   bash run-stage4-formal-batch.sh stage4-heldout-seeds.json formal-v1
#
# Generates the 60 held-out initial states (20 per level) if they are not yet
# recorded in the batch state, then runs every seed under both execution modes
# with the frozen runners.  Every attempt is appended to attempts.jsonl; a
# failed fold never aborts the batch and never replaces an earlier result.
# A missing result directory after a runner call is treated as an
# infrastructure error and stops the batch, because the remaining attempts
# would not be comparable.
#
# This script adds no waypoints, actions or thresholds.  It only calls the
# frozen entrypoints and records what they produced.
set -euo pipefail
# Released only in work package E after A-C converge. Never set during D.
[ "${STAGE4_FORMAL_RELEASE:-}" = "A_B_C_FROZEN" ] || { echo "PAUSED: A-C must converge before E" >&2; exit 2; }
here=$(cd "$(dirname "$0")" && pwd)
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
"$python_bin" "$here/a5_entry.py" gate
seeds_json=${1:?usage: bash run-stage4-formal-batch.sh <stage4-heldout-seeds.json> <batch-tag>}
[ "$(realpath "$seeds_json")" = "$(realpath "$here/stage4-heldout-seeds.json")" ] || { echo "Use pinned seeds from candidate directory"; exit 2; }
tag=${2:?usage: bash run-stage4-formal-batch.sh <stage4-heldout-seeds.json> <batch-tag>}
[[ "$tag" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "invalid batch tag" >&2; exit 2; }
state=/root/autodl-tmp/stage4-formal-batch-$tag
mkdir -p "$state"
jsonl=$state/attempts.jsonl
log=$state/batch.log

say() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$log"; }

# Stale locks require inspecting the journal and remote process before removal.
mkdir "$state/driver.lock" || { say "BATCH_LOCKED"; exit 2; }
trap 'rmdir "$state/driver.lock"' EXIT
helper() { "$python_bin" "$here/stage4_batch_preflight.py" "$@" --state "$state"; }
helper bind --seeds "$seeds_json" --plan "$here/square-initial-plan.json"

# Fail fast if the uploaded seed list and the plan disagree.
"$python_bin" - "$seeds_json" <<'PY' || exit 2
import json, sys
from pathlib import Path
seeds = json.loads(Path(sys.argv[1]).read_text())
plan = json.loads(Path('square-initial-plan.json').read_text())
rows = {r['seed']: r for r in plan['episodes']}
for r in seeds['heldout']:
    p = rows.get(r['seed'])
    assert p is not None, 'seed missing from plan: %s' % r['seed']
    for key in ('level', 'translation_xy_m', 'yaw_rad'):
        assert p[key] == r[key], (r['seed'], key, p[key], r[key])
    assert len(seeds['heldout']) == 60
print('SEED_LIST_MATCHES_PLAN', len(seeds['heldout']), flush=True)
PY

# seed -> initial dir (one generation per seed, reused by both modes)
declare -A init_dir
if [ -f "$state/init_dirs.txt" ]; then
  while read -r lvl seed dir; do init_dir["$seed"]=$dir; done < "$state/init_dirs.txt"
fi

seed_rows() {
  "$python_bin" - "$seeds_json" <<'PY'
import json, sys
for row in json.loads(open(sys.argv[1]).read())['heldout']:
    print(row['level'], row['seed'])
PY
}

generate_initial() {
  local level=$1 seed=$2 out rc dir
  local runner=run-square-initial.sh
  [ "$level" != flat ] && runner=run-square-initial-stripfold.sh
  say "INIT_BEGIN $level $seed $runner"
  set +e
  out=$(bash "$runner" "$seed" 2>&1); rc=$?
  set -e
  echo "$out" >> "$state/init-$seed.log"
  dir=$(printf '%s\n' "$out" | sed -n 's/^DOWNLOAD_DIR //p' | tail -1)
  if [ $rc -ne 0 ] || [ -z "$dir" ]; then
    say "INIT_FAILED $level $seed rc=$rc"
    return 1
  fi
  init_dir["$seed"]=$dir
  printf '%s %s %s\n' "$level" "$seed" "$dir" >> "$state/init_dirs.txt"
  say "INIT_SAVED $level $seed $dir"
}

record_attempt() {
  local level=$1 seed=$2 exec_mode=$3 idir=$4 rdir=$5 rc=$6
  helper finish --level "$level" --seed "$seed" --execution "$exec_mode" --initial-dir "$idir" --result-dir "$rdir" --exit-code "$rc"
}

while read -r level seed; do
  [ -z "$level" ] && continue
  if [ -z "${init_dir[$seed]:-}" ]; then
    generate_initial "$level" "$seed" || { say "BATCH_ABORT initial state $level $seed"; exit 3; }
  fi
  idir=${init_dir[$seed]}
  helper initial --level "$level" --seed "$seed" --initial-dir "$idir"
  for exec_mode in single arc4; do
    status=$(helper status --level "$level" --seed "$seed" --execution "$exec_mode")
    if [ "$status" = done ]; then say "SKIP_RECORDED $level $seed $exec_mode"; continue; fi
    helper start --level "$level" --seed "$seed" --execution "$exec_mode" --initial-dir "$idir"
    set +e
    say "FOLD_BEGIN $level $seed $exec_mode A5 $idir"
    out=$("$python_bin" "$here/a5_entry.py" run --initial "$idir" --mode "$exec_mode" --split formal --journal "$state/episodes" 2>&1); rc=$?
    set -e
    echo "$out" >> "$state/fold-$level-$seed-$exec_mode.log"
    rdir=$(printf '%s\n' "$out" | sed -n 's/^DOWNLOAD_DIR //p' | tail -1)
    if [ -z "$rdir" ] || [ ! -f "$rdir/result.json" ]; then
      say "FOLD_INFRASTRUCTURE_ERROR $level $seed $exec_mode rc=$rc"
      record_attempt "$level" "$seed" "$exec_mode" "$idir" "$rdir" "$rc"
      say "BATCH_ABORT no result directory"
      exit 4
    fi
    record_attempt "$level" "$seed" "$exec_mode" "$idir" "$rdir" "$rc"
    if [ $rc -gt 1 ]; then say "BATCH_ABORT A5 evidence error $seed rc=$rc"; exit 4; fi
    say "FOLD_DONE $level $seed $exec_mode rc=$rc $rdir"
  done
done < <(seed_rows)

say "BATCH_FINISHED $state"
