"""Source-inherited freeze for the hold120 rc7 seven-case development RC.

slot1 is evaluated against the parent manifest 41db790f; slots2-7 against the
revised manifest 40858efc.  The tool reruns the seven-case audit/evaluator and
creates verified-dev.json/E_RELEASE.json with exclusive creates.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/root/autodl-tmp')
CAND = Path(__file__).resolve().parent
APP = CAND / 'app'
PARENT = CAND / 'parent-rc7-manifest.json'
PARENT_APP = ROOT / 'a5-rc8b-recovery-hold120-rc7/app'
ORIG = ROOT / 'a5-rc8b-recovery-hold120-rc7-runs'
RESUME = ROOT / 'a5-rc8b-recovery-hold120-rc7-r2-resume'
VERIFY_MANIFEST = CAND / 'verification-manifest.json'
VERIFIED = CAND / 'verified-dev.json'
RELEASE = CAND / 'E_RELEASE.json'
PARENT_SHA = '41db790f256396e07df079e511090d14a9852c1f55197afa36ea847a9403c2df'
sys.path.insert(0, str(APP))


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save_new(p, data):
    with Path(p).open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.flush()


def load_jsonl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def assess_case(directory, manifest, manifest_sha):
    import numpy as np
    from audit_episode_evidence import audit
    from stage4_success_v1 import evaluate
    policy = read(APP / 'a5-candidate.json')
    result = read(directory / 'result.json')
    case = result['initial_case']
    spec = policy['tasks'][case['level']]
    expected = spec['actions']
    mode = result['execution_mode']
    horizons = [1] * expected if mode == 'single' else [1] * (expected - 5) + [4, 1]
    out = dict(protocol='stage4-a5-rc2', seed=case['seed'], level=case['level'], mode=mode,
               development_pass=result['passed'], errors=result['errors'],
               manifest_sha256=manifest_sha, status='incomplete', success=None)
    if not all((directory / name).is_file() for name in
               ('success_trace.npz', 'success_meta.json', 'evidence/summary.json')):
        return out
    meta = read(directory / 'success_meta.json')
    with np.load(directory / 'success_trace.npz', allow_pickle=False) as z:
        data = dict(z)
    quality = evaluate(meta, data)
    capture = audit(directory / 'evidence')
    summary = read(directory / 'evidence/summary.json')
    samples = summary['samples']
    timeline = [json.loads(l) for l in (directory / 'evidence/timeline.jsonl').read_text().splitlines()]
    calls = [r for r in timeline if r['kind'] == 'action_begin']
    end = [r for r in timeline if r['kind'] == 'action_end']
    labels = [a['label'] for a in result['actions']]
    target = np.array(calls[-1]['targets'][0][:3])
    released = samples['released']
    retreated = samples['retreated']
    start_time = meta['sim_time_s']
    inputs = Path(result['initial_dir'])
    checks = dict(
        video_and_samples=capture['evidence_complete'],
        actual_sim=summary['synthetic'] is False,
        source=result['code_files'] == manifest and meta['manifest_sha256'] == manifest_sha,
        input_hashes=all(sha(inputs / n) == meta['initial_hashes'][n]
                         for n in ('result.json', 'initial_geometry.npz')),
        identity=(meta['task'], meta['edge'], meta['seed'], meta['level'], meta['execution_mode']) ==
                 (spec['task'], spec['edge'], case['seed'], case['level'], mode),
        actual_budget=capture['attempted_public_actions'] == result['action_count'] == meta['action_count'] == expected,
        horizons=[r['horizon'] for r in calls] == result['call_horizons'] == horizons,
        final_open=labels[-1] == 'release_retreat' and calls[-1]['commands'] == [0] and
                   calls[-1]['call_id'] == released['call_id'] == end[-1]['call_id'],
        upward_public_target=np.allclose(target, np.array(released['ee_m']) + [0, 0, .15], atol=.002, rtol=0)
                              and retreated['ee_m'][2] - released['ee_m'][2] >= .01,
        clock_origin=abs(end[-1]['sim_time_s'] - start_time) < 1e-6 and
                     abs(retreated['sim_time_s'] - start_time) < 1e-6,
        absolute_clock=np.array_equal(data['absolute_steps'], meta['absolute_step'] + np.arange(331)) and
                       np.allclose(data['sim_time_s'], start_time + np.arange(331) / 60, atol=1e-5, rtol=0),
        double_hold=all(np.array_equal(np.load(directory / 'evidence' / (key + '.npz'))['vertices'],
                                       data['vertices'][i])
                        for key, i in [('hold_3s', 180), ('hold_4s', 240)]),
        terminal_matches=np.array_equal(np.load(directory / 'final.npz')['vertices'], data['vertices'][330]))
    out.update(evidence_checks={k: bool(v) for k, v in checks.items()}, criteria=quality)
    if all(checks.values()) and quality['status'] in ('accepted', 'rejected'):
        out.update(status=quality['status'], success=quality['success'])
    return out


def collect():
    parent = read(PARENT)
    revised = read(APP / 'a5-manifest.json')
    assert sha(APP / 'a5-manifest.json') == '40858efc1a5840ab2bf51e025f823382e8586bc037fbe41bf1d1de5b21dee86a'
    assert sha(PARENT) == PARENT_SHA
    for name, digest in revised.items():
        assert sha(APP / name) == digest, ('revised file mismatch', name)
    if PARENT_APP.is_dir():
        assert sha(PARENT_APP / 'a5-manifest.json') == PARENT_SHA
        for name, digest in parent.items():
            assert sha(PARENT_APP / name) == digest, ('parent file mismatch', name)
    inh = read(CAND / 'inheritance.json')
    reg = read(CAND / 'registration.json')
    assert sha(CAND / 'inheritance.json') == reg['identity']['inheritance_sha256']
    assert sha(CAND / 'audit_hold120_case.py') == inh['verification']['audit_sha256']
    assert sha(CAND / 'hold_contract.py') == inh['verification']['hold_contract_sha256']
    assert sha(CAND / 'verify_rc7_sources.py') == inh['verification']['verify_rc7_sources_sha256']
    orig = load_jsonl(ORIG / 'attempts.jsonl')
    assert [r['state'] for r in orig] == ['started', 'paused']
    assert int(orig[0]['slot']) == 1 and not (ORIG / 'completed').exists()
    slot1 = Path(read(APP / 'a5-rc2-pfs1-observation-v2.json')['resume']['slot1_result'])
    assert slot1.is_dir()
    res = load_jsonl(RESUME / 'attempts.jsonl')
    started = [r for r in res if r['state'] == 'started']
    finished = [r for r in res if r['state'] == 'finished']
    assert len(started) == len(finished) == 6, (len(started), len(finished))
    assert (RESUME / 'completed').is_file()
    by_slot = {int(r['slot']): r for r in finished}
    assert sorted(by_slot) == [2, 3, 4, 5, 6, 7]
    assert len({(int(r['slot']), int(r['seed']), r['mode']) for r in finished}) == 6
    for r in finished:
        assert r['manifest_sha256'] == '40858efc1a5840ab2bf51e025f823382e8586bc037fbe41bf1d1de5b21dee86a'
    slots = {1: {'seed': 4100, 'mode': 'single', 'run': str(slot1), 'manifest': parent,
                 'manifest_sha': PARENT_SHA}}
    for s in (6, 5, 4, 3, 2, 7):
        if s in by_slot:
            slots[s] = {'seed': int(by_slot[s]['seed']), 'mode': by_slot[s]['mode'],
                        'run': by_slot[s]['run'], 'manifest': revised,
                        'manifest_sha': sha(APP / 'a5-manifest.json')}
    assert sorted(slots) == [1, 2, 3, 4, 5, 6, 7]
    return slots


def verify_all():
    slots = collect()
    assert sorted(slots) == list(range(1, 8))
    expected = {1: (4100, 'single'), 2: (4100, 'arc4'), 3: (4202, 'single'),
                4: (4202, 'arc4'), 5: (4302, 'single'), 6: (4302, 'arc4'),
                7: (4201, 'single')}
    cases = {}
    for slot, rec in slots.items():
        seed, mode = expected[slot]
        assert (rec['seed'], rec['mode']) == (seed, mode)
        d = Path(rec['run'])
        a = assess_case(d, rec['manifest'], rec['manifest_sha'])
        assert a['status'] in ('accepted', 'rejected'), (slot, a['evidence_checks'])
        assert a['seed'] == seed and a['mode'] == mode
        verdict = read(d / 'a5-verdict.json')
        assert verdict['status'] == a['status']
        if seed in (4100, 4202, 4302):
            assert a['success'] is True, ('positive failed', slot)
        h = None
        if seed == 4100:
            assert not (d / 'recovery_hold_trace.npz').exists()
        else:
            h = read(d / 'recovery_hold_metadata.json')
            assert h['completed_steps'] == 120 and h['frames'] == 121
            assert abs(float(h['duration_s']) - 2.0) <= 1e-6
        cases[slot] = {'slot': slot, 'seed': seed, 'mode': mode, 'status': a['status'],
                       'success': a['success'], 'result_dir': str(d),
                       'trace_sha256': sha(d / 'success_trace.npz'),
                       'hold': None if h is None else {'steps': h['completed_steps'],
                                                       'frames': h['frames'],
                                                       'duration_s': h['duration_s']},
                       'source_manifest': rec['manifest_sha']}
    for seed, sslot, aslot in ((4100, 1, 2), (4202, 3, 4), (4302, 5, 6)):
        s = read(Path(cases[sslot]['result_dir']) / 'result.json')
        a = read(Path(cases[aslot]['result_dir']) / 'result.json')
        if seed == 4100:
            x = s['actions'][0]['target_pose']; y = a['actions'][0]['target_pose']
        else:
            x = next(z['target_pose'] for z in s['actions'] if z['label'] == 'fold_approach')
            y = next(z['target_pose'] for z in a['actions'] if z['label'] == 'fold_approach')
        d = max(abs(float(p) - float(q)) for p, q in zip(x, y))
        assert d <= 1e-6, (seed, d)
    return cases


def build_manifest(cases):
    parent = read(PARENT)
    revised = read(APP / 'a5-manifest.json')
    entries = {}
    for name in ('candidate_manifest', 'parent_manifest', 'audit_hold120_case.py',
                 'hold_contract.py', 'verify_rc7_sources.py', 'freeze_rc7_sources.py', 'gate_rc7_sources.py',
                 'inheritance.json', 'registration.json', 'README.md'):
        p = APP / 'a5-manifest.json' if name == 'candidate_manifest' else \
            PARENT if name == 'parent_manifest' else CAND / name
        entries[name] = sha(p)
    for name in ('attempts.jsonl', 'batch.log'):
        entries['original_' + name] = sha(ORIG / name)
    for name in ('attempts.jsonl', 'batch.jsonl', 'batch.log', 'completed'):
        entries['resume_' + name] = sha(RESUME / name)
    for slot, c in cases.items():
        d = Path(c['result_dir'])
        for fn in ('result.json', 'a5-verdict.json', 'success_meta.json', 'success_trace.npz',
                   'final.npz', 'evidence/summary.json', 'evidence/manifest.json'):
            entries['slot%d:%s' % (slot, fn)] = sha(d / fn)
        if (d / 'recovery_hold_metadata.json').is_file():
            entries['slot%d:recovery_hold_metadata.json' % slot] = sha(d / 'recovery_hold_metadata.json')
            entries['slot%d:recovery_hold_trace.npz' % slot] = sha(d / 'recovery_hold_trace.npz')
    for name in ('local_recompute.json', 'source_verification.json', 'summary.json',
                 'combined_summary.json', 'cases.csv', 'source_verify.log',
                 'hold120_rc7_contact_sheet.png', 'hold120_rc7_review.md'):
        entries['archive_' + name] = sha(CAND / 'archive' / name)
    data = {
        'schema': 'a5-verification-manifest-source-inherited-v1',
        'candidate_manifest_sha256': sha(APP / 'a5-manifest.json'),
        'candidate_manifest_entries': len(revised),
        'parent_manifest_sha256': sha(PARENT),
        'source_mode': 'slot1_parent + slots2-7_revised',
        'entries': entries,
        'cases': cases,
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'original_verify_dev_used': False,
        'source_compatible_verifier_used': 'verify_rc7_sources.py',
    }
    VERIFY_MANIFEST.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true')
    a = ap.parse_args()
    if VERIFIED.exists() or RELEASE.exists():
        raise SystemExit('Receipt already exists; refuse to overwrite: %s %s' % (VERIFIED, RELEASE))
    cases = verify_all()
    vm = build_manifest(cases)
    print('FREEZE_VERIFIED_CASES', len(cases), 'six_positives',
          all(c['status'] == 'accepted' for s, c in cases.items() if s <= 6))
    if not a.execute:
        print('FREEZE_DRY_RUN_OK', sha(VERIFY_MANIFEST))
        return
    verified = {
        'schema': 'a5-verified-dev-source-inherited-v1',
        'manifest_sha256': sha(APP / 'a5-manifest.json'),
        'parent_manifest_sha256': sha(PARENT),
        'source_mode': 'slot1_parent + slots2-7_revised',
        'verification_manifest': str(VERIFY_MANIFEST),
        'verification_manifest_sha256': sha(VERIFY_MANIFEST),
        'cases': [cases[s] for s in sorted(cases)],
        'all_six_positives_accepted': all(cases[s]['status'] == 'accepted' for s in (1, 2, 3, 4, 5, 6)),
        'slot7_quality': cases[7]['status'],
        'audit_history': {'slot1_initial_exit': 5,
                          'slot1_postaudit_exit': 0,
                          'original_manifest': sha(PARENT),
                          'revised_manifest': sha(APP / 'a5-manifest.json')},
        'created_utc': datetime.now(timezone.utc).isoformat(),
    }
    save_new(VERIFIED, verified)
    release = {'manifest_sha256': sha(APP / 'a5-manifest.json'),
               'parent_manifest_sha256': sha(PARENT),
               'verification_file': str(VERIFIED),
               'verification_sha256': sha(VERIFIED),
               'verification_manifest_sha256': sha(VERIFY_MANIFEST),
               'source_mode': 'slot1_parent + slots2-7_revised'}
    save_new(RELEASE, release)
    print('A5_DEV_VERIFIED_SOURCE', len(cases))
    print('VERIFIED_SHA', sha(VERIFIED), 'RELEASE_SHA', sha(RELEASE),
          'VERIFICATION_MANIFEST_SHA', sha(VERIFY_MANIFEST))


if __name__ == '__main__':
    main()
