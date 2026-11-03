"""Offline aggregation of the Stage 4 formal batch (no simulation).

Reads downloaded run directories and, when available, the batch attempt log.
Only held-out seeds from the registered seed list are counted.  Per level and
per execution mode it reports attempts, development-gate passes, rejected
attempts, errors and the rejection rate defined in DAY4_EVALUATION_RECORDING.md:

    rejection rate = (rejected + error) / total attempts
    an empty batch reports an empty rate, never 0 %

A pass here is the script's own development gate (`passed`).  The formal
Stage 4 success definition and its numeric thresholds are frozen separately;
this tool never promotes `passed` to a formal success.

Usage:
    python -I stage4_formal_report.py --seeds stage4-heldout-seeds.json \
        --root results --attempts stage4-formal-batch-formal-v1/attempts.jsonl \
        --out results/STAGE4_FORMAL_BATCH_20261102/report.json
"""

import argparse
import json
import sys
import hashlib
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage4_batch_preflight import journal

PREFIX = {'flat': 'day4-l1-xfold-yaw-aware-',
          'perturbed': 'day4-recovery-fold-',
          'crumpled': 'day4-recovery-fold-'}


def load_seeds(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return {(row['level'], row['seed']) for row in data['heldout']}


def scan(roots, held):
    rows, skipped = [], []
    seen = {}
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            skipped.append({'dir': str(root), 'reason': 'root_missing'})
            continue
        for prefix in sorted(set(PREFIX.values())):
            for path in sorted(root.glob(prefix + '*')):
                result_file = path / 'result.json'
                if not path.is_dir() or not result_file.exists():
                    continue
                try:
                    result = json.loads(result_file.read_text(encoding='utf-8'))
                except (ValueError, UnicodeError) as exc:
                    skipped.append({'dir': path.name, 'reason': 'invalid_result_json', 'error': str(exc)})
                    continue  # corresponding logged attempt is still an error
                case = result.get('initial_case') or {}
                key = (case.get('level'), case.get('seed'))
                if key not in held:
                    continue
                metrics = result.get('fold_metrics') or {}
                row = {
                    'level': key[0],
                    'seed': key[1],
                    'execution': result.get('execution_mode'),
                    'dir': path.name,
                    'passed': result.get('passed') is True,
                    'formal_success': False,
                    'formal_status': 'not_evaluated_by_frozen_formal_audit',
                    'legacy_formal_claim': bool(result.get('formal_day4_success')
                                              or result.get('fold_success_accepted')),
                    'result_sha256': hashlib.sha256(result_file.read_bytes()).hexdigest(),
                    'fold_edge': result.get('fold_edge'),
                    'action_count': result.get('action_count'),
                    'crossed': metrics.get('moving_half_crossed_fraction',
                                           metrics.get('crossed_fraction')),
                    'frozen_code': False,
                    'code_identity_recorded': bool(result.get('code_files')),
                    'errors': result.get('errors') or [],
                    'outcome': ('passed' if result.get('passed') is True else
                                'rejected' if result.get('passed') is False else 'error'),
                }
                # One timestamped result directory is one attempt, even if copied
                # into several supplied roots or a root is supplied twice.
                if path.name in seen:
                    if seen[path.name] != row:
                        raise ValueError('conflicting copies of result: ' + path.name)
                    continue
                seen[path.name] = row
                rows.append(row)
    return rows, skipped


def summarize(rows, level, execution):
    subset = [r for r in rows if r['level'] == level
              and (execution is None or r['execution'] == execution)]
    return summarize_rows(subset, level, execution)


def summarize_rows(subset, level, execution):
    attempts = len(subset)
    passed = sum(r['outcome'] == 'passed' for r in subset)
    rejected = sum(r['outcome'] == 'rejected' for r in subset)
    error = sum(r['outcome'] == 'error' for r in subset)
    assert passed + rejected + error == attempts
    counts = Counter((r['level'], r['seed'], r['execution']) for r in subset)
    empty = attempts == 0
    return {
        'level': level,
        'execution': execution or 'both',
        'attempts': attempts,
        'passed': passed,
        'development_passed': passed,
        'rejected': rejected,
        'error': error,
        'rejection_rate': None if empty else (rejected + error) / attempts,
        'seeds': len({r['seed'] for r in subset}),
        'duplicate_attempts': sorted({seed for (_, seed, _), count in counts.items() if count > 1}),
        'non_frozen_code': sorted({r['dir'] for r in subset
                                   if r['dir'] is not None and not r['frozen_code']}),
        'formal_success': sum(1 for r in subset if r['formal_success']),
        'formal_evaluated': 0,
        'formal_success_rate': None,
    }


def reconcile_attempts(rows, attempt_paths, held):
    """Add logged attempts without a downloaded result as explicit error rows.

    Result rows already scanned are never counted a second time from the log.
    Retries with no result remain separate attempts, including the same seed.
    """
    missing, skipped = [], []
    logged = 0
    seen_logs = set()
    by_dir = {r['dir']: r for r in rows}
    for path in attempt_paths:
        path = Path(path).resolve()
        if path in seen_logs:
            continue
        seen_logs.add(path)
        for line_number, rec in enumerate(journal(path), 1):
            key = (rec['level'], rec['seed'])
            if key not in held:
                skipped.append({'log': str(path), 'line': line_number, 'reason': 'attempt_not_heldout'})
                continue
            if rec['execution'] not in ('single', 'arc4'):
                raise ValueError('invalid logged execution: ' + str(rec['execution']))
            logged += 1
            name = Path(rec['result_dir']).name if rec.get('result_dir') else None
            if name in by_dir:
                result = by_dir[name]
                if (result['level'], result['seed'], result['execution']) != (*key, rec['execution']):
                    raise ValueError('attempt/result identity mismatch: ' + name)
                if rec.get('result_sha256') and rec['result_sha256'] != result['result_sha256']:
                    raise ValueError('logged result hash mismatch: ' + name)
                if rec.get('exit_code') not in (None, 0) and result['passed']:
                    result['outcome'] = 'error'
                    result['passed'] = False
                    result['errors'].append('runner failed despite result passed=true')
                continue
            missing.append(rec)
            rows.append({'level': key[0], 'seed': key[1], 'execution': rec['execution'],
                         'dir': None, 'expected_result_dir': rec.get('result_dir'),
                         'passed': False, 'formal_success': False, 'fold_edge': None,
                         'action_count': None, 'crossed': None, 'frozen_code': None,
                         'outcome': 'error', 'errors': ['logged attempt has no downloaded result'],
                         'exit_code': rec.get('exit_code'), 'attempt_log': str(path),
                         'attempt_line': line_number})
    return missing, skipped, logged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', required=True)
    ap.add_argument('--root', action='append', required=True)
    ap.add_argument('--attempts', action='append', default=[])
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    held = load_seeds(args.seeds)
    rows, skipped = scan([Path(r) for r in args.root], held)

    # Attempts recorded by the batch driver but with no downloaded result are
    # errors in the denominator, not silently absent.
    missing, skipped_attempts, logged = reconcile_attempts(rows, args.attempts, held)
    skipped.extend(skipped_attempts)

    table = []
    for level in ('flat', 'perturbed', 'crumpled'):
        for execution in ('single', 'arc4', None):
            table.append(summarize(rows, level, execution))
    tasks = {
        'A_l1': summarize(rows, 'flat', None),
        'B_l2l3': summarize_rows([r for r in rows if r['level'] in ('perturbed', 'crumpled')],
                                'l2l3', None),
    }
    tasks['B_l2l3']['split'] = {
        level: summarize(rows, level, None) for level in ('perturbed', 'crumpled')}

    print(f'{"level":10s} {"mode":8s} {"att":>4s} {"pass":>5s} {"rej":>4s} {"err":>4s} '
          f'{"rate":>6s} {"seeds":>6s}')
    for row in table:
        rate = 'empty' if row['rejection_rate'] is None else f"{row['rejection_rate']:.3f}"
        print(f"{row['level']:10s} {row['execution']:8s} {row['attempts']:4d} "
              f"{row['passed']:5d} {row['rejected']:4d} {row['error']:4d} {rate:>6s} {row['seeds']:6d}")
    print('\ntasks:')
    for name, row in tasks.items():
        rate = 'empty' if row.get('rejection_rate') is None else f"{row['rejection_rate']:.3f}"
        print(f"  {name}: attempts {row['attempts']} passed {row['passed']} "
              f"error {row['error']} rate {rate} seeds {row['seeds']}")
    print(f'\nlogged attempts {logged}; missing results {len(missing)}')
    if missing:
        print('  missing:', [f"{m['level']}/{m['seed']}/{m['execution']}"
                             for m in missing])
    if skipped:
        print('skipped:', skipped)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    observed = {(r['level'], r['seed'], r['execution']) for r in rows}
    not_attempted = [{'level': level, 'seed': seed, 'execution': mode}
                     for level, seed in sorted(held) for mode in ('single', 'arc4')
                     if (level, seed, mode) not in observed]
    payload = {'rows': rows, 'summary': table, 'tasks': tasks,
               'missing': missing, 'skipped': skipped, 'logged_attempts': logged,
               'planned_attempts': len(held) * 2, 'not_attempted': not_attempted,
               'formal_status': 'pending_independent_frozen_evaluator_audit',
               'denominator_complete': bool(args.attempts) and not skipped}
    with out.open('x', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print('wrote', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
