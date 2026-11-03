"""Offline evidence audit. Does not certify cloth quality or formal success."""
import json
from pathlib import Path
import numpy as np
from episode_evidence import digest


def audit(directory):
    import cv2
    p = Path(directory)
    summary = json.loads((p / 'summary.json').read_text())
    manifest = json.loads((p / 'manifest.json').read_text())
    rows = [json.loads(line) for line in (p / 'timeline.jsonl').read_text().splitlines()]
    checks = {}
    checks['file_hashes'] = all((p / n).is_file() and digest(p / n) == h for n, h in manifest.items())
    checks['source_hashes'] = bool(summary['sources']) and all(
        digest(p / 'source' / n) == v['sha256'] for n, v in summary['sources'].items())
    checks['time_monotonic'] = all(b['monotonic_ns'] >= a['monotonic_ns'] and
        b['sim_time_s'] >= a['sim_time_s'] for a, b in zip(rows, rows[1:]))
    states = [r for r in rows if r['kind'] == 'state']
    checks['continuous_steps'] = [r['observed_step'] for r in states] == list(range(1, summary['observed_steps'] + 1))
    checks['state_consistent'] = bool(states) and all(r['holding'] == r['attached'] for r in states)
    frames = [r for r in rows if r['kind'] == 'frame']
    cap = cv2.VideoCapture(str(p / 'episode.mp4'))
    decoded = 0
    while True:
        ok, image = cap.read()
        if not ok:
            break
        decoded += 1
    cap.release()
    checks['video_decodes'] = decoded == len(frames) == summary['frames'] and decoded > 0
    checks['frame_indices'] = [r['frame_index'] for r in frames] == list(range(decoded))
    begins = [r for r in rows if r['kind'] == 'action_begin']
    ends = [r for r in rows if r['kind'] in ('action_end', 'action_error')]
    checks['actions_complete'] = bool(begins) and len(begins) == len(ends) and all(
        a['call_id'] == b['call_id'] and (b['kind'] == 'action_error' or a['horizon'] == b['executed_steps'])
        for a, b in zip(begins, ends))
    checks['no_capture_errors'] = not summary['errors']
    samples = summary['samples']
    labels = ['released', 'retreated', 'hold_3s', 'hold_4s']
    checks['retention_samples'] = all(k in samples and (p / (k + '.npz')).is_file() for k in labels)
    checks['retention_timing'] = checks['retention_samples'] and (
        samples['hold_3s']['sim_time_s'] - samples['retreated']['sim_time_s'] >= 3. - 1e-6 and
        samples['hold_4s']['sim_time_s'] - samples['hold_3s']['sim_time_s'] >= 1. - 1e-6)
    checks['retention_detached'] = checks['retention_samples'] and all(
        not samples[k]['holding'] and not samples[k]['attached'] for k in labels)
    checks['retreat_moved'] = checks['retention_samples'] and np.linalg.norm(
        np.asarray(samples['retreated']['ee_m']) - samples['released']['ee_m']) >= .01
    checks['retreat_public_action'] = checks['retention_samples'] and any(
        r['kind'] == 'action_end' and samples['released']['monotonic_ns'] <= r['monotonic_ns'] <= samples['retreated']['monotonic_ns']
        for r in rows)
    checks['terminal_saved'] = 'terminal' in samples and (p / 'terminal.npz').is_file()
    checks = {key: bool(value) for key, value in checks.items()}
    count = sum(r['horizon'] for r in begins)
    return dict(checks=checks, evidence_complete=all(checks.values()), decoded_frames=decoded,
                attempted_public_actions=count, action_budget_passed=count <= 12,
                synthetic=summary['synthetic'], formal_day4_success=False,
                note='Evidence completeness is not fold quality acceptance; synthetic examples are never experiments.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    args = parser.parse_args()
    report = audit(args.directory)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['evidence_complete'] else 1)
