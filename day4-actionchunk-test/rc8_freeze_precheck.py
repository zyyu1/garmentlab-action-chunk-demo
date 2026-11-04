"""Pre-freeze identity and formal-entry checks for rc8.

Read-only.  Does not write receipts and does not run freeze.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAND = HERE / 'a5-rc2-pfs1-observation-v2-rc8'
APP = CAND / 'app'
ROOT = HERE / 'results' / 'RC8_SEVEN_CASE_20261104'
BATCH = ROOT / 'a5-rc2-pfs1-observation-v2-rc8-runs'
REMOTE = '/root/autodl-tmp'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


manifest = json.loads((APP / 'a5-manifest.json').read_text())
bad = [n for n, w in manifest.items()
       if not (APP / n).is_file() or sha(APP / n) != w]
print('IDENTITY manifest_entries', len(manifest), 'sha', sha(APP / 'a5-manifest.json'))
print('IDENTITY manifest_bad', bad)
print('IDENTITY receipts_present',
      (APP / 'verified-dev.json').exists(), (APP / 'E_RELEASE.json').exists())

fm = json.loads((ROOT / 'freeze_manifest.json').read_text())
print('FREEZE_MANIFEST candidate_manifest_match',
      fm['candidate']['manifest_sha256'] == sha(APP / 'a5-manifest.json'))
for key, rel in (('config_sha256', 'a5-rc2-pfs1-observation-v2.json'),
                 ('runner_sha256', 'run-a5-rc2-pfs1-observation-v2.sh'),
                 ('a5_l1_sha256', 'a5_l1.py'),
                 ('pfs1_observation_v2_sha256', 'pfs1_observation_v2.py')):
    print('FREEZE_MANIFEST', key, fm['candidate'][key] == sha(APP / rel))
print('FREEZE_MANIFEST cases', len(fm['cases']))

attempts = [json.loads(l) for l in (BATCH / 'attempts.jsonl').read_text().splitlines() if l.strip()]
started = [a for a in attempts if a['state'] == 'started']
finished = [a for a in attempts if a['state'] == 'finished']
pairs = {(a['slot'], a['seed'], a['mode']) for a in started}
done = {(a['slot'], a['seed'], a['mode']) for a in finished}
print('LEDGER lines', len(attempts), 'started', len(started), 'finished', len(finished))
print('LEDGER unfinished', sorted(pairs - done))
print('LEDGER manifests', sorted({a['manifest_sha256'] for a in attempts}))

l1 = (APP / 'a5_l1.py').read_text()
strip = (APP / 'day4-square-initial-stripfold.py').read_text()
formal = (APP / 'run-stage4-formal-batch.sh').read_text()
print('FORMAL a5_l1_scale_0', "kwargs['particle_friction_scale'] = 0." in l1)
print('FORMAL stripfold_forces_0', "kwargs['particle_friction_scale'] = 0." in strip)
print('FORMAL stripfold_asserts_0', "particle_friction_scale'] != 0" in strip)
print('FORMAL batch_uses_stripfold_for_nonflat', 'run-square-initial-stripfold.sh' in formal)
print('FORMAL batch_uses_local_entry', '"$here/a5_entry.py"' in formal)
