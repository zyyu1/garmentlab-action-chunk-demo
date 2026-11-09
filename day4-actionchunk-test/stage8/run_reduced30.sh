#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp/stage5-trial
exec /root/autodl-tmp/envs/isaac40/bin/python -u stage8/batch_run.py \
  --manifest /root/autodl-tmp/stage8_frozen/STAGE8_REDUCED30_MANIFEST.json \
  --out-root /root/autodl-tmp/stage8_reduced30/results \
  --attempt-root /root/autodl-tmp/stage8_reduced30/attempts \
  --csv /root/autodl-tmp/stage8_reduced30/raw_results.csv \
  --forward-csv /root/autodl-tmp/stage8_reduced30/forward_timings.csv \
  --label-prefix day4-a5-stage8r30 \
  --policy-device cuda
