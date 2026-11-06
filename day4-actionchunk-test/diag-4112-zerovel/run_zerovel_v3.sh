#!/usr/bin/env bash
# v3: single attempt, no retry. Same intervention as v2; readback conversion fixed.
cd /root/autodl-tmp/stage4-4112-zerovel || exit 9
/root/autodl-tmp/envs/isaac40/bin/python diagnose_arc135_zerovel_v3.py > run_v3.log 2>&1
echo EXIT:$? >> run_v3.log
