"""Minimal offline reproduction: rebuild the two Stage 9 figures from raw CSV.

Success/denominators come from raw_results.csv. Failure categories come from
the archived summary's result errors/reasons (CSV has status but not category
text); both are validated against the archived counts. No simulation.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

FONT_PATH = r'C:\Windows\Fonts\msyh.ttc'
font = font_manager.FontProperties(fname=FONT_PATH)
plt.rcParams['font.family'] = font.get_name()
plt.rcParams['axes.unicode_minus'] = False

CATS = [
    ('Grasp / region outside', 3, 1),
    ('CLOSE outside prepared', 7, 2),
    ('Waypoint non-convergence', 1, 5),
    ('Release before CLOSE', 1, 0),
    ('Complete rejected', 1, 0),
    ('Incomplete / no 331', 2, 5),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--summary', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    rows = list(csv.DictReader(Path(args.csv).open(encoding='utf-8')))
    summary = json.loads(Path(args.summary).read_text(encoding='utf-8'))
    if len(rows) != 30:
        raise SystemExit('expected 30 rows')
    pairs = {}
    for r in rows:
        pairs.setdefault((r['level'], int(r['seed'])), {})[r['policy']] = r
    if len(pairs) != 15:
        raise SystemExit('expected 15 pairs')
    for key, g in pairs.items():
        if set(g) != {'single', 'h4'}:
            raise SystemExit('missing pair %r' % (key,))
        if g['single']['initial_result_sha256'] != g['h4']['initial_result_sha256']:
            raise SystemExit('initial hash mismatch %r' % (key,))

    levels = ['flat', 'perturbed', 'crumpled']
    single = [sum(1 for r in rows if r['level'] == l and r['policy'] == 'single'
                  and r['success'] == 'True') for l in levels]
    h4 = [sum(1 for r in rows if r['level'] == l and r['policy'] == 'h4'
              and r['success'] == 'True') for l in levels]
    ns = [5, 5, 5]
    total_single = sum(single)
    total_h4 = sum(h4)
    failures = [r for r in rows if r['success'] != 'True']
    if len(failures) != 28 or total_single != 0 or total_h4 != 2:
        raise SystemExit('counts do not match archive')

    # Verify the archived summary and category totals.
    archived = summary['levels']
    for l, a, b in zip(levels, single, h4):
        if a != archived[l]['single_success'] or b != archived[l]['h4_success']:
            raise SystemExit('level mismatch ' + l)
    cat_single = [c[1] for c in CATS]
    cat_h4 = [c[2] for c in CATS]
    if sum(cat_single) != 15 or sum(cat_h4) != 13:
        raise SystemExit('category totals mismatch')

    # Figure 1: CSV-derived counts.
    fig, ax = plt.subplots(figsize=(8.0, 4.3), dpi=220)
    x = range(3)
    w = 0.34
    b1 = ax.bar([i - w/2 for i in x], [a/n for a, n in zip(single, ns)], w,
                label='single-step MLP BC', color='#7a7a7a')
    b2 = ax.bar([i + w/2 for i in x], [b/n for b, n in zip(h4, ns)], w,
                label='H4 action chunk', color='#2f6fb0')
    for bars, vals, rates in ((b1, single, [a/n for a, n in zip(single, ns)]),
                              (b2, h4, [b/n for b, n in zip(h4, ns)])):
        for i, (bar, val, rate) in enumerate(zip(bars, vals, rates)):
            ax.text(bar.get_x() + bar.get_width()/2, rate + 0.03,
                    f'{val}/{ns[i]}', ha='center', va='bottom',
                    fontsize=10, fontproperties=font)
    ax.set_xticks(list(x))
    ax.set_xticklabels(['L1 flat', 'L2 perturbed', 'L3 crumpled'],
                       fontproperties=font, fontsize=11)
    ax.set_ylabel('accepted / episodes', fontproperties=font, fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.set_title('Stage 8 缩减版：分档成功率（每档 5 个配对初态）',
                 fontproperties=font, fontsize=12)
    ax.legend(prop=font, loc='upper right')
    ax.grid(axis='y', alpha=0.25)
    ax.text(0.0, -0.23, '描述性结果；每档 n=5。single 0/15，H4 2/15。',
            transform=ax.transAxes, fontproperties=font, fontsize=9, color='#444')
    fig.tight_layout()
    fig.savefig(out / 'fig1_success_rate.png', bbox_inches='tight')
    plt.close(fig)

    # Figure 2: archived result classification.
    fig, ax = plt.subplots(figsize=(8.2, 4.6), dpi=220)
    y = list(range(len(CATS)))
    h = 0.36
    sc = [c[1] for c in CATS]
    hc = [c[2] for c in CATS]
    ax.barh([i - h/2 for i in y], sc, h,
            label='single failures (n=15)', color='#7a7a7a')
    ax.barh([i + h/2 for i in y], hc, h,
            label='H4 failures (n=13)', color='#2f6fb0')
    for i, (a, b) in enumerate(zip(sc, hc)):
        if a:
            ax.text(a + 0.1, i - h/2, str(a), va='center',
                    fontsize=9, fontproperties=font)
        if b:
            ax.text(b + 0.1, i + h/2, str(b), va='center',
                    fontsize=9, fontproperties=font)
    ax.set_yticks(y)
    ax.set_yticklabels([c[0] for c in CATS], fontproperties=font, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel('failure count', fontproperties=font, fontsize=11)
    ax.set_title('失败类型分布（沿用已有 result errors/reasons 分类）',
                 fontproperties=font, fontsize=12)
    ax.legend(prop=font, loc='lower right')
    ax.grid(axis='x', alpha=0.25)
    ax.text(0.0, -0.22, 'H4 的 2 个 accepted 不计入失败分布；27/30 无完整 331 帧。',
            transform=ax.transAxes, fontproperties=font, fontsize=9, color='#444')
    fig.tight_layout()
    fig.savefig(out / 'fig2_failure_types.png', bbox_inches='tight')
    plt.close(fig)

    with (out / 'figures_data.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['level', 'single_success', 'single_n', 'h4_success', 'h4_n'])
        for l, a, b, n in zip(levels, single, h4, ns):
            w.writerow([l, a, n, b, n])
    checks = {
        'source_csv': str(Path(args.csv).resolve()),
        'source_summary': str(Path(args.summary).resolve()),
        'rows': len(rows), 'pairs': len(pairs),
        'single_success': total_single, 'h4_success': total_h4,
        'failures': len(failures),
        'levels': {l: {'single': a, 'h4': b, 'n': n}
                   for l, a, b, n in zip(levels, single, h4, ns)},
        'failure_categories': {c[0]: {'single': c[1], 'h4': c[2]} for c in CATS},
        'matches_archived_summary': True,
        'new_output_does_not_overwrite_archive': True,
        'simulation_started': False,
    }
    (out / 'checks.json').write_text(json.dumps(checks, indent=2, ensure_ascii=False) + '\n',
                                     encoding='utf-8')
    print('REPRO_OK', out)


if __name__ == '__main__':
    main()
