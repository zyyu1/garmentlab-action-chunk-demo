"""Minimal Stage 8 batch driver: one runner call per manifest case.

Writes an incremental raw_results.csv and forward_timings.csv.  It does not
retry, does not choose seeds, and stops on interface/identity/timing errors.
Normal policy failures (accepted/rejected/execution_error/incomplete with a
saved result) are recorded and the batch continues.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import statistics
import subprocess
import time
from pathlib import Path

PY = '/root/autodl-tmp/envs/isaac40/bin/python'
RUNNER = '/root/autodl-tmp/stage5-trial/stage6/a5_bc_single.py'
APP = '/root/autodl-tmp/stage5-trial/app'
REPO = '/root/autodl-tmp/garmentlab-action-chunk-demo'
RESULT_ROOT = '/root/autodl-tmp/stage8_runs/results'

MAIN_FIELDS = [
    'run_id', 'policy', 'level', 'seed', 'status', 'success', 'action_count',
    'budget', 'policy_calls', 'stop_reason', 'result_dir',
    'initial_result_sha256', 'initial_geometry_sha256',
    'checkpoint_sha256', 'stats_sha256', 'forward_count',
    'first_forward_ms', 'forward_median_ms', 'forward_p95_ms',
    'discarded_actions',
    'geometry_available', 'stability_available', 'geometry_note', 'notes',
]
FORWARD_FIELDS = [
    'run_id', 'policy', 'level', 'seed', 'call_index', 'first_call',
    'inference_ms', 'start_action_index', 'execute_k', 'predicted_actions',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def append_csv(path, fields, row):
    exists = Path(path).is_file()
    with Path(path).open('a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        if not exists:
            writer.writeheader()
        writer.writerow(row)
        f.flush()


def p95(values):
    values = sorted(float(v) for v in values)
    if not values:
        return None
    index = min(len(values) - 1, max(0, int(round(0.95 * (len(values) - 1)))))
    return values[index]


def find_result(out_root, label):
    cands = sorted(glob.glob(os.path.join(out_root, label + '-*')))
    return cands[-1] if cands else None


def stop_reason(result):
    if result.get('terminal_release') and result.get('terminal_release', {}).get('terminal_ok'):
        return 'terminal_release'
    verdict_status = result.get('status')
    if verdict_status in ('execution_error', 'incomplete'):
        return verdict_status
    if result.get('errors'):
        return 'error'
    budget = (result.get('budget') or {}).get('used')
    limit = (result.get('budget') or {}).get('level_limit')
    if budget is not None and limit is not None and budget >= limit:
        return 'budget_exhausted'
    return 'stopped'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--out-root', default=RESULT_ROOT)
    parser.add_argument('--attempt-root', default='/root/autodl-tmp/stage8_runs/attempts')
    parser.add_argument('--csv', required=True)
    parser.add_argument('--forward-csv', required=True)
    parser.add_argument('--label-prefix', default='day4-a5-stage8')
    parser.add_argument('--policy-device', choices=('cpu', 'cuda'), default='cuda')
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--max-cases', type=int, default=None)
    parser.add_argument('--resume', action='store_true',
                        help='skip run_ids already present in the main CSV')
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    if not manifest.get('frozen'):
        raise SystemExit('manifest is not frozen')
    cases = list(manifest['cases'])
    if args.max_cases is not None:
        cases = cases[:args.max_cases]
    Path(args.out_root).mkdir(parents=True, exist_ok=True)
    Path(args.attempt_root).mkdir(parents=True, exist_ok=True)
    Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
    Path(args.forward_csv).parent.mkdir(parents=True, exist_ok=True)

    # Pair check: same level/seed must use the same initial file and hashes.
    pairs = {}
    for case in cases:
        key = (case['level'], int(case['seed']))
        pairs.setdefault(key, []).append(case)
        if not Path(case['initial_dir']).is_dir():
            raise SystemExit('missing initial dir: ' + case['initial_dir'])
        if sha(Path(case['initial_dir']) / 'result.json') != case['initial_result_sha256']:
            raise SystemExit('initial result hash mismatch: %r' % (key,))
        if sha(Path(case['initial_dir']) / 'initial_geometry.npz') != case['initial_geometry_sha256']:
            raise SystemExit('initial geometry hash mismatch: %r' % (key,))
    for key, group in pairs.items():
        if len(group) != 2 or {c['policy'] for c in group} != {'single', 'h4'}:
            raise SystemExit('incomplete policy pair for %r' % (key,))
        if group[0]['initial_dir'] != group[1]['initial_dir']:
            raise SystemExit('initial dir mismatch for %r' % (key,))
        if (group[0]['initial_result_sha256'] != group[1]['initial_result_sha256']
                or group[0]['initial_geometry_sha256'] != group[1]['initial_geometry_sha256']):
            raise SystemExit('initial hash mismatch for %r' % (key,))

    completed = set()
    if args.resume and Path(args.csv).is_file():
        with Path(args.csv).open(newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row.get('run_id'):
                    completed.add(row['run_id'])
        cases = [c for c in cases if c['run_id'] not in completed]

    policies = manifest['policies']
    for name, meta in policies.items():
        if sha(meta['checkpoint']) != meta['checkpoint_sha256']:
            raise SystemExit('checkpoint hash mismatch: ' + name)
        if sha(meta['stats']) != meta['stats_sha256']:
            raise SystemExit('stats hash mismatch: ' + name)
    if args.policy_device == 'cuda':
        import torch
        if not torch.cuda.is_available():
            raise SystemExit('CUDA requested but unavailable')
    else:
        import torch
        if torch.cuda.is_available():
            raise SystemExit('cuda available but policy-device cpu requested')

    for index, case in enumerate(cases, 1):
        run_id = case['run_id']
        policy = case['policy']
        meta = policies[policy]
        label = '%s-%s' % (args.label_prefix, run_id)
        existing = find_result(args.out_root, label)
        if existing is not None and not args.resume:
            raise SystemExit('refusing to overwrite existing result ' + existing)
        attempt = Path(args.attempt_root) / ('%s-%s' % (args.label_prefix, run_id))
        if existing is not None:
            result_dir = existing
            log_path = attempt / 'runner.log'
            result_path = Path(result_dir) / 'result.json'
            if not result_path.is_file():
                raise SystemExit('resume result missing result.json: ' + run_id)
            proc = None
            elapsed = None
            log_text = ''
            print('RESUME_EXISTING %s' % run_id, flush=True)
        else:
            if attempt.exists():
                raise SystemExit('refusing to overwrite existing attempt ' + str(attempt))
            attempt.mkdir(parents=True)
            log_path = attempt / 'runner.log'
            cmd = [
                PY, '-u', RUNNER,
                '--initial-dir', case['initial_dir'],
                '--checkpoint', meta['checkpoint'],
                '--stats', meta['stats'],
                '--app-dir', APP,
                '--repo-root', REPO,
                '--out-root', args.out_root,
                '--label', label,
                '--policy', ('bc' if policy == 'single' else policy),
                '--execute-k', str(int(meta.get('execute_k', 1))),
                '--policy-device', args.policy_device,
                '--skip-identity-check',
            ]
            started = time.time()
            with log_path.open('w', encoding='utf-8') as log:
                proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                                      timeout=args.timeout)
            elapsed = time.time() - started
            log_text = log_path.read_text(errors='replace')
            dirs = [s[12:].strip() for s in log_text.splitlines()
                    if s.startswith('DOWNLOAD_DIR ')]
            result_dir = dirs[-1] if dirs else find_result(args.out_root, label)
            result_path = Path(result_dir) / 'result.json' if result_dir else None
        if not result_path or not result_path.is_file():
            proc_code = -1 if proc is None else proc.returncode
            row = {'run_id': run_id, 'policy': policy, 'level': case['level'],
                   'seed': case['seed'], 'status': 'interface_error',
                   'success': '', 'notes': 'no result.json; process=%s; log=%s'
                   % (proc_code, log_path)}
            append_csv(args.csv, MAIN_FIELDS, row)
            raise SystemExit('interface error: no result for ' + run_id)
        result = load_json(result_path)
        if result.get('policy', {}).get('device') != args.policy_device:
            raise SystemExit('policy device mismatch in result: ' + run_id)
        if policy == 'h4' and int(result.get('policy', {}).get('execute_k', -1)) != 4:
            raise SystemExit('H4 execute_k is not 4: ' + run_id)
        if int(result.get('action_count', 0)) > int(
                (result.get('budget') or {}).get('level_limit', 0)):
            raise SystemExit('action budget exceeded: ' + run_id)
        verdict_path = Path(result_dir) / 'bc-verdict.json'
        verdict = load_json(verdict_path) if verdict_path.is_file() else {}
        calls = result.get('policy_calls') or []
        discarded = sum(len(c.get('discarded') or []) for c in calls)
        timings = []
        for call_index, call in enumerate(calls):
            ms = call.get('inference_ms')
            if ms is None or not isinstance(ms, (int, float)) or ms < 0:
                raise SystemExit('missing/invalid timing: %s call %d'
                                 % (run_id, call_index))
            timings.append(float(ms))
            append_csv(args.forward_csv, FORWARD_FIELDS, {
                'run_id': run_id, 'policy': policy, 'level': case['level'],
                'seed': case['seed'], 'call_index': call_index,
                'first_call': bool(call_index == 0),
                'inference_ms': float(ms),
                'start_action_index': call.get('start_action_index'),
                'execute_k': call.get('execute_k'),
                'predicted_actions': len(call.get('predicted_actions') or []),
            })
        trace = Path(result_dir) / 'success_trace.npz'
        trace_frames = 0
        if trace.is_file():
            import numpy as np
            with np.load(trace, allow_pickle=False) as data:
                if 'steps' in data.files:
                    trace_frames = int(np.asarray(data['steps']).size)
        geometry_available = trace_frames >= 331 and result.get('status') in (
            'accepted', 'rejected')
        stability_available = bool(
            (verdict.get('adapter') or {}).get('stability'))
        row = {
            'run_id': run_id, 'policy': policy, 'level': case['level'],
            'seed': case['seed'], 'status': result.get('status'),
            'success': result.get('success'),
            'action_count': result.get('action_count'),
            'budget': (result.get('budget') or {}).get('level_limit'),
            'policy_calls': len(calls),
            'stop_reason': stop_reason(result),
            'result_dir': result_dir,
            'initial_result_sha256': case['initial_result_sha256'],
            'initial_geometry_sha256': case['initial_geometry_sha256'],
            'checkpoint_sha256': meta['checkpoint_sha256'],
            'stats_sha256': meta['stats_sha256'],
            'forward_count': len(timings),
            'first_forward_ms': timings[0] if timings else None,
            'forward_median_ms': statistics.median(timings) if timings else None,
            'forward_p95_ms': p95(timings),
            'discarded_actions': discarded,
            'geometry_available': bool(geometry_available),
            'stability_available': bool(stability_available),
            'geometry_note': ('complete 331-frame window' if geometry_available
                              else 'unavailable: no complete 331-frame window'),
            'notes': 'process=%s elapsed_s=%s log=%s' % (
                'resumed' if proc is None else proc.returncode,
                'n/a' if elapsed is None else '%.1f' % elapsed, log_path),
        }
        append_csv(args.csv, MAIN_FIELDS, row)
        print('CASE_OK %d/%d %s status=%s actions=%s calls=%s'
              % (index, len(cases), run_id, row['status'], row['action_count'],
                 row['policy_calls']), flush=True)

    print('BATCH_COMPLETE cases=%d' % len(cases), flush=True)


if __name__ == '__main__':
    main()
