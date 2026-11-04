#!/usr/bin/env python3
"""Offline preflight for a5-rc2-d1-120.

Checks syntax, identity/manifest hashes, the 120-step insertion point, the
12-public-action budget, the event/acquisition logic, and that the wait is
reachable only from the final release path.  It never imports Isaac, never
starts a simulation and never writes into the diagnostic app.
"""
import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / 'a5-rc2-d1-120' / 'app'
VERSION_DIR = ROOT / 'a5-rc2-d1-120'
PARENT_APP = ROOT / 'a5-rc2-drift-diag' / 'app'
DIAG_NAMES = ['release_diag.py', 'a5_capture_diag.py', 'a5_recovery_diag.py',
              'a5_diag_assess.py', 'a5-rc2-d1-120.json', 'run-a5-rc2-d1-120.sh']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def text(path):
    return Path(path).read_text(encoding='utf-8')


def check(results, name, ok, detail=None):
    results[name] = {'ok': bool(ok), 'detail': detail}
    return bool(ok)


def function_text(source, name):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(source, node)
    return None


def ordered(body, parts):
    positions = [body.find(part) for part in parts]
    return all(pos >= 0 for pos in positions) and positions == sorted(positions)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path,
                    default=ROOT / 'results' / 'D1_120_PREFLIGHT_20261103')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()) and not args.force:
        raise SystemExit('Output exists; pass --force or another --out: ' + str(out))
    out.mkdir(parents=True, exist_ok=True)

    r = {}
    reg = read(VERSION_DIR / 'registration.json')
    config_path = APP / 'a5-rc2-d1-120.json'
    manifest_path = APP / 'a5-rc2-d1-120-files.json'
    config = read(config_path)
    manifest = read(manifest_path)
    base_manifest = read(APP / 'a5-manifest.json')
    candidate = read(APP / 'a5-candidate.json')
    runner = APP / 'run-a5-rc2-d1-120.sh'
    runner_text = text(runner)

    # 1. Identity and parent/base hashes.
    check(r, 'registration_present', (VERSION_DIR / 'registration.json').is_file()
          and (VERSION_DIR / 'static-audit.json').is_file())
    check(r, 'config_hash_matches_registration',
          sha(config_path) == reg['new_identity']['config_sha256'])
    check(r, 'manifest_hash_matches_registration',
          sha(manifest_path) == reg['new_identity']['manifest_sha256'])
    check(r, 'parent_config_hash',
          sha(PARENT_APP / 'a5-rc2-drift-diag-v1.json')
          == reg['parent_diagnostic']['config_sha256'])
    check(r, 'parent_manifest_hash',
          sha(PARENT_APP / 'a5-rc2-drift-diag-v1-files.json')
          == reg['parent_diagnostic']['manifest_sha256'])
    parent_sources_ok = all(
        sha(PARENT_APP / name) == want
        for name, want in reg['parent_diagnostic']['source_sha256'].items())
    check(r, 'parent_source_hashes', parent_sources_ok)
    check(r, 'base_candidate_hash',
          sha(APP / 'a5-candidate.json') == reg['base']['candidate_sha256'])
    check(r, 'base_manifest_hash',
          sha(APP / 'a5-manifest.json') == reg['base']['manifest_sha256'])
    check(r, 'initial_hashes_recorded',
          reg['initial']['hashes']['result.json']
          == '4472f4df6332a240da52b8c2ebaf7dd91f5f958e10a09803b64658699aea8adb'
          and reg['initial']['hashes']['initial_geometry.npz']
          == 'a6646d66bed8d00d046c2195c733f7f3aefc6471ca458995e247c11091e86106')

    # 2. Manifest content and verifiability.
    missing = []
    mismatch = []
    for name, want in manifest.items():
        p = APP / name
        if not p.is_file():
            missing.append(name)
        elif sha(p) != want:
            mismatch.append(name)
    base_keys = set(base_manifest)
    diag_keys = set(manifest) - base_keys
    check(r, 'manifest_entry_count', len(manifest) == 66, len(manifest))
    check(r, 'manifest_all_present', not missing, missing)
    check(r, 'manifest_all_hashes', not mismatch, mismatch)
    check(r, 'manifest_base_entries_60', len(base_manifest) == 60, len(base_manifest))
    check(r, 'manifest_base_hashes_match',
          all(manifest.get(k) == v for k, v in base_manifest.items()))
    check(r, 'manifest_diagnostic_entries_exact', diag_keys == set(DIAG_NAMES),
          sorted(diag_keys))
    check(r, 'manifest_no_self_entry', 'a5-rc2-d1-120-files.json' not in manifest)
    check(r, 'candidate_base_identity',
          candidate.get('version') == 'stage4-a5-rc2'
          and candidate.get('parent') == 'stage4-a5-rc1')

    # 3. Config scope and registration.
    delay = config.get('delay') or {}
    subject = config.get('subject') or {}
    check(r, 'config_version', config.get('version') == 'a5-rc2-d1-120')
    check(r, 'config_delay_120', delay.get('steps') == 120, delay.get('steps'))
    check(r, 'config_delay_internal',
          delay.get('counted_as_public_action') is False
          and delay.get('control_stage') == 'internal_delay')
    check(r, 'config_public_actions_12',
          config.get('public_actions') == 12
          or (config.get('delay') or {}).get('public_actions') == 12)
    check(r, 'config_scope_4202_single',
          subject.get('seed') == 4202 and subject.get('mode') == 'single'
          and subject.get('level') == 'perturbed')
    check(r, 'config_only_4202',
          'revalidation' not in config and '4302' not in json.dumps(config))
    check(r, 'config_flags',
          config.get('public_actions_unchanged') is True
          and config.get('action_targets_unchanged') is True
          and config.get('physics_step_count_changed') is True
          and config.get('diagnostic_only') is True
          and config.get('observation_only') is False)
    check(r, 'config_output_prefix',
          config.get('output_prefix') == 'day4-a5-rc2-d1-120-')
    check(r, 'registration_stage',
          reg.get('stage') == 'step2_step3_step4_implemented')
    check(r, 'registration_source_hashes',
          all(sha(APP / name) == want
              for name, want in reg['new_identity']['source_sha256'].items()))
    check(r, 'registration_test_hashes',
          all(sha(APP / name) == want
              for name, want in reg['new_identity']['test_sha256'].items()))

    # 4. Runner scope and entry identity.
    check(r, 'runner_manifest_name',
          'a5-rc2-d1-120-files.json' in runner_text)
    check(r, 'runner_config_name', 'a5-rc2-d1-120.json' in runner_text)
    check(r, 'runner_scope_rejection',
          '!= "4202"' in runner_text and '!= "single"' in runner_text)
    check(r, 'runner_entry_scripts',
          'a5_recovery_diag.py' in runner_text
          and 'a5_diag_assess.py' in runner_text)
    check(r, 'runner_preflight_args',
          '"$python_bin" - "$seed" "$mode" <<\'PY\'' in runner_text)
    check(r, 'runner_initial_resolution',
          'initial=$("$python_bin" - "$seed"' in runner_text
          and '--initial-dir "$initial"' in runner_text)
    check(r, 'runner_preflight_only_guard',
          'D1_PREFLIGHT_ONLY' in runner_text)

    # 5. Syntax and tests.
    syntax_ok = True
    syntax_errors = {}
    for name in ['release_diag.py', 'a5_capture_diag.py', 'a5_recovery_diag.py',
                 'a5_diag_assess.py', 'test_release_diag.py',
                 'test_d1_120_delay.py']:
        try:
            compile(text(APP / name), name, 'exec')
        except Exception as exc:
            syntax_ok = False
            syntax_errors[name] = repr(exc)
    check(r, 'python_syntax', syntax_ok, syntax_errors)
    bash = subprocess.run(['bash', '-n', str(runner)], capture_output=True, text=True)
    check(r, 'bash_syntax', bash.returncode == 0,
          (bash.stdout + bash.stderr).strip())

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    test_outputs = {}
    for name, expected in [('test_d1_120_delay.py', 'Ran 5 tests'),
                           ('test_release_diag.py', 'Ran 1 test')]:
        proc = subprocess.run([sys.executable, name], cwd=str(APP), env=env,
                              capture_output=True, text=True)
        test_outputs[name] = {'returncode': proc.returncode,
                              'stdout': proc.stdout[-3000:],
                              'stderr': proc.stderr[-3000:]}
        combined = proc.stdout + '\n' + proc.stderr
        check(r, 'fixture_' + name, proc.returncode == 0
              and expected in combined and 'OK' in combined)

    # 6. Insertion point and exact wait.
    capture = text(APP / 'a5_capture_diag.py')
    release = text(APP / 'release_diag.py')
    recovery = text(APP / 'a5_recovery_diag.py')
    assess = text(APP / 'a5_diag_assess.py')
    check(r, 'recovery_output_prefix', "day4-a5-rc2-d1-120-" in recovery)
    helper = function_text(capture, 'hold_open_for_steps') or ''
    measure = function_text(capture, 'measure_detachment') or ''
    ungrasp = function_text(capture, 'measure_ungrasp') or ''
    check(r, 'helper_loop_120',
          'for _ in range(steps):' in helper
          and 'world.step(render=True)' in helper
          and helper.find('for _ in range(steps):') < helper.find('world.step(render=True)'))
    check(r, 'helper_no_control_or_cloth_reset',
          all(token not in helper for token in
              ('control.robot_goto_position', 'robot.open(', 'robot.close(',
               '_set_garment_world_positions', '_clear_garment_velocities',
               'apply_action', 'backend.execute')))
    check(r, 'helper_rejects_wrong_steps',
          "if steps != 120:" in helper and "raise ValueError" in helper)
    check(r, 'registered_delay_reads_config',
          "config.get('delay')" in capture and "get('steps'" in capture)
    check(r, 'ungrasp_event_actual',
          ordered(ungrasp, ["original_ungrasp(*args, **kwargs)",
                            "record_event('ungrasp_return')"]))
    check(r, 'measure_event_order',
          ordered(measure, ["record_event('delay_begin')",
                            'hold_open_for_steps',
                            "record_event('delay_end')",
                            "record_event('retreat_begin')",
                            'original(*args',
                            "record_event('retreat_end')"]))
    check(r, 'measure_action_gate',
          "len(result.get('actions') or []) + 1 != 12" in measure
          and "sum(result.get('call_horizons') or []) != 12" in measure)
    check(r, 'events_emitted_once',
          all(capture.count("record_event('%s')" % name) == 1 for name in
              ('ungrasp_return', 'delay_begin', 'delay_end', 'retreat_begin', 'retreat_end')))
    check(r, 'capture_release_target_unchanged',
          'target = start_ee + [0., 0., .15]' in capture
          and 'release(target)' in capture)
    check(r, 'capture_install_scope',
          capture.count('control.ungrasp = measure_ungrasp') == 1
          and capture.count('control.ungrasp = original_ungrasp') == 1
          and capture.count('control.robot_goto_position = measure_detachment') == 1
          and capture.count('control.robot_goto_position = original') == 1)

    # 7. Recovery isolation.
    check(r, 'recovery_imports_diag_capture_once',
          recovery.count('from a5_capture_diag import release_window') == 1)
    check(r, 'recovery_release_window_once',
          recovery.count('release_window(b, evidence') == 1)
    check(r, 'recovery_has_no_delay',
          'hold_open_for_steps' not in recovery
          and 'delay_begin' not in recovery and 'delay_end' not in recovery)
    check(r, 'recovery_actions_present',
          "'rec_release'" in recovery and "'release_retreat'" in recovery)
    parent_recovery = text(PARENT_APP / 'a5_recovery_diag.py')
    pattern = ('action(', 'action_chunk(', 'fold_rows', 'fold_horizons', 'call_horizons')
    old_action_lines = [ln.strip() for ln in parent_recovery.splitlines()
                        if any(p in ln for p in pattern)]
    new_action_lines = [ln.strip() for ln in recovery.splitlines()
                        if any(p in ln for p in pattern)]
    check(r, 'recovery_action_lines_identical',
          old_action_lines == new_action_lines,
          {'old': len(old_action_lines), 'new': len(new_action_lines)})
    check(r, 'recovery_action_budget_checks',
          "if result['action_count'] != 12:" in recovery
          and "if sum(result['call_horizons']) != 12:" in recovery
          and "result['call_horizons'] = [1] * 7 + fold_horizons + [1]" in recovery)
    check(r, 'assessor_action_checks',
          "result.get('action_count') == 12" in assess
          and "sum(result.get('call_horizons') or []) == 12" in assess)

    # 8. Acquisition/event logic.
    check(r, 'release_required_events',
          "REQUIRED_EVENTS = ['ungrasp_return', 'delay_begin', 'delay_end'," in release
          and "'retreat_begin', 'retreat_end']" in release)
    check(r, 'release_event_paths',
          'release_diag_events.csv' in release
          and 'events_complete' in release and "self.emit('event'" in release)
    check(r, 'release_npz_keys',
          all(key in release for key in
              ('vertices=vertices', 'ee_m=ee', 'joint_positions=joints',
               'gripper_aperture_m=aperture', 'holding=', 'attached=',
               'enabled_slots=', 'sim_time_s=', 'observed_step=', 'phase=phases')))
    check(r, 'release_phase_labels',
          all(label in release for label in ('delay', 'retreat', 'released')))
    check(r, 'capture_internal_delay',
          "internal_delay=result.get('internal_delay')" in capture)
    check(r, 'recovery_diagnostic_fields',
          all(key in recovery for key in
              ("'diagnostic_only': True", "'observation_only': False",
               "'internal_delay': result.get('internal_delay')",
               "'public_actions_unchanged': True",
               "'action_targets_unchanged': True",
               "'physics_step_count_changed': True")))
    check(r, 'assessor_delay_event_checks',
          all(key in assess for key in
              ('internal_delay_registered', 'internal_delay_public_action',
               'internal_delay_no_control', 'internal_delay_no_cloth_reset',
               'release_diag_events', 'release_diag_event_steps',
               'release_diag_event_phases')))

    # 9. No result directory from this version yet.
    local_outputs = sorted(str(p) for p in ROOT.glob('day4-a5-rc2-d1-120-*'))
    check(r, 'no_local_d1_outputs', not local_outputs, local_outputs)

    all_ok = all(v['ok'] for v in r.values())
    payload = {
        'version': 'a5-rc2-d1-120',
        'created_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'scope': 'offline preflight only; no Isaac, no simulation, no held-out',
        'app': str(APP),
        'checks': r,
        'all_ok': all_ok,
        'hashes': {
            'config_sha256': sha(config_path),
            'manifest_sha256': sha(manifest_path),
            'registration_sha256': sha(VERSION_DIR / 'registration.json'),
        },
        'test_outputs': test_outputs,
    }
    (out / 'preflight.json').write_text(json.dumps(payload, indent=2) + '\n',
                                        encoding='utf-8')
    lines = ['D1_PREFLIGHT version=%s all_ok=%s checks=%d' %
             ('a5-rc2-d1-120', all_ok, len(r)),
             'config_sha256=%s' % payload['hashes']['config_sha256'],
             'manifest_sha256=%s' % payload['hashes']['manifest_sha256']]
    failed = []
    for name, value in r.items():
        lines.append('%s %s %s' % ('PASS' if value['ok'] else 'FAIL', name,
                                   '' if value['ok'] else json.dumps(value['detail'])))
        if not value['ok']:
            failed.append(name)
    lines.append('D1_PREFLIGHT_OK' if all_ok else 'D1_PREFLIGHT_FAIL ' + ','.join(failed))
    (out / 'preflight_stdout.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    return 0 if all_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
