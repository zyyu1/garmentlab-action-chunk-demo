#!/usr/bin/env bash
# l2pose launcher
cd /root/autodl-tmp/a5-rc2-pfs1-observation-v2-l2pose/app || exit 9
exec bash run-a5-rc2-pfs1-observation-v2.sh > /root/autodl-tmp/l2pose-tmux.log 2>&1
