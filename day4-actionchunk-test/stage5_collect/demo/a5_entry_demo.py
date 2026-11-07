"""Stage 5 demo entry: run the frozen a5_l1/a5_recovery runner with split=demo.

The frozen entry is not modified.  Demo authorization is installed in the runner
process by the deployment-copy sitecustomize (STAGE5_DEMO=1); this entry only
spawns the runner, assesses the result with the frozen evaluator and writes a
verdict with split=demo.
"""
import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

DEMO = Path(__file__).resolve().parent
APP = Path('/root/autodl-tmp/stage5-trial/app')
CAND = Path('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2')
sys.path.insert(0, str(APP))
import a5_entry  # noqa: E402


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='operation', required=True)
    p = sub.add_parser('run')
    p.add_argument('--initial', type=Path, required=True)
    p.add_argument('--mode', choices=('single', 'arc4'), required=True)
    p.add_argument('--split', choices=('demo',), required=True)
    p.add_argument('--journal', type=Path, required=True)
    a = ap.parse_args()
    if a.operation != 'run':
        raise SystemExit('unsupported operation')

    case = read(a.initial / 'result.json')['initial_case']
    seed, level = int(case['seed']), case['level']
    runner = 'l1' if level == 'flat' else 'recovery'
    spec = read(APP / 'a5-candidate.json')['tasks'][level]
    assert spec['runner'] == runner, 'task/runner mismatch'

    a.journal.mkdir(parents=True, exist_ok=True)
    attempt = a.journal / ('%d-%s-%s' % (seed, a.mode, uuid.uuid4().hex))
    attempt.mkdir()
    (attempt / 'started.json').write_text(json.dumps(
        {'seed': seed, 'level': level, 'mode': a.mode, 'split': 'demo',
         'initial': str(a.initial), 'manifest_sha256': sha(APP / 'a5-manifest.json')},
        indent=2) + '\n', encoding='utf-8')

    cmd = [sys.executable, '-u', str(APP / ('a5_' + runner + '.py')),
           '--initial-dir', str(a.initial), '--allow-root', '--execution', a.mode,
           '--split', 'dev']
    cmd += ['--overhang', '.02'] if runner == 'l1' else ['--fold-edge', 'right']
    env = dict(os.environ)
    env.update(GARMENTLAB_ATTACHMENT_OVERLAP='0.005',
               GARMENTLAB_DISABLED_ATTACHMENT_PROBE='0',
               STAGE5_DEMO='1', STAGE5_DEMO_DIR=str(DEMO))
    with (attempt / 'runner.log').open('xb') as log:
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
    lines = (attempt / 'runner.log').read_text(errors='replace').splitlines()
    dirs = [l[13:] for l in lines if l.startswith('DOWNLOAD_DIR ')]
    if len(dirs) != 1:
        print('DEMO_NO_RESULT', attempt, flush=True)
        raise SystemExit(4)
    directory = Path(dirs[0])
    verdict = a5_entry.assess(directory)
    verdict.update(split='demo', runner_exit=proc.returncode,
                   result_dir=str(directory), attempt_dir=str(attempt))
    if proc.returncode != 0:
        verdict.update(status='execution_error', success=None)
    (directory / 'a5-verdict.json').write_text(json.dumps(verdict, indent=2) + '\n', encoding='utf-8')
    (attempt / 'finished.json').write_text(json.dumps(verdict, indent=2) + '\n', encoding='utf-8')
    print('DOWNLOAD_DIR', directory, flush=True)
    raise SystemExit({'accepted': 0, 'rejected': 1}.get(verdict['status'], 3))


if __name__ == '__main__':
    main()
