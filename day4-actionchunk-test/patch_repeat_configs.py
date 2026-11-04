import json
from pathlib import Path

root = Path(__file__).resolve().parent


def patch(path, **updates):
    p = Path(path)
    d = json.loads(p.read_text())
    d.update(updates)
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('patched', p)


patch(root / 'a5-rc2-pfs1-observation-v2-l2pose-repeat1' / 'app' / 'a5-rc2-pfs1-observation-v2.json',
      revision='diagnostic-l2-pose-control-repeat1',
      status='repeat1_registered_not_run',
      kind='diagnostic_single_case_repeat',
      parent='a5-rc2-pfs1-observation-v2-l2pose',
      parent_manifest_sha256='3a97a5000ac856b758b65a78d15d1f31fe826048ab59f79714c99b7fb89667f0',
      repeat_of='a5-rc2-pfs1-observation-v2-l2pose',
      run={'one_attempt': True, 'retry': False,
           'lock': 'a5-rc2-pfs1-observation-v2-l2pose-repeat1-runs',
           'journal': '/root/autodl-tmp/a5-rc2-pfs1-observation-v2-l2pose-repeat1-runs/journal',
           'output_prefix': 'day4-a5-rc2-pfs1-observation-v2-'})

patch(root / 'a5-rc2-pfs1-observation-v2-rc8b-repeat1' / 'app' / 'a5-rc2-pfs1-observation-v2.json',
      revision='diagnostic-rc8b-4202-repeat1',
      status='repeat1_registered_not_run',
      kind='diagnostic_single_case_repeat',
      parent='a5-rc2-pfs1-observation-v2-rc8b',
      parent_manifest_sha256='cce573ddd626715b15818467290152a4c68502bafc9595b11780fe1dd601bc8e',
      repeat_of='a5-rc2-pfs1-observation-v2-rc8b',
      run={'one_attempt': True, 'retry': False,
           'lock': 'a5-rc2-pfs1-observation-v2-rc8b-repeat1-runs',
           'journal': '/root/autodl-tmp/a5-rc2-pfs1-observation-v2-rc8b-repeat1-runs/journal',
           'output_prefix': 'day4-a5-rc2-pfs1-observation-v2-'})
