#!/usr/bin/env bash
cd /root/autodl-tmp/a5-rc2-pfs1-observation-v2-l2patch9/app || exit 9
exec bash run-a5-rc2-pfs1-observation-v2.sh > /root/autodl-tmp/l2patch9-tmux.log 2>&1
