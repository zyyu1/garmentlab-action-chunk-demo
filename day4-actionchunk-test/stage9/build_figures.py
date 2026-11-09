"""Stage 9 offline figures from the frozen reduced-30 summary."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = Path(r'E:\learning\project\stage8_reduced30_20261109')
OUT = Path(r'E:\learning\project\stage9_showcase_20261109')
OUT.mkdir(parents=True, exist_ok=True)

FONT_PATH = r'C:\Windows\Fonts\msyh.ttc'
font = font_manager.FontProperties(fname=FONT_PATH)
plt.rcParams['font.family'] = font.get_name()
plt.rcParams['axes.unicode_minus'] = False

summary = json.loads((BASE / 'summary.json').read_text(encoding='utf-8'))
levels = ['flat', 'perturbed', 'crumpled']
labels = ['L1 flat', 'L2 perturbed', 'L3 crumpled']
single = [summary['levels'][l]['single_success'] for l in levels]
h4 = [summary['levels'][l]['h4_success'] for l in levels]
ns = [summary['levels'][l]['single_n'] for l in levels]
single_rate = [a / n for a, n in zip(single, ns)]
h4_rate = [a / n for a, n in zip(h4, ns)]

fig, ax = plt.subplots(figsize=(8.0, 4.3), dpi=220)
x = range(len(levels))
w = 0.34
b1 = ax.bar([i - w/2 for i in x], single_rate, w,
            label='single-step MLP BC', color='#7a7a7a')
b2 = ax.bar([i + w/2 for i in x], h4_rate, w,
            label='H4 action chunk', color='#2f6fb0')
for bars, values, rates in ((b1, single, single_rate),
                            (b2, h4, h4_rate)):
    for i, (bar, value, rate) in enumerate(zip(bars, values, rates)):
        ax.text(bar.get_x() + bar.get_width()/2, rate + 0.03,
                f'{value}/{ns[i]}', ha='center', va='bottom', fontsize=10,
                fontproperties=font)
ax.set_xticks(list(x))
ax.set_xticklabels(labels, fontproperties=font, fontsize=11)
ax.set_ylabel('accepted / episodes', fontproperties=font, fontsize=11)
ax.set_ylim(0, 1.0)
ax.set_title('Stage 8 缩减版：分档成功率（每档 5 个配对初态）',
             fontproperties=font, fontsize=12)
ax.legend(prop=font, loc='upper right')
ax.grid(axis='y', alpha=0.25)
ax.text(0.0, -0.23, '描述性结果；每档 n=5。single 0/15，H4 2/15。',
        transform=ax.transAxes, fontproperties=font, fontsize=9, color='#444')
fig.tight_layout()
fig.savefig(OUT / 'fig1_success_rate.png', bbox_inches='tight')
plt.close(fig)

# Failure categories are the existing result classifications.
# single failures: 15 total; H4 failures: 13 total (2 accepted excluded).
categories = [
    'Grasp / region outside',
    'CLOSE outside prepared',
    'Waypoint non-convergence',
    'Release before CLOSE',
    'Complete rejected',
    'Incomplete / no 331',
]
single_counts = [3, 7, 1, 1, 1, 2]
h4_counts = [1, 2, 5, 0, 0, 5]
assert sum(single_counts) == 15
assert sum(h4_counts) == 13

fig, ax = plt.subplots(figsize=(8.2, 4.6), dpi=220)
y = list(range(len(categories)))
h = 0.36
ax.barh([i - h/2 for i in y], single_counts, h,
        label='single failures (n=15)', color='#7a7a7a')
ax.barh([i + h/2 for i in y], h4_counts, h,
        label='H4 failures (n=13)', color='#2f6fb0')
for i, (a, b) in enumerate(zip(single_counts, h4_counts)):
    if a:
        ax.text(a + 0.1, i - h/2, str(a), va='center', fontsize=9, fontproperties=font)
    if b:
        ax.text(b + 0.1, i + h/2, str(b), va='center', fontsize=9, fontproperties=font)
ax.set_yticks(y)
ax.set_yticklabels(categories, fontproperties=font, fontsize=10)
ax.invert_yaxis()
ax.set_xlabel('failure count', fontproperties=font, fontsize=11)
ax.set_title('失败类型分布（沿用已有 result errors/reasons 分类）',
             fontproperties=font, fontsize=12)
ax.legend(prop=font, loc='lower right')
ax.grid(axis='x', alpha=0.25)
ax.text(0.0, -0.22, 'H4 的 2 个 accepted 不计入失败分布；27/30 无完整 331 帧。',
        transform=ax.transAxes, fontproperties=font, fontsize=9, color='#444')
fig.tight_layout()
fig.savefig(OUT / 'fig2_failure_types.png', bbox_inches='tight')
plt.close(fig)

# Small machine-readable table for the figures.
with (OUT / 'figures_data.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['level', 'single_success', 'single_n', 'h4_success', 'h4_n'])
    for level, a, b, n in zip(levels, single, h4, ns):
        w.writerow([level, a, n, b, n])

print('FIGURES_OK')
