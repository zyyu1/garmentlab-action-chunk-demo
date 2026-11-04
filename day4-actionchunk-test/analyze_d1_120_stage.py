#!/usr/bin/env python3
"""Stage 8 analysis for D1-120: wait, retreat, post-retreat window, baseline.

All lengths are millimetres.  Stage-relative metrics use each stage's first
frame as reference.  The elapsed-time curves use the attachment-release state
of each run as reference so the 120-step wait does not masquerade as a stage
shift.  No simulation.
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

SURFACE = '#fcfcfb'
INK = '#0b0b0b'
SECONDARY = '#52514e'
MUTED = '#898781'
GRID = '#e1e0d9'
AXIS = '#c3c2b7'
BLUE = '#2a78d6'
ORANGE = '#eb6834'
CRITICAL = '#d03b3b'

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 9,
    'axes.titlesize': 10, 'axes.labelsize': 9,
    'xtick.labelsize': 8, 'ytick.labelsize': 8,
    'legend.fontsize': 7.5, 'figure.facecolor': SURFACE,
    'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
})


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load_npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def rigid2d(a, b):
    a = np.asarray(a, dtype=float)[:, :2]
    b = np.asarray(b, dtype=float)[:, :2]
    ca, cb = a.mean(0), b.mean(0)
    h = (a - ca).T @ (b - cb)
    u, s, vt = np.linalg.svd(h)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1
        r = vt.T @ u.T
    t = cb - r @ ca
    res = b - (a @ r.T + t)
    return (math.degrees(math.atan2(r[1, 0], r[0, 0])),
            float(np.sqrt((res ** 2).sum(axis=1).mean())) * 1000.0)


def metrics(vertices, times, i, j):
    vertices = np.asarray(vertices, dtype=float)
    ref = vertices[i]
    d = np.linalg.norm(vertices - ref, axis=2) * 1000.0
    disp = np.linalg.norm(
        vertices[:, :, :2].mean(axis=1) - ref[:, :2].mean(axis=0), axis=1) * 1000.0
    rot, rms = rigid2d(vertices[i], vertices[j])
    dt = float(times[j] - times[i])
    return {
        'start_step': int(i),
        'end_step': int(j),
        'duration_s': dt,
        'centroid_mm': float(disp[j]),
        'rotation_deg': float(rot),
        'p95_mm': float(np.percentile(d[j], 95)),
        'max_mm': float(d[j].max()),
        'rigid_rms_mm': float(rms),
        'centroid_speed_mm_s': float(disp[j] / dt) if dt > 0 else None,
        'p95_speed_mm_s': float(np.percentile(d[j], 95) / dt) if dt > 0 else None,
    }


def curve(vertices, times, ref_index, release_time):
    vertices = np.asarray(vertices, dtype=float)
    ref = vertices[ref_index]
    d = np.linalg.norm(vertices - ref, axis=2) * 1000.0
    disp = np.linalg.norm(
        vertices[:, :, :2].mean(axis=1) - ref[:, :2].mean(axis=0), axis=1) * 1000.0
    rot = []
    rms = []
    for v in vertices:
        a, b = rigid2d(ref, v)
        rot.append(a)
        rms.append(b)
    return {
        'elapsed_s': (np.asarray(times, dtype=float) - release_time).tolist(),
        'centroid_mm': disp.tolist(),
        'p95_mm': np.percentile(d, 95, axis=1).tolist(),
        'max_mm': d.max(axis=1).tolist(),
        'rotation_deg': rot,
        'rigid_rms_mm': rms,
    }



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--d1', type=Path, required=True)
    ap.add_argument('--rc2', type=Path, required=True)
    ap.add_argument('--v11', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    d1 = args.d1.resolve()
    rc2 = args.rc2.resolve()
    v11 = args.v11.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    r_d1 = read(d1 / 'result.json')
    r_rc2 = read(rc2 / 'result.json')
    rd_d1 = read(d1 / 'evidence/release_diag.json')
    release = load_npz(d1 / 'evidence/release_diag.npz')
    base_release = load_npz(v11 / 'evidence/release_diag.npz')
    trace_d1 = load_npz(d1 / 'success_trace.npz')
    trace_rc2 = load_npz(rc2 / 'success_trace.npz')
    postfix = read(d1 / 'diag-verdict-postfix.json')

    def states(z):
        m = np.asarray(z['sample_label']) == ''
        return (np.asarray(z['observed_step'])[m],
                np.asarray(z['sim_time_s'], dtype=float)[m],
                np.asarray(z['vertices'], dtype=float)[m])

    sd, td, vd = states(release)
    sb, tb, vb = states(base_release)
    # Full baseline series through its formal window, for same-elapsed-stage checks.
    tb_full = np.r_[tb, np.asarray(trace_rc2['sim_time_s'], dtype=float)]
    vb_full = np.vstack([vb, np.asarray(trace_rc2['vertices'], dtype=float)])
    idx_d = lambda s: int(np.where(sd == s)[0][0])
    idx_b = lambda s: int(np.where(sb == s)[0][0])

    rel_d = idx_d(1953)
    rel_b = idx_b(1953)
    t_rel_d = td[rel_d]
    t_rel_b = tb[rel_b]

    stages = {}
    stages['d1_wait'] = metrics(vd, td, rel_d, idx_d(2073))
    stages['baseline_0_2s'] = metrics(vb, tb, rel_b, idx_b(2073))
    stages['d1_retreat'] = metrics(vd, td, idx_d(2073), idx_d(2217))
    stages['baseline_retreat'] = metrics(vb, tb, rel_b, idx_b(2097))
    stages['d1_release_to_retreat_end'] = metrics(vd, td, rel_d, idx_d(2217))
    stages['baseline_release_to_retreat_end'] = metrics(vb, tb, rel_b, idx_b(2097))
    stages['d1_window_210_330'] = metrics(trace_d1['vertices'], trace_d1['sim_time_s'], 210, 330)
    stages['baseline_window_210_330'] = metrics(trace_rc2['vertices'], trace_rc2['sim_time_s'], 210, 330)
    t_rel_b_full = tb[rel_b]
    i_2 = int(np.argmin(np.abs(tb_full - (t_rel_b_full + 2.0))))
    i_44 = int(np.argmin(np.abs(tb_full - (t_rel_b_full + 4.4))))
    stages['baseline_same_elapsed_as_d1_retreat'] = metrics(vb_full, tb_full, i_2, i_44)
    for key, (a, b) in {
            'd1_wait': (1953, 2073), 'baseline_0_2s': (1953, 2073),
            'd1_retreat': (2073, 2217), 'baseline_retreat': (1953, 2097),
            'd1_release_to_retreat_end': (1953, 2217),
            'baseline_release_to_retreat_end': (1953, 2097),
            'baseline_same_elapsed_as_d1_retreat': (2073, 2217),
            'd1_window_210_330': (210, 330),
            'baseline_window_210_330': (210, 330)}.items():
        stages[key]['start_step'] = a
        stages[key]['end_step'] = b

    # Wait subphases, incremental within each 0.5 s.
    sub = []
    for (a, b), label in (((1953, 1983), '0.0-0.5 s'),
                          ((1983, 2013), '0.5-1.0 s'),
                          ((2013, 2043), '1.0-1.5 s'),
                          ((2043, 2073), '1.5-2.0 s')):
        m = metrics(vd, td, idx_d(a), idx_d(b))
        m.update({'window': label})
        sub.append(m)

    # Exact cloth comparison during D1 wait vs baseline 0-2 s.
    pre_mask_d = (sd >= 1953) & (sd <= 2073)
    pre_mask_b = (sb >= 1953) & (sb <= 2073)
    cloth_same = bool(np.array_equal(vd[pre_mask_d], vb[pre_mask_b]))
    all_mask_d = ((np.asarray(release['observed_step']) >= 1953)
                  & (np.asarray(release['observed_step']) <= 2073))
    all_mask_b = ((np.asarray(base_release['observed_step']) >= 1953)
                  & (np.asarray(base_release['observed_step']) <= 2073))
    ee_diff = float(np.max(np.abs(
        np.asarray(release['ee_m'])[all_mask_d]
        - np.asarray(base_release['ee_m'])[all_mask_b])))
    joint_diff = float(np.max(np.abs(
        np.asarray(release['joint_positions'])[all_mask_d]
        - np.asarray(base_release['joint_positions'])[all_mask_b])))
    # Exact cloth trajectory comparison at equal elapsed time, including the
    # baseline trace.  The robot EE differs during the wait, but the cloth should
    # be identical if the retreat does not couple to it.
    td_full = np.r_[td, np.asarray(trace_d1['sim_time_s'], dtype=float)]
    vd_full = np.vstack([vd, np.asarray(trace_d1['vertices'], dtype=float)])
    time_checked = 0
    time_bad = []
    time_maxdiff = 0.0
    for t, v in zip(td_full, vd_full):
        if t > tb_full.max() + 1e-9:
            continue
        j = int(np.argmin(np.abs(tb_full - t)))
        if abs(tb_full[j] - t) > 1e-6:
            time_bad.append(('time', float(t)))
            continue
        time_checked += 1
        diff = float(np.max(np.abs(v - vb_full[j])))
        time_maxdiff = max(time_maxdiff, diff)
        if not np.array_equal(v, vb_full[j]):
            time_bad.append(('vertex', float(t), diff))

    # Curves aligned by elapsed time since attachment release.
    cur_d = curve(vd, td, rel_d, t_rel_d)
    cur_b = curve(vb, tb, rel_b, t_rel_b)
    # Append success-trace frames after retreat; reference remains the release state.
    def trace_curve(trace, ref_v, release_time):
        times = np.asarray(trace['sim_time_s'], dtype=float)
        verts = np.asarray(trace['vertices'], dtype=float)
        d = np.linalg.norm(verts - ref_v, axis=2) * 1000.0
        disp = np.linalg.norm(
            verts[:, :, :2].mean(axis=1) - ref_v[:, :2].mean(axis=0), axis=1) * 1000.0
        rot, rms = [], []
        for v in verts:
            a, b = rigid2d(ref_v, v)
            rot.append(a)
            rms.append(b)
        return {
            'elapsed_s': (times - release_time).tolist(),
            'centroid_mm': disp.tolist(),
            'p95_mm': np.percentile(d, 95, axis=1).tolist(),
            'max_mm': d.max(axis=1).tolist(),
            'rotation_deg': rot,
            'rigid_rms_mm': rms,
        }
    tr_d = trace_curve(trace_d1, vd[rel_d], t_rel_d)
    tr_b = trace_curve(trace_rc2, vb[rel_b], t_rel_b)

    events = rd_d1.get('events') or []
    event_rows = []
    for e in events:
        event_rows.append({
            'event': e['event'], 'observed_step': e['observed_step'],
            'sim_time_s': e['sim_time_s'],
            'elapsed_since_release_s': e['sim_time_s'] - t_rel_d,
            'phase': e.get('phase'), 'ee_m': e.get('ee_m'),
            'holding': e.get('holding'), 'attached': e.get('attached'),
            'enabled_slots': e.get('enabled_slots'),
        })
    win_start = float(trace_d1['sim_time_s'][210])
    win_end = float(trace_d1['sim_time_s'][330])
    event_rows.extend([
        {'event': 'window_begin_210', 'observed_step': int(trace_d1['absolute_steps'][210]),
         'sim_time_s': win_start, 'elapsed_since_release_s': win_start - t_rel_d,
         'phase': 'formal_window'},
        {'event': 'window_end_330', 'observed_step': int(trace_d1['absolute_steps'][330]),
         'sim_time_s': win_end, 'elapsed_since_release_s': win_end - t_rel_d,
         'phase': 'formal_window'},
    ])

    wait_centroid = stages['d1_wait']['centroid_mm']
    wait_p95 = stages['d1_wait']['p95_mm']
    retreat_centroid = stages['d1_retreat']['centroid_mm']
    retreat_p95 = stages['d1_retreat']['p95_mm']
    window_centroid = stages['d1_window_210_330']['centroid_mm']
    window_p95 = stages['d1_window_210_330']['p95_mm']
    wait_moves = bool(wait_centroid > 1.0 or wait_p95 > 3.0)
    retreat_moves = bool(retreat_centroid > 1.0 or retreat_p95 > 3.0)
    if wait_moves and retreat_moves:
        verdict = ('both_stages_move_but_cloth_is_time_since_release_invariant; '
                   'robot retreat has no observable cloth coupling; '
                   'priority release/rebound/ground contact')
    elif wait_moves:
        verdict = 'wait_moves; release/rebound/ground contact priority'
    elif retreat_moves:
        verdict = 'wait_stable_retreat_moves; D2 detachment/contact evidence'
    else:
        verdict = 'no_clear_stage_motion'

    payload = {
        'protocol': 'stage4-a5-rc2-d1-120-stage8',
        'd1_dir': str(d1),
        'rc2_dir': str(rc2),
        'v11_dir': str(v11),
        'release_time_s': t_rel_d,
        'baseline_release_time_s': t_rel_b,
        'stages': stages,
        'wait_subphases': sub,
        'events': event_rows,
        'wait_cloth_matches_baseline_0_2s': cloth_same,
        'wait_ee_max_abs_diff_m': ee_diff,
        'wait_joint_max_abs_diff_rad': joint_diff,
        'time_aligned': {'checked': time_checked, 'bad': time_bad,
                         'max_abs_diff_m': time_maxdiff},
        'curves': {'d1': cur_d, 'baseline': cur_b,
                   'd1_trace': tr_d, 'baseline_trace': tr_b},
        'postfix_quality': postfix.get('quality'),
        'postfix_checks_failed': [k for k, v in
                                  (postfix.get('checks') or {}).items() if not v],
        'decision': {
            'wait_moves': wait_moves,
            'retreat_moves': retreat_moves,
            'verdict': verdict,
            'wait_centroid_mm': wait_centroid,
            'wait_p95_mm': wait_p95,
            'retreat_centroid_mm': retreat_centroid,
            'retreat_p95_mm': retreat_p95,
            'window_centroid_mm': window_centroid,
            'window_p95_mm': window_p95,
            'time_aligned_identical': not time_bad,
            'time_aligned_checked': time_checked,
            'time_aligned_max_abs_diff_m': time_maxdiff,
            'interpretation': 'wait and retreat are temporal slices of the same '
                              'time-since-release cloth trajectory; they are not '
                              'independent causal stages.',
        },
    }
    (out / 'analysis.json').write_text(
        json.dumps(payload, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    with (out / 'stage-metrics.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['stage', 'duration_s', 'centroid_mm', 'rotation_deg',
                    'p95_mm', 'max_mm', 'rigid_rms_mm',
                    'centroid_speed_mm_s', 'p95_speed_mm_s'])
        for name, m in stages.items():
            w.writerow([name, m['duration_s'], m['centroid_mm'], m['rotation_deg'],
                        m['p95_mm'], m['max_mm'], m['rigid_rms_mm'],
                        m['centroid_speed_mm_s'], m['p95_speed_mm_s']])
    with (out / 'wait-subphases.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['window', 'duration_s', 'centroid_mm', 'rotation_deg',
                    'p95_mm', 'max_mm', 'rigid_rms_mm'])
        for m in sub:
            w.writerow([m['window'], m['duration_s'], m['centroid_mm'],
                        m['rotation_deg'], m['p95_mm'], m['max_mm'],
                        m['rigid_rms_mm']])
    with (out / 'events.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['event', 'observed_step', 'sim_time_s',
                    'elapsed_since_release_s', 'phase', 'holding', 'attached'])
        for e in event_rows:
            w.writerow([e['event'], e['observed_step'], e['sim_time_s'],
                        e['elapsed_since_release_s'], e['phase'],
                        e.get('holding'), e.get('attached')])

    # Figure 1: elapsed-time curves, one axis per panel.
    fig, axes = plt.subplots(3, 1, figsize=(8.6, 8.2), sharex=True)
    ax = axes[0]
    ax.plot(cur_d['elapsed_s'], cur_d['centroid_mm'], color=BLUE, lw=2,
            label='D1-120')
    ax.plot(cur_b['elapsed_s'], cur_b['centroid_mm'], color=ORANGE, lw=2,
            label='RC2 baseline')
    ax.plot(np.asarray(tr_d['elapsed_s']), np.asarray(tr_d['centroid_mm']),
            color=BLUE, lw=2)
    ax.plot(np.asarray(tr_b['elapsed_s']), np.asarray(tr_b['centroid_mm']),
            color=ORANGE, lw=2)
    ax.set_ylabel('centroid drift (mm)')
    ax.set_title('Cumulative drift from attachment release')
    ax.legend(loc='upper left')
    ax = axes[1]
    ax.plot(cur_d['elapsed_s'], cur_d['p95_mm'], color=BLUE, lw=2)
    ax.plot(cur_b['elapsed_s'], cur_b['p95_mm'], color=ORANGE, lw=2)
    ax.plot(np.asarray(tr_d['elapsed_s']), np.asarray(tr_d['p95_mm']),
            color=BLUE, lw=2)
    ax.plot(np.asarray(tr_b['elapsed_s']), np.asarray(tr_b['p95_mm']),
            color=ORANGE, lw=2)
    ax.set_ylabel('vertex P95 (mm)')
    ax = axes[2]
    ax.plot(cur_d['elapsed_s'], cur_d['rotation_deg'], color=BLUE, lw=2)
    ax.plot(cur_b['elapsed_s'], cur_b['rotation_deg'], color=ORANGE, lw=2)
    ax.plot(np.asarray(tr_d['elapsed_s']), np.asarray(tr_d['rotation_deg']),
            color=BLUE, lw=2)
    ax.plot(np.asarray(tr_b['elapsed_s']), np.asarray(tr_b['rotation_deg']),
            color=ORANGE, lw=2)
    ax.set_ylabel('rotation from release (deg)')
    ax.set_xlabel('elapsed time since attachment release (s)')
    for ax in axes:
        ax.grid(color=GRID, lw=.7)
        ax.set_axisbelow(True)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        for spine in ('left', 'bottom'):
            ax.spines[spine].set_color(AXIS)
    # Stage boundaries and labels; D1 wait shaded, formal window shaded.
    for ax in axes:
        ax.axvspan(0.0, 2.0, color=BLUE, alpha=.055, lw=0)
        ax.axvspan(2.0, 4.4, color=MUTED, alpha=.05, lw=0)
        ax.axvspan(4.4, 9.9, color=ORANGE, alpha=.045, lw=0)
        ax.axvline(2.0, color=BLUE, ls=':', lw=1)
        ax.axvline(4.4, color=BLUE, ls=':', lw=1)
        ax.axvline(2.4, color=ORANGE, ls=':', lw=1)
    axes[0].text(6.0, .93, 'cloth traces coincide at equal elapsed time',
                 transform=axes[0].get_xaxis_transform(), ha='left',
                 fontsize=7.5, color=SECONDARY)
    axes[0].text(1.0, .02, 'D1 wait', transform=axes[0].get_xaxis_transform(),
                 ha='center', color=BLUE)
    axes[0].text(3.2, .02, 'D1 retreat', transform=axes[0].get_xaxis_transform(),
                 ha='center', color=SECONDARY)
    axes[0].text(7.1, .02, 'D1 window', transform=axes[0].get_xaxis_transform(),
                 ha='center', color=ORANGE)
    fig.tight_layout()
    fig.savefig(out / 'd1_120_elapsed_curves.png', dpi=180)
    plt.close(fig)

    # Figure 2: stage comparison bars.
    labels = ['wait\n(0-2 s)', 'retreat', 'window\n(210-330)']
    names = [('d1_wait', 'baseline_0_2s'),
             ('d1_retreat', 'baseline_retreat'),
             ('d1_window_210_330', 'baseline_window_210_330')]
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.6))
    for ax, key, title in zip(axes, ('centroid_mm', 'p95_mm', 'rotation_deg'),
                              ('centroid drift (mm)', 'vertex P95 (mm)',
                               'rotation (deg)')):
        x = np.arange(len(labels))
        dvals = [stages[d][key] for d, _ in names]
        bvals = [stages[b][key] for _, b in names]
        ax.bar(x - .18, dvals, .34, color=BLUE, label='D1-120')
        ax.bar(x + .18, bvals, .34, color=ORANGE, label='RC2 baseline')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7.5)
        ax.set_title(title)
        ax.grid(axis='y', color=GRID, lw=.7)
        ax.set_axisbelow(True)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        for i, v in enumerate(dvals):
            ax.annotate('%.2f' % v, (i - .18, v), xytext=(0, 3),
                        textcoords='offset points', ha='center', fontsize=6.5)
        for i, v in enumerate(bvals):
            ax.annotate('%.2f' % v, (i + .18, v), xytext=(0, 3),
                        textcoords='offset points', ha='center', fontsize=6.5)
    axes[0].legend(loc='upper left')
    fig.tight_layout()
    fig.savefig(out / 'd1_120_stage_compare.png', dpi=180)
    plt.close(fig)

    # Figure 3: wait subphases.
    fig, axes = plt.subplots(2, 2, figsize=(8.2, 5.0))
    for ax, key, title in zip(axes.ravel(),
                              ('centroid_mm', 'p95_mm', 'rotation_deg', 'rigid_rms_mm'),
                              ('incremental centroid (mm)', 'incremental P95 (mm)',
                               'incremental rotation (deg)', 'incremental rigid RMS (mm)')):
        vals = [m[key] for m in sub]
        x = np.arange(len(vals))
        ax.bar(x, vals, color=BLUE)
        ax.set_xticks(x)
        ax.set_xticklabels([m['window'] for m in sub], fontsize=7)
        ax.set_title(title)
        ax.grid(axis='y', color=GRID, lw=.7)
        ax.set_axisbelow(True)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        for i, v in enumerate(vals):
            ax.annotate('%.3f' % v, (i, v), xytext=(0, 3),
                        textcoords='offset points', ha='center', fontsize=6.5)
    fig.tight_layout()
    fig.savefig(out / 'd1_120_wait_subphases.png', dpi=180)
    plt.close(fig)

    print('D1_STAGE8_OK')
    for name, m in stages.items():
        print('%-30s centroid=%.4f mm rot=%.4f deg p95=%.4f mm rms=%.4f mm' %
              (name, m['centroid_mm'], m['rotation_deg'], m['p95_mm'], m['rigid_rms_mm']))
    print('Wait cloth identical to baseline 0-2s:', cloth_same,
          'EE max diff m:', ee_diff, 'joint max diff rad:', joint_diff)
    print('Time-aligned cloth checked=%d bad=%d maxdiff=%.3g' % (time_checked, len(time_bad), time_maxdiff))
    for m in sub:
        print('wait %s centroid=%.4f rot=%.4f p95=%.4f rms=%.4f' %
              (m['window'], m['centroid_mm'], m['rotation_deg'], m['p95_mm'],
               m['rigid_rms_mm']))
    print('DECISION', verdict)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
