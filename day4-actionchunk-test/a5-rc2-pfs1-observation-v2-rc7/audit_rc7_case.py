#!/usr/bin/env python3
"""Per-case evidence + observation-semantics audit for the rc7 seven-case RC.

Combines the original RC collection requirements (already checked by
a5_entry.assess) with the v2 observation semantics.  Task-aware: the L1 runner
has no recovery stage and no pre-release hold file.

Exit 0 when the case is complete and semantically valid (and the optional
single/arc4 pair matches); 5 otherwise.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

CENTROID_LIMIT_MM = 1.0
P95_LIMIT_MM = 3.0


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
    expected_actions = 7 if flat else 12
    expected_horizons = ([1, 1, 4, 1] if flat else [1] * 7 + [4, 1]) if args.mode == 'arc4' \
        else [1] * expected_actions

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
        mat_values = mat_values and close(friction, 0.3, 1e-5) and close(scale, 1.0, 1e-6)
        mat_binding = mat_binding and bool(pm_path) and pm_path in targets
        mat_self = mat_self and rec.get('self_collision_value') is True
        mat_nonparticle = mat_nonparticle and rec.get('non_particle_collision_value') is True
        mat_solver = mat_solver and 'unverified' in str(rec.get('solver_effective', ''))

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
    text = json.dumps(out, indent=2, allow_nan=False) + '\n'
    Path(args.out).write_text(text, encoding='utf-8')
    (d / 'rc7_semantics.json').write_text(text, encoding='utf-8')
    print('RC7_CASE_AUDIT', json.dumps({k: out[k] for k in
          ('seed', 'mode', 'file_complete', 'observation_semantics_valid', 'quality_status',
           'pair_pass', 'overall_valid')}, sort_keys=True), flush=True)
    return 0 if out['overall_valid'] else 5


if __name__ == '__main__':
    sys.exit(main())
