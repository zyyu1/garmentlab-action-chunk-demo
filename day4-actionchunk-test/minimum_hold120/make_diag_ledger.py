import json
import hashlib
from pathlib import Path

root = Path('/root/autodl-tmp/stage4-4112-diag')
init = Path('/root/autodl-tmp/day4-square-initial-20261105-232137-703257')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


led = {
    'diagnostic': '4112_arc135_readonly_v1',
    'initial_dir': str(init),
    'initial_sha256': {
        'result.json': sha(init / 'result.json'),
        'initial_geometry.npz': sha(init / 'initial_geometry.npz'),
        'initial.png': sha(init / 'initial.png'),
    },
    'candidate_manifest_sha256': sha('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2/app/a5-manifest.json'),
    'parent_receipt_sha256': sha('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2/E_RELEASE.json'),
    'child_receipt_sha256': sha(root / 'app/E_RELEASE.json'),
    'verified_dev_sha256': sha('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2/verified-dev.json'),
    'diagnostic_wrapper_sha256': sha(root / 'diagnose_arc135.py'),
    'original_4112_result': '/root/autodl-tmp/day4-a5-rc2-l1-20261106-033055-623326',
    'command': 'python diagnose_arc135.py',
}
(root / 'ledger.json').write_text(json.dumps(led, indent=2) + '\n', encoding='utf-8')
print(json.dumps(led, indent=2))
