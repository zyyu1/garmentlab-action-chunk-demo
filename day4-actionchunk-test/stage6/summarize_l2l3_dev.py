"""Summarize L2/L3 development evaluation and merge the L1 summary."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

STAGE5 = Path('/root/autodl-tmp/stage5-trial')
L2L3 = Path('/root/autodl-tmp/stage6_runs/evals/l2l3_dev_budget500_20261108')
ATTEMPTS = Path('/root/autodl-tmp/stage6_runs/attempts')
L1_SUMMARY = Path('/root/autodl-tmp/stage6_runs/evals/l1_dev_budget500_20261108/summary.json')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:
        return None


def newest(pattern):
    for path in sorted(ATTEMPTS.glob(pattern), reverse=True):
        if (path / 'finished.json').is_file():
            return path, load(path / 'finished.json')
    return None, None


def first_failure(result, result_dir):
    obs = result_dir / 'bc_observations.npz'
    executed = int(result.get('action_count') or 0)
    if obs.is_file():
        with np.load(obs, allow_pickle=True) as z:
            labels = z['action_label'].tolist() if 'action_label' in z.files else []
            commands = z['action_command'].tolist() if 'action_command' in z.files else []
            targets = z['prediction_xyz'].tolist() if 'prediction_xyz' in z.files else []
        if executed < len(labels):
            return {
                'prediction_index': executed,
                'label': labels[executed],
                'command': int(commands[executed]),
                'prediction_xyz': targets[executed],
            }
    return None


def classify(result, verdict):
    status = (verdict or {}).get('status') or result.get('status')
    errors = ' '.join(str(x) for x in (result.get('errors') or []))
    if status == 'accepted':
        return 'success'
    if 'Grasp is outside the preselected cloth region' in errors:
        return 'grasp_region_reject'
    if 'outside unused prepared regions' in errors:
        return 'prepared_region_reject'
    if 'timed out' in errors or 'did not reach' in errors:
        return 'waypoint_timeout'
    terminal = result.get('terminal_release')
    if terminal is not None:
        if not terminal.get('held_check_ok'):
            return 'terminal_held_check_failed'
        if not terminal.get('terminal_ok'):
            return 'terminal_rejected'
    if status == 'rejected':
        return 'physical_rejected'
    if len(result.get('actions') or []) >= 12:
        return 'budget_exhausted'
    return status or 'unknown'


def record(case):
    attempt, finished = newest('l2l3dev-learned-%s-%d-*'
                               % (case['level'], case['seed']))
    if finished is None:
        raise SystemExit('missing result for %s/%d'
                         % (case['level'], case['seed']))
    result_dir = Path(finished['result_dir'])
    result = load(result_dir / 'result.json')
    verdict = load(result_dir / 'bc-verdict.json')
    if result is None:
        raise SystemExit('missing result.json for %s/%d'
                         % (case['level'], case['seed']))
    status = (verdict or {}).get('status') or result.get('status')
    adapter = (verdict or {}).get('adapter') or {}
    success_meta = result_dir / 'success_meta.json'
    complete = (adapter.get('physics') is not None
                or success_meta.is_file())
    terminal = result.get('terminal_release')
    video = result_dir / 'evidence' / 'episode.mp4'
    return {
        'level': case['level'],
        'seed': case['seed'],
        'initial_dir': case['initial_dir'],
        'attempt_dir': str(attempt),
        'result_dir': str(result_dir),
        'status': status,
        'success': bool(status == 'accepted'
                        and (verdict or {}).get('success') is True),
        'action_count': result.get('action_count'),
        'errors': result.get('errors') or [],
        'failure_class': classify(result, verdict),
        'first_failure_action': first_failure(result, result_dir),
        'terminal': terminal,
        'terminal_ok': result.get('terminal_ok'),
        'bc_grasps': result.get('bc_grasps'),
        'recovery_count': result.get('recovery_count'),
        'complete_window': bool(complete),
        'physical_metrics': (
            {
                'success_meta': load(success_meta) if success_meta.is_file() else None,
                'adapter_status': adapter.get('status'),
                'adapter_physics': adapter.get('physics'),
                'adapter_stability': adapter.get('stability'),
                'failed_geometry_frames_count': len(
                    adapter.get('failed_geometry_frames') or []),
            } if complete else 'unavailable (no complete 331-frame window)'),
        'video': None if not video.is_file() else {
            'path': str(video), 'sha256': sha(video), 'bytes': video.stat().st_size},
        'artifact_hashes': {
            name: sha(result_dir / name)
            for name in ('result.json', 'bc-verdict.json', 'failure.json',
                         'partial_trace.npz', 'bc_observations.npz')
            if (result_dir / name).is_file()
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=L2L3)
    args = parser.parse_args()
    manifest = load(L2L3 / 'manifest.json')
    records = [record(case) for case in manifest['cases']]
    l2 = [r for r in records if r['level'] == 'perturbed']
    l3 = [r for r in records if r['level'] == 'crumpled']
    l1 = load(L1_SUMMARY)
    if l1 is None:
        raise SystemExit('missing L1 summary')
    l2_success = sum(r['success'] for r in l2)
    l3_success = sum(r['success'] for r in l3)
    report = {
        'purpose': 'development_evaluation_l2_l3',
        'not_independent_test': True,
        'model': manifest['model'],
        'initial_selection': manifest['selection'],
        'budgets': manifest['budgets'],
        'settle_hold_note': manifest['settle_hold_note'],
        'l2_success_count': l2_success,
        'l2_total': len(l2),
        'l3_success_count': l3_success,
        'l3_total': len(l3),
        'records': records,
        'class_counts': {
            level: {
                name: sum(1 for r in records
                          if r['level'] == level
                          and r['failure_class'] == name)
                for name in sorted(set(r['failure_class'] for r in records
                                       if r['level'] == level))
            } for level in ('perturbed', 'crumpled')
        },
        'l1_reference': {
            'learned_success_count': l1['learned_success_count'],
            'learned_total': l1['learned_total'],
            'random_success_count': l1['random_success_count'],
            'random_total': l1['random_total'],
        },
        'combined': {
            'learned_success': l1['learned_success_count'] + l2_success + l3_success,
            'learned_total': 5 + len(l2) + len(l3),
            'random_success': l1['random_success_count'],
            'random_total': l1['random_total'],
        },
        'physical_note': ('Only a complete 331-frame window yields physical '
                          'geometry/stability metrics; all other rows are '
                          'unavailable, not zero.'),
    }
    (args.out / 'summary_l2l3.json').write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    lines = ['# L2/L3 development evaluation (not independent test)', '',
             'L2 learned: %d/%d; L3 learned: %d/%d' % (
                 report['l2_success_count'], len(l2),
                 report['l3_success_count'], len(l3)), '',
             '| level | seed | status | class | action_count | first failure | video |',
             '|---|---:|---|---|---:|---|---|']
    for r in records:
        ff = r['first_failure_action']
        ff_text = 'n/a' if not ff else '%s/%s' % (ff['label'], ff['command'])
        lines.append('| %s | %d | %s | %s | %s | %s | [mp4](%s) |' % (
            r['level'], r['seed'], r['status'], r['failure_class'],
            r['action_count'], ff_text,
            r['video']['path'] if r['video'] else 'n/a'))
    lines += ['', 'Physical metrics: unavailable for every L2/L3 case because '
              'no complete 331-frame window was produced.', '',
              'Development evaluation only; L2/L3 reduced-data results are exploratory.']
    (args.out / 'summary_l2l3.md').write_text('\n'.join(lines) + '\n',
                                               encoding='utf-8')
    combined = {
        'l1': report['l1_reference'],
        'l2': {'success': len([r for r in l2 if r['success']]), 'total': len(l2)},
        'l3': {'success': len([r for r in l3 if r['success']]), 'total': len(l3)},
        'learned_total': report['combined']['learned_success'],
        'random_total': report['combined']['random_success'],
        'note': ('Development evaluation only; not an independent test. '
                 'L2/L3 are exploratory reduced-data results.'),
    }
    (args.out / 'summary_all.json').write_text(
        json.dumps(combined, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print('L2L3_SUMMARY_OK')
    print(json.dumps({
        'l2_success_count': report['l2_success_count'],
        'l2_total': report['l2_total'],
        'l3_success_count': report['l3_success_count'],
        'l3_total': report['l3_total'],
        'class_counts': report['class_counts'],
        'records': [{k: r[k] for k in
                     ('level', 'seed', 'status', 'failure_class',
                      'action_count', 'first_failure_action', 'terminal_ok',
                      'bc_grasps', 'recovery_count', 'complete_window',
                      'video')} for r in records],
        'combined': combined,
    }, indent=2))


if __name__ == '__main__':
    main()
