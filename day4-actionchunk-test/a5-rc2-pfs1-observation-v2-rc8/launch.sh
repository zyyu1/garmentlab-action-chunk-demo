#!/usr/bin/env bash
# rc8 batch launcher: no quoting through ssh; the runner does its own cd.
cd /root/autodl-tmp/a5-rc2-pfs1-observation-v2-rc8/app || exit 9
exec bash run-a5-rc2-pfs1-observation-v2.sh > /root/autodl-tmp/rc8-tmux.log 2>&1
