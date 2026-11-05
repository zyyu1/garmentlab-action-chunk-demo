import json
import hashlib
from pathlib import Path

root = Path('/root/autodl-tmp/stage4-4112-deep')
init = Path('/root/autodl-tmp/day4-square-initial-20261105-232137-703257')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


led = {
    'diagnostic': '4112_arc135_deep_v1',
    'initial_dir': str(init),
    'initial_sha256': {'result.json': sha(init / 'result.json'),
                       'initial_geometry.npz': sha(init / 'initial_geometry.npz')},
    'candidate_manifest_sha256': sha('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2/app/a5-manifest.json'),
    'parent_receipt_sha256': sha('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2/E_RELEASE.json'),
    'child_receipt_sha256': sha(root / 'app/E_RELEASE.json'),
    'wrapper_sha256': sha(root / 'diagnose_arc135_deep.py'),
    'command': 'python diagnose_arc135_deep.py',
}
(root / 'ledger.json').write_text(json.dumps(led, indent=2) + '\n', encoding='utf-8')
print(json.dumps(led, indent=2))
