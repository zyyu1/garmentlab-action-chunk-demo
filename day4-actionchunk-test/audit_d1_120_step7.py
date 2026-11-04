#!/usr/bin/env python3
"""Step-7 audit for the single D1-120 run.

Compares remote/local SHA256, initial identity, action identity, physical clocks,
attachment state, delay events/phases, and the pre-wait trajectory against the
RC2 4202 single and v1.1 release_diag.  Never runs Isaac.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def eq(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape:
        return False
    if a.dtype.kind == 'f' or b.dtype.kind == 'f':
        return bool(np.array_equal(a, b, equal_nan=True))
    return bool(np.array_equal(a, b))


def maxdiff(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.shape != b.shape or a.size == 0:
        return None
    return float(np.max(np.abs(a - b)))


def check(r, name, ok, detail=None):
    r[name] = {'ok': bool(ok), 'detail': detail}
    return bool(ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--d1', type=Path, required=True)
    ap.add_argument('--rc2', type=Path, required=True)
    ap.add_argument('--v11', type=Path, required=True)
    ap.add_argument('--version', type=Path, required=True,
                    help='a5-rc2-d1-120 version directory')
    ap.add_argument('--remote-hashes', type=Path, required=True)
    ap.add_argument('--remote-initial', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    d1, rc2, v11 = args.d1.resolve(), args.rc2.resolve(), args.v11.resolve()
    version = args.version.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    checks = {}
    result = read(d1 / 'result.json')
    meta = read(d1 / 'success_meta.json')
    bresult = read(rc2 / 'result.json')
    bmeta = read(rc2 / 'success_meta.json')
    config = read(version / 'app' / 'a5-rc2-d1-120.json')
    registration = read(version / 'registration.json')
    postfix = read(d1 / 'diag-verdict-postfix.json')
    ledger = read(d1 / 'run_ledger.json')

    # 1. Remote/local file inventory and SHA256.
    remote = {}
    for line in args.remote_hashes.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        h, name = line.split(None, 1)
        remote[name.strip().removeprefix('./')] = h
    local_files = sorted(str(p.relative_to(d1)).replace('\\', '/')
                         for p in d1.rglob('*') if p.is_file())
    check(checks, 'remote_file_count', len(remote) == 97, len(remote))
    check(checks, 'local_file_set_matches_remote',
          set(local_files) == set(remote),
          {'missing_local': sorted(set(remote) - set(local_files)),
           'extra_local': sorted(set(local_files) - set(remote))})
    bad = {name: {'remote': h, 'local': sha(d1 / name)}
           for name, h in remote.items()
           if not (d1 / name).is_file() or sha(d1 / name) != h}
    check(checks, 'all_local_sha256_match_remote', not bad, bad)

    # 2. Initial identity.
    remote_initial = {}
    for line in args.remote_initial.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        h, name = line.split(None, 1)
        remote_initial[Path(name).name] = h
    check(checks, 'remote_initial_hashes_match_config',
          remote_initial == config['initial']['hashes'],
          {'remote': remote_initial, 'config': config['initial']['hashes']})
    check(checks, 'result_initial_dir',
          Path(result.get('initial_dir', '')).name
          == Path(config['initial']['dir_remote']).name)
    check(checks, 'success_meta_initial_hashes',
          meta.get('initial_hashes') == config['initial']['hashes'])
    initial_case = result.get('initial_case') or {}
    check(checks, 'initial_case_identity',
          initial_case.get('seed') == 4202
          and initial_case.get('level') == 'perturbed'
          and initial_case.get('status')
          == 'blocked_unvalidated_corner_lift_drop',
          initial_case)

    # 3. Action identity against RC2 4202 single.
    da, ba = result.get('actions') or [], bresult.get('actions') or []
    check(checks, 'action_count_12', len(da) == 12 and len(ba) == 12,
          {'d1': len(da), 'rc2': len(ba)})
    check(checks, 'action_labels_match',
          [a['label'] for a in da] == [a['label'] for a in ba])
    check(checks, 'action_commands_match',
          [a['command'] for a in da] == [a['command'] for a in ba])
    check(checks, 'action_horizons_match',
          result.get('call_horizons') == bresult.get('call_horizons')
          == [1] * 12)
    dtargets = np.asarray([a['target_pose'] for a in da], dtype=float)
    btargets = np.asarray([a['target_pose'] for a in ba], dtype=float)
    action_delta = maxdiff(dtargets, btargets)
    check(checks, 'action_targets_match', action_delta == 0.0,
          {'max_abs_diff_m': action_delta, 'shape': list(dtargets.shape)})
    check(checks, 'last_action_release_retreat',
          (result.get('action_labels') or [])[-1:] == ['release_retreat'])

    # 4. Physical clocks and delay.
    delay = result.get('internal_delay') or {}
    check(checks, 'meta_dt_1_60', abs(float(meta.get('dt_s', -1)) - 1 / 60) <= 1e-12)
    check(checks, 'delay_120_world_steps',
          delay.get('requested_steps') == 120
          and delay.get('elapsed_steps') == 120
          and delay.get('end_step', 0) - delay.get('start_step', 0) == 120,
          delay)
    check(checks, 'delay_sim_time_2s',
          abs(float(delay.get('elapsed_sim_time_s', -1)) - 2.0) <= 1e-6,
          delay.get('elapsed_sim_time_s'))
    check(checks, 'delay_ee_stationary',
          delay.get('ee_displacement_m') == 0.0
          and delay.get('control_calls') == 0
          and delay.get('target_changes') == 0)
    check(checks, 'delay_no_cloth_reset',
          delay.get('cloth_position_reset') is False
          and delay.get('cloth_velocity_reset') is False)
    check(checks, 'delay_public_action_12',
          delay.get('public_action_index') == 12
          and delay.get('public_action_label') == 'release_retreat'
          and delay.get('public_action') is False)
    # The world-step clock and observed-step clock are offset by 2 in this
    # episode; the trace starts at absolute 2219 and the events at observed 2217.
    check(checks, 'clock_offsets_consistent',
          delay.get('start_step') - 1953 == 2
          and delay.get('end_step') - 2073 == 2
          and int(np.asarray(npz(d1 / 'success_trace.npz')['absolute_steps'])[0])
          - 2217 == 2,
          {'delay_start': delay.get('start_step'),
           'delay_end': delay.get('end_step'), 'retreat_end_observed': 2217,
           'trace_start_absolute': int(np.asarray(
               npz(d1 / 'success_trace.npz')['absolute_steps'])[0])})
    check(checks, 'absolute_step_delta_vs_rc2',
          int(meta.get('absolute_step')) - int(bmeta.get('absolute_step')) == 120
          and abs(float(meta.get('sim_time_s')) - float(bmeta.get('sim_time_s')) - 2.0) <= 1e-6,
          {'d1_absolute': meta.get('absolute_step'),
           'rc2_absolute': bmeta.get('absolute_step'),
           'd1_sim': meta.get('sim_time_s'), 'rc2_sim': bmeta.get('sim_time_s')})

    # 5. Attachment state through the wait and after release.
    rdz = npz(d1 / 'evidence/release_diag.npz')
    phases = np.asarray(rdz['phase'])
    wait = phases == 'delay'
    check(checks, 'delay_phase_rows_120', int(wait.sum()) == 120, int(wait.sum()))
    check(checks, 'delay_rows_detached',
          bool(np.all(~np.asarray(rdz['holding'])[wait]))
          and bool(np.all(~np.asarray(rdz['attached'])[wait]))
          and bool(np.all(~np.asarray(rdz['enabled_slots'])[wait]))
          and bool(np.all(~np.asarray(rdz['logical_attached'])[wait]))
          and bool(np.all(np.asarray(rdz['gripper_state'])[wait] == 0)),
          {'holding': int(np.asarray(rdz['holding'])[wait].sum()),
           'attached': int(np.asarray(rdz['attached'])[wait].sum()),
           'enabled_slots_any': int(np.asarray(rdz['enabled_slots'])[wait].sum())})
    rdj = read(d1 / 'evidence/release_diag.json')
    events = rdj.get('events') or []
    names = [e.get('event') for e in events]
    steps = {e.get('event'): int(e.get('observed_step', -1)) for e in events}
    required = ['ungrasp_return', 'delay_begin', 'delay_end',
                'retreat_begin', 'retreat_end']
    check(checks, 'required_events_exact', names == required, names)
    check(checks, 'event_steps_and_order',
          steps.get('delay_end', 0) - steps.get('delay_begin', 0) == 120
          and steps.get('ungrasp_return', 10**9) <= steps.get('delay_begin', -1)
          and steps.get('retreat_begin', -1) >= steps.get('delay_end', 10**9)
          and steps.get('retreat_end', -1) >= steps.get('retreat_begin', 10**9),
          steps)
    check(checks, 'events_complete', rdj.get('events_complete') is True)
    check(checks, 'phase_counts',
          int((phases == 'delay').sum()) == 120
          and int((phases == 'retreat').sum()) > 0,
          {str(k): int(v) for k, v in zip(*np.unique(phases, return_counts=True))})
    trace = npz(d1 / 'success_trace.npz')
    check(checks, 'success_trace_331', len(trace['vertices']) == 331,
          len(trace['vertices']))
    check(checks, 'trace_detached',
          bool(not np.any(trace['holding']))
          and bool(not np.any(trace['attachment_enabled']))
          and bool(np.all(trace['gripper_open'])))

    # 6. Pre-wait trajectory exact against v1.1.
    brd = npz(v11 / 'evidence/release_diag.npz')
    d_pre = np.asarray(rdz['observed_step']) <= 1953
    b_pre = np.asarray(brd['observed_step']) <= 1953
    keys = ['vertices', 'ee_m', 'ee_quaternion_wxyz', 'joint_positions',
            'gripper_aperture_m', 'gripper_state', 'holding', 'attached',
            'enabled_slots', 'logical_attached', 'command_holding', 'sim_time_s',
            'observed_step', 'backend_step', 'call_id',
            'ee_min_vertex_distance_mm', 'finger_min_vertex_distance_mm',
            'sample_label']
    prewait_bad = {}
    for key in keys:
        a = np.asarray(rdz[key])[d_pre]
        b = np.asarray(brd[key])[b_pre]
        if not eq(a, b):
            prewait_bad[key] = {'d1_shape': list(a.shape),
                                'v11_shape': list(b.shape),
                                'max_abs_diff': maxdiff(a, b)}
    check(checks, 'prewait_release_rows_count',
          int(d_pre.sum()) == int(b_pre.sum()) == 12,
          {'d1': int(d_pre.sum()), 'v11': int(b_pre.sum())})
    check(checks, 'prewait_release_arrays_identical', not prewait_bad, prewait_bad)
    prehold = eq(npz(d1 / 'pre_release_hold.npz')['vertices'],
                 npz(rc2 / 'pre_release_hold.npz')['vertices'])
    recovered = eq(npz(d1 / 'recovered.npz')['vertices'],
                   npz(rc2 / 'recovered.npz')['vertices'])
    constructed = eq(npz(d1 / 'cloth_constructed.npz')['points'],
                     npz(rc2 / 'cloth_constructed.npz')['points'])
    check(checks, 'prewait_pre_release_hold_identical', prehold)
    check(checks, 'prewait_recovered_identical', recovered)
    check(checks, 'prewait_cloth_constructed_identical', constructed)
    check(checks, 'prewait_initial_hashes_match',
          meta.get('initial_hashes') == bmeta.get('initial_hashes'))
    check(checks, 'prewait_pick_yaw_match',
          meta.get('pick_index') == bmeta.get('pick_index')
          and meta.get('yaw_rad') == bmeta.get('yaw_rad'))
    check(checks, 'retreat_upward_displacement_match',
          abs(float(meta.get('upward_displacement_m'))
              - float(bmeta.get('upward_displacement_m'))) <= 1e-6,
          {'d1': meta.get('upward_displacement_m'),
           'rc2': bmeta.get('upward_displacement_m')})

    # 7. Postfix quality / evidence / contact.
    q = postfix.get('quality') or {}
    check(checks, 'postfix_complete', postfix.get('complete_diagnostic') is True)
    check(checks, 'postfix_no_failed_checks',
          not [k for k, v in (postfix.get('checks') or {}).items() if not v],
          [k for k, v in (postfix.get('checks') or {}).items() if not v])
    check(checks, 'quality_rejected',
          q.get('status') == 'rejected' and q.get('success') is False)
    check(checks, 'stability_values',
          abs(float(q.get('stability', {}).get('centroid_drift_max_m'))
              - 0.00204088167284051) <= 1e-12
          and abs(float(q.get('stability', {}).get('vertex_drift_p95_max_m'))
                  - 0.0044134143018154616) <= 1e-12)
    ev = postfix.get('evidence') or {}
    check(checks, 'evidence_complete', ev.get('evidence_complete') is True)
    check(checks, 'video_frames_1279', ev.get('decoded_frames') == 1279,
          ev.get('decoded_frames'))
    check(checks, 'episode_passed', result.get('passed') is True
          and result.get('errors') == [])
    contact = read(d1 / 'contact_report.json')
    check(checks, 'contact_zero_not_no_contact',
          contact.get('subscription_created') is True
          and contact.get('event_count') == 0
          and contact.get('diagnosis')
          == 'configured_no_events_channel_not_independently_validated', contact)
    check(checks, 'postfix_preserves_standard_assess_status',
          ledger.get('assess_status') == 1 and ledger.get('sim_process_status') == 0
          and ledger.get('episode_passed') is True, ledger)

    all_ok = all(v['ok'] for v in checks.values())
    payload = {
        'version': 'a5-rc2-d1-120',
        'created_utc': None,
        'scope': 'step-7 offline audit; no simulation',
        'd1_dir': str(d1),
        'rc2_dir': str(rc2),
        'v11_dir': str(v11),
        'checks': checks,
        'all_ok': all_ok,
        'action_target_max_abs_diff_m': action_delta,
        'prewait_bad': prewait_bad,
        'quality': q,
        'events': {'names': names, 'steps': steps},
        'delay': delay,
    }
    # Stable timestamp from the run directory name, not a new wall clock.
    payload['created_utc'] = '2026-11-04T00:40:00Z'
    (out / 'audit.json').write_text(json.dumps(payload, indent=2) + '\n',
                                    encoding='utf-8')
    lines = ['D1_STEP7 all_ok=%s checks=%d' % (all_ok, len(checks))]
    for name, value in checks.items():
        lines.append('%s %s %s' % ('PASS' if value['ok'] else 'FAIL', name,
                                   '' if value['ok'] else json.dumps(value['detail'])))
    lines.append('D1_STEP7_OK' if all_ok else 'D1_STEP7_FAIL')
    (out / 'audit_stdout.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    return 0 if all_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
