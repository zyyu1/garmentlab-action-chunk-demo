#!/usr/bin/env bash
# Sequential fixed L2/L3 remaining cases. One attempt per case, no retry.
set -uo pipefail

ROOT=/root/autodl-tmp
STAGE5="$ROOT/stage5-trial"
RUN="$STAGE5/stage6/run_l2l3_dev_learned_one.sh"
ATTEMPTS="$ROOT/stage6_runs/attempts"
LOG="$ROOT/stage6_runs/evals/l2l3_dev_budget500_20261108/queue.log"
mkdir -p "$(dirname "$LOG")"

run_case() {
  level="$1"; seed="$2"; initial="$3"
  echo "=== CASE $level $seed $initial $(date -u +%FT%TZ) ===" | tee -a "$LOG"
  bash "$RUN" "$level" "$seed" "$initial" >> "$LOG" 2>&1
  code=$?
  latest="$ATTEMPTS/LATEST_L2L3DEV_LEARNED_${level}_${seed}"
  if [ ! -f "$latest" ]; then
    echo "INTERFACE_STOP missing LATEST for $level $seed" | tee -a "$LOG"
    return 90
  fi
  attempt=$(cat "$latest")
  if [ ! -f "$attempt/finished.json" ]; then
    echo "INTERFACE_STOP missing finished.json for $level $seed at $attempt" | tee -a "$LOG"
    return 91
  fi
  result=$("$ROOT/envs/isaac40/bin/python" -c "import json;print(json.load(open('$attempt/finished.json')).get('result_dir') or '')")
  if [ -z "$result" ] || [ ! -f "$result/result.json" ]; then
    echo "INTERFACE_STOP missing result.json for $level $seed" | tee -a "$LOG"
    return 92
  fi
  for name in bc_observations.npz evidence/episode.mp4 evidence/summary.json; do
    if [ ! -f "$result/$name" ]; then
      echo "INTERFACE_STOP missing $name for $level $seed at $result" | tee -a "$LOG"
      return 93
    fi
  done
  echo "CASE_DONE $level $seed exit=$code result=$result" | tee -a "$LOG"
  return 0
}

CASES=(
  "perturbed 4211 /root/autodl-tmp/day4-square-initial-stripfold-20261105-235820-496122"
  "perturbed 4212 /root/autodl-tmp/day4-square-initial-stripfold-20261106-000823-290425"
  "perturbed 4213 /root/autodl-tmp/day4-square-initial-stripfold-20261106-001834-589781"
  "perturbed 4214 /root/autodl-tmp/day4-square-initial-stripfold-20261106-002833-401772"
  "crumpled 6504 /root/autodl-tmp/day4-square-initial-stripfold-20261108-093047-198298"
  "crumpled 6507 /root/autodl-tmp/day4-square-initial-stripfold-20261108-105733-388488"
  "crumpled 4310 /root/autodl-tmp/day4-square-initial-stripfold-20261106-012851-089364"
  "crumpled 4311 /root/autodl-tmp/day4-square-initial-stripfold-20261106-013935-792487"
  "crumpled 4312 /root/autodl-tmp/day4-square-initial-stripfold-20261106-015028-989706"
)

for row in "${CASES[@]}"; do
  read -r level seed initial <<< "$row"
  run_case "$level" "$seed" "$initial"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "QUEUE_STOP rc=$rc after $level $seed" | tee -a "$LOG"
    exit "$rc"
  fi
done
echo "QUEUE_COMPLETE $(date -u +%FT%TZ)" | tee -a "$LOG"
