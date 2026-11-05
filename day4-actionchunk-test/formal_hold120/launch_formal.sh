#!/usr/bin/env bash
# Formal hold120 launcher (do not run while another batch lock exists).
cd /root/autodl-tmp/stage4-formal-hold120 || exit 9
exec /root/autodl-tmp/envs/isaac40/bin/python -u formal_driver.py \
  --state /root/autodl-tmp/stage4-formal-hold120-formal-v1 \
  >> /root/autodl-tmp/stage4-formal-hold120/formal_run.log 2>&1
