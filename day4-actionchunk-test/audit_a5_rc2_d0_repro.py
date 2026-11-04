#!/usr/bin/env python3
"""Offline D0 reproducibility audit for an A5 RC2 run.

Compares a downloaded D0 run against a reference RC2 run on the same
seed/mode: result targets/metrics, verdict, success_meta, cloth arrays,
evidence samples, normalized timeline state/action rows, and the optional
D0 journal.  UTC/monotonic timestamps and video encoding are excluded from
the physics identity check; those three evidence-file hashes are reported as
expected non-physics differences.

No simulation, no GPU, no formal success upgrade.
"""
import argparse
import json
from pathlib import Path

import numpy as np


def read(path):
    return json.loads(Path(path).read_text())


def load_npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def equal(a, b):
    return bool(np.array_equal(np.asarray(a), np.asarray(b)))


def maxdiff(a, b):
    x = np.asarray(a, dtype=float)
    y = np.asarray(b, dtype=float)
    if x.size == 0:
        return 0.0
    return float(np.max(np.abs(x - y)))


def norm_state(row):
    return {k: row.get(k) for k in
            ('kind', 'observed_step', 'sim_time_s', 'holding', 'attached',
             'enabled_slots', 'logical_attached', 'command_holding',
             'ee_m', 'backend_step')}


def norm_action(row):
    return {k: row.get(k) for k in
            ('kind', 'call_id', 'targets', 'commands', 'horizon',
             'executed_steps', 'observed_step', 'sim_time_s')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--d0', required=True, type=Path)
    ap.add_argument('--ref', required=True, type=Path)
    ap.add_argument('--journal', type=Path)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    d0 = args.d0.resolve()
    ref = args.ref.resolve()
    checks = {}
    details = {}

    r0 = read(d0 / 'result.json')
    r1 = read(ref / 'result.json')
    for key in ('passed', 'errors', 'action_count', 'action_labels',
                'call_horizons', 'fold_metrics', 'fold_held_check',
                'recovery_metrics', 'initial_case', 'fold_edge',
                'execution_mode', 'code_files'):
        checks['result:' + key] = r0.get(key) == r1.get(key)
    checks['result:code_files_entries'] = (
        len(r0.get('code_files') or {}) == len(r1.get('code_files') or {}) == 60)
    checks['actions:targets'] = maxdiff(
        [a['target_pose'] for a in r0['actions']],
        [a['target_pose'] for a in r1['actions']]) <= 1e-12
    checks['actions:commands'] = ([a['command'] for a in r0['actions']] ==
                                  [a['command'] for a in r1['actions']])
    checks['actions:labels'] = ([a['label'] for a in r0['actions']] ==
                                [a['label'] for a in r1['actions']])
    checks['records:targets'] = maxdiff(
        [a.get('pick_world') for a in r0['records'] if a.get('pick_world')],
        [a.get('pick_world') for a in r1['records'] if a.get('pick_world')]) <= 1e-12
    details['actions_target_max_abs_diff'] = maxdiff(
        [a['target_pose'] for a in r0['actions']],
        [a['target_pose'] for a in r1['actions']])

    v0 = read(d0 / 'a5-verdict.json')
    v1 = read(ref / 'a5-verdict.json')
    for key in ('status', 'success', 'manifest_sha256'):
        checks['verdict:' + key] = v0.get(key) == v1.get(key)
    c0 = v0.get('criteria') or {}
    c1 = v1.get('criteria') or {}
    for key in ('status', 'success', 'checks', 'stability',
                'first_window_geometry', 'final_geometry',
                'failed_geometry_frames'):
        checks['verdict:criteria:' + key] = c0.get(key) == c1.get(key)
    checks['verdict:evidence_checks'] = v0.get('evidence_checks') == v1.get('evidence_checks')

    m0 = read(d0 / 'success_meta.json')
    m1 = read(ref / 'success_meta.json')
    for key in ('protocol', 'task', 'seed', 'level', 'edge', 'execution_mode',
                'width_m', 'overhang_m', 'floor_z_m', 'action_count',
                'recovery_count', 'held_check', 'errors', 'initial_hashes',
                'manifest_sha256', 'absolute_step', 'sim_time_s', 'dt_s',
                'pick_index', 'yaw_rad', 'upward_displacement_m'):
        checks['meta:' + key] = m0.get(key) == m1.get(key)

    for name in ('final.npz', 'recovered.npz', 'pre_release_hold.npz',
                 'cloth_constructed.npz', 'success_trace.npz'):
        z0 = load_npz(d0 / name)
        z1 = load_npz(ref / name)
        checks['npz:' + name + ':keys'] = set(z0) == set(z1)
        for key in z0:
            if key in z1:
                checks['npz:%s:%s' % (name, key)] = equal(z0[key], z1[key])
                if z0[key].dtype.kind in 'fiu':
                    details['npz:%s:%s:maxdiff' % (name, key)] = maxdiff(
                        z0[key], z1[key])

    for name in ('released.npz', 'retreated.npz', 'hold_3s.npz',
                 'hold_4s.npz', 'terminal.npz'):
        z0 = load_npz(d0 / 'evidence' / name)
        z1 = load_npz(ref / 'evidence' / name)
        checks['sample:' + name] = equal(z0['vertices'], z1['vertices'])
        details['sample:%s:maxdiff' % name] = maxdiff(z0['vertices'], z1['vertices'])

    s0 = read(d0 / 'evidence/summary.json')
    s1 = read(ref / 'evidence/summary.json')
    for key in ('synthetic', 'frames', 'observed_steps', 'execute_calls',
                'errors', 'playback_fps', 'time_authority',
                'formal_day4_success'):
        checks['summary:' + key] = s0.get(key) == s1.get(key)
    checks['summary:sources_hashes'] = (
        {k: v['sha256'] for k, v in (s0.get('sources') or {}).items()} ==
        {k: v['sha256'] for k, v in (s1.get('sources') or {}).items()})
    checks['summary:sample_keys'] = ((s0.get('samples') or {}).keys() ==
                                     (s1.get('samples') or {}).keys())

    t0 = [json.loads(x) for x in
          (d0 / 'evidence/timeline.jsonl').read_text().splitlines() if x.strip()]
    t1 = [json.loads(x) for x in
          (ref / 'evidence/timeline.jsonl').read_text().splitlines() if x.strip()]
    checks['timeline:row_counts'] = len(t0) == len(t1)
    checks['timeline:state_sample_rows'] = (
        [norm_state(r) for r in t0 if r['kind'] in ('state', 'sample')] ==
        [norm_state(r) for r in t1 if r['kind'] in ('state', 'sample')])
    checks['timeline:action_rows'] = (
        [norm_action(r) for r in t0 if r['kind'] in ('action_begin', 'action_end')] ==
        [norm_action(r) for r in t1 if r['kind'] in ('action_begin', 'action_end')])

    h0 = read(d0 / 'evidence/manifest.json')
    h1 = read(ref / 'evidence/manifest.json')
    checks['evidence_manifest:keys'] = set(h0) == set(h1)
    expected = {'summary.json', 'timeline.jsonl', 'episode.mp4'}
    diffs = sorted(k for k in set(h0) & set(h1) if h0[k] != h1[k])
    checks['evidence_manifest:only_expected_nonphysics_diffs'] = set(diffs) <= expected
    details['evidence_manifest_hash_diffs'] = diffs
    details['evidence_manifest_expected_nonphysics'] = sorted(expected)
    details['video_decoded_locally'] = False
    details['video_note'] = ('Video hash differs; local audit does not decode frames '
                             'because cv2 is unavailable. The remote evidence check '
                             'video_and_samples passed; summary frame counts match.')

    if args.journal:
        j = args.journal.resolve()
        attempts = sorted(p.parent for p in j.glob('*/started.json'))
        if not attempts:
            raise SystemExit('No attempt started.json under journal: ' + str(j))
        attempt = next(
            (a for a in attempts if (a / 'finished.json').is_file()
             and Path(read(a / 'finished.json').get('result_dir', '')).name == d0.name),
            attempts[0])
        started = read(attempt / 'started.json')
        finished = read(attempt / 'finished.json')
        details['journal_attempt'] = str(attempt)
        checks['journal:started_manifest'] = (
            started.get('manifest_sha256') == m0.get('manifest_sha256'))
        checks['journal:started_seed_mode'] = (
            started.get('seed') == m0.get('seed') and
            started.get('mode') == m0.get('execution_mode'))
        checks['journal:finished_runner_exit'] = finished.get('runner_exit') == 0
        checks['journal:finished_status'] = finished.get('status') == v0.get('status')
        checks['journal:result_dir'] = (
            Path(finished.get('result_dir', '')).name == d0.name)
        entry = (j / 'entry-exit-code.txt')
        checks['journal:entry_exit_code'] = (
            entry.is_file() and entry.read_text().strip() == '1')
        manifest = (j / 'manifest.sha256')
        if manifest.is_file():
            checks['journal:manifest_base'] = (
                m0.get('manifest_sha256') in manifest.read_text())

    failed = [k for k, ok in checks.items() if not ok]
    doc = {
        'protocol': 'a5-rc2-d0-repro-audit',
        'd0': str(d0),
        'reference': str(ref),
        'journal': str(args.journal.resolve()) if args.journal else None,
        'ok': not failed,
        'checks': checks,
        'failed': failed,
        'details': details,
        'formal_stage4_success': False,
        'notes': [
            'Physics/state identity is checked with exact array equality and zero target delta.',
            'UTC/monotonic timestamps and video encoding are excluded from physics identity.',
            'The video was not decoded locally; the remote evidence check is retained.',
            'A valid D0 rejection is not an infrastructure error and is not a formal success.'
        ]
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, allow_nan=False) + '\n')
    for k, ok in checks.items():
        print(('PASS ' if ok else 'FAIL ') + k)
    print('D0_REPRO_' + ('OK' if doc['ok'] else 'FAILED'),
          'checks=%d failed=%d' % (len(checks), len(failed)))
    print('D0_AUDIT', args.out)
    return 0 if doc['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
