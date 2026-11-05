#!/usr/bin/env python3
"""Per-case evidence + observation-semantics audit for recovery-hold120.

Combines the original RC collection requirements with the v2 observation
semantics, the task-scoped initial protocol, and the 120-step recovery-hold
trace/event checks.  `check_output_contract` protects the printed projection
from missing keys.

Exit 0 when the case is complete and semantically valid; 5 otherwise.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import hold_contract

CENTROID_LIMIT_MM = 1.0
P95_LIMIT_MM = 3.0
REQUIRED_OUT_KEYS = ('seed', 'mode', 'level', 'recovery_hold', 'hold_applicable', 'file_complete',
                     'observation_semantics_valid', 'quality_status', 'overall_valid')


def check_output_contract(out):
    """Fail before printing if the audit output projection is incomplete."""
    missing = [k for k in REQUIRED_OUT_KEYS if k not in out]
    if missing:
        raise KeyError('audit output contract missing keys: ' + repr(missing))
    if not isinstance(out['recovery_hold'], bool):
        raise TypeError('recovery_hold must be bool in audit output')
    return True

APP = Path(__file__).resolve().parent / 'app'
INITIAL_SPEC = {
    'flat': (0.0, 'A_l1_overfold', 'day4-square-initial.py', 'square-initial-files.json'),
    'perturbed': (1.0, 'B_nominal', 'day4-square-initial-stripfold.py',
                  'square-initial-stripfold-files.json'),
    'crumpled': (1.0, 'B_nominal', 'day4-square-initial-stripfold.py',
                 'square-initial-stripfold-files.json'),
}


def read(p, default=None):
    p = Path(p)
    if not p.is_file():
        return default
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def call_value(x):
    if isinstance(x, dict) and x.get('ok') is True:
        return x.get('value')
    return None


def close(a, b, tol):
    return isinstance(a, (int, float)) and abs(float(a) - b) <= tol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--mode', choices=('single', 'arc4'), required=True)
    ap.add_argument('--single-dir', type=Path, default=None)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    d = args.run.resolve()
    result = read(d / 'result.json', {}) or {}
    case = result.get('initial_case') or {}
    level = case.get('level')
    flat = level == 'flat'
    expected_scale, expected_task, initial_script, initial_files = INITIAL_SPEC[level]
    init_result = read(Path(result.get('initial_dir', '')) / 'result.json', {}) or {}
    init_proto = init_result.get('protocol') or {}
    init_binding = init_proto.get('material_binding') or {}
    init_gen = init_proto.get('generator') or {}
    initial_protocol_ok = bool(
        init_proto.get('version') == 'stage4-initial-v2-task-scoped'
        and (init_proto.get('task'), init_proto.get('level'), init_proto.get('seed'))
        == (expected_task, level, args.seed)
        and abs(float(init_proto.get('particle_friction_scale_expected', -1)) - expected_scale) <= 1e-6
        and abs(float(init_proto.get('particle_friction_scale_readback', -1)) - expected_scale) <= 1e-6
        and init_binding.get('particle_material') == '/World/Garment/particleMaterial'
        and bool(init_binding.get('particle_system'))
        and init_gen.get('script') == initial_script
        and init_gen.get('script_sha256') == sha(APP / initial_script)
        and init_gen.get('files_manifest') == initial_files
        and init_gen.get('files_manifest_sha256') == sha(APP / initial_files)
    )
    expected_actions = 7 if flat else 12
    expected_horizons = ([1, 1, 4, 1] if flat else [1] * 7 + [4, 1]) if args.mode == 'arc4' \
        else [1] * expected_actions

    import numpy as np
    hold = result.get('recovery_hold') or {}
    events = {e.get('name'): e for e in (result.get('events') or [])}
    trace_path = d / 'recovery_hold_trace.npz'
    hold_applicable = not flat
    hold_ok = False
    if flat:
        hold_ok = bool('recovery_hold' not in result and not trace_path.exists())
    elif trace_path.is_file() and hold:
        with np.load(trace_path, allow_pickle=False) as z:
            V = np.asarray(z['vertices'], float)
            fd = np.asarray(z['fd_velocities'], float)
            dt = np.asarray(z['fd_interval_s'], float)
            steps = np.asarray(z['absolute_step'], int)
            times = np.asarray(z['sim_time_s'], float)
            target = np.asarray(z['control_target'], float)
            holding = np.asarray(z['holding'], bool)
            attached = np.asarray(z['logical_attached'], bool)
            command = np.asarray(z['command_holding'], bool)
            enabled_any = np.asarray(z['attachment_enabled_any'], bool)
            enabled = np.asarray(z['enabled_slots'], bool)
        hold_ok = bool(
            hold.get('schema') == 'recovery-hold-v1'
            and int(hold.get('steps_requested', 0)) == 120
            and int(hold.get('completed_steps', 0)) == 120
            and int(hold.get('frames', 0)) == 121
            and abs(float(hold.get('dt_s', 0)) - 1 / 60) <= 1e-12
            and abs(float(hold.get('duration_s', 0)) - 2.0) <= 1e-6
            and hold.get('error') is None
            and bool(hold.get('checks', {}).get('all_frames_ok'))
            and bool(hold.get('checks', {}).get('all_time_ok'))
            and V.shape == (121, 441, 3)
            and fd.shape == (120, 441, 3)
            and dt.shape == (120,)
            and times.shape == (121,) and steps.shape == (121,)
            and np.all(np.isfinite(V)) and np.all(np.isfinite(fd))
            and np.all(dt > 0)
            and np.allclose(dt, 1 / 60, atol=1e-6, rtol=0)
            and np.all(np.diff(steps) == 1)
            and np.allclose(np.diff(times), 1 / 60, atol=1e-6, rtol=0)
            and not holding.any() and not attached.any()
            and not command.any() and not enabled_any.any()
            and not enabled.any()
            and np.array_equal(target, np.repeat(target[:1], 121, axis=0))
            and abs(float(target[0][0] - result['actions'][4]['target_pose'][0])) <= 1e-9
            and abs(float(target[0][1] - result['actions'][4]['target_pose'][1])) <= 1e-9
            and abs(float(target[0][2] - result['actions'][4]['target_pose'][2])) <= 1e-9
            and result['actions'][4]['label'] == 'rec_release'
            and len(result['actions']) == 12
            and all(k in events for k in ('recovery_retreat_end', 'recovery_hold_begin',
                                          'recovery_hold_end', 'fold_observation'))
            and int(events['recovery_hold_end']['step']) - int(events['recovery_hold_begin']['step']) == 120
            and abs(float(events['recovery_hold_end']['sim_time_s'])
                    - float(events['recovery_hold_begin']['sim_time_s']) - 2.0) <= 1e-6
            and int(events['fold_observation']['step']) == int(events['recovery_hold_end']['step'])
            and int(events['recovery_retreat_end']['step']) <= int(events['recovery_hold_begin']['step']))
        try:
            trace_data = None
            if trace_path.is_file():
                with np.load(trace_path, allow_pickle=False) as z:
                    trace_data = {k: z[k].copy() for k in z.files}
            c_ok, c_app, c_err = hold_contract.evaluate(
                level, result, trace_path.is_file(), trace_data)
            hold_ok = bool(hold_ok and c_ok)
            hold_applicable = bool(c_app)
        except Exception:
            hold_ok = False
        if hold_ok and hold_applicable:
            stage = np.load(d / 'pfs1_stages' / 'after_recovery.npz')
            hold_ok = bool(abs(float(stage['sim_time_s']) - float(events['recovery_hold_end']['sim_time_s'])) <= 1e-6)

    common = [
        'result.json', 'a5-verdict.json', 'success_trace.npz', 'success_meta.json', 'final.png',
        'final.npz', 'pfs1_stage_index.json',
        'pfs1_release_steps.npz', 'pfs1_release_steps.json',
        'pfs1_first_0_5s.npz', 'pfs1_first_0_5s.json',
        'pfs1_formal_210_330.npz', 'pfs1_formal_210_330.json',
        'pfs1_release_clock.json', 'material_readbacks.json',
        'contact_capability.json', 'evidence/summary.json',
        'evidence/timeline.jsonl', 'evidence/manifest.json',
    ]
    required = list(common) + ([] if flat else ['pre_release_hold.npz', 'recovered.npz'])
    presence = {name: (d / name).is_file() for name in required}
    file_complete = all(presence.values())

    stage_index = read(d / 'pfs1_stage_index.json', []) or []
    labels = [x.get('label') for x in stage_index if isinstance(x, dict)]
    required_stages = ['initial_loaded', 'pre_release', 'release_boundary'] + \
                      ([] if flat else ['after_recovery'])
    stage_files_ok = all((d / 'pfs1_stages' / (label + '.npz')).is_file() for label in required_stages)
    file_complete = bool(file_complete and stage_files_ok)

    evidence = read(d / 'evidence' / 'manifest.json', {}) or {}
    evidence_bad = []
    for name, want in evidence.items():
        p = d / 'evidence' / name
        if not p.is_file():
            evidence_bad.append((name, 'missing'))
        elif sha(p) != want:
            evidence_bad.append((name, 'mismatch'))

    verdict = read(d / 'a5-verdict.json', {}) or {}
    criteria = verdict.get('criteria') or {}
    status = criteria.get('status')
    checks = criteria.get('checks') or {}
    stability = criteria.get('stability') or {}
    evidence_checks = verdict.get('evidence_checks') or {}

    release_meta = read(d / 'pfs1_release_steps.json', {}) or {}
    first_meta = read(d / 'pfs1_first_0_5s.json', {}) or {}
    formal_meta = read(d / 'pfs1_formal_210_330.json', {}) or {}
    fd_policy_ok = all(isinstance(m.get('fd_method'), str) and m.get('fd_method')
                       and isinstance(m.get('fd_time_source'), str) and m.get('fd_time_source')
                       for m in (release_meta, first_meta, formal_meta))
    fd_valid = int(release_meta.get('fd_velocity_valid_count') or 0) > 0
    raw_unvalidated = (release_meta.get('readback_velocity_validated') is False
                       and all(x.get('readback_velocity_validated') is False
                               for x in stage_index if isinstance(x, dict)))

    mat = read(d / 'material_readbacks.json', {}) or {}
    stages = mat.get('stages') or {}
    expected_scale = 0.0 if flat else 1.0
    mat_required = ['after_construction', 'after_reset', 'after_initial_settle', 'pre_release'] + \
                   ([] if flat else ['after_recovery'])
    mat_present = all(x in stages for x in mat_required)
    mat_values = mat_binding = mat_self = mat_nonparticle = mat_solver = True
    for label in mat_required:
        if label == 'after_construction':
            continue
        rec = stages.get(label) or {}
        if not isinstance(rec, dict):
            mat_values = False
            continue
        pm = rec.get('particle_material') or {}
        friction = call_value(pm.get('friction'))
        scale = call_value(pm.get('particle_friction_scale'))
        pm_path = pm.get('prim_path')
        targets = rec.get('binding_targets') or []
        mat_values = mat_values and close(friction, 0.3, 1e-5) and close(scale, expected_scale, 1e-6)
        mat_binding = mat_binding and bool(pm_path) and pm_path in targets
        mat_self = mat_self and rec.get('self_collision_value') is True
        mat_nonparticle = mat_nonparticle and rec.get('non_particle_collision_value') is True
        mat_solver = mat_solver and 'unverified' in str(rec.get('solver_effective', ''))
    mat_expected_block = close((mat.get('expected') or {}).get('particle_friction_scale'),
                               expected_scale, 1e-9)

    contact = read(d / 'contact_capability.json', {}) or {}
    contact_ok = (contact.get('cloth_ground_force_impulse') is False
                  and contact.get('required_for_acceptance') is False
                  and bool(contact.get('reason')))
    clock = read(d / 'pfs1_release_clock.json', {}) or {}
    clock_ok = (isinstance(clock, dict) and bool(clock.get('t0_definition'))
                and isinstance(clock.get('sampling_error_steps'), int)
                and (clock.get('release_boundary') or {}).get('attachment_enabled_any') is False)

    budget_ok = (result.get('action_count') == expected_actions
                 and result.get('call_horizons') == expected_horizons)
    identity_ok = (case.get('seed') == args.seed and result.get('execution_mode') == args.mode)
    stability_mm = {
        'centroid_mm': float(stability.get('centroid_drift_max_m', float('nan')) * 1000),
        'vertex_p95_mm': float(stability.get('vertex_drift_p95_max_m', float('nan')) * 1000),
    }
    stability_ok = (stability_mm['centroid_mm'] <= CENTROID_LIMIT_MM
                    and stability_mm['vertex_p95_mm'] <= P95_LIMIT_MM)

    semantics = {
        'fd_policy_recorded': bool(fd_policy_ok),
        'fd_velocity_valid_present': bool(fd_valid),
        'raw_readback_marked_unvalidated': bool(raw_unvalidated),
        'material_stages_present': bool(mat_present),
        'material_values_match': bool(mat_values),
        'material_expected_block': bool(mat_expected_block),
        'material_binding_match': bool(mat_binding),
        'self_collision_true': bool(mat_self),
        'non_particle_collision_true': bool(mat_nonparticle),
        'solver_effective_boundary_recorded': bool(mat_solver),
        'contact_capability_recorded': bool(contact_ok),
        'release_clock_boundary_recorded': bool(clock_ok),
        'quality_status_recorded': status in ('accepted', 'rejected'),
        'action_budget_and_horizons': bool(budget_ok),
        'case_identity': bool(identity_ok),
        'original_rc_evidence_checks': bool(evidence_checks and all(evidence_checks.values())),
        'initial_protocol': bool(initial_protocol_ok),
        'recovery_hold': bool(hold_ok),
    }
    observation_semantics_valid = all(semantics.values())

    pair = None
    pair_ok = True
    if args.single_dir is not None:
        single = read(args.single_dir / 'result.json', {}) or {}
        a = single.get('actions') or []
        b = result.get('actions') or []
        target_max = 0.0
        labels_equal = commands_equal = True
        n = min(len(a), len(b))
        for k in range(n):
            labels_equal &= a[k].get('label') == b[k].get('label')
            commands_equal &= int(a[k].get('command', -1)) == int(b[k].get('command', -2))
            x = a[k].get('target_pose')
            y = b[k].get('target_pose')
            if x is None or y is None:
                pair_ok = False
                continue
            diff = max(abs(float(u) - float(v)) for u, v in zip(x, y))
            target_max = max(target_max, diff)
        pair_ok = bool(pair_ok and labels_equal and commands_equal and n == expected_actions
                       and target_max <= 1e-6)
        pair = {
            'single_dir': str(args.single_dir),
            'actions': n,
            'labels_identical': bool(labels_equal),
            'commands_identical': bool(commands_equal),
            'target_max_abs_m': float(target_max),
            'target_atol': 1e-6,
            'pass': bool(pair_ok),
        }

    out = {
        'seed': args.seed,
        'mode': args.mode,
        'level': level,
        'task_protocol_expected_scale': expected_scale,
        'initial_protocol': bool(initial_protocol_ok),
        'recovery_hold': bool(hold_ok),
        'hold_applicable': bool(hold_applicable),
        'initial_dir': result.get('initial_dir'),
        'expected_actions': expected_actions,
        'expected_horizons': expected_horizons,
        'file_complete': bool(file_complete),
        'presence': presence,
        'required_stages': required_stages,
        'stage_labels': labels,
        'evidence_manifest_entries': len(evidence),
        'evidence_bad': evidence_bad,
        'quality_status': status,
        'evaluator_checks': checks,
        'stability': stability,
        'stability_mm': stability_mm,
        'stability_within_limits': bool(stability_ok),
        'semantic_checks': semantics,
        'observation_semantics_valid': bool(observation_semantics_valid),
        'pair': pair,
        'pair_pass': bool(pair_ok),
        'overall_valid': bool(file_complete and observation_semantics_valid and pair_ok
                              and not evidence_bad),
    }
    check_output_contract(out)
    text = json.dumps(out, indent=2, allow_nan=False) + '\n'
    Path(args.out).write_text(text, encoding='utf-8')
    (d / 'hold120_semantics.json').write_text(text, encoding='utf-8')
    print('HOLD120RC7_CASE_AUDIT', json.dumps({k: out[k] for k in
          ('seed', 'mode', 'task_protocol_expected_scale', 'initial_protocol', 'recovery_hold',
           'hold_applicable', 'file_complete', 'observation_semantics_valid', 'quality_status',
           'pair_pass', 'overall_valid')},
          sort_keys=True), flush=True)
    return 0 if out['overall_valid'] else 5


if __name__ == '__main__':
    sys.exit(main())
