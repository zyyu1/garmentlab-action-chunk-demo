import json,hashlib
from pathlib import Path
new={'square-initial-plan.json':'32e61d57','run-square-initial.sh':'b22f848e','run-square-initial-stripfold.sh':'1116550f'}
for f,prefix in new.items():
    h=hashlib.sha256(Path(f).read_bytes()).hexdigest()
    print('NEW',f,h,'EXPECTED_PREFIX_MATCH',h.startswith(prefix))
for mf in ('square-initial-files.json','square-initial-stripfold-files.json'):
    d=json.loads(Path(mf).read_text())
    bad=[]
    for name,digest in d.items():
        p=Path(name) if Path(name).exists() else Path('garmentlab-action-chunk-demo')/name
        if not p.exists(): bad.append((name,'missing')); continue
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        if h!=digest and name not in new: bad.append((name,'mismatch'))
    print('MANIFEST',mf,'other-entries-bad',bad)
