"""Finalize Stage 5 reduced-run archive: episode manifest, identity, report."""
import hashlib
import json
from pathlib import Path

S = Path('/root/autodl-tmp/stage5-formal-state-v1')
T = Path('/root/autodl-tmp/stage5-trial')
OUT = T / 'final'
OUT.mkdir(parents=True, exist_ok=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


demos = [json.loads(l) for l in (S / 'demonstrations.jsonl').read_text().splitlines() if l.strip()]
rows = [json.loads(l) for l in (S / 'attempts.jsonl').read_text().splitlines() if l.strip()]
recs = []
for d in sorted(demos, key=lambda x: (x['level'], x['seed'])):
    ex = S / 'exports' / ('%s-%s' % (d['level'], d['seed']))
    s = json.loads((ex / 'export_summary.json').read_text())
    recs.append({
        'level': d['level'], 'seed': d['seed'], 'split': s['split'],
        'result_dir': d['result_dir'],
        'obs_dir': str(T / 'obs-formal' / Path(d['result_dir']).name),
        'exports_dir': str(ex),
        'single_samples': s['single_step']['count'],
        'h4_chunks': s['h4']['total_chunks'],
        'h4_tail_actions': s['h4']['tail_actions'],
        'sha256_single': sha(ex / 'single_step.npz'),
        'sha256_h4': sha(ex / 'h4.npz'),
    })
(OUT / 'episodes.jsonl').write_text('\n'.join(json.dumps(r) for r in recs) + '\n', encoding='utf-8')

ident = hashlib.sha256((''.join(sorted(r['sha256_single'] + r['sha256_h4'] for r in recs))).encode()).hexdigest()
identity = {
    'episodes': len(recs),
    'by_level': {l: sum(1 for r in recs if r['level'] == l) for l in ('flat', 'perturbed', 'crumpled')},
    'by_split': {s: sum(1 for r in recs if r['split'] == s) for s in ('train', 'val', 'test')},
    'dataset_sha256': ident,
    'attempts_sha256': sha(S / 'attempts.jsonl'),
    'demonstrations_sha256': sha(S / 'demonstrations.jsonl'),
}
(OUT / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8')

stats = json.loads((T / 'training' / 'final' / 'stats.json').read_text())
(OUT / 'stats.json').write_text(json.dumps(stats, indent=2) + '\n', encoding='utf-8')
config = {
    'label': 'Stage 5 缩减版 50/10/10',
    'input_dim': 1340,
    'backbone': 'MLP 512 -> 512 (GELU + LayerNorm)',
    'heads': {'single': 'cont (4) + gripper logits (3)',
              'h4': 'cont (4,4) + gripper logits (4,3), padding excluded'},
    'loss': 'normalized MSE (dims 0-3) + CE (3 classes)',
    'optimizer': 'AdamW lr=1e-3 wd=1e-4',
    'batch': 128, 'max_epochs': 100, 'early_stop': 15, 'seed': 0,
    'selection': 'best val total loss',
    'splits': 'episode-level from export files',
    'h4': {'chunk': 4, 'mask': 'tail [1,...,0], padding excluded', 'no_cross_episode': True},
}
(OUT / 'config.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')

summary = {'episodes': identity, 'stats': {k: stats[k] for k in
           ('obs_dim', 'single_samples', 'h4_chunks', 'h4_mask_ones', 'h4_mask_total', 'splits')}}
for mode in ('single', 'h4'):
    m = T / 'training' / 'runs' / mode / 'metrics.json'
    if m.is_file():
        summary[mode] = json.loads(m.read_text())
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')

lines = ['# Stage 5 缩减版 50/10/10 归档', '',
         '| 档 | 有效演示 | train/val/test (episodes) |', '|---|---:|---:|']
for l in ('flat', 'perturbed', 'crumpled'):
    lines.append('| %s | %d | %d/%d/%d |' % (l, identity['by_level'][l],
                 sum(1 for r in recs if r['level'] == l and r['split'] == 'train'),
                 sum(1 for r in recs if r['level'] == l and r['split'] == 'val'),
                 sum(1 for r in recs if r['level'] == l and r['split'] == 'test')))
lines += ['', '总计：%d episodes；single-step %d 条；H=4 %d 块（mask 有效 %d/%d）；dataset sha256 `%s`'
          % (identity['episodes'], stats['single_samples'], stats['h4_chunks'],
             stats['h4_mask_ones'], stats['h4_mask_total'], ident), '']
for mode in ('single', 'h4'):
    m = summary.get(mode)
    if m:
        lines += ['## %s' % mode, '',
                  'test: xyz_mae=%.4f m, yaw_mae=%.4f rad, grip_acc=%.4f, cont_mse=%.4f, grip_ce=%.4f' %
                  (m.get('test_xyz_mae_m', float('nan')), m.get('test_yaw_mae_rad', float('nan')),
                   m.get('test_grip_acc', float('nan')), m.get('test_cont_mse', float('nan')),
                   m.get('test_grip_ce', float('nan'))), '']
        for lvl, v in m.get('test_by_level', {}).items():
            lines.append('- %s: n=%d, xyz=%.4f m, yaw=%.4f rad, grip_acc=%.3f' %
                         (lvl, v['n'], v['xyz_mae_m'], v['yaw_mae_rad'], v['grip_acc']))
        lines.append('')
(OUT / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('FINALIZE_OK', json.dumps(identity))
print((OUT / 'REPORT.md').read_text())
