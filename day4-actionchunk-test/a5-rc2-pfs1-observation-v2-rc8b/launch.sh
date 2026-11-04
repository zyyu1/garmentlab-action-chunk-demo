#!/usr/bin/env bash
# rc8b batch launcher: no quoting through ssh; the runner does its own cd.
cd /root/autodl-tmp/a5-rc2-pfs1-observation-v2-rc8b/app || exit 9
exec bash run-a5-rc2-pfs1-observation-v2.sh > /root/autodl-tmp/rc8b-tmux.log 2>&1
