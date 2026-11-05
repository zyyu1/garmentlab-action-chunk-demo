import hashlib
import json
from pathlib import Path

CAND = Path('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2')
DEP = Path('/root/autodl-tmp/stage4-minimum-hold120')
m = json.loads((DEP / 'minimum_deployment_manifest.json').read_text())
paths = {
    'minimum_driver.py': DEP / 'minimum_driver.py',
    'formal_driver.py': DEP / 'formal_driver.py',
    'minimum_config.json': DEP / 'minimum_config.json',
    'minimum_slots.json': DEP / 'minimum_slots.json',
    'MINIMUM_ACCEPTANCE_PLAN.md': DEP / 'MINIMUM_ACCEPTANCE_PLAN.md',
    'test_minimum_driver.py': DEP / 'test_minimum_driver.py',
    'test_minimum_driver.log': DEP / 'test_minimum_driver.log',
    'launch_minimum.sh': DEP / 'launch_minimum.sh',
    'candidate_manifest': CAND / 'app' / 'a5-manifest.json',
    'gate_rc7_sources.py': CAND / 'gate_rc7_sources.py',
    'audit_hold120_case.py': CAND / 'audit_hold120_case.py',
    'hold_contract.py': CAND / 'hold_contract.py',
    'verification_manifest': CAND / 'verification-manifest.json',
    'verified_dev': CAND / 'verified-dev.json',
    'e_release': CAND / 'E_RELEASE.json',
    'seed_list': CAND / 'app' / 'stage4-heldout-seeds.json',
    'initial_plan': CAND / 'app' / 'square-initial-plan.json',
}
bad = []
for k, want in m['entries'].items():
    got = hashlib.sha256(paths[k].read_bytes()).hexdigest()
    if got != want:
        bad.append((k, want, got))
print('MINIMUM_DEPLOYMENT_ENTRIES', len(m['entries']), 'bad', len(bad))
for row in bad:
    print(row)
raise SystemExit(0 if not bad else 5)
