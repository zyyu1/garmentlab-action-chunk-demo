"""Index registered development evidence without selecting by outcome or running GPU."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

SELECTED = {
    'flat': ('day4-square-initial-20261031-', 4100,
             '094446-203825 095254-316552 095611-471489 095925-799656 100246-659222 '
             '100558-317616 100909-165817 101224-181183 101541-103282 101853-191858'),
    'perturbed': ('day4-square-initial-stripfold-20261102-', 4200,
                  '023311-548690 031859-758705 032804-246519 033648-809964 034544-830190 '
                  '035436-003676 040355-509776 041256-658874 042215-851125 043151-454479'),
    'crumpled': ('day4-square-initial-stripfold-20261102-', 4300,
                 '074349-406408 075606-421583 080548-693912 082753-692325 083848-796253 '
                 '084918-410795 090016-424984 091001-304307 092049-522618 093018-418187'),
}
RESET = 'day4-prepared-square-backend-reset-20261101-080713-870146'


def artifact(path):
    row = {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
           'bytes': path.stat().st_size}
    if path.suffix == '.png':
        with Image.open(path) as im:
            row['size'] = list(im.size); im.verify()
    elif path.suffix == '.npz':
        with np.load(path, allow_pickle=False) as data:
            row['arrays'] = {k: list(data[k].shape) for k in data.files}
    elif path.suffix == '.json':
        json.loads(path.read_text(encoding='utf-8'))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    roots = [Path(p).resolve() for p in args.root]
    dirs = {}
    for root in roots:
        for p in root.rglob('*'):
            if p.is_dir() and p.name.startswith('day4-'):
                dirs.setdefault(p.name, []).append(p)
    rows = []
    for level, (prefix, first, suffixes) in SELECTED.items():
        for i, suffix in enumerate(suffixes.split()):
            name = prefix + suffix
            files = {}
            for f in ('initial.png', 'result.json', 'initial_geometry.npz'):
                files[f] = [artifact(p / f) for p in dirs.get(name, []) if (p / f).is_file()]
            results = [json.loads(Path(a['path']).read_text(encoding='utf-8')) for a in files['result.json']]
            identity_ok = bool(results) and all(
                (r.get('initial_case', {}).get('level'), r.get('initial_case', {}).get('seed')) ==
                (level, first + i) for r in results)
            rows.append({'level': level, 'seed': first + i, 'registered_dir': name,
                         'files': files, 'missing': [f for f, copies in files.items() if not copies],
                         'result_identity_verified': identity_ok,
                         'json_copies_semantically_equal': bool(results) and all(r == results[0] for r in results),
                         'development_passed': all(r.get('passed') is True for r in results) if results else None,
                         'conflicting_copies': [f for f, copies in files.items()
                                                if len({a['sha256'] for a in copies}) > 1]})
    resets = []
    for p in dirs.get(RESET, []):
        if not (p / 'result.json').exists():
            continue
        r = json.loads((p / 'result.json').read_text())
        cycles = []
        for i in range(1, 11):
            cycle = p / f'cycle_{i:02d}'
            names = ('reset.json', 'reset_state.npz', 'reset.png', 'cycle.json')
            files = {n: artifact(cycle / n) for n in names if (cycle / n).exists()}
            checks = json.loads((cycle / 'reset.json').read_text())['checks'] if 'reset.json' in files else {}
            saved = json.loads((cycle / 'cycle.json').read_text()) if 'cycle.json' in files else {}
            cycles.append({'cycle': i, 'files': files, 'missing': sorted(set(names) - set(files)),
                           'checks': checks, 'rollout': saved.get('rollout'),
                           'state_checks_passed': all(checks.get(k) is True for k in
                               ('all_slots_released', 'not_holding', 'not_enabled',
                                'constraints_exist', 'paths_distinct_and_valid', 'finite'))})
        resets.append({'result': artifact(p / 'result.json'), 'passed': r.get('passed'),
                       'cycle_count': r.get('cycle_count'), 'settings': r.get('settings'),
                       'errors': r.get('errors'), 'cycles': cycles,
                       'scope': 'development lifecycle evidence; not ten complete folds or formal successes'})
    sheets = [artifact(p) for root in roots for p in root.glob('initial30_sheet*.png')]
    # Preserve and enumerate older image-only sets too; do not substitute them for final registrations.
    image_inventory = [artifact(p) for root in roots for p in root.glob('initial30/*/initial.png')]
    data = {'selection_source': '2026-11-02 handoff: final 6a registered directories',
            'initial_states': rows, 'contact_sheets': sheets, 'historical_image_inventory': image_inventory,
            'reset_evidence': resets,
            'totals': {'registered': len(rows), 'images_available': sum(bool(r['files']['initial.png']) for r in rows),
                       'complete_bundles': sum(not r['missing'] and r['result_identity_verified'] and
                                               not r['conflicting_copies'] for r in rows),
                       'complete_semantic_bundles': sum(not r['missing'] and r['result_identity_verified'] and
                           r['json_copies_semantically_equal'] and
                           not (set(r['conflicting_copies']) - {'result.json'}) for r in rows)},
            'formal_successes_added': 0, 'simulation_started': False}
    out = Path(args.out); out.mkdir(parents=True, exist_ok=False)
    (out / 'index.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# D：初态与 reset 证据索引', '',
             '按最终登记目录选择；未以 passed 筛选。链接指向原始文件，SHA256 与解码结果见 index.json。', '',
             '|档|seed|登记目录|图片|结果身份|缺失文件|', '|---|---:|---|---|---|---|']
    for r in rows:
        imgs = r['files']['initial.png']
        link = '[查看](<' + imgs[0]['path'].replace('\\', '/') + '>)' if imgs else '缺失'
        lines.append(f"|{r['level']}|{r['seed']}|{r['registered_dir']}|{link}|{r['result_identity_verified']}|{', '.join(r['missing']) or '无'}|")
    lines += ['', '## Reset', '', '10 次生命周期 reset/rollout 中只有 1 次完整折叠；不增加正式成功。']
    for r in resets:
        lines.append(f"\n[原始结果](<{r['result']['path'].replace(chr(92), '/')}>)；循环数 {r['cycle_count']}，"
                     f"状态检查通过 {sum(c['state_checks_passed'] for c in r['cycles'])}/10。")
    lines += ['', '## 本地材料限制', '', json.dumps(data['totals'], ensure_ascii=False),
              '', '旧 initial30 目录的图片单独保留在 historical_image_inventory，不替代最终登记的 L3 图片。',
              '缺失材料需从原登记目录补齐；本次未生成任何初态、未重跑 reset、未运行 held-out。']
    (out / 'index.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(data['totals']))


if __name__ == '__main__':
    main()
