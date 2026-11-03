"""Build an LF-normalized overlay; registered simulator dependencies stay byte-pinned."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = HERE.parent
parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
args = parser.parse_args()
payload = {}
required = {}
def add(name, path):
    data = path.read_bytes().replace(b'\r\n', b'\n')
    digest = hashlib.sha256(data).hexdigest()
    if name in required and required[name] != digest:
        raise ValueError('Conflicting deployed dependency: '+name)
    required[name] = digest
    payload[name] = data
for mf in ('square-initial-files.json','square-initial-stripfold-files.json','square-l1-xfold-yaw-files.json','square-recovery-fold-files.json'):
    for n,h in json.loads((D/mf).read_text()).items():
        if required.setdefault(n,h) != h: raise ValueError('Inconsistent base dependency: '+n)
    add(mf,D/mf)
for n in ('a5_l1.py','a5_recovery.py','a5_entry.py','a5_capture.py','a5-candidate.json','run-stage4-formal-batch.sh','stage4_batch_preflight.py','a5_report.py'):
    add(n,HERE/n)
for n in ('episode_evidence.py','audit_episode_evidence.py','stage4-success-v1-files.json','stage4-heldout-seeds.json','square-initial-plan.json'):
    add(n,D/n)
for n in json.loads((D/'stage4-success-v1-files.json').read_text()):
    add(n,D/n)
manifest = (json.dumps(required,indent=2,sort_keys=True)+'\n').encode()
(HERE/'a5-manifest.json').write_bytes(manifest)
args.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for n,data in payload.items():
        z.writestr(n[3:] if n.startswith('../') else 'app/'+n,data)
    z.writestr('app/a5-manifest.json',manifest)
    z.writestr('canonical-e-entry.sh',(D/'run-stage4-formal-batch.sh').read_bytes())
print('MANIFEST', hashlib.sha256(manifest).hexdigest(), len(required))
