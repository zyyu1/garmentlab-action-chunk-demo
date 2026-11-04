#!/usr/bin/env python3
"""Offline phase analysis of a downloaded a5-rc2-drift-diag release window.

The v1 release_diag includes one anchor state row at the last pre-release hold
step, then the per-step release action rows, the released/retreated samples and
the retreat rows.  The anchor is a diagnostic anchor, so the phase analysis
uses it as the t=0 reference but does not treat it as a new physics step.

Outputs: release_diag_analysis.json, release_diag_segments.csv,
release_diag_events.csv, release_diag_<seed>.png, analysis.md.
"""
import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
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
    return json.loads(Path(path).read_text())


def rigid2d(src, dst):
    a = np.asarray(src, dtype=float)[:, :2]
    b = np.asarray(dst, dtype=float)[:, :2]
    ca, cb = a.mean(0), b.mean(0)
    h = (a - ca).T @ (b - cb)
    u, s, vt = np.linalg.svd(h)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1
        r = vt.T @ u.T
    t = cb - r @ ca
    res = b - (a @ r.T + t)
    return math.degrees(math.atan2(r[1, 0], r[0, 0])), math.sqrt(
        float((res ** 2).sum(axis=1).mean())) * 1000.0


def segment(a, b, dt):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    d = b[:, :2].mean(0) - a[:, :2].mean(0)
    disp = np.linalg.norm(b - a, axis=1)
    ang, rms = rigid2d(a, b)
    return {
        'centroid_dx_mm': float(d[0] * 1000),
        'centroid_dy_mm': float(d[1] * 1000),
        'centroid_mm': float(np.linalg.norm(d) * 1000),
        'rotation_deg': float(ang),
        'vertex_p95_mm': float(np.percentile(disp, 95) * 1000),
        'vertex_max_mm': float(disp.max() * 1000),
        'rigid_rms_mm': float(rms),
        'centroid_speed_mm_s': float(np.linalg.norm(d) * 1000 / dt) if dt > 0 else None,
        'vertex_speed_p95_mm_s': float(np.percentile(disp, 95) * 1000 / dt) if dt > 0 else None,
        'vertex_speed_max_mm_s': float(disp.max() * 1000 / dt) if dt > 0 else None,
        'duration_s': float(dt),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--diag-dir', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--rc2-ref-dir', type=Path)
    args = ap.parse_args()
    d = args.diag_dir.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    with np.load(d / 'evidence/release_diag.npz', allow_pickle=False) as z:
        data = {k: z[k].copy() for k in z.files}
    meta = read(d / 'evidence/release_diag.json')
    contact = read(d / 'contact_report.json')
    result = read(d / 'result.json')
    verdict = read(d / 'diag-verdict.json')
    lab = np.asarray(data['sample_label'])
    state = lab == ''
    V = np.asarray(data['vertices'], dtype=float)[state]
    T = np.asarray(data['sim_time_s'], dtype=float)[state]
    O = np.asarray(data['observed_step'], dtype=int)[state]
    AP = np.asarray(data['gripper_aperture_m'], dtype=float)[state]
    EZ = np.asarray(data['ee_m'], dtype=float)[state, 2]
    ED = np.asarray(data['ee_min_vertex_distance_mm'], dtype=float)[state]
    FD = np.asarray(data['finger_min_vertex_distance_mm'], dtype=float)[state]
    H = np.asarray(data['holding'], bool)[state]
    A = np.asarray(data['attached'], bool)[state]
    C = np.asarray(data['command_holding'], bool)[state]
    E = np.asarray(data['enabled_slots'], bool)[state]
    assert len(O) == 155 and O[0] == 1943 and O[-1] == 2097

    def at(step):
        return int(np.argmin(np.abs(O - step)))

    release = at(1944)
    released = at(1953)
    command = at(1954)
    one_mm = at(1955)
    end = len(O) - 1
    ref = V[0]
    cdisp = np.linalg.norm(V[:, :, :2].mean(1) - ref[:, :2].mean(0), axis=1) * 1000.0
    p95 = np.percentile(np.linalg.norm(V - ref, axis=2), 95, axis=1) * 1000.0
    maxd = np.linalg.norm(V - ref, axis=2).max(axis=1) * 1000.0

    segments = [
        ('anchor_1943_to_release_1944', 0, release),
        ('opening_1944_to_released_1953', release, released),
        ('released_1953_to_command_1954', released, command),
        ('command_1954_to_1mm_1955', command, one_mm),
        ('retreat_1955_to_end_2097', one_mm, end),
        ('opening_total_1943_to_1953', 0, released),
        ('retreat_total_1953_to_2097', released, end),
        ('total_1943_to_2097', 0, end),
    ]
    rows = []
    for name, i, j in segments:
        m = segment(V[i], V[j], T[j] - T[i])
        m.update({'segment': name, 'start_step': int(O[i]), 'end_step': int(O[j])})
        rows.append(m)

    events = [
        {'id': 'A', 'event': 'anchor / last pre-release hold state', 'step': int(O[0]),
         'sim_time_s': float(T[0]), 'source': 'release_start_anchor'},
        {'id': 'B', 'event': 'attachment release / opening starts', 'step': int(O[release]),
         'sim_time_s': float(T[release]), 'source': 'first detached state'},
        {'id': 'C', 'event': 'released snapshot / retreat not yet commanded', 'step': int(O[released]),
         'sim_time_s': float(T[released]), 'source': 'released sample'},
        {'id': 'D', 'event': 'retreat command start', 'step': int(O[command]),
         'sim_time_s': float(T[command]), 'source': 'command_holding false'},
        {'id': 'E', 'event': 'retreat reaches 1 mm upward', 'step': int(O[one_mm]),
         'sim_time_s': float(T[one_mm]), 'source': 'EE z > released EE z + 1 mm'},
        {'id': 'F', 'event': 'retreat end / success-trace t0', 'step': int(O[end]),
         'sim_time_s': float(T[end]), 'source': 'action_end'},
    ]

    # action target identity: release_diag records float32; result stores float64.
    target = np.asarray(meta['action_begin']['targets'][0], dtype=float)
    last_target = np.asarray(result['actions'][-1]['target_pose'], dtype=float)
    target32_equal = bool(np.array_equal(target.astype(np.float32),
                                         last_target.astype(np.float32)))
    target_maxdiff = float(np.max(np.abs(target - last_target)))
    verdict_failed = [k for k, ok in (verdict.get('checks') or {}).items() if not ok]
    evidence_failed = [k for k, ok in (verdict.get('evidence', {}).get('checks') or {}).items()
                       if not ok]

    doc = {
        'protocol': 'a5-rc2-release-diag-analysis',
        'diag_dir': str(d),
        'release_diag': {
            'count': int(len(O)), 'state_rows': 155, 'samples': ['released', 'retreated'],
            'dt_s': float(meta['dt_s']), 'start_step': int(O[0]), 'end_step': int(O[-1]),
            'start_sim_time_s': float(T[0]), 'end_sim_time_s': float(T[-1]),
            'joint_count': int(np.asarray(data['joint_positions']).shape[1]),
            'aperture_finite': int(np.isfinite(AP).sum()),
            'ee_distance_finite': int(np.isfinite(ED).sum()),
            'finger_distance_finite': int(np.isfinite(FD).sum()),
            'contact_events': int(contact.get('event_count', 0)),
            'contact_diagnosis': contact.get('diagnosis'),
            'contact_scope': contact.get('scope'),
            'gripper_aperture_note': meta.get('gripper_aperture_note'),
            'finger_link_names': meta.get('finger_link_names'),
            'physics_mode': meta.get('physics_control_actions', {}).get('mode'),
        },
        'action_target': {
            'float32_equal': target32_equal,
            'float64_max_abs_diff_m': target_maxdiff,
            'note': 'release_diag records the execute() float32 target; result.json stores '
                    'the float64 target. float32 comparison is the identity check.',
        },
        'assessment': {
            'complete_diagnostic': verdict.get('complete_diagnostic'),
            'quality_status': (verdict.get('quality') or {}).get('status'),
            'failed_checks': verdict_failed,
            'evidence_failed': evidence_failed,
            'note': 'release_diag data is present and passive; failed_checks lists '
                    'any audit failures; quality is reported separately and is not '
                    'upgraded to formal success.',
        },
        'events': events,
        'segments': rows,
        'curves': {
            'steps': O.tolist(), 'sim_time_s': T.tolist(),
            'centroid_from_anchor_mm': cdisp.tolist(),
            'p95_from_anchor_mm': p95.tolist(),
            'max_from_anchor_mm': maxd.tolist(),
            'aperture_mm': (AP * 1000.0).tolist(),
            'ee_z_mm': (EZ * 1000.0).tolist(),
            'ee_min_distance_mm': ED.tolist(),
        },
    }
    (out / 'release_diag_analysis.json').write_text(
        json.dumps(doc, indent=2) + '\n', encoding='utf-8')

    fields = ['segment', 'start_step', 'end_step', 'duration_s', 'centroid_dx_mm',
              'centroid_dy_mm', 'centroid_mm', 'rotation_deg', 'vertex_p95_mm',
              'vertex_max_mm', 'rigid_rms_mm', 'centroid_speed_mm_s',
              'vertex_speed_p95_mm_s', 'vertex_speed_max_mm_s']
    with open(out / 'release_diag_segments.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})
    with open(out / 'release_diag_events.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['id', 'event', 'step', 'sim_time_s', 'source'])
        w.writeheader()
        for e in events:
            w.writerow(e)

    # Figure: centroid, P95, aperture+EE z, distance. No dual axis.
    fig, axes = plt.subplots(4, 1, figsize=(12, 12), sharex=True,
                             gridspec_kw={'height_ratios': [1, 1, 0.9, 0.8]})
    fig.suptitle('RC2 release-window diagnostic — seed 4202 single', color=INK,
                 fontsize=13, y=0.985)
    fig.text(0.5, 0.958,
             '157 rows (155 state steps) · contact_events=0 · quality=%s · '
             'release_diag v1; anchor row duplicate is a known v1 audit issue' % (
                 (verdict.get('quality') or {}).get('status')),
             ha='center', color=SECONDARY, fontsize=8.5)
    for ax in axes:
        ax.set_facecolor(SURFACE)
        ax.grid(True, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color(AXIS)
        ax.tick_params(colors=MUTED)
        ax.axvspan(O[0], O[released], color='#cde2fb', alpha=0.35, zorder=0)
        ax.axvspan(O[released], O[-1], color='#f0efec', alpha=0.65, zorder=0)
        for e, style in ((events[0], ':'), (events[1], '--'), (events[2], '--'),
                         (events[3], ':'), (events[4], ':'), (events[5], ':')):
            ax.axvline(e['step'], color=MUTED, linewidth=0.7, linestyle=style, zorder=1)

    ax0, ax1, ax2, ax3 = axes
    ax0.plot(O, cdisp, color=BLUE, linewidth=2)
    ax0.axhline(1.0, color=CRITICAL, linewidth=1.0, linestyle='--')
    ax0.text(O[-1], 1.05, '1 mm', color=CRITICAL, ha='right', va='bottom', fontsize=8)
    ax0.set_ylabel('centroid (mm)')
    ax0.set_title('planar centroid displacement from the release anchor', color=INK, loc='left')
    ax0.set_ylim(0, max(3.5, float(cdisp.max()) * 1.08))

    ax1.plot(O, p95, color=ORANGE, linewidth=2)
    ax1.axhline(3.0, color=CRITICAL, linewidth=1.0, linestyle='--')
    ax1.text(O[-1], 3.08, '3 mm', color=CRITICAL, ha='right', va='bottom', fontsize=8)
    imax = int(np.argmax(p95))
    ax1.annotate('max %.3f mm at step %d' % (p95[imax], O[imax]),
                 (O[imax], p95[imax]), xytext=(-8, 8), textcoords='offset points',
                 color=ORANGE, fontsize=8, ha='right')
    ax1.set_ylabel('vertex P95 (mm)')
    ax1.set_title('vertex drift P95 from the release anchor', color=INK, loc='left')
    ax1.set_ylim(0, max(16.0, float(p95.max()) * 1.12))

    ax2.plot(O, AP * 1000.0, color=BLUE, linewidth=2, label='aperture (mm)')
    ax2.plot(O, EZ * 1000.0, color=ORANGE, linewidth=2, label='EE z (mm)')
    ax2.set_ylabel('mm')
    ax2.set_title('gripper aperture and EE height', color=INK, loc='left')
    ax2.legend(loc='upper left', frameon=False)
    ax2.set_ylim(0, max(200.0, float((EZ * 1000).max()) * 1.08))

    ax3.plot(O, ED, color=BLUE, linewidth=2)
    ax3.set_ylabel('EE min distance (mm)')
    ax3.set_xlabel('physical step (release anchor = 1943)')
    ax3.set_title('EE-to-nearest-vertex distance (geometric evidence, not contact)',
                  color=INK, loc='left')
    ax3.set_ylim(0, max(180.0, float(ED.max()) * 1.08))
    ax3.text(O[0] + 5, float(ED.max()) * 0.92,
             'contact channel: 0 events (not evidence of no contact); '
             'finger-link distance unavailable', color=SECONDARY, fontsize=8)

    handles = [Line2D([0], [0], color=MUTED, linewidth=0.8, linestyle=s)
               for s in (':', '--', '--', ':', ':', ':')]
    labels = ['%s (step %d)' % (e['event'], e['step']) for e in events]
    fig.legend(handles, labels, loc='lower center', ncol=3, frameon=False,
               fontsize=7.5, bbox_to_anchor=(0.5, 0.055))
    fig.text(0.01, 0.008,
             'source: evidence/release_diag.npz (157 rows). Opening shaded blue; '
             'retreat shaded grey. EE/finger distance is geometric evidence; '
             'contact channel is not cloth-particle certification.',
             fontsize=7, color=MUTED, ha='left')
    fig.tight_layout(rect=[0, 0.10, 1, 0.94])
    fig.savefig(out / 'release_diag_4202_single.png', dpi=150)
    plt.close(fig)

    def fmt(v):
        return 'n/a' if v is None else '%.4f' % v

    lines = ['# RC2 release-window diagnostic: 4202 single', '',
             'Source: `%s`' % d, '',
             '## Phase table', '',
             '| phase | steps | duration s | centroid mm | rotation deg | P95 mm | '
             'max mm | rigid RMS mm | speed P95 / max mm/s |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append('| %s | %d-%d | %.4f | %.4f | %.4f | %.4f | %.4f | %.4f | %s / %s |' % (
            r['segment'], r['start_step'], r['end_step'], r['duration_s'],
            r['centroid_mm'], r['rotation_deg'], r['vertex_p95_mm'],
            r['vertex_max_mm'], r['rigid_rms_mm'],
            fmt(r['vertex_speed_p95_mm_s']), fmt(r['vertex_speed_max_mm_s'])))
    lines += ['', '## Events', '',
              '| id | event | step | sim s |',
              '|---|---|---:|---:|']
    for e in events:
        lines.append('| %s | %s | %d | %.6f |' % (e['id'], e['event'], e['step'], e['sim_time_s']))
    lines += ['', '## Findings', '',
              '- The release/opening phase (1943→1953) is a **local, non-rigid** transient: '
              'aperture opens 0→80 mm, EE z stays at ~46.8 mm, centroid peaks ~1.24 mm at '
              '1948 and recoils to 0.85 mm by 1953; P95 grows to ~13.8 mm and max to ~25.6 mm.',
              '- The retreat phase (1955→2097) is **nearly rigid**: centroid 2.28 mm, '
              'rotation -0.80°, P95 4.89 mm, rigid RMS 0.094 mm; the local release '
              'deformation persists but the retreat adds a rigid translation/rotation.',
              '- The formal 210–330 window then continues the rigid sliding/rotation and '
              'fails the 1 mm / 3 mm limits; the release transient is the local-deformation '
              'source, the retreat/window the rigid-motion source.',
              '- Contact channel: subscription created, 0 events. This is not evidence of '
              'no contact. EE distance is 3.8 mm at the anchor, 14.7 mm after release, '
              '21.1 mm at the released snapshot, and 166.0 mm at the retreat end. '
              'Finger-link distance is unavailable (0 finite values); only EE distance is '
              'reported.',
              '- v1.1 run: the anchor is emitted as `release_anchor` (non-state) and action '
              'targets are compared at float32; the diagnostic is complete and no '
              'physics/control/action change occurred. v1 had `complete=False` because '
              '`release_diag_action_target` compared the float32 recorded target to the '
              'float64 result target with atol 1e-9 (float32 cast is exactly equal; max '
              'float64 diff 1.26e-8 m) and `evidence continuous_steps` saw the anchor as a '
              'duplicate `state` at step 1943. Neither was a physics/action change.']
    (out / 'analysis.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('RELEASE_DIAG_ANALYSIS_OK', out)
    print('segments', len(rows), 'state_rows', len(O), 'contact_events',
          contact.get('event_count'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
