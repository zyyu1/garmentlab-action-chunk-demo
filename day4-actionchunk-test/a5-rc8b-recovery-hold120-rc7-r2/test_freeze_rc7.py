"""Negative/positive tests for freeze/gate on temporary copies (no simulation)."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import freeze_rc7_sources as f

BASE = Path(tempfile.mkdtemp(prefix='hold120_freeze_test_'))
REAL = {'CAND': f.CAND, 'APP': f.APP, 'PARENT': f.PARENT, 'PARENT_APP': f.PARENT_APP,
        'ORIG': f.ORIG, 'RESUME': f.RESUME, 'VERIFY_MANIFEST': f.VERIFY_MANIFEST,
        'VERIFIED': f.VERIFIED, 'RELEASE': f.RELEASE}
results = []
REAL_COLLECT = f.collect


def setup(name):
    d = BASE / name
    shutil.copytree(REAL['CAND'], d, ignore=shutil.ignore_patterns('__pycache__', 'verified-dev.json', 'E_RELEASE.json'))
    f.CAND = d
    f.APP = d / 'app'
    f.PARENT = d / 'parent-rc7-manifest.json'
    f.PARENT_APP = REAL['PARENT_APP']
    f.ORIG = REAL['ORIG']
    f.RESUME = REAL['RESUME']
    f.collect = REAL_COLLECT
    f.VERIFY_MANIFEST = d / 'verification-manifest.json'
    f.VERIFIED = d / 'verified-dev.json'
    f.RELEASE = d / 'E_RELEASE.json'
    return d


def expect_fail(name, fn):
    try:
        fn()
    except Exception as exc:
        results.append({'case': name, 'rejected': True, 'error': str(exc)[:120]})
        return
    raise SystemExit('expected rejection: ' + name)


# 1 correct complete material passes
d = setup('correct')
assert len(f.verify_all()) == 7
results.append({'case': 'correct_complete_passes', 'rejected': False, 'ok': True})

# 2 modified candidate file
d = setup('candidate')
with (d / 'app' / 'a5_recovery.py').open('a', encoding='utf-8') as fh:
    fh.write('\n# tamper\n')
expect_fail('candidate_file_modified', f.verify_all)

# 3 modified audit
d = setup('audit')
with (d / 'audit_hold120_case.py').open('a', encoding='utf-8') as fh:
    fh.write('\n# tamper\n')
expect_fail('audit_modified', f.verify_all)

# 4 modified inheritance
d = setup('inheritance')
inh = json.loads((d / 'inheritance.json').read_text())
inh['scope'] = 'tampered'
(d / 'inheritance.json').write_text(json.dumps(inh, indent=2))
expect_fail('inheritance_modified', f.verify_all)

# 5 modified verifier
d = setup('verifier')
with (d / 'verify_rc7_sources.py').open('a', encoding='utf-8') as fh:
    fh.write('\n# tamper\n')
expect_fail('verifier_modified', f.verify_all)

# 6 modified evidence: copy one result, tamper final.npz, monkeypatch collect
d = setup('evidence')
slots = f.collect()
src = Path(slots[3]['run'])
tam = d / 'slot3'
shutil.copytree(src, tam)
(tam / 'final.npz').write_bytes(b'not a npz')
slots[3] = dict(slots[3], run=str(tam))
f.collect = lambda: slots
expect_fail('evidence_modified', f.verify_all)

# 7 missing slot
d = setup('missing')
slots = f.collect()
slots.pop(7)
f.collect = lambda: slots
expect_fail('missing_slot', f.verify_all)

# 8 duplicate slot
d = setup('duplicate')
slots = f.collect()
slots[7] = dict(slots[6])
f.collect = lambda: slots
expect_fail('duplicate_slot', f.verify_all)

# 9 unfinished attempt
d = setup('unfinished')
resume = d / 'resume'
shutil.copytree(REAL['RESUME'], resume)
lines = (resume / 'attempts.jsonl').read_text().splitlines()
(resume / 'attempts.jsonl').write_text('\n'.join(lines[:-1]) + '\n')
f.RESUME = resume
expect_fail('unfinished_attempt', f.verify_all)

# 10 existing receipt cannot be overwritten
d = setup('receipts')
f.VERIFY_MANIFEST = d / 'verification-manifest.json'
f.VERIFIED = d / 'verified-dev.json'
f.RELEASE = d / 'E_RELEASE.json'
sys.argv = ['freeze_rc7_sources.py', '--execute']
f.main()
try:
    f.main()
except SystemExit as exc:
    results.append({'case': 'receipt_no_overwrite', 'rejected': True, 'error': str(exc)})
else:
    raise SystemExit('expected receipt overwrite rejection')

(BASE / 'freeze_tests.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
print('FREEZE_TESTS_OK', json.dumps(results, indent=2))
shutil.rmtree(BASE)
