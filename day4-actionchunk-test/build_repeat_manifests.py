import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(name, parent_file, alias):
    d = root / name
    app = d / 'app'
    parent = json.loads((d / parent_file).read_text())
    new = {n: sha(app / n) for n in parent}
    assert len(new) == 63
    expected = {'a5-rc2-pfs1-observation-v2.json', 'run-a5-rc2-pfs1-observation-v2.sh'}
    changed = sorted(n for n in parent if new[n] != parent[n])
    print(name, 'changed', changed, 'identical', 63 - len(changed))
    assert set(changed) == expected, changed
    text = json.dumps(new, indent=2, sort_keys=True) + '\n'
    for fn in ('a5-manifest.json', alias):
        with (app / fn).open('w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
    print(name, 'manifest sha', hashlib.sha256(text.encode()).hexdigest())


build('a5-rc2-pfs1-observation-v2-l2pose-repeat1', 'parent-l2pose-manifest.json',
      'a5-rc2-pfs1-observation-v2-l2pose-repeat1-files.json')
build('a5-rc2-pfs1-observation-v2-rc8b-repeat1', 'parent-rc8b-manifest.json',
      'a5-rc2-pfs1-observation-v2-rc8b-repeat1-files.json')
