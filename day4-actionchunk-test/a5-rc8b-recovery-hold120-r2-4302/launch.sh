#!/usr/bin/env bash
cd /root/autodl-tmp/a5-rc8b-recovery-hold120-r2-4302/app || exit 9
exec bash run-a5-rc2-pfs1-observation-v2.sh > /root/autodl-tmp/hold120-r2-4302-tmux.log 2>&1
