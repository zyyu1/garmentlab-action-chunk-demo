import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
app = root / 'app'
patch_dir = root.parent / 'results' / 'RC8B_L2_DIAG_20261105' / 'day4-square-initial-stripfold-20261104-221219-l2patch9'
patch_def = root.parent / 'results' / 'RC8B_L2_DIAG_20261105' / 'patch_definition.json'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

policy = json.loads((app / 'a5-candidate.json').read_text())
entry = policy['development']['4202']
entry['initial'] = patch_dir.name
entry['files'] = {'result.json': sha(patch_dir / 'result.json'),
                  'initial_geometry.npz': sha(patch_dir / 'initial_geometry.npz')}
entry['modes'] = ['single']
(app / 'a5-candidate.json').write_text(json.dumps(policy, indent=2) + '\n', encoding='utf-8')

cfg_path = app / 'a5-rc2-pfs1-observation-v2.json'
cfg = json.loads(cfg_path.read_text())
cfg.update({
    'revision': 'diagnostic-l2-nine-point-z-patch',
    'status': 'patch9_registered_not_run',
    'kind': 'diagnostic_single_case_patch',
    'parent': 'a5-rc2-pfs1-observation-v2-rc8b',
    'parent_manifest_sha256': 'cce573ddd626715b15818467290152a4c68502bafc9595b11780fe1dd601bc8e',
    'diagnostic_of': 'a5-rc2-pfs1-observation-v2-rc8b',
    'patch_definition_sha256': sha(patch_def),
    'patch': {
        'name': 'l2patch9',
        'source_initial': 'day4-square-initial-stripfold-20261105-015817-115841',
        'indices': [69, 70, 71, 90, 91, 92, 111, 112, 113],
        'rule': 'only z of the nine indices replaced by the l2pose derived z; all else unchanged',
        'initial_diagnostic': True,
    },
    'run': {'one_attempt': True, 'retry': False,
            'lock': 'a5-rc2-pfs1-observation-v2-l2patch9-runs',
            'journal': '/root/autodl-tmp/a5-rc2-pfs1-observation-v2-l2patch9-runs/journal',
            'output_prefix': 'day4-a5-rc2-pfs1-observation-v2-'},
})
cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('updated', entry['initial'], sha(patch_def))
