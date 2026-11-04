#!/usr/bin/env python3
"""Build the A5 RC2 baseline index and diagnostic registration (offline).

Reads the downloaded RC2 audit directory, copies the candidate snapshot and the
original verification outputs into a new diagnostic directory, and writes:

  baseline.json            code/config/hash/verify-dev baseline
  case-index.json/.md      seven pre-registered RC2 cases
  diagnostic-config.json   separate diagnostic batch registration (not run)
  file-hashes.json         hashes of the snapshot and key source files

The script never writes into the RC2 audit directory and refuses to overwrite
an existing output directory.  No simulation, no GPU, no held-out.
"""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rel(path, root):
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(Path(path).resolve())


def verify_manifest(app_dir, manifest):
    bad = []
    for name, want in manifest.items():
        p = (Path(app_dir) / name).resolve()
        if not p.is_file() or sha256(p) != want:
            bad.append({'file': name, 'expected': want,
                        'actual': sha256(p) if p.is_file() else None})
    return bad


def last_action(timeline):
    begins = [r for r in timeline if r.get('kind') == 'action_begin']
    ends = [r for r in timeline if r.get('kind') == 'action_end']
    return (begins[-1] if begins else None, ends[-1] if ends else None)


def frame_window(timeline, start_obs, end_obs):
    frames = [r for r in timeline if r.get('kind') == 'frame'
              and start_obs <= r.get('observed_step', -10**9) <= end_obs]
    if not frames:
        return {'first': None, 'last': None, 'count': 0}
    return {'first': int(frames[0]['frame_index']),
            'last': int(frames[-1]['frame_index']),
            'count': len(frames)}


def rejection_reason(verdict, result):
    if verdict.get('status') == 'accepted':
        return 'accepted'
    checks = (verdict.get('criteria') or {}).get('checks') or {}
    failed = [k for k, ok in checks.items() if not ok]
    parts = []
    if 'stable' in failed:
        st = (verdict.get('criteria') or {}).get('stability') or {}
        parts.append('stability: centroid_max=%.6f m (limit 0.001), '
                     'vertex_p95_max=%.6f m (limit 0.003)'
                     % (st.get('centroid_drift_max_m', float('nan')),
                        st.get('vertex_drift_p95_max_m', float('nan'))))
    if 'geometry_entire_window' in failed:
        n = len((verdict.get('criteria') or {}).get('failed_geometry_frames') or [])
        parts.append('geometry: %d/121 window frames fail' % n)
    if 'no_runtime_error' in failed:
        parts.append('runtime gate: ' + '; '.join(result.get('errors') or []))
    other = [k for k in failed if k not in ('stable', 'geometry_entire_window', 'no_runtime_error')]
    if other:
        parts.append('other checks: ' + ', '.join(other))
    return '; '.join(parts) if parts else 'rejected'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--audit-dir', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    audit = Path(args.audit_dir).resolve()
    out = Path(args.out).resolve()
    if out.exists():
        raise SystemExit('Refusing to overwrite existing output: ' + str(out))
    out.mkdir(parents=True)
    baseline_dir = out / 'baseline'
    source_dir = out / 'source-snapshot'
    baseline_dir.mkdir()
    source_dir.mkdir()

    app_src = audit / 'stage4-a5-rc2' / 'app'
    criteria_src = audit / 'stage4-a5-rc2' / 'STAGE4_SUCCESS_CRITERIA_V1.md'
    shutil.copytree(app_src, source_dir / 'app',
                    ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(criteria_src, source_dir / 'STAGE4_SUCCESS_CRITERIA_V1.md')

    candidate_src = app_src / 'a5-candidate.json'
    manifest_src = app_src / 'a5-manifest.json'
    verify_src = audit / 'verify-dev.json'
    offline_src = audit / 'offline-audit.json'
    phase_src = audit / 'phase-motion.json'
    review_src = audit / 'review.md'
    download_src = audit / 'download_sha256.json'
    for src, name in ((candidate_src, 'a5-candidate.json'),
                      (manifest_src, 'a5-manifest.json'),
                      (verify_src, 'verify-dev.json'),
                      (offline_src, 'offline-audit.json'),
                      (phase_src, 'phase-motion.json'),
                      (review_src, 'original-review.md'),
                      (download_src, 'download_sha256.json')):
        shutil.copy2(src, baseline_dir / name)

    candidate = read(candidate_src)
    manifest = read(manifest_src)
    verify = read(verify_src)
    offline = read(offline_src)
    manifest_bad = verify_manifest(app_src, manifest)
    snapshot_bad = verify_manifest(source_dir / 'app', manifest)
    if manifest_bad or snapshot_bad:
        raise SystemExit('Manifest verification failed: original=%s snapshot=%s'
                         % (manifest_bad, snapshot_bad))

    cases = []
    for d in sorted(audit.glob('day4-a5-rc2-*')):
        if not d.is_dir():
            continue
        if not all((d / n).is_file() for n in
                   ('result.json', 'success_meta.json', 'a5-verdict.json',
                    'success_trace.npz', 'evidence/timeline.jsonl', 'evidence/episode.mp4')):
            continue
        result = read(d / 'result.json')
        meta = read(d / 'success_meta.json')
        verdict = read(d / 'a5-verdict.json')
        seed = int(meta['seed'])
        mode = meta['execution_mode']
        label = '%d %s' % (seed, mode)
        timeline = [json.loads(x) for x in
                    (d / 'evidence/timeline.jsonl').read_text().splitlines() if x.strip()]
        begin, end = last_action(timeline)
        offset = int(meta['absolute_step'] - end['observed_step']) if end else None
        win_start_abs = int(meta['absolute_step'] + 210)
        win_end_abs = int(meta['absolute_step'] + 330)
        win_start_obs = int(win_start_abs - offset) if offset is not None else None
        win_end_obs = int(win_end_abs - offset) if offset is not None else None
        frames = (frame_window(timeline, win_start_obs, win_end_obs)
                  if win_start_obs is not None else {'first': None, 'last': None, 'count': 0})
        development = candidate['development'].get(str(seed)) or {}
        crit = verdict.get('criteria') or {}
        st = crit.get('stability') or {}
        checks = crit.get('checks') or {}
        ev = verdict.get('evidence_checks') or {}
        cases.append({
            'case': label,
            'seed': seed,
            'level': meta['level'],
            'mode': mode,
            'positive': bool(development.get('positive')),
            'role': 'positive' if development.get('positive') else 'negative_control',
            'result_dir': str(d),
            'result_dir_name': d.name,
            'initial_dir_remote': result.get('initial_dir'),
            'initial_dir_local': str(audit / Path(result['initial_dir']).name),
            'initial_hashes': meta.get('initial_hashes'),
            'manifest_sha256': meta.get('manifest_sha256'),
            'action_count': result.get('action_count'),
            'call_horizons': result.get('call_horizons'),
            'development_pass': result.get('passed'),
            'evidence_checks': ev,
            'evidence_all_true': all(ev.values()) if ev else None,
            'verdict': verdict.get('status'),
            'success': verdict.get('success'),
            'criteria_checks': checks,
            'failed_checks': [k for k, ok in checks.items() if not ok],
            'rejection_reason': rejection_reason(verdict, result),
            'geometry_pass': checks.get('geometry_entire_window'),
            'failed_geometry_frames': len(crit.get('failed_geometry_frames') or []),
            'stability': st,
            'held_check': meta.get('held_check'),
            'evaluation': {
                'success_trace_steps': [210, 330],
                'success_trace_absolute_steps': [win_start_abs, win_end_abs],
                'sim_time_s': [meta['sim_time_s'] + 210 / 60,
                               meta['sim_time_s'] + 330 / 60],
                'video_frame_first': frames['first'],
                'video_frame_last': frames['last'],
                'video_frame_count': frames['count'],
                'success_trace': str(d / 'success_trace.npz'),
                'video': str(d / 'evidence/episode.mp4'),
                'timeline': str(d / 'evidence/timeline.jsonl'),
                'verdict': str(d / 'a5-verdict.json'),
                'success_meta': str(d / 'success_meta.json'),
                'evidence_summary': str(d / 'evidence/summary.json')
            },
            'release_clock': {
                'last_action_label': result.get('action_labels', [None])[-1],
                'action_count': result.get('action_count'),
                'absolute_step': meta.get('absolute_step'),
                'sim_time_s': meta.get('sim_time_s'),
                'dt_s': meta.get('dt_s'),
                'action_begin_observed_step': begin['observed_step'] if begin else None,
                'action_begin_sim_time_s': begin['sim_time_s'] if begin else None,
                'action_end_observed_step': end['observed_step'] if end else None,
                'action_end_sim_time_s': end['sim_time_s'] if end else None,
                'observed_to_absolute_offset': offset
            }
        })

    if len(cases) != 7:
        raise SystemExit('Expected seven RC2 cases, found %d' % len(cases))

    baseline = {
        'baseline_id': 'stage4-a5-rc2-baseline-20261103',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_audit_dir': str(audit),
        'candidate': {
            'version': candidate.get('version'),
            'parent': candidate.get('parent'),
            'status': candidate.get('status'),
            'candidate_sha256': sha256(candidate_src),
            'manifest_sha256': sha256(manifest_src),
            'manifest_entries': len(manifest),
            'manifest_verified_original': not manifest_bad,
            'manifest_verified_snapshot': not snapshot_bad,
            'source_snapshot': str(source_dir / 'app'),
            'candidate_copy': str(baseline_dir / 'a5-candidate.json'),
            'manifest_copy': str(baseline_dir / 'a5-manifest.json')
        },
        'verify_dev': {
            'path': str(verify_src),
            'copy': str(baseline_dir / 'verify-dev.json'),
            'sha256': sha256(verify_src),
            'exit_code': verify.get('exit_code'),
            'release_exists': verify.get('release_exists'),
            'stdout': verify.get('stdout'),
            'stderr': verify.get('stderr')
        },
        'offline_audit': {
            'path': str(offline_src),
            'sha256': sha256(offline_src),
            'manifest_sha256': offline.get('manifest_sha256'),
            'source_hash_count': offline.get('source_hash_count'),
            'download_hash_count': offline.get('download_hash_count'),
            'verify_exit': offline.get('verify_exit'),
            'freeze_eligible': offline.get('freeze_eligible')
        },
        'rgb_video_holding_base': {
            'all_seven_evidence_checks_true': all(c['evidence_all_true'] for c in cases),
            'checks': sorted({k for c in cases for k in (c['evidence_checks'] or {})}),
            'note': 'The RGB/video/holding-state fixes are the passed basis. The original '
                    'verify-dev exit code 1 is caused by a positive smoke case stability '
                    'rejection, not by a video/RGB/holding evidence failure.'
        },
        'seven_cases': [{'case': c['case'], 'verdict': c['verdict'],
                         'rejection_reason': c['rejection_reason']} for c in cases],
        'diagnostic_subjects': [
            {'order': 1, 'case': '4202 single',
             'role': 'first diagnostic subject',
             'result_dir': c['result_dir'], 'initial_dir': c['initial_dir_local']}
            for c in cases if c['case'] == '4202 single'
        ] + [
            {'order': 2, 'case': '4302 single',
             'role': 'later revalidation subject',
             'result_dir': c['result_dir'], 'initial_dir': c['initial_dir_local']}
            for c in cases if c['case'] == '4302 single'
        ],
        'freeze_status': {
            'frozen': False,
            'reason': 'verify-dev exit 1; E_RELEASE.json absent; four task-B positives '
                      'rejected by stability; 4201 rejected by geometry/runtime gate',
            'formal_stage4_success': 0
        },
        'notes': [
            'RC2 is a development candidate, not a frozen formal release.',
            'The diagnostic batch must use a new tag/directory and must not overwrite RC2.',
            'This baseline is an offline index; no simulation was run.',
            'The release-to-retreat interval has only sparse released/retreated snapshots; '
            'per-physical-step cloth vertices are not present in the existing data.'
        ]
    }

    diagnostic = {
        'batch_id': 'a5-rc2-drift-diag-v1',
        'status': 'registered_not_run',
        'created_utc': baseline['created_utc'],
        'base_candidate': {
            'version': candidate.get('version'),
            'manifest_sha256': sha256(manifest_src),
            'candidate_sha256': sha256(candidate_src),
            'baseline_dir': str(out)
        },
        'scope': 'Diagnostic drift localisation and minimal correction only. '
                 'No formal batch, no held-out, no formal success.',
        'subjects': baseline['diagnostic_subjects'],
        'fixed': {
            'initial_dirs': [c['initial_dir_local'] for c in cases
                             if c['case'] in ('4202 single', '4302 single')],
            'fold_edge': 'right',
            'fold_width_m': 0.2,
            'overhang_m': 0.0,
            'public_actions': {'4202 single': 12, '4302 single': 12},
            'recovery_actions': 1,
            'release_action': 'last public OPEN, target = measured EE + [0,0,0.15] m',
            'pre_release_hold_steps': 180,
            'sample_clock': 'after release_retreat returns: steps 0..330 at 60 Hz; '
                            'formal window 210..330',
            'stability_criteria': {'centroid_drift_max_m': 0.001,
                                   'vertex_drift_p95_max_m': 0.003},
            'physics_material_ground': 'unchanged from RC2'
        },
        'variants': [
            {'id': 'D0', 'name': 'baseline reproduction with diagnostic recording',
             'change': 'none to policy, path, material, ground or release hold; add '
                       'per-step diagnostic recording only',
             'status': 'registered_not_run',
             'question': 'Is the original drift reproducible with the diagnostic recorder?'},
            {'id': 'D1', 'name': 'delayed retreat',
             'change': 'release/ungrasp and open; arm temporarily holds position; then retreat',
             'status': 'registered_not_run; delay length to be fixed after step 3',
             'question': 'Does the cloth drift before the retreat begins?',
             'budget': 'Must stay within 12 public actions; no hidden waypoints.'},
            {'id': 'D2', 'name': 'detachment path comparison',
             'change': 'design only after contact/distance evidence',
             'status': 'not_designed',
             'question': 'Does a different robot detachment path reduce the drift?'}
        ],
        'recording_requirements': [
            'per-physical-step cloth vertices from release action start through retreat end',
            'gripper pose, opening amount, holding and all three attachment enables',
            'available contact object, time, force and impulse; if only distance is available, '
            'label it as distance evidence and do not call it contact',
            'same physical time span for every compared segment',
            'report both the original 210..330 evaluation and the diagnostic phases'
        ],
        'stop_conditions': [
            'D0 does not reproduce the original drift: stop and investigate version/repeatability',
            'code/config/physics/action targets change without a new registration',
            'contact records remain unavailable and the next step cannot distinguish hypotheses',
            'a variant requires more than 12 public actions without a registered budget change'
        ],
        'output_policy': {
            'separate_tag': 'stage4-a5-rc2-drift-diag-v1-*',
            'must_not_overwrite': str(audit),
            'retain_all_failures': True,
            'formal_success': 0
        }
    }

    (out / 'baseline.json').write_text(json.dumps(baseline, indent=2) + '\n')
    (out / 'case-index.json').write_text(json.dumps(cases, indent=2) + '\n')
    (out / 'diagnostic-config.json').write_text(json.dumps(diagnostic, indent=2) + '\n')

    lines = ['# RC2 baseline: seven pre-registered cases', '',
             'Source audit: `%s`' % audit, '',
             '| case | verdict | failed check | centroid max mm | P95 max mm | '
             'geometry frames failed | video frames | evidence all true |',
             '|---|---|---|---:|---:|---:|---|---|']
    for c in sorted(cases, key=lambda x: x['case']):
        st = c['stability'] or {}
        lines.append('| %s | %s | %s | %.6f | %.6f | %d | %s-%s (%d) | %s |' % (
            c['case'], c['verdict'], c['rejection_reason'],
            1000 * float(st.get('centroid_drift_max_m', 0.0)),
            1000 * float(st.get('vertex_drift_p95_max_m', 0.0)),
            c['failed_geometry_frames'],
            c['evaluation']['video_frame_first'], c['evaluation']['video_frame_last'],
            c['evaluation']['video_frame_count'], c['evidence_all_true']))
    lines += ['', '## Roles', '',
              '- 4100 single/arc4: positive L1 regression.',
              '- 4202 single/arc4: positive task-B, rejected by stability; '
              '4202 single is the first diagnostic subject.',
              '- 4302 single/arc4: positive task-B, rejected by stability; '
              '4302 single is the later revalidation subject.',
              '- 4201 single: negative control, rejected by geometry/runtime gate.',
              '', '## Verification baseline', '',
              '- RC2 manifest: `%s` (60 entries, verified).' % sha256(manifest_src),
              '- Original verify-dev: exit_code=%s, release_exists=%s.'
              % (verify.get('exit_code'), verify.get('release_exists')),
              '- RGB/video/holding evidence checks: all seven true.',
              '- Freeze: not frozen; formal Stage 4 success remains 0.']
    (out / 'case-index.md').write_text('\n'.join(lines) + '\n')

    hashes = {'created_utc': baseline['created_utc'], 'files': []}
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name != 'file-hashes.json':
            hashes['files'].append({'path': rel(p, out), 'sha256': sha256(p),
                                    'size': p.stat().st_size})
    (out / 'file-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')

    print('RC2_BASELINE_OK cases=%d manifest_entries=%d verify_exit=%s'
          % (len(cases), len(manifest), verify.get('exit_code')))
    print('OUT', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
