#!/usr/bin/env python3
"""Offline diagnostic assessor for a5-rc2-d2c-release-order runs.

Never upgrades a diagnostic run to formal Stage 4 success.  It checks the
diagnostic manifest/source identity, the original B v1 evidence/quality, and
the presence of the release-window recording.  The main purpose is to make the
diagnostic trajectory auditable, not to change the RC2 verdict.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from audit_episode_evidence import audit
from stage4_success_v1 import evaluate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('directory', type=Path)
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    d = args.directory.resolve()
    manifest_path = Path(__file__).with_name('a5-rc2-d2c-release-order-files.json')
    manifest = read(manifest_path)
    manifest_sha = sha(manifest_path)
    result = read(d / 'result.json')
    checks = {}
    checks['manifest_self_check'] = sha(__file__) == manifest.get(Path(__file__).name)
    checks['result_code_files'] = result.get('code_files') == manifest
    checks['result_probe_version'] = result.get('probe_version') == 'a5-rc2-d2c-release-order'
    checks['action_count_12'] = result.get('action_count') == 12
    checks['call_horizons_12'] = sum(result.get('call_horizons') or []) == 12
    checks['fold_edge_right'] = result.get('fold_edge') == 'right'
    checks['execution_single'] = result.get('execution_mode') == 'single'
    diag = result.get('diagnostic') or {}
    delay = result.get('internal_delay') or {}
    checks['diagnostic_only'] = bool(diag.get('diagnostic_only'))
    checks['diagnostic_manifest'] = bool(
        diag.get('diagnostic_manifest_sha256') == manifest_sha)
    checks['internal_delay_registered'] = bool(
        delay.get('requested_steps') == 120 and delay.get('elapsed_steps') == 120
        and delay.get('start_step') is not None and delay.get('end_step') is not None
        and delay['end_step'] - delay['start_step'] == 120)
    checks['internal_delay_public_action'] = delay.get('public_action_index') == 12
    checks['internal_delay_no_control'] = bool(
        delay.get('control_calls') == 0 and delay.get('target_changes') == 0)
    checks['internal_delay_no_cloth_reset'] = bool(
        delay.get('cloth_position_reset') is False
        and delay.get('cloth_velocity_reset') is False)
    checks['public_actions_unchanged'] = diag.get('public_actions_unchanged') is True
    checks['action_targets_unchanged'] = diag.get('action_targets_unchanged') is True
    checks['physics_step_count_changed'] = diag.get('physics_step_count_changed') is True
    last_target = (result.get('actions') or [{}])[-1].get('target_pose')
    delay_target = (np.asarray(delay.get('public_action_target'), dtype=float).reshape(-1)
                    if delay.get('public_action_target') is not None else None)
    last_target_arr = (np.asarray(last_target, dtype=float).reshape(-1)
                       if last_target is not None else None)
    checks['internal_delay_public_target'] = bool(
        delay_target is not None and last_target_arr is not None
        and delay_target.size >= 3 and last_target_arr.size >= 3
        and np.allclose(delay_target[:3], last_target_arr[:3], atol=1e-6, rtol=0))
    ro = result.get('release_order') or {}
    checks['release_order_present'] = bool(ro)
    checks['release_order_intervention'] = bool(
        ro.get('intervention') == 'open_while_attached_then_disable')
    checks['release_order_preopen_10'] = bool(
        ro.get('preopen_steps') == 10
        and ro.get('preopen_end_step', 0) - ro.get('preopen_start_step', 0) == 10)
    checks['release_order_preopen_state_checks'] = bool(
        ro.get('preopen_state_checks') == 10)
    checks['release_order_boundary_recorded'] = bool(
        ro.get('preopen_last_state_observed_step') is not None
        and ro.get('release_boundary_observed_step') is not None
        and ro.get('released_sample_observed_step') is not None
        and ro.get('release_boundary_sample_step_delta') is not None
        and ro.get('first_wait_state_observed_step') is not None)
    checks['release_order_boundary_internal'] = bool(
        checks['release_order_boundary_recorded']
        and ro.get('preopen_last_state_observed_step')
            == ro.get('release_boundary_observed_step')
        and ro.get('release_boundary_sample_step_delta')
            == ro.get('released_sample_observed_step')
               - ro.get('release_boundary_observed_step')
        and ro.get('first_wait_state_observed_step')
            == ro.get('released_sample_observed_step') + 1)
    checks['release_order_open_while_attached'] = bool(
        ro.get('attachment_enabled_before') is True
        and ro.get('attachment_enabled_after_preopen') is True
        and ro.get('gripper_aperture_increased') is True)
    checks['release_order_disable_after_open'] = bool(
        ro.get('attachment_enabled_after_ungrasp') is False
        and ro.get('attachment_disabled_step') == ro.get('preopen_end_step'))
    checks['release_order_second_open_suppressed'] = bool(
        ro.get('suppressed_second_open') is True)

    meta_path = d / 'success_meta.json'
    trace_path = d / 'success_trace.npz'
    quality = {'status': 'incomplete', 'success': None, 'checks': {},
               'reason': 'missing success_trace/meta'}
    evidence = {'evidence_complete': False, 'checks': {}}
    if meta_path.is_file() and trace_path.is_file():
        meta = read(meta_path)
        checks['meta_manifest'] = meta.get('manifest_sha256') == manifest_sha
        checks['meta_dt'] = abs(float(meta.get('dt_s', -1)) - 1 / 60) <= 1e-12
        with np.load(trace_path, allow_pickle=False) as z:
            data = {k: z[k] for k in z.files}
        try:
            quality = evaluate(meta, data)
        except Exception as exc:
            quality = {'status': 'incomplete', 'success': None,
                       'error': repr(exc), 'checks': {}}
        checks['success_trace_331'] = len(data.get('vertices', [])) == 331
        checks['release_observed'] = bool(
            not np.any(data['holding']) and not np.any(data['attachment_enabled'])
            and np.all(data['gripper_open']))
        try:
            evidence = audit(d / 'evidence')
        except Exception as exc:
            evidence = {'evidence_complete': False, 'error': repr(exc), 'checks': {}}
    else:
        checks['meta_manifest'] = False
        checks['meta_dt'] = False
        checks['success_trace_331'] = False
        checks['release_observed'] = False

    rd_npz = d / 'evidence' / 'release_diag.npz'
    rd_json = d / 'evidence' / 'release_diag.json'
    release = {'present': rd_npz.is_file() and rd_json.is_file()}
    if release['present']:
        doc = read(rd_json)
        with np.load(rd_npz, allow_pickle=False) as z:
            state = np.asarray(z['sample_label']) == ''
            times = np.asarray(z['sim_time_s'], dtype=float)[state]
            steps = np.asarray(z['observed_step'], dtype=int)[state]
            phases = np.asarray(z['phase'])
            release.update({
                'count': int(len(z['vertices'])),
                'vertices_shape': list(z['vertices'].shape),
                'ee_shape': list(z['ee_m'].shape),
                'joint_shape': list(z['joint_positions'].shape),
                'joint_count': int(z['joint_positions'].shape[1]),
                'aperture_finite': int(np.isfinite(z['gripper_aperture_m']).sum()),
                'ee_distance_finite': int(np.isfinite(z['ee_min_vertex_distance_mm']).sum()),
                'finger_distance_finite': int(np.isfinite(z['finger_min_vertex_distance_mm']).sum()),
                'sample_labels': [str(x) for x in z['sample_label'] if str(x)],
                'state_rows': int(state.sum()),
                'state_dt_ok': bool(len(times) > 1 and np.allclose(
                    np.diff(times), 1 / 60, atol=1e-6, rtol=0)),
                'state_step_ok': bool(len(steps) > 1 and np.array_equal(
                    np.diff(steps), np.ones(len(steps) - 1, dtype=int))),
                'phase_delay_rows': int(np.sum(phases == 'delay')),
                'phase_retreat_rows': int(np.sum(phases == 'retreat')),
                'physics_mode': (doc.get('physics_control_actions') or {}).get('mode'),
                'contact_channel': doc.get('contact_channel'),
                'distance_evidence': doc.get('distance_evidence'),
                'action_begin_targets': (doc.get('action_begin') or {}).get('targets'),
                'action_begin_commands': (doc.get('action_begin') or {}).get('commands'),
            })
        events = doc.get('events') or []
        event_names = [e.get('event') for e in events]
        event_steps = {e.get('event'): int(e.get('observed_step', -1))
                       for e in events}
        required = ['ungrasp_return', 'delay_begin', 'delay_end',
                    'retreat_begin', 'retreat_end']
        release.update({
            'event_count': len(events),
            'event_names': event_names,
            'events_complete': doc.get('events_complete') is True,
        })
        checks['release_diag_present'] = True
        checks['release_diag_vertices_441'] = release['vertices_shape'][1:] == [441, 3]
        checks['release_diag_events'] = event_names == required
        checks['release_diag_events_complete'] = doc.get('events_complete') is True
        checks['release_diag_event_steps'] = bool(
            all(name in event_steps for name in required)
            and event_steps['delay_end'] - event_steps['delay_begin'] == 120
            and event_steps['ungrasp_return'] <= event_steps['delay_begin']
            and event_steps['retreat_begin'] >= event_steps['delay_end']
            and event_steps['retreat_end'] >= event_steps['retreat_begin'])
        checks['release_diag_event_phases'] = bool(
            release['phase_delay_rows'] == 120
            and release['phase_retreat_rows'] > 0)
        checks['release_diag_samples'] = bool(
            'released' in release['sample_labels'] and 'retreated' in release['sample_labels'])
        checks['release_diag_state_dt'] = release['state_dt_ok']
        checks['release_diag_state_steps'] = release['state_step_ok']
        checks['release_diag_joint_positions'] = release['joint_count'] >= 9
        checks['release_diag_aperture_derivable'] = release['joint_count'] >= 9
        checks['release_diag_passive'] = release['physics_mode'] == 'passive post-step reads only'
        last_target = (result.get('actions') or [{}])[-1].get('target_pose')
        # release_diag records the execute() float32 target; result.json stores
        # the float64 target built by the same action call.  Compare at float32.
        target32 = (np.asarray(release['action_begin_targets'][0], dtype=np.float32)
                    if release['action_begin_targets'] else None)
        last32 = (np.asarray(last_target, dtype=np.float32)
                  if last_target is not None else None)
        checks['release_diag_action_target'] = bool(
            target32 is not None and last32 is not None
            and target32.shape == last32.shape
            and np.array_equal(target32, last32))
        checks['release_diag_action_open'] = release['action_begin_commands'] == [0]
    else:
        checks['release_diag_present'] = False
        checks['release_diag_vertices_441'] = False
        checks['release_diag_samples'] = False
        checks['release_diag_state_dt'] = False
        checks['release_diag_state_steps'] = False
        checks['release_diag_joint_positions'] = False
        checks['release_diag_aperture_derivable'] = False
        checks['release_diag_passive'] = False
        checks['release_diag_action_target'] = False
        checks['release_diag_action_open'] = False
        checks['release_diag_events'] = False
        checks['release_diag_events_complete'] = False
        checks['release_diag_event_steps'] = False
        checks['release_diag_event_phases'] = False

    contact_path = d / 'contact_report.json'
    contact = {'present': contact_path.is_file()}
    if contact['present']:
        contact_doc = read(contact_path)
        contact.update({
            'scope': contact_doc.get('scope'),
            'subscription_created': contact_doc.get('subscription_created'),
            'callback_count': contact_doc.get('callback_count'),
            'event_count': contact_doc.get('event_count'),
            'diagnosis': contact_doc.get('diagnosis'),
            'errors': contact_doc.get('errors'),
        })
    checks['contact_report_present'] = contact['present']
    checks['contact_is_not_distance_claim'] = True

    complete = (checks['release_diag_present'] and checks['release_diag_vertices_441']
                and checks['release_diag_samples'] and checks['release_diag_state_dt']
                and checks['release_diag_state_steps']
                and checks['release_diag_joint_positions']
                and checks['release_diag_passive']
                and checks['release_diag_events']
                and checks['release_diag_events_complete']
                and checks['release_diag_event_steps']
                and checks['release_diag_event_phases']
                and checks['diagnostic_only']
                and checks['internal_delay_registered']
                and checks['internal_delay_public_action']
                and checks['internal_delay_no_control']
                and checks['internal_delay_no_cloth_reset']
                and checks['internal_delay_public_target']
                and checks['release_order_present']
                and checks['release_order_intervention']
                and checks['release_order_preopen_10']
                and checks['release_order_preopen_state_checks']
                and checks['release_order_boundary_recorded']
                and checks['release_order_boundary_internal']
                and checks['release_order_open_while_attached']
                and checks['release_order_disable_after_open']
                and checks['release_order_second_open_suppressed']
                and checks['public_actions_unchanged']
                and checks['action_targets_unchanged']
                and checks['physics_step_count_changed']
                and quality.get('status') in ('accepted', 'rejected')
                and bool(evidence.get('evidence_complete')))
    out = {
        'protocol': 'stage4-a5-rc2-d2c-release-order',
        'directory': str(d),
        'manifest_sha256': manifest_sha,
        'diagnostic_only': True,
        'formal_stage4_success': False,
        'complete_diagnostic': bool(complete),
        'checks': checks,
        'quality': quality,
        'evidence': evidence,
        'release_diag': release,
        'internal_delay': delay,
        'release_order': ro,
        'contact_report': contact,
        'notes': [
            'The original B v1 evaluation is reported for comparison only.',
            'Contact is the available robot-rigid contact channel; zero events are '
            'not evidence of no contact.',
            'EE/finger distances are geometric evidence, not contact records.',
            'No formal Stage 4 success is claimed or implied.'
        ]
    }
    out_path = args.output or (d / 'diag-verdict.json')
    out_path.write_text(json.dumps(out, indent=2, allow_nan=False) + '\n')
    print('DIAG_ASSESS', 'complete=' + str(complete),
          'quality=' + str(quality.get('status')),
          'release_rows=' + str(release.get('count')),
          'contact_events=' + str(contact.get('event_count')))
    print('DIAG_VERDICT', out_path)
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
