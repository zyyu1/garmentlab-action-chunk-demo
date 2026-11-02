"""Run exactly the three user-requested remote L1 cases; download before next case."""
import hashlib
import json
import queue
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HOST = 'root@connect.nmb2.seetacloud.com'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-p', '23636', HOST]
ROOT = Path(r'E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\results')
CASES = [(4101, 'day4-square-initial-20261031-095254-316552'),
         (4106, 'day4-square-initial-20261031-100909-165817'),
         (4103, 'day4-square-initial-20261031-095925-799656')]
OUT = ROOT / ('L1_OVERHANG_002_REMAINING_' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
OUT.mkdir(parents=True)
ledger = {'scope': 'three_requested_development_cases', 'overhang_m': .02,
          'host': HOST, 'port': 23636, 'cases': [], 'status': 'running'}

def save():
    temp = OUT / 'batch.tmp'
    temp.write_text(json.dumps(ledger, indent=2), encoding='utf-8')
    temp.replace(OUT / 'batch.json')

def emit(kind, data):
    print(kind, json.dumps(data, ensure_ascii=False), flush=True)

def stream(command, log, seed):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding='utf-8', errors='replace', bufsize=1)
    messages = queue.Queue()
    def read():
        for line in proc.stdout:
            messages.put(line)
        messages.put(None)
    threading.Thread(target=read, daemon=True).start()
    lines = []
    with log.open('w', encoding='utf-8') as f:
        while True:
            try:
                line = messages.get(timeout=35)
            except queue.Empty:
                emit('RUNNING', {'seed': seed, 'elapsed_s': round(time.monotonic()-started)})
                continue
            if line is None:
                break
            f.write(line)
            f.flush()
            lines.append(line)
            if any(line.startswith(s) for s in ('L1_XFOLD_', 'RESULT_FILE ', 'DOWNLOAD_DIR ', 'EPISODE_ACTION ', 'ACTION ', 'Traceback', 'RuntimeError', 'AssertionError')):
                print(str(seed), line.rstrip(), flush=True)
    return proc.wait(), ''.join(lines)

emit('BATCH_DIRECTORY', str(OUT))
try:
    for seed, initial in CASES:
        # Reject overlapping simulation workloads; the match cannot match this pgrep itself.
        busy = subprocess.run(SSH + ["pgrep -af '[p]ython.*-u day4-'"], capture_output=True, text=True)
        if busy.returncode not in (0, 1) or busy.stdout.strip():
            raise RuntimeError('Remote workload/connectivity check failed: ' + busy.stdout + busy.stderr)
        row = {'seed': seed, 'initial_dir': '/root/autodl-tmp/' + initial, 'status': 'running'}
        ledger['cases'].append(row)
        save()
        started = time.monotonic()
        code, output = stream(SSH + ['L1_XFOLD_OVERHANG=0.02 bash /root/autodl-tmp/run-l1-xfold-yaw-aware.sh ' + row['initial_dir']], OUT / f'{seed}_ssh.log', seed)
        row['runner_exit'] = code
        candidates = set(re.findall(r'^DOWNLOAD_DIR (/root/autodl-tmp/day4-l1-xfold-yaw-aware-\d{8}-\d{6}-\d+)\s*$', output, re.M))
        if len(candidates) != 1:
            raise RuntimeError(f'{seed}: expected one output directory, got {candidates}; retain SSH log')
        remote = candidates.pop()
        local = ROOT / remote.rsplit('/', 1)[-1]
        row.update(remote_dir=remote, local_dir=str(local), status='downloading')
        save()
        emit('DOWNLOADING', row)
        subprocess.run(['scp', '-o', 'BatchMode=yes', '-P', '23636', '-r', HOST + ':' + remote, str(ROOT)], check=True)
        hashes = subprocess.check_output(SSH + ['find ' + remote + ' -type f -exec sha256sum {} \\;'], text=True)
        verified = []
        for line in hashes.splitlines():
            digest, path = line.split(None, 1)
            relative = path.removeprefix(remote + '/')
            if relative == path or '..' in Path(relative).parts:
                raise RuntimeError('Unexpected remote file path')
            actual = hashlib.sha256((local / relative).read_bytes()).hexdigest()
            if digest != actual:
                raise RuntimeError('Download hash mismatch: ' + relative)
            verified.append({'file': relative, 'sha256': actual})
        if not verified:
            raise RuntimeError('No downloaded files')
        (OUT / f'{seed}_transfer.json').write_text(json.dumps(verified, indent=2), encoding='utf-8')
        result = json.loads((local / 'result.json').read_text(encoding='utf-8'))
        if result['initial_case']['seed'] != seed or abs(result['fold_definition']['fold_overhang_m']-.02) > 1e-12:
            raise RuntimeError('Unexpected seed/overhang; no further experiments')
        row.update(status='download_verified', file_count=len(verified), passed=result['passed'],
                   errors=result['errors'], action_count=result.get('action_count'),
                   fold_metrics=result.get('fold_metrics'), elapsed_s=round(time.monotonic()-started))
        save()
        emit('CASE_DOWNLOADED_VERIFIED', row)
    ledger['status'] = 'complete'
    save()
    emit('ALL_THREE_DOWNLOADED', str(OUT))
except BaseException as exc:
    ledger['status'] = 'stopped_with_error'
    ledger['error'] = repr(exc)
    save()
    raise
