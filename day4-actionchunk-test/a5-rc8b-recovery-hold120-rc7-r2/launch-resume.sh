#!/usr/bin/env bash
cd /root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2 || exit 9
exec bash resume-slots2-7.sh > /root/autodl-tmp/hold120-rc7-r2-resume-tmux.log 2>&1
