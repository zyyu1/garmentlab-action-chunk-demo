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
set -uo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
seeds_json=${1:?usage: bash run-stage4-formal-batch.sh <stage4-heldout-seeds.json> <batch-tag>}
tag=${2:?usage: bash run-stage4-formal-batch.sh <stage4-heldout-seeds.json> <batch-tag>}
state=/root/autodl-tmp/stage4-formal-batch-$tag
mkdir -p "$state"
jsonl=$state/attempts.jsonl
log=$state/batch.log

say() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$log"; }

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
  out=$(bash "$runner" "$seed" 2>&1); rc=$?
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
  "$python_bin" - "$jsonl" "$level" "$seed" "$exec_mode" "$idir" "$rdir" "$rc" <<'PY'
import json, sys, datetime
path, level, seed, mode, idir, rdir, rc = sys.argv[1:8]
row = {'level': level, 'seed': int(seed), 'execution': mode,
       'initial_dir': idir, 'result_dir': rdir, 'exit_code': int(rc),
       'attempted_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
with open(path, 'a', encoding='utf-8') as fh:
    fh.write(json.dumps(row) + '\n')
PY
}

while read -r level seed; do
  [ -z "$level" ] && continue
  if [ -z "${init_dir[$seed]:-}" ]; then
    generate_initial "$level" "$seed" || { say "BATCH_ABORT initial state $level $seed"; exit 3; }
  fi
  idir=${init_dir[$seed]}
  for exec_mode in single arc4; do
    if [ "$level" = flat ]; then
      say "FOLD_BEGIN $level $seed $exec_mode $idir"
      out=$(L1_XFOLD_OVERHANG=0.02 L1_XFOLD_EXECUTION="$exec_mode" \
        bash run-l1-xfold-yaw-aware.sh "$idir" 2>&1); rc=$?
    else
      say "FOLD_BEGIN $level $seed $exec_mode left $idir"
      out=$(RECOVERY_FOLD_EXECUTION="$exec_mode" \
        bash run-recovery-fold-episode.sh "$idir" left 2>&1); rc=$?
    fi
    echo "$out" >> "$state/fold-$level-$seed-$exec_mode.log"
    rdir=$(printf '%s\n' "$out" | sed -n 's/^DOWNLOAD_DIR //p' | tail -1)
    if [ -z "$rdir" ]; then
      say "FOLD_INFRASTRUCTURE_ERROR $level $seed $exec_mode rc=$rc"
      record_attempt "$level" "$seed" "$exec_mode" "$idir" "" "$rc"
      say "BATCH_ABORT no result directory"
      exit 4
    fi
    record_attempt "$level" "$seed" "$exec_mode" "$idir" "$rdir" "$rc"
    say "FOLD_DONE $level $seed $exec_mode rc=$rc $rdir"
  done
done < <(seed_rows)

say "BATCH_FINISHED $state"
