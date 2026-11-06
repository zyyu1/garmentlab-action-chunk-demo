#!/usr/bin/env bash
# v2: single attempt, no retry. Writes run_v2.log next to the script.
cd /root/autodl-tmp/stage4-4112-zerovel || exit 9
/root/autodl-tmp/envs/isaac40/bin/python diagnose_arc135_zerovel_v2.py > run_v2.log 2>&1
echo EXIT:$? >> run_v2.log
