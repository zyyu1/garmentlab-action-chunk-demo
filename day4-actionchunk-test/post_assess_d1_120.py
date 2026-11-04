#!/usr/bin/env python3
"""Post-run audit for the D1-120 result, fixing only the assessor's target-shape bug.

The executed app/manifest are left untouched.  The standard assessor compared a
3-D delay target with the 4-D public action target and crashed before writing a
verdict.  This script reuses the same quality/evidence functions, compares the
delay target's XYZ with the public target's XYZ, and writes a separate postfix
verdict.  It never runs Isaac or changes the episode.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result_dir', type=Path)
    ap.add_argument('--app', type=Path, required=True)
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    d = args.result_dir.resolve()
    app = args.app.resolve()
    sys.path.insert(0, str(app))
    from stage4_success_v1 import evaluate
    from audit_episode_evidence import audit

    manifest_path = app / 'a5-rc2-d1-120-files.json'
    manifest = read(manifest_path)
    manifest_sha = sha(manifest_path)
    result = read(d / 'result.json')
    meta = read(d / 'success_meta.json')
    with np.load(d / 'success_trace.npz', allow_pickle=False) as z:
        trace = {k: z[k] for k in z.files}
    quality = evaluate(meta, trace)
    evidence = audit(d / 'evidence')
    contact = read(d / 'contact_report.json')
    release = read(d / 'evidence/release_diag.json')
    with np.load(d / 'evidence/release_diag.npz', allow_pickle=False) as z:
        phases = np.asarray(z['phase'])
        sample_labels = [str(x) for x in z['sample_label'] if str(x)]
        state = np.asarray(z['sample_label']) == ''
        times = np.asarray(z['sim_time_s'], dtype=float)[state]
        steps = np.asarray(z['observed_step'], dtype=int)[state]

    delay = result.get('internal_delay') or {}
    diag = result.get('diagnostic') or {}
    events = release.get('events') or []
    event_names = [e.get('event') for e in events]
    event_steps = {e.get('event'): int(e.get('observed_step', -1)) for e in events}
    required = ['ungrasp_return', 'delay_begin', 'delay_end',
                'retreat_begin', 'retreat_end']
    last_target = np.asarray((result.get('actions') or [{}])[-1].get('target_pose'),
                             dtype=float).reshape(-1)
    delay_target = np.asarray(delay.get('public_action_target'), dtype=float).reshape(-1)
    action_begin = (release.get('action_begin') or {})
    action_begin_targets = action_begin.get('targets') or []

    checks = {
        'manifest_self_check': sha(app / 'a5_diag_assess.py')
        == manifest.get('a5_diag_assess.py'),
        'result_code_files': result.get('code_files') == manifest,
        'result_probe_version': result.get('probe_version') == 'a5-rc2-d1-120',
        'diagnostic_manifest': diag.get('diagnostic_manifest_sha256') == manifest_sha,
        'action_count_12': result.get('action_count') == 12,
        'call_horizons_12': sum(result.get('call_horizons') or []) == 12,
        'last_action_release_retreat': (result.get('action_labels') or [])[-1:]
        == ['release_retreat'],
        'diagnostic_only': diag.get('diagnostic_only') is True,
        'public_actions_unchanged': diag.get('public_actions_unchanged') is True,
        'action_targets_unchanged': diag.get('action_targets_unchanged') is True,
        'physics_step_count_changed': diag.get('physics_step_count_changed') is True,
        'internal_delay_registered': delay.get('requested_steps') == 120
        and delay.get('elapsed_steps') == 120
        and delay.get('end_step', 0) - delay.get('start_step', 0) == 120,
        'internal_delay_public_action': delay.get('public_action_index') == 12,
        'internal_delay_no_control': delay.get('control_calls') == 0
        and delay.get('target_changes') == 0,
        'internal_delay_no_cloth_reset': delay.get('cloth_position_reset') is False
        and delay.get('cloth_velocity_reset') is False,
        'internal_delay_public_target_xyz': delay_target.size >= 3
        and last_target.size >= 3
        and np.allclose(delay_target[:3], last_target[:3], atol=1e-6, rtol=0),
        'release_diag_present': True,
        'release_diag_samples': 'released' in sample_labels
        and 'retreated' in sample_labels,
        'release_diag_state_dt': bool(len(times) > 1 and np.allclose(
            np.diff(times), 1 / 60, atol=1e-6, rtol=0)),
        'release_diag_state_steps': bool(len(steps) > 1 and np.array_equal(
            np.diff(steps), np.ones(len(steps) - 1, dtype=int))),
        'release_diag_events': event_names == required,
        'release_diag_events_complete': release.get('events_complete') is True,
        'release_diag_event_steps': all(n in event_steps for n in required)
        and event_steps['delay_end'] - event_steps['delay_begin'] == 120
        and event_steps['ungrasp_return'] <= event_steps['delay_begin']
        and event_steps['retreat_begin'] >= event_steps['delay_end']
        and event_steps['retreat_end'] >= event_steps['retreat_begin'],
        'release_diag_event_phases': int(np.sum(phases == 'delay')) == 120
        and int(np.sum(phases == 'retreat')) > 0,
        'release_diag_action_target': bool(action_begin_targets)
        and np.array_equal(np.asarray(action_begin_targets[0], dtype=np.float32),
                           np.asarray(last_target, dtype=np.float32)),
        'release_diag_action_open': action_begin.get('commands') == [0],
        'meta_manifest': meta.get('manifest_sha256') == manifest_sha,
        'meta_dt': abs(float(meta.get('dt_s', -1)) - 1 / 60) <= 1e-12,
        'success_trace_331': len(trace.get('vertices', [])) == 331,
        'release_observed': bool(not np.any(trace['holding'])
                                 and not np.any(trace['attachment_enabled'])
                                 and np.all(trace['gripper_open'])),
        'contact_report_present': True,
        'contact_is_not_distance_claim': True,
    }
    checks = {k: bool(v) for k, v in checks.items()}
    complete = (all(checks.values())
                and quality.get('status') in ('accepted', 'rejected')
                and bool(evidence.get('evidence_complete')))
    out = {
        'protocol': 'stage4-a5-rc2-d1-120-postfix',
        'assessment_kind': 'post_run_audit_fix',
        'directory': str(d),
        'manifest_sha256': manifest_sha,
        'app': str(app),
        'postfix_note': 'The executed standard assessor compared a 3-D delay '
                        'target with the 4-D public action target and crashed. '
                        'This audit compares XYZ and leaves the executed app/manifest unchanged.',
        'complete_diagnostic': bool(complete),
        'checks': checks,
        'quality': quality,
        'evidence': evidence,
        'internal_delay': delay,
        'release_diag': {
            'count': int(len(phases)),
            'events': event_names,
            'event_steps': event_steps,
            'phase_counts': {str(k): int(v) for k, v in
                             zip(*np.unique(phases, return_counts=True))},
            'sample_labels': sample_labels,
            'action_begin_targets': action_begin_targets,
        },
        'contact_report': contact,
        'formal_stage4_success': False,
    }
    out_path = args.output or (d / 'diag-verdict-postfix.json')
    out_path.write_text(json.dumps(out, indent=2, allow_nan=False) + '\n',
                        encoding='utf-8')
    print('D1_POSTFIX complete=%s quality=%s checks=%d failed=%s' % (
        complete, quality.get('status'), len(checks),
        [k for k, v in checks.items() if not v]))
    print('D1_POSTFIX_VERDICT', out_path)
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
