"""Source-compatible verification for the hold120 rc7 seven slots.

slot1 is inherited from the rc7 parent manifest; slots2-7 come from the revised
manifest.  The original app manifest is single-hash; this entry verifies both
sources explicitly instead of pretending one manifest covers both.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path('/root/autodl-tmp')
ORIG = ROOT / 'a5-rc8b-recovery-hold120-rc7-runs'
RESUME = ROOT / 'a5-rc8b-recovery-hold120-rc7-r2-resume'
CAND = ROOT / 'a5-rc8b-recovery-hold120-rc7-r2'
PARENT_MANIFEST = '41db790f256396e07df079e511090d14a9852c1f55197afa36ea847a9403c2df'
REVISED_MANIFEST = '40858efc1a5840ab2bf51e025f823382e8586bc037fbe41bf1d1de5b21dee86a'
SLOTS = [(1, 4100, 'single'), (2, 4100, 'arc4'), (3, 4202, 'single'),
         (4, 4202, 'arc4'), (5, 4302, 'single'), (6, 4302, 'arc4'),
         (7, 4201, 'single')]


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_jsonl(p):
    p = Path(p)
    if not p.is_file():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def target_pose(run, label):
    r = read(Path(run) / 'result.json')
    for a in r['actions']:
        if a['label'] == label:
            return a['target_pose']
    raise KeyError(label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preflight', action='store_true')
    args = ap.parse_args()
    inh = read(CAND / 'inheritance.json')
    assert inh['parent']['manifest_sha256'] == PARENT_MANIFEST
    assert inh['revised']['manifest_sha256'] == REVISED_MANIFEST
    assert inh['audit']['revised_sha256'] == sha(CAND / 'audit_hold120_case.py')

    orig = load_jsonl(ORIG / 'attempts.jsonl')
    assert [r['state'] for r in orig] == ['started', 'paused']
    assert all(int(r['slot']) == 1 for r in orig)
    slot1 = Path(read(CAND / 'app' / 'a5-rc2-pfs1-observation-v2.json')['resume']['slot1_result'])
    if not slot1.is_absolute():
        slot1 = ROOT / slot1
    assert read(slot1 / 'a5-verdict.json')['status'] == 'accepted'
    assert (ORIG / 'slot1-postaudit.json').is_file()
    assert read(ORIG / 'slot1-postaudit.json')['overall_valid'] is True
    assert not (ORIG / 'completed').exists()

    res = load_jsonl(RESUME / 'attempts.jsonl')
    if args.preflight:
        assert not res, 'resume ledger is not empty'
        assert not (RESUME / 'completed').exists()
        out = {'stage': 'preflight', 'ok': True, 'slot1_manifest': PARENT_MANIFEST,
               'revised_manifest': REVISED_MANIFEST, 'slot1': str(slot1)}
        print('RC7_SOURCE_PREFLIGHT_OK', json.dumps(out, sort_keys=True))
        return 0

    assert (RESUME / 'completed').is_file(), 'resume not completed'
    finished = [r for r in res if r['state'] == 'finished']
    assert len(finished) == 6, len(finished)
    by_slot = {int(r['slot']): r for r in finished}
    assert sorted(by_slot) == [2, 3, 4, 5, 6, 7]
    assert len({(int(r['slot']), int(r['seed']), r['mode']) for r in finished}) == 6
    for r in finished:
        assert r['manifest_sha256'] == REVISED_MANIFEST
        assert r['state'] == 'finished' and r.get('run')

    rows = {1: {'seed': 4100, 'mode': 'single', 'run': str(slot1),
                'semantics': str(ORIG / 'slot1-postaudit.json')}}
    for slot, seed, mode in SLOTS[1:]:
        sem = RESUME / ('slot%d-semantics.json' % slot)
        assert sem.is_file(), str(sem)
        rows[slot] = {'seed': seed, 'mode': mode, 'run': by_slot[slot]['run'],
                      'semantics': str(sem)}
    for slot, row in rows.items():
        s = read(row['semantics'])
        assert s['overall_valid'] is True, (slot, s.get('semantic_checks'))
        assert s['file_complete'] is True
        if row['seed'] == 4100:
            assert s['hold_applicable'] is False and s['recovery_hold'] is True
        else:
            assert s['hold_applicable'] is True and s['recovery_hold'] is True
        assert read(Path(row['run']) / 'a5-verdict.json')['status'] == s['quality_status']

    pair = {}
    for seed in (4100, 4202, 4302):
        single = rows[{4100: 1, 4202: 3, 4302: 5}[seed]]['run']
        arc = rows[{4100: 2, 4202: 4, 4302: 6}[seed]]['run']
        if seed == 4100:
            a = read(Path(single) / 'result.json')['actions'][0]['target_pose']
            b = read(Path(arc) / 'result.json')['actions'][0]['target_pose']
        else:
            a = target_pose(single, 'fold_approach')
            b = target_pose(arc, 'fold_approach')
        d = max(abs(float(x) - float(y)) for x, y in zip(a, b))
        pair[seed] = d
        assert d <= 1e-6, (seed, d)
        if seed != 4100:
            for run in (single, arc):
                h = read(Path(run) / 'recovery_hold_metadata.json')
                assert int(h['completed_steps']) == 120
                assert abs(float(h['duration_s']) - 2.0) <= 1e-6

    positives = [1, 2, 3, 4, 5, 6]
    for slot in positives:
        assert read(Path(rows[slot]['run']) / 'a5-verdict.json')['status'] == 'accepted', slot
    assert read(Path(rows[7]['run']) / 'a5-verdict.json')['status'] in ('accepted', 'rejected')
    out = {'stage': 'full', 'ok': True, 'slots': len(rows),
           'slot1_manifest': PARENT_MANIFEST, 'revised_manifest': REVISED_MANIFEST,
           'all_six_positives_accepted': True,
           'slot7_quality': read(Path(rows[7]['run']) / 'a5-verdict.json')['status'],
           'pair_target_max_abs_m': pair}
    (CAND / 'source_verification.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print('RC7_SOURCE_VERIFIED', json.dumps(out, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
