"""Summarize the seven hold120 rc7 cases, pairs and hold timing."""
import csv
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE / 'results' / 'RC8B_L2_DIAG_20261105'
RUNS = [
    (1, 4100, 'single', BASE / 'hold120_rc7' / 'day4-a5-rc2-l1-20261105-081311-735952'),
    (2, 4100, 'arc4', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-l1-20261105-083859-341524'),
    (3, 4202, 'single', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-pfs1-observation-v2-20261105-085248-353214'),
    (4, 4202, 'arc4', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-pfs1-observation-v2-20261105-091038-643466'),
    (5, 4302, 'single', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-pfs1-observation-v2-20261105-092821-242307'),
    (6, 4302, 'arc4', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-pfs1-observation-v2-20261105-094700-143205'),
    (7, 4201, 'single', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-pfs1-observation-v2-20261105-100445-893957'),
]
rows = []
for slot, seed, mode, d in RUNS:
    v = json.loads((d / 'a5-verdict.json').read_text())['criteria']
    r = json.loads((d / 'result.json').read_text())
    h = None
    hp = d / 'recovery_hold_metadata.json'
    if hp.is_file():
        h = json.loads(hp.read_text())
    fg = (v.get('final_geometry') or {}).get('metrics') or {}
    rows.append({
        'slot': slot, 'seed': seed, 'mode': mode, 'quality': v['status'],
        'centroid_mm': v['stability']['centroid_drift_max_m'] * 1000,
        'p95_mm': v['stability']['vertex_drift_p95_max_m'] * 1000,
        'stable': v['checks']['stable'], 'geometry': v['checks']['geometry_entire_window'],
        'stationary_mm': fg.get('stationary_drift_mean_m', float('nan')) * 1000,
        'fold_extent': (r.get('fold_metrics') or {}).get('extent'),
        'hold_steps': None if h is None else h['completed_steps'],
        'hold_frames': None if h is None else h['frames'],
        'hold_duration_s': None if h is None else h['duration_s'],
        'hold_begin': None if h is None else h['hold_begin'],
        'hold_end': None if h is None else h['hold_end'],
        'run': str(d),
    })

with (BASE / 'hold120_rc7_r2_resume' / 'cases.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['slot', 'seed', 'mode', 'quality', 'centroid_mm', 'p95_mm', 'geometry', 'stable',
                'stationary_mm', 'hold_steps', 'hold_frames', 'hold_duration_s'])
    for r in rows:
        w.writerow([r['slot'], r['seed'], r['mode'], r['quality'], round(r['centroid_mm'], 6),
                    round(r['p95_mm'], 6), r['geometry'], r['stable'],
                    round(r['stationary_mm'], 6), r['hold_steps'], r['hold_frames'], r['hold_duration_s']])

pairs = {}
for seed, sslot, aslot in ((4100, 1, 2), (4202, 3, 4), (4302, 5, 6)):
    s = next(r for r in rows if r['slot'] == sslot)
    a = next(r for r in rows if r['slot'] == aslot)
    src = json.loads((Path(s['run']) / 'result.json').read_text())
    arc = json.loads((Path(a['run']) / 'result.json').read_text())
    if seed == 4100:
        x = src['actions'][0]['target_pose']; y = arc['actions'][0]['target_pose']
    else:
        x = next(z['target_pose'] for z in src['actions'] if z['label'] == 'fold_approach')
        y = next(z['target_pose'] for z in arc['actions'] if z['label'] == 'fold_approach')
    d = max(abs(float(p) - float(q)) for p, q in zip(x, y))
    timing = None
    if seed != 4100:
        timing = {
            'single_steps': s['hold_steps'], 'arc_steps': a['hold_steps'],
            'single_duration': s['hold_duration_s'], 'arc_duration': a['hold_duration_s'],
            'same_steps': s['hold_steps'] == a['hold_steps'] == 120,
            'same_duration': abs(s['hold_duration_s'] - a['hold_duration_s']) <= 1e-9,
        }
    pairs[seed] = {'target_max_abs_m': d, 'pass': d <= 1e-6, 'hold_timing': timing}

summary = {
    'cases': rows,
    'all_six_positives_accepted': all(r['quality'] == 'accepted' for r in rows if r['slot'] <= 6),
    'slot7_quality': next(r['quality'] for r in rows if r['slot'] == 7),
    'pairs': pairs,
}
(BASE / 'hold120_rc7_r2_resume' / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
for r in rows:
    print(r['slot'], r['seed'], r['mode'], r['quality'], round(r['centroid_mm'], 6),
          round(r['p95_mm'], 6), r['hold_steps'])
print('pairs', {k: (round(v['target_max_abs_m'], 9), v['pass'], v['hold_timing']) for k, v in pairs.items()})
print('six positives', summary['all_six_positives_accepted'], 'slot7', summary['slot7_quality'])
