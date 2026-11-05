import hashlib
import json
from pathlib import Path

CAND = Path('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2')
DEP = Path('/root/autodl-tmp/stage4-formal-hold120')
FREEZE = CAND
m = json.loads((DEP / 'deployment_manifest.json').read_text())
paths = {
    'formal_driver.py': DEP / 'formal_driver.py',
    'formal_config.json': DEP / 'formal_config.json',
    'formal_slots.json': DEP / 'formal_slots.json',
    'test_formal_driver.py': DEP / 'test_formal_driver.py',
    'test_formal_driver.log': DEP / 'test_formal_driver.log',
    'launch_formal.sh': DEP / 'launch_formal.sh',
    'download_formal.py': DEP / 'download_formal.py',
    'check_deployment.py': DEP / 'check_deployment.py',
    'candidate_manifest': CAND / 'app' / 'a5-manifest.json',
    'gate_rc7_sources.py': CAND / 'gate_rc7_sources.py',
    'freeze_rc7_sources.py': CAND / 'freeze_rc7_sources.py',
    'audit_hold120_case.py': CAND / 'audit_hold120_case.py',
    'hold_contract.py': CAND / 'hold_contract.py',
    'verification_manifest': FREEZE / 'verification-manifest.json',
    'verified_dev': FREEZE / 'verified-dev.json',
    'e_release': FREEZE / 'E_RELEASE.json',
    'seed_list': CAND / 'app' / 'stage4-heldout-seeds.json',
    'initial_plan': CAND / 'app' / 'square-initial-plan.json',
}
bad = []
for k, want in m['entries'].items():
    p = paths[k]
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != want:
        bad.append((k, want, got))
print('DEPLOYMENT_ENTRIES', len(m['entries']), 'bad', len(bad))
for row in bad:
    print(row)
raise SystemExit(0 if not bad else 5)
