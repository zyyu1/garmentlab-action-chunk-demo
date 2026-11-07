"""Non-GPU test: run_with_timeout kills the whole process group on timeout."""
import os
import subprocess
import sys

sys.path.insert(0, '/root/autodl-tmp/stage5-trial/collect')
import collect_demos as cd  # noqa: E402

cmd = [sys.executable, '-c',
       'import subprocess,time; subprocess.Popen(["sleep","300"]); time.sleep(300)']
r = cd.run_with_timeout(cmd, '/tmp', dict(os.environ), 4)
print('timeout_flag', r['timeout'], 'exit', r['exit'])
left = subprocess.run(['pgrep', '-af', 'sleep 300'], capture_output=True, text=True).stdout.strip()
print('remaining_sleep_procs', left if left else 'none')
print('TEST_PASS' if r['timeout'] and not left else 'TEST_FAIL')
