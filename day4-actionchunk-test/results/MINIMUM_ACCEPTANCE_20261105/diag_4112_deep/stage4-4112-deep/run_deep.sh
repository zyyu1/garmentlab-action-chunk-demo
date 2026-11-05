#!/usr/bin/env bash
cd /root/autodl-tmp/stage4-4112-deep || exit 9
/root/autodl-tmp/envs/isaac40/bin/python diagnose_arc135_deep.py > run.log 2>&1
echo EXIT:$? >> run.log
