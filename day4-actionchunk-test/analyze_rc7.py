#!/usr/bin/env python3
"""Offline summary of the rc7 seven-case RC.

Reads the downloaded batch ledger, the seven result directories and the
per-case rc7_semantics.json files; computes evaluator stability, release-window
speeds from world-vertex finite differences, and writes cases.csv/cases.json
plus a stability figure.  No simulation.
"""
import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

SURFACE = '#fcfcfb'; GRID = '#e1e0d9'; AXIS = '#c3c2b7'; BLUE = '#2a78d6'
ORANGE = '#eb6834'; RED = '#d03b3b'; GREEN = '#2e8b57'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
                     'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
                     'savefig.facecolor': SURFACE})


def read(p, default=None):
    p = Path(p)
    if not p.is_file():
        return default
    return json.loads(p.read_text(encoding='utf-8'))


def load(p):
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def unique_indices(times, i=0, j=None):
    times = np.asarray(times, float)
    if j is None:
        j = len(times) - 1
    out, last = [], None
    for k in range(int(i), int(j) + 1):
        t = float(times[k])
        if last is None or t - last > 1e-9:
            out.append(k)
            last = t
    return out


def fd_window(V, times):
    V = np.asarray(V, float); times = np.asarray(times, float)
    idx = unique_indices(times)
    if len(idx) < 2:
        return None
    dt = np.diff(times[idx])
    p = np.linalg.norm(V[idx[1:]] - V[idx[:-1]], axis=2).mean(1) * 1000 / dt
    c = np.linalg.norm(V[idx[1:]].mean(1) - V[idx[:-1]].mean(1), axis=1) * 1000 / dt
    return {'n_frames': len(idx), 'duration_s': float(times[idx[-1]] - times[idx[0]]),
            'particle_mean_speed_mean_mm_s': float(p.mean()),
            'centroid_speed_mean_mm_s': float(c.mean())}


def case_row(slot, seed, mode, run, sem):
    r = read(Path(run) / 'result.json', {}) or {}
    v = read(Path(run) / 'a5-verdict.json', {}) or {}
    crit = v.get('criteria') or {}
    checks = crit.get('checks') or {}
    stab = crit.get('stability') or {}
    first = load(Path(run) / 'pfs1_first_0_5s.npz')
    rel = load(Path(run) / 'pfs1_release_steps.npz')
    f05 = fd_window(first['vertices'], first['sim_time_s'])
    tb = float(np.asarray(rel['sim_time_s'], float)[0])
    rt = np.asarray(rel['sim_time_s'], float)
    steady_idx = [i for i in range(len(rt)) if tb + 1.5 - 1e-9 <= rt[i] <= tb + 8.0 + 1e-9]
    steady = fd_window(np.asarray(rel['vertices'], float)[steady_idx[0]:steady_idx[-1] + 1],
                       rt[steady_idx[0]:steady_idx[-1] + 1]) if steady_idx else None
    zmin = float(np.asarray(rel['vertices'], float)[:, :, 2].min() * 1000)
    pair = (sem or {}).get('pair') or {}
    return {
        'slot': slot, 'seed': seed, 'mode': mode,
        'level': (r.get('initial_case') or {}).get('level'),
        'quality': crit.get('status'),
        'centroid_mm': float(stab.get('centroid_drift_max_m', float('nan')) * 1000),
        'p95_mm': float(stab.get('vertex_drift_p95_max_m', float('nan')) * 1000),
        'geometry': bool(checks.get('geometry_entire_window')),
        'stable': bool(checks.get('stable')),
        'held': bool(checks.get('held')),
        'released': bool(checks.get('released_continuously')),
        'first_0_5s_centroid_mm_s': f05['centroid_speed_mean_mm_s'] if f05 else None,
        'first_0_5s_particle_mm_s': f05['particle_mean_speed_mean_mm_s'] if f05 else None,
        'steady_centroid_mm_s': steady['centroid_speed_mean_mm_s'] if steady else None,
        'steady_particle_mm_s': steady['particle_mean_speed_mean_mm_s'] if steady else None,
        'z_min_mm': zmin,
        'actions': r.get('action_count'),
        'horizons': r.get('call_horizons'),
        'semantics_valid': bool((sem or {}).get('observation_semantics_valid')),
        'file_complete': bool((sem or {}).get('file_complete')),
        'pair_pass': bool((sem or {}).get('pair_pass')) if sem else None,
        'pair_max_mm': float(pair.get('target_max_abs_m', 0.0) * 1000) if pair else None,
        'errors': r.get('errors'),
        'run': str(run),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', type=Path, required=True, help='downloaded batch ledger directory')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--remote-root', default='/root/autodl-tmp')
    ap.add_argument('--local-root', type=Path, default=None)
    args = ap.parse_args()
    batch, out = args.batch.resolve(), args.out.resolve()
    local_root = (args.local_root or batch.parent).resolve()
    out.mkdir(parents=True, exist_ok=True)

    def local_run(run):
        run = str(run)
        if run.startswith(args.remote_root.rstrip('/') + '/'):
            return local_root / run[len(args.remote_root.rstrip('/')) + 1:]
        return Path(run)

    rows = []
    for line in (batch / 'batch.jsonl').read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        sem = rec.get('semantics') or read(batch / ('slot%d-semantics.json' % rec['slot']), {})
        rows.append(case_row(rec['slot'], rec['seed'], rec['mode'], local_run(rec['run']), sem))
    rows.sort(key=lambda r: r['slot'])

    with (out / 'cases.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        keys = ['slot', 'seed', 'level', 'mode', 'quality', 'centroid_mm', 'p95_mm',
                'geometry', 'stable', 'held', 'released',
                'first_0_5s_centroid_mm_s', 'first_0_5s_particle_mm_s',
                'steady_centroid_mm_s', 'steady_particle_mm_s', 'z_min_mm',
                'actions', 'horizons', 'file_complete', 'semantics_valid', 'pair_pass', 'pair_max_mm']
        w.writerow(keys)
        for r in rows:
            w.writerow([r[k] for k in keys])

    summary = {
        'cases': len(rows),
        'accepted': sum(1 for r in rows if r['quality'] == 'accepted'),
        'rejected': sum(1 for r in rows if r['quality'] == 'rejected'),
        'all_six_positives_accepted': all(r['quality'] == 'accepted' for r in rows if r['seed'] != 4201),
        'pairs_pass': all(r['pair_pass'] for r in rows if r['pair_pass'] is not None),
        'all_evidence_valid': all(r['file_complete'] and r['semantics_valid'] for r in rows),
        'rows': rows,
    }
    (out / 'cases.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    fig, axes = plt.subplots(1, 2, figsize=(10.6, 3.6))
    labels = ['%s %s' % (r['seed'], r['mode']) for r in rows]
    x = np.arange(len(rows))
    axes[0].bar(x - 0.2, [r['centroid_mm'] for r in rows], width=0.38, color=BLUE, label='centroid drift')
    axes[0].bar(x + 0.2, [r['p95_mm'] for r in rows], width=0.38, color=ORANGE, label='vertex P95')
    axes[0].axhline(1.0, color=RED, lw=1, ls=':', label='centroid limit 1 mm')
    axes[0].axhline(3.0, color=RED, lw=1, ls='-.', label='P95 limit 3 mm')
    axes[0].set_xticks(x); axes[0].set_xticklabels(labels, rotation=30, ha='right')
    axes[0].set_ylabel('mm'); axes[0].set_title('formal window 210-330 drift')
    axes[0].legend(fontsize=7)
    axes[1].bar(x - 0.2, [r['first_0_5s_centroid_mm_s'] or 0 for r in rows], width=0.38, color=BLUE,
                label='first 0.5 s centroid')
    axes[1].bar(x + 0.2, [r['steady_centroid_mm_s'] or 0 for r in rows], width=0.38, color=GREEN,
                label='steady 1.5-8 s centroid')
    axes[1].set_xticks(x); axes[1].set_xticklabels(labels, rotation=30, ha='right')
    axes[1].set_ylabel('mm/s'); axes[1].set_title('post-release centroid speed')
    axes[1].legend(fontsize=7)
    for ax in axes:
        ax.grid(color=GRID, lw=.7, axis='y'); ax.set_axisbelow(True)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        for s in ('left', 'bottom'):
            ax.spines[s].set_color(AXIS)
    fig.tight_layout(); fig.savefig(out / 'rc7_cases.png', dpi=180); plt.close(fig)

    print('RC7_SUMMARY', json.dumps({k: summary[k] for k in
          ('cases', 'accepted', 'rejected', 'all_six_positives_accepted', 'pairs_pass',
           'all_evidence_valid')}))
    for r in rows:
        print('CASE', r['slot'], r['seed'], r['mode'], r['quality'],
              round(r['centroid_mm'], 4), round(r['p95_mm'], 4),
              'pair', r['pair_max_mm'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
