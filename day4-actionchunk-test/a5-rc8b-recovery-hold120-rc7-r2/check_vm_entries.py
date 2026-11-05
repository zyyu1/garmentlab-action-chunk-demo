import hashlib
import json
from pathlib import Path

CAND = Path('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2')
ROOT = Path('/root/autodl-tmp')
ORIG = ROOT / 'a5-rc8b-recovery-hold120-rc7-runs'
RESUME = ROOT / 'a5-rc8b-recovery-hold120-rc7-r2-resume'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


vm = json.loads((CAND / 'verification-manifest.json').read_text())
cases = {c['slot']: c for c in (vm['cases'].values() if isinstance(vm['cases'], dict) else vm['cases'])}
fixed = {
    'candidate_manifest': CAND / 'app' / 'a5-manifest.json',
    'parent_manifest': CAND / 'parent-rc7-manifest.json',
    'audit_hold120_case.py': CAND / 'audit_hold120_case.py',
    'hold_contract.py': CAND / 'hold_contract.py',
    'verify_rc7_sources.py': CAND / 'verify_rc7_sources.py',
    'freeze_rc7_sources.py': CAND / 'freeze_rc7_sources.py',
    'gate_rc7_sources.py': CAND / 'gate_rc7_sources.py',
    'inheritance.json': CAND / 'inheritance.json',
    'registration.json': CAND / 'registration.json',
    'README.md': CAND / 'README.md',
    'original_attempts.jsonl': ORIG / 'attempts.jsonl',
    'original_batch.log': ORIG / 'batch.log',
    'resume_attempts.jsonl': RESUME / 'attempts.jsonl',
    'resume_batch.jsonl': RESUME / 'batch.jsonl',
    'resume_batch.log': RESUME / 'batch.log',
    'resume_completed': RESUME / 'completed',
}
for name in ('local_recompute.json', 'source_verification.json', 'summary.json',
             'combined_summary.json', 'cases.csv', 'source_verify.log',
             'hold120_rc7_contact_sheet.png', 'hold120_rc7_review.md'):
    fixed['archive_' + name] = CAND / 'archive' / name

bad = []
for label, want in vm['entries'].items():
    if label in fixed:
        p = fixed[label]
    elif ':' in label:
        slot_s, name = label.split(':', 1)
        p = Path(cases[int(slot_s.replace('slot', ''))]['result_dir']) / name
    else:
        bad.append((label, 'unknown_label'))
        continue
    if not p.is_file():
        bad.append((label, 'missing', str(p)))
    elif sha(p) != want:
        bad.append((label, 'mismatch', str(p)))
out = {'entries': len(vm['entries']), 'bad': bad, 'ok': not bad,
       'verification_manifest_sha256': sha(CAND / 'verification-manifest.json')}
(CAND / 'verification-manifest-check.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
print('VM_ENTRY_CHECK', len(vm['entries']), 'bad', len(bad))
for row in bad:
    print(row)
raise SystemExit(0 if not bad else 5)
