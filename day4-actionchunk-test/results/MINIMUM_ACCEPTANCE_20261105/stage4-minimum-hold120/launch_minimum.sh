#!/usr/bin/env bash
cd /root/autodl-tmp/stage4-minimum-hold120 || exit 9
exec /root/autodl-tmp/envs/isaac40/bin/python -u minimum_driver.py \
  --state /root/autodl-tmp/stage4-minimum-hold120-state-v1 \
  >> /root/autodl-tmp/stage4-minimum-hold120/run.log 2>&1
