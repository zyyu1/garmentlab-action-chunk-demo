#!/usr/bin/env python3
"""Offline A1 preflight for the b-right-dev-v2 development coverage batch.

Checks, without starting Isaac or any GPU workload:

  * the frozen hashes of the v2 config, variant manifest, entry, batch driver,
    base manifest, initial-state manifest/runner/script and initial plan;
  * all 21 base entries and all 23 variant entries resolve locally and match
    either their raw bytes or their LF-normalised bytes;
  * the registered seed matrix, fold edge, width, overhang, execution modes,
    action count and held-out exclusion;
  * the fold-episode sampling code really is OPEN + 30 release ticks +
    settle(180) for both levels, with settle(240) only after recovery;
  * the initial plan contains the 18 A2/A3 seeds with the registered levels,
    settles and strips;
  * B/C additions are not part of the registered 21/23-item identity and are
    not imported by the registered runner.

The script is read-only.  It never upgrades a development result to formal
Stage 4 success.

Usage:
  python -I stage4_a1_right_v2_preflight.py [--root .] [--out preflight.json]
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# A1-frozen identities (2026-11-02, after the v2.1 sampling-description fix).
FROZEN = {
    'stage4-b-right-dev-v2.json':
        '91c0fe7f12cf28cdab1a62d4d1a4b9a63c2418857744f0b0f7711b7cf095bff5',
    'square-recovery-fold-right-v2-files.json':
        'c3e34c9149d75c56932873b4705ee996b808f61348ca0e700d3d49a505deff97',
    'run-recovery-fold-right-v2.sh':
        '3822bd98d3d05bc6cba3880ba756f3a438a6985b6abc19c19259a67b47091af3',
    'run-stage4-b-right-dev-v2-batch.sh':
        'd4c0016202949a45ec6ff8a4edca746581f95832c5d528534c1be6f144231142',
    'square-recovery-fold-files.json':
        'cb947b85c4d5acdaf2028cfcbde8eb3743158d3868e9ca082e85994beadb73b1',
    'square-initial-stripfold-files.json':
        '70b1793b5a87f69e9a4cbde5f6b40b047120eed798bdd895dee27e33072477f0',
    'run-square-initial-stripfold.sh':
        '1116550f65b9282c2a0e85f321c9ceb863cf8f1fe152c36bc48e387ebc34b631',
    'day4-square-initial-stripfold.py':
        '178ab10c08511b6dbb2ec1fd4581ab5af2493ee6a1ca7577ac49b575b913dcc6',
}
PLAN_LF_SHA256 = '32e61d575d77eae0943cb2251d10c25b12d7f0d9f8f962ddd96dc1a4d4d2ab85'
EXPECTED_V2_SEEDS = list(range(4201, 4210)) + list(range(4301, 4310))
EXPECTED_LEVEL = {**{s: 'perturbed' for s in range(4201, 4210)},
                  **{s: 'crumpled' for s in range(4301, 4310)}}
HELDOUT = set(range(4210, 4230)) | set(range(4310, 4330))
FORBIDDEN_IN_IDENTITY = ('episode_evidence.py', 'stage4_success_v1.py',
                         'stage4-success-v1.json', 'day4-c-')


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def resolve(root, key):
    p = Path(key)
    if p.is_absolute():
        return p if p.exists() else None
    local = root / key
    if local.exists():
        return local
    if key.startswith('garmentlab-action-chunk-demo/'):
        local = root.parent / key.split('/', 1)[1]
        if local.exists():
            return local
    return None


def hash_mode(path, want):
    raw = sha256_file(path)
    lf = sha256_bytes(Path(path).read_bytes().replace(b'\r\n', b'\n'))
    if raw == want:
        return 'raw'
    if lf == want:
        return 'lf'
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(Path(__file__).resolve().parent))
    ap.add_argument('--out')
    args = ap.parse_args()
    root = Path(args.root).resolve()

    checks = []
    notes = []

    def check(name, ok, detail=''):
        checks.append({'name': name, 'ok': bool(ok), 'detail': str(detail)})
        return bool(ok)

    def load(name):
        return json.loads((root / name).read_text())

    # ---- frozen file hashes ------------------------------------------------
    frozen = {}
    for name, want in FROZEN.items():
        p = root / name
        mode = hash_mode(p, want) if p.exists() else None
        frozen[name] = {'sha256': sha256_file(p) if p.exists() else None,
                        'expected': want, 'mode': mode}
        check('frozen_hash:' + name, mode is not None,
              'missing' if not p.exists() else (mode or 'mismatch'))

    # ---- manifest structure ------------------------------------------------
    base = load('square-recovery-fold-files.json')
    variant = load('square-recovery-fold-right-v2-files.json')
    config = load('stage4-b-right-dev-v2.json')
    check('variant_manifest_entries', len(variant) == 23, len(variant))
    check('base_manifest_entries', len(base) == 21, len(base))
    check('variant_manifest_set',
          set(variant) == set(base) | {'run-recovery-fold-right-v2.sh',
                                       'stage4-b-right-dev-v2.json'},
          sorted(set(variant) ^ (set(base) | {'run-recovery-fold-right-v2.sh',
                                              'stage4-b-right-dev-v2.json'})))
    check('base_values_identical',
          all(variant[k] == v for k, v in base.items()), '')
    check('config_hash_in_manifest',
          variant.get('stage4-b-right-dev-v2.json') == frozen[
              'stage4-b-right-dev-v2.json']['sha256'], '')
    check('base_manifest_hash_in_config',
          sha256_file(root / 'square-recovery-fold-files.json') ==
          config.get('base_manifest_sha256'), '')

    entry_modes = {}
    entry_bad = []
    for name, want in variant.items():
        p = resolve(root, name)
        if p is None:
            entry_bad.append((name, 'missing'))
            continue
        mode = hash_mode(p, want)
        entry_modes[mode] = entry_modes.get(mode, 0) + 1
        if mode is None:
            entry_bad.append((name, 'mismatch'))
    check('variant_entries_resolve_and_match', not entry_bad, entry_bad)
    notes.append('variant entry hash modes: ' + json.dumps(entry_modes, sort_keys=True))

    # ---- config registration ----------------------------------------------
    check('config_variant_id', config.get('variant_id') == 'b-right-dev-v2',
          config.get('variant_id'))
    check('config_fold_edge_right', config.get('fold_edge') == 'right',
          config.get('fold_edge'))
    check('config_width', config.get('fold_width_m') == 0.2, config.get('fold_width_m'))
    check('config_overhang_zero', config.get('overhang_m') == 0.0,
          config.get('overhang_m'))
    check('config_execution_single', config.get('execution_modes') == ['single'],
          config.get('execution_modes'))
    check('config_action_count_12', config.get('public_action_count') == 12,
          config.get('public_action_count'))
    cases = {int(c['seed']): c['level'] for c in config.get('development_cases', [])}
    check('config_seed_matrix', cases == EXPECTED_LEVEL,
          sorted(set(cases) ^ set(EXPECTED_LEVEL)))
    check('config_attempt_order',
          config.get('attempt_order') == [[s, 'single'] for s in EXPECTED_V2_SEEDS],
          '')
    check('config_no_heldout', not (set(cases) & HELDOUT), sorted(set(cases) & HELDOUT))
    check('config_development_only',
          config.get('development_only') is True
          and config.get('formal_stage4_success') is False,
          f"{config.get('development_only')}/{config.get('formal_stage4_success')}")
    sampling = str(config.get('sampling', ''))
    check('config_sampling_text',
          '30 release ticks' in sampling and 'settle(180)' in sampling
          and 'for both levels' in sampling and '240 for crumpled' not in sampling,
          sampling)
    check('config_registry_name',
          config.get('initial_registry') == 'stage4-b-right-dev-v2-initials.json',
          config.get('initial_registry'))

    # ---- initial plan and initial generator -------------------------------
    plan = load('square-initial-plan.json')
    rows = {int(e['seed']): e for e in plan.get('episodes', [])}
    plan_ok = True
    for seed in EXPECTED_V2_SEEDS:
        e = rows.get(seed)
        if e is None:
            plan_ok = False
            continue
        expected_settle = 180 if seed < 4300 else 240
        strips = e.get('strips') or []
        expected_edge = 'bottom' if seed < 4300 else 'left'
        expected_width = 0.2 if seed >= 4300 else None
        ok = (e.get('level') == EXPECTED_LEVEL[seed]
              and int(e.get('settle_steps', -1)) == expected_settle
              and len(strips) == 1 and strips[0].get('edge') == expected_edge
              and (expected_width is None
                   or float(strips[0].get('width_m', -1)) == expected_width))
        if not ok:
            plan_ok = False
    check('initial_plan_a2_a3_entries', plan_ok, '18 seeds')
    check('initial_plan_totals',
          len(plan.get('episodes', [])) == 90
          and {l: sum(1 for e in plan['episodes'] if e['level'] == l)
               for l in ('flat', 'perturbed', 'crumpled')}
          == {'flat': 30, 'perturbed': 30, 'crumpled': 30},
          len(plan.get('episodes', [])))
    plan_lf = sha256_bytes((root / 'square-initial-plan.json').read_bytes()
                           .replace(b'\r\n', b'\n'))
    check('initial_plan_lf_hash', plan_lf == PLAN_LF_SHA256, plan_lf[:12])
    init_manifest = load('square-initial-stripfold-files.json')
    init_bad = []
    for name, want in init_manifest.items():
        p = resolve(root, name)
        if p is None or hash_mode(p, want) is None:
            init_bad.append((name, 'missing' if p is None else 'mismatch'))
    check('initial_manifest_entries', not init_bad, init_bad)
    initial_runner = (root / 'run-square-initial-stripfold.sh').read_text()
    check('initial_runner_seed_ranges',
          '4200<=seed<=4229' in initial_runner and '4300<=seed<=4329' in initial_runner,
          '')

    # ---- sampling source ---------------------------------------------------
    runner = (root / 'day4-recovery-fold-episode.py').read_text()
    rec_rel = runner.find("'rec_release'")
    rec_settle = runner.find('b._settle(240)', rec_rel)
    fold_rel = runner.find("'fold_release'")
    ticks = runner.find('for _ in range(30):', fold_rel)
    final_settle = runner.find('b._settle(180)', ticks)
    between = runner[fold_rel:final_settle] if fold_rel >= 0 and final_settle >= 0 else ''
    check('sampling_recovery_240',
          rec_rel >= 0 and rec_settle > rec_rel and rec_settle < fold_rel,
          f'{rec_rel}/{rec_settle}/{fold_rel}')
    check('sampling_release_30_then_180',
          fold_rel >= 0 and ticks > fold_rel and final_settle > ticks,
          f'{fold_rel}/{ticks}/{final_settle}')
    check('sampling_no_240_after_release', 'b._settle(240)' not in between, '')
    check('sampling_fold_width', 'fold_width = .2' in runner, '')
    check('sampling_right_lateral',
          "np.array([1. if args.fold_edge == 'left' else -1., 0., 0.])" in runner, '')
    check('sampling_action_count',
          "if result['action_count'] != 12:" in runner
          and "if sum(result['call_horizons']) != 12:" in runner, '')
    check('runner_no_b_c_integration',
          not any(x in runner for x in ('episode_evidence', 'stage4_success_v1',
                                        'day4-c-', 'success_trace')),
          '')

    # ---- entry and driver text -------------------------------------------
    entry = (root / 'run-recovery-fold-right-v2.sh').read_text()
    check('entry_registry_only',
          'Only initial directories recorded by the v2 batch driver are allowed' in entry,
          '')
    check('entry_initial_hashes',
          "for name,digest in row['files'].items():" in entry, '')
    check('entry_base_manifest',
          "config['base_manifest_sha256']" in entry, '')
    check('entry_right_and_12',
          'run-recovery-fold-episode.sh "$initial_dir" right' in entry
          and "r['fold_edge']=='right'" in entry
          and "r['action_count']==12" in entry, '')
    driver = (root / 'run-stage4-b-right-dev-v2-batch.sh').read_text()
    check('driver_registry_flow',
          all(x in driver for x in ('registry_append', 'registry_lookup',
                                    'already_done', 'attempts.jsonl')),
          '')
    check('driver_single_only', 'RECOVERY_FOLD_EXECUTION=single' in driver, '')
    check('driver_abort_on_infrastructure',
          'BATCH_ABORT no result directory' in driver
          and 'BATCH_ABORT initial state' in driver, '')

    # ---- B/C isolation ----------------------------------------------------
    identity_names = set(variant)
    forbidden = [n for n in identity_names if any(x in n for x in FORBIDDEN_IN_IDENTITY)]
    check('identity_excludes_b_c', not forbidden, forbidden)
    notes.append('B/C files exist outside the 21/23-item identity; the registered '
                 'runner imports none of them.')

    # ---- initial registry -------------------------------------------------
    reg_path = root / config.get('initial_registry', '')
    registry = {'present': reg_path.exists(), 'path': str(reg_path)}
    if reg_path.exists():
        doc = json.loads(reg_path.read_text())
        rows_reg = {int(r['seed']): r for r in doc.get('seeds', [])}
        registry['rows'] = len(rows_reg)
        reg_ok = (set(rows_reg) <= set(EXPECTED_V2_SEEDS)
                  and all(set(r.get('files', {})) == {'result.json', 'initial_geometry.npz'}
                          for r in rows_reg.values()))
        reg_bad = []
        for seed, row in rows_reg.items():
            idir = Path(row.get('initial_dir', ''))
            if idir.exists():
                for name, want in row.get('files', {}).items():
                    p = idir / name
                    if not p.exists() or sha256_file(p) != want:
                        reg_bad.append((seed, name))
            elif not idir.is_absolute():
                reg_bad.append((seed, 'non-absolute initial_dir'))
        registry['bad'] = reg_bad
        check('initial_registry_schema', reg_ok, registry)
        check('initial_registry_hashes', not reg_bad, reg_bad)
    else:
        notes.append('initial registry is remote-only and absent locally; A2 will '
                     'create it before the first fold.')
        check('initial_registry_absent_expected', True, 'A2 creates it')

    # ---- output -----------------------------------------------------------
    failed = [c for c in checks if not c['ok']]
    doc = {
        'a1': 'b-right-dev-v2',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'root': str(root),
        'ok': not failed,
        'checks': len(checks),
        'failed': len(failed),
        'failed_names': [c['name'] for c in failed],
        'frozen': frozen,
        'variant_entry_modes': entry_modes,
        'config': {
            'variant_id': config.get('variant_id'),
            'revision': config.get('revision'),
            'revised_utc': config.get('revised_utc'),
            'fold_edge': config.get('fold_edge'),
            'width_m': config.get('fold_width_m'),
            'overhang_m': config.get('overhang_m'),
            'execution_modes': config.get('execution_modes'),
            'public_action_count': config.get('public_action_count'),
            'seed_matrix': {str(k): v for k, v in sorted(cases.items())},
            'sampling': sampling,
        },
        'initial_plan': {
            'episodes': len(plan.get('episodes', [])),
            'a2_a3_entries': len([s for s in EXPECTED_V2_SEEDS if s in rows]),
            'plan_lf_sha256': plan_lf,
        },
        'initial_registry': registry,
        'notes': notes,
        'checks_detail': checks,
    }
    for c in checks:
        print(('PASS ' if c['ok'] else 'FAIL ') + c['name'] +
              ((' | ' + c['detail']) if c['detail'] else ''))
    print()
    print('A1_PREFLIGHT_' + ('OK' if doc['ok'] else 'FAILED') +
          f" checks={doc['checks']} failed={doc['failed']}")
    if failed:
        print('FAILED_NAMES ' + json.dumps(doc['failed_names']))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, indent=2) + '\n')
        print('A1_PREFLIGHT_JSON', out)
    return 0 if doc['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
