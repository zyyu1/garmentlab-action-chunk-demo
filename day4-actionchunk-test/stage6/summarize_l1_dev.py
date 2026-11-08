"""Summarize the fixed L1 development evaluation (learned + random)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

STAGE5 = Path('/root/autodl-tmp/stage5-trial')
EVAL = Path('/root/autodl-tmp/stage6_runs/evals/l1_dev_budget500_20261108')
MANIFEST = EVAL / 'manifest.json'
ATTEMPTS = Path('/root/autodl-tmp/stage6_runs/attempts')
PICKS = {'left_210': 210, 'right_230': 230, 'hem_10': 10}
THRESHOLD = 0.03


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:
        return None


def newest_finished(pattern):
    matches = sorted(ATTEMPTS.glob(pattern))
    for path in reversed(matches):
        finished = path / 'finished.json'
        if finished.is_file():
            return path, load(finished)
    return None, None


def close_info(result_dir, result):
    path = result_dir / 'bc_observations.npz'
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=True) as z:
        commands = z['action_command'].tolist() if 'action_command' in z.files else []
        if not commands:
            return None
        close_rows = [i for i, command in enumerate(commands) if int(command) == 1]
        if not close_rows:
            return None
        row = close_rows[-1]
        target = np.asarray(z['prediction_xyz'][row], dtype=float)
        vertices = np.asarray(z['vertices'][row], dtype=float)
        distances = {
            name: float(np.linalg.norm(vertices[index] - target))
            for name, index in PICKS.items()
        }
        nearest = min(distances.items(), key=lambda item: item[1])
        return {
            'observation_index': row,
            'target_xyz': target.tolist(),
            'nearest_region': nearest[0],
            'nearest_distance_m': nearest[1],
            'max_distance_m': THRESHOLD,
            'within_max_distance': bool(nearest[1] < THRESHOLD),
            'grasp_success': bool(any(
                action.get('holding') is True
                for action in (result.get('actions') or []))),
            'distances': distances,
        }


def first_failure(result, result_dir):
    observations = result_dir / 'bc_observations.npz'
    executed = int(result.get('action_count') or 0)
    if observations.is_file():
        with np.load(observations, allow_pickle=True) as z:
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
    errors = result.get('errors') or []
    text = ' '.join(str(item) for item in errors)
    if status == 'accepted':
        return 'success'
    if 'outside unused prepared regions' in text:
        return 'prepared_region_reject'
    if 'timed out' in text or 'did not reach' in text:
        return 'waypoint_timeout'
    if len(result.get('actions') or []) >= 7 and not result.get('terminal_release'):
        return 'budget_exhausted'
    if status == 'rejected':
        return 'physical_rejected'
    if not result.get('terminal_release'):
        return 'no_terminal'
    return status or 'unknown'


def summarize_record(seed, policy, result_dir, attempt_dir):
    result = load(result_dir / 'result.json')
    verdict = load(result_dir / 'bc-verdict.json')
    if result is None:
        raise SystemExit('missing result for %s %s at %s' % (seed, policy, result_dir))
    status = (verdict or {}).get('status') or result.get('status')
    success = bool((verdict or {}).get('success') is True and status == 'accepted')
    video = result_dir / 'evidence' / 'episode.mp4'
    success_meta_path = result_dir / 'success_meta.json'
    adapter = (verdict or {}).get('adapter') or {}
    if success_meta_path.is_file() or adapter.get('physics') is not None:
        physical = {
            'success_meta': load(success_meta_path) if success_meta_path.is_file() else None,
            'adapter_status': adapter.get('status'),
            'adapter_physics': adapter.get('physics'),
            'adapter_stability': adapter.get('stability'),
            'failed_geometry_frames_count': len(
                adapter.get('failed_geometry_frames') or []),
        }
    else:
        physical = 'unavailable (no complete 331-frame evaluation window)'
    return {
        'seed': seed,
        'policy': policy,
        'attempt_dir': str(attempt_dir),
        'result_dir': str(result_dir),
        'status': status,
        'success': success,
        'action_count': result.get('action_count'),
        'errors': result.get('errors') or [],
        'failure_class': classify(result, verdict),
        'first_failure_action': first_failure(result, result_dir),
        'close': close_info(result_dir, result),
        'terminal_release': result.get('terminal_release'),
        'waiting_window': {
            'success_trace': (result_dir / 'success_trace.npz').is_file(),
            'success_meta': (result_dir / 'success_meta.json').is_file(),
            'partial_trace': (result_dir / 'partial_trace.npz').is_file(),
            'final_npz': (result_dir / 'final.npz').is_file(),
        },
        'bc_verdict': verdict,
        'evidence_checks': result.get('evidence_checks'),
        'physical_metrics': physical,
        'video': None if not video.is_file() else {
            'path': str(video),
            'sha256': sha(video),
            'bytes': video.stat().st_size,
        },
        'artifact_hashes': {
            name: sha(result_dir / name)
            for name in ('result.json', 'bc-verdict.json', 'failure.json',
                         'partial_trace.npz', 'bc_observations.npz')
            if (result_dir / name).is_file()
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--out', type=Path, default=EVAL)
    args = parser.parse_args()
    manifest = load(args.manifest)
    cases = manifest['cases']
    records = []
    for case in cases:
        seed = int(case['seed'])
        if seed == 6120:
            learned_attempt = Path('/root/autodl-tmp/stage6_runs/attempts/'
                                   '6120-recheck-budget500-20261108-190259')
            learned_dir = Path(manifest['existing_learned_6120']['result_dir'])
        else:
            learned_attempt, learned_finished = newest_finished(
                'l1dev-learned-%d-*' % seed)
            if learned_finished is None:
                raise SystemExit('missing learned result for %d' % seed)
            learned_dir = Path(learned_finished['result_dir'])
        records.append(summarize_record(
            seed, 'learned', learned_dir, learned_attempt))
        random_attempt, random_finished = newest_finished(
            'l1dev-random-%d-*' % seed)
        if random_finished is None:
            raise SystemExit('missing random result for %d' % seed)
        records.append(summarize_record(
            seed, 'random', Path(random_finished['result_dir']), random_attempt))

    learned = [r for r in records if r['policy'] == 'learned']
    random = [r for r in records if r['policy'] == 'random']
    pair_table = []
    for seed in [c['seed'] for c in cases]:
        pair_table.append({
            'seed': seed,
            'learned': next(r for r in learned if r['seed'] == seed),
            'random': next(r for r in random if r['seed'] == seed),
        })
    report = {
        'purpose': 'development_evaluation_l1',
        'not_independent_test': True,
        'manifest': str(args.manifest),
        'model': manifest['model'],
        'random_policy': manifest['random_policy'],
        'learned_success_count': sum(r['success'] for r in learned),
        'learned_total': len(learned),
        'random_success_count': sum(r['success'] for r in random),
        'random_total': len(random),
        'records': records,
        'pair_table': pair_table,
        'class_counts': {
            policy: {
                name: sum(1 for r in records
                          if r['policy'] == policy and r['failure_class'] == name)
                for name in sorted(set(r['failure_class'] for r in records
                                       if r['policy'] == policy))
            }
            for policy in ('learned', 'random')
        },
        'physical_note': ('Physical metrics are reported only for accepted '
                          'episodes with a complete 331-frame evaluation; '
                          'all other rows are unavailable, not zero.'),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'summary.json').write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    lines = ['# L1 development evaluation (not independent test)', '',
             'Learned success: %d/%d; random success: %d/%d' % (
                 report['learned_success_count'], len(learned),
                 report['random_success_count'], len(random)), '',
             '| seed | learned status | learned class | learned first failure | learned close distance | random status | random class | random first failure | random close distance |',
             '|---:|---|---|---|---:|---|---|---|---:|']
    for row in pair_table:
        l, r = row['learned'], row['random']
        def close_text(value):
            if not value:
                return 'n/a'
            return '%.6f' % value['nearest_distance_m']
        def first_text(value):
            if not value:
                return 'n/a'
            return '%s/%s' % (value.get('label'), value.get('command'))
        lines.append('| %d | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            row['seed'], l['status'], l['failure_class'], first_text(
                l['first_failure_action']), close_text(l['close']),
            r['status'], r['failure_class'], first_text(
                r['first_failure_action']), close_text(r['close'])))
    lines += ['', 'Physical metrics: unavailable unless an episode is accepted '
              'with a complete 331-frame evaluation.', '',
              'Development evaluation only; not statistical significance or '
              'Stage 6 automatic acceptance.']
    (args.out / 'summary.md').write_text('\n'.join(lines) + '\n',
                                         encoding='utf-8')
    print('L1_DEV_SUMMARY_OK')
    print(json.dumps({
        'learned_success_count': report['learned_success_count'],
        'learned_total': report['learned_total'],
        'random_success_count': report['random_success_count'],
        'random_total': report['random_total'],
        'pair_table': [
            {'seed': p['seed'],
             'learned': {k: p['learned'][k] for k in
                         ('status', 'failure_class', 'action_count',
                          'first_failure_action', 'close', 'terminal_release',
                          'video')},
             'random': {k: p['random'][k] for k in
                        ('status', 'failure_class', 'action_count',
                         'first_failure_action', 'close', 'terminal_release',
                         'video')}}
            for p in pair_table
        ],
        'class_counts': report['class_counts'],
    }, indent=2))


if __name__ == '__main__':
    main()
