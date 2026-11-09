"""Summarize the Stage 8 reduced-30 results (offline; no simulation)."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


def p95(values):
    values = sorted(float(v) for v in values)
    if not values:
        return None
    idx = min(len(values) - 1, max(0, int(round(0.95 * (len(values) - 1)))))
    return values[idx]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    parser.add_argument('--forward-csv', required=True)
    parser.add_argument('--out-json', required=True)
    parser.add_argument('--out-md', required=True)
    args = parser.parse_args()
    rows = list(csv.DictReader(Path(args.csv).open(encoding='utf-8')))
    forwards = list(csv.DictReader(Path(args.forward_csv).open(encoding='utf-8')))
    if len(rows) != 30:
        raise SystemExit('expected 30 rows, got %d' % len(rows))
    pairs = {}
    for row in rows:
        pairs.setdefault((row['level'], int(row['seed'])), {})[row['policy']] = row
    if len(pairs) != 15:
        raise SystemExit('expected 15 pairs, got %d' % len(pairs))
    for key, group in pairs.items():
        if set(group) != {'single', 'h4'}:
            raise SystemExit('missing pair %r' % (key,))
        if group['single']['initial_result_sha256'] != group['h4']['initial_result_sha256']:
            raise SystemExit('initial hash mismatch %r' % (key,))
    levels = ['flat', 'perturbed', 'crumpled']
    summary = {'levels': {}, 'pairs': [], 'failures': [], 'timing': {}, 'geometry': {}}
    for level in levels:
        level_rows = [r for r in rows if r['level'] == level]
        summary['levels'][level] = {
            'single_success': sum(r['success'] == 'True' for r in level_rows
                                  if r['policy'] == 'single'),
            'h4_success': sum(r['success'] == 'True' for r in level_rows
                              if r['policy'] == 'h4'),
            'single_n': sum(r['policy'] == 'single' for r in level_rows),
            'h4_n': sum(r['policy'] == 'h4' for r in level_rows),
        }
    for (level, seed), group in sorted(pairs.items(), key=lambda kv: (
            levels.index(kv[0][0]), kv[0][1])):
        rec = {'level': level, 'seed': seed}
        for policy in ('single', 'h4'):
            row = group[policy]
            rec[policy] = {
                'status': row['status'], 'success': row['success'],
                'action_count': int(row['action_count']),
                'policy_calls': int(row['policy_calls']),
                'stop_reason': row['stop_reason'],
                'geometry_available': row['geometry_available'] == 'True',
                'result_dir': row['result_dir'],
            }
        summary['pairs'].append(rec)
    for row in rows:
        if row['success'] != 'True':
            result_path = Path(row['result_dir']) / 'result.json'
            result = json.loads(result_path.read_text(encoding='utf-8')) if result_path.is_file() else {}
            summary['failures'].append({
                'run_id': row['run_id'], 'level': row['level'],
                'seed': int(row['seed']), 'policy': row['policy'],
                'status': row['status'], 'action_count': int(row['action_count']),
                'stop_reason': row['stop_reason'],
                'errors': result.get('errors') or [],
                'reasons': result.get('reasons') or [],
                'geometry_available': row['geometry_available'] == 'True',
            })
    for policy in ('single', 'h4'):
        subset = [r for r in rows if r['policy'] == policy]
        first = [float(r['first_forward_ms']) for r in subset
                 if r['first_forward_ms'] not in ('', None)]
        calls = [float(v) for r in forwards if r['policy'] == policy
                 for v in [r['inference_ms']]]
        summary['timing'][policy] = {
            'cases': len(subset),
            'forward_calls': len(calls),
            'first_call_mean_ms': statistics.mean(first) if first else None,
            'subsequent_median_ms': statistics.median(
                [float(r['inference_ms']) for r in forwards
                 if r['policy'] == policy and r['first_call'] != 'True']) if calls else None,
            'subsequent_p95_ms': p95(
                [float(r['inference_ms']) for r in forwards
                 if r['policy'] == policy and r['first_call'] != 'True']) if calls else None,
        }
        summary['geometry'][policy] = {
            'available': sum(r['geometry_available'] == 'True' for r in subset),
            'unavailable': sum(r['geometry_available'] != 'True' for r in subset),
        }
    # Representative existing videos: first success/failure per level/policy.
    reps = []
    for level in levels:
        for policy in ('single', 'h4'):
            for wanted in ('True', 'False'):
                hit = next((r for r in rows if r['level'] == level
                            and r['policy'] == policy and r['success'] == wanted), None)
                if hit is None:
                    continue
                video = Path(hit['result_dir']) / 'evidence' / 'episode.mp4'
                reps.append({'level': level, 'policy': policy,
                             'success': hit['success'], 'seed': int(hit['seed']),
                             'video': str(video), 'exists': video.is_file()})
    summary['representative_videos'] = reps
    summary['formal_120_started'] = False
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n',
                                   encoding='utf-8')
    lines = ['# Stage 8 缩减版 30 例汇总', '',
             '| 档 | single success | H4 success |', '|---|---:|---:|']
    for level in levels:
        s = summary['levels'][level]
        lines.append('| %s | %d/%d | %d/%d |' % (
            level, s['single_success'], s['single_n'],
            s['h4_success'], s['h4_n']))
    lines += ['', '## 配对', '',
              '| 档 | seed | single | H4 | action single/H4 |',
              '|---|---:|---|---|---:|']
    for rec in summary['pairs']:
        lines.append('| %s | %d | %s | %s | %d/%d |' % (
            rec['level'], rec['seed'], rec['single']['status'],
            rec['h4']['status'], rec['single']['action_count'],
            rec['h4']['action_count']))
    lines += ['', '## Timing', '',
              '| policy | cases | forward calls | first mean ms | subsequent median ms | subsequent P95 ms |',
              '|---|---:|---:|---:|---:|---:|']
    for policy in ('single', 'h4'):
        t = summary['timing'][policy]
        lines.append('| %s | %d | %d | %.3f | %.3f | %.3f |' % (
            policy, t['cases'], t['forward_calls'],
            t['first_call_mean_ms'], t['subsequent_median_ms'],
            t['subsequent_p95_ms']))
    lines += ['', '小样本描述性统计；不宣称稳定延迟优势。',
              '', '## 失败分类', '']
    for f in summary['failures']:
        err = ('; '.join(f['errors']) if f['errors'] else
               '; '.join(f['reasons']) if f['reasons'] else 'no error text')
        lines.append('- %s %s %s: %s, actions=%d, stop=%s; %s' % (
            f['level'], f['seed'], f['policy'], f['status'],
            f['action_count'], f['stop_reason'], err))
    Path(args.out_md).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('SUMMARY_OK', args.out_json, args.out_md)


if __name__ == '__main__':
    main()
