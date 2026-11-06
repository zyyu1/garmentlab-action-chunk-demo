#!/usr/bin/env bash
# Single attempt, no retry. Writes run.log next to the script.
cd /root/autodl-tmp/stage4-4112-zerovel || exit 9
/root/autodl-tmp/envs/isaac40/bin/python diagnose_arc135_zerovel.py > run.log 2>&1
echo EXIT:$? >> run.log
