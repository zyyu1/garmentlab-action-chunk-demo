"""Check the paired Stage 8 dry-run CSV against the saved raw results."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--forward-csv', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    rows = list(csv.DictReader(Path(args.csv).open(encoding='utf-8')))
    forwards = list(csv.DictReader(Path(args.forward_csv).open(encoding='utf-8')))
    checks = {'rows': len(rows), 'pairs': {}, 'cases': {}, 'forward_rows': len(forwards)}
    if len(rows) != 4:
        raise SystemExit('expected 4 dry-run rows, got %d' % len(rows))
    for row in rows:
        key = (row['level'], int(row['seed']), row['policy'])
        result_dir = Path(row['result_dir'])
        result = json.loads((result_dir / 'result.json').read_text(encoding='utf-8'))
        verdict = json.loads((result_dir / 'bc-verdict.json').read_text(encoding='utf-8'))
        calls = result.get('policy_calls') or []
        if row['status'] != result.get('status'):
            raise SystemExit('status mismatch for %r' % (key,))
        if int(row['action_count']) != int(result.get('action_count')):
            raise SystemExit('action_count mismatch for %r' % (key,))
        if int(row['policy_calls']) != len(calls):
            raise SystemExit('policy_calls mismatch for %r' % (key,))
        if result['policy']['device'] != 'cuda':
            raise SystemExit('not CUDA for %r' % (key,))
        if row['policy'] == 'h4' and int(result['policy']['execute_k']) != 4:
            raise SystemExit('H4 execute_k mismatch for %r' % (key,))
        if any(a.get('target_override') is not False
               for a in result.get('actions', [])):
            raise SystemExit('target override found for %r' % (key,))
        for i, call in enumerate(calls):
            ms = call.get('inference_ms')
            if ms is None or not np.isfinite(float(ms)) or float(ms) < 0:
                raise SystemExit('bad forward timing %r call %d' % (key, i))
        trace = result_dir / 'success_trace.npz'
        partial = result_dir / 'partial_trace.npz'
        trace_frames = 0
        if trace.is_file():
            with np.load(trace, allow_pickle=False) as data:
                trace_frames = int(np.asarray(data['steps']).size) if 'steps' in data.files else 0
        ev = result_dir / 'evidence' / 'episode.mp4'
        checks['cases'][str(key)] = {
            'status': row['status'], 'success': row['success'],
            'action_count': int(row['action_count']),
            'policy_calls': len(calls),
            'execute_k': result['policy'].get('execute_k'),
            'discarded_actions': int(row['discarded_actions']),
            'forward_ms': [float(c['inference_ms']) for c in calls],
            'trace_frames': trace_frames,
            'partial_trace': partial.is_file(),
            'video': ev.is_file(),
            'verdict_status': verdict.get('status'),
            'evidence_readable': (trace_frames >= 331 or partial.is_file()) and ev.is_file(),
        }
    for key in sorted({(r['level'], int(r['seed'])) for r in rows}):
        group = [r for r in rows if (r['level'], int(r['seed'])) == key]
        if {r['policy'] for r in group} != {'single', 'h4'}:
            raise SystemExit('missing pair for %r' % (key,))
        if group[0]['initial_result_sha256'] != group[1]['initial_result_sha256'] or \
                group[0]['initial_geometry_sha256'] != group[1]['initial_geometry_sha256']:
            raise SystemExit('pair initial hash mismatch for %r' % (key,))
        checks['pairs'][str(key)] = {
            'same_initial': True,
            'initial_result_sha256': group[0]['initial_result_sha256'],
            'initial_geometry_sha256': group[0]['initial_geometry_sha256'],
        }
    if len(forwards) != sum(int(r['policy_calls']) for r in rows):
        raise SystemExit('forward CSV row count mismatch')
    first = [r for r in forwards if r['first_call'] == 'True']
    if len(first) != 4:
        raise SystemExit('expected one first-call row per case')
    checks['first_forward_ms'] = {r['run_id']: float(r['inference_ms']) for r in first}
    checks['all_evidence_readable'] = all(
        v['evidence_readable'] for v in checks['cases'].values())
    checks['formal_120_started'] = False
    Path(args.out).write_text(json.dumps(checks, indent=2, ensure_ascii=False) + '\n',
                              encoding='utf-8')
    print('DRYRUN_CHECK_OK')
    print(json.dumps(checks, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
