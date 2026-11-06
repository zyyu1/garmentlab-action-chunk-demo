"""Build minimum_deployment_manifest_v2.json (adds the continuation rule)."""
import hashlib
import json
from pathlib import Path

CAND = Path('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2')
DEP = Path('/root/autodl-tmp/stage4-minimum-hold120')

FILES = {
    'minimum_driver.py': DEP / 'minimum_driver.py',
    'minimum_driver_v2.py': DEP / 'minimum_driver_v2.py',
    'adapter_run.py': DEP / 'adapter_run.py',
    'formal_driver.py': DEP / 'formal_driver.py',
    'minimum_config.json': DEP / 'minimum_config.json',
    'minimum_slots.json': DEP / 'minimum_slots.json',
    'MINIMUM_ACCEPTANCE_PLAN.md': DEP / 'MINIMUM_ACCEPTANCE_PLAN.md',
    'CONTINUATION_RULE_20261106.md': DEP / 'CONTINUATION_RULE_20261106.md',
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


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    entries = {}
    for k, p in FILES.items():
        if not Path(p).is_file():
            raise SystemExit('MISSING ' + k + ' ' + str(p))
        entries[k] = sha(p)
    man = {
        'schema': 'minimum-hold120-deployment-v2',
        'candidate': 'a5-rc8b-recovery-hold120-rc7-r2',
        'candidate_manifest_sha256': entries['candidate_manifest'],
        'verification_manifest_sha256': entries['verification_manifest'],
        'app_overlay_manifest_sha256': entries['candidate_manifest'],
        'stop_rule': 'per level 5 valid successes, max 20 attempts',
        'continuation_rule': 'waypoint non-convergence = failed attempt, continue; other anomalies pause',
        'entries': entries,
    }
    out = DEP / 'minimum_deployment_manifest_v2.json'
    out.write_text(json.dumps(man, indent=2) + '\n', encoding='utf-8')
    print('V2_MANIFEST_WRITTEN', out, 'entries', len(entries))


if __name__ == '__main__':
    main()
