#!/usr/bin/env python3
"""D2-E step 4: offline sustained-slip characterization from D1/D2-C.

No simulation.  Release t=0 is the last attached state (D1 release anchor,
D2-C last preopen state).  For D2-C the zero-step released sample shares t=0
and is not treated as a separate physics interval.  Bins are elapsed seconds
after t=0; all lengths are millimetres, angles degrees, times seconds.
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


def load(path):
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


def angle_diff(a, b):
    d = (float(a) - float(b) + 180.0) % 360.0 - 180.0
    return d


def stats(v, times, i, j):
    """Stats over frames i..j inclusive; velocities over i..j-1 intervals."""
    if j <= i:
        raise ValueError('empty interval')
    dt = float(times[j] - times[i])
    c0 = v[i].mean(0)
    c1 = v[j].mean(0)
    cvec = (c1[:2] - c0[:2]) * 1000.0
    dts = np.diff(times[i:j + 1])
    if np.any(dts <= 0):
        raise ValueError('non-increasing time in stats')
    spacing = np.linalg.norm(v[i + 1:j + 1].mean(1) - v[i:j].mean(1), axis=1) * 1000.0
    pdisp = np.linalg.norm(v[i + 1:j + 1] - v[i:j], axis=2).mean(1) * 1000.0
    cs = spacing / dts
    ps = pdisp / dts
    ang = np.array([abs(rigid2d(v[k], v[k + 1])[0]) / dts[k - i]
                    for k in range(i, j)])
    d = np.linalg.norm(v[j] - v[i], axis=1) * 1000.0
    return {
        'n_frames': int(j - i + 1),
        'n_intervals': int(j - i),
        'duration_s': dt,
        'centroid_mm': float(np.linalg.norm(cvec)),
        'p95_mm': float(np.percentile(d, 95)),
        'max_mm': float(d.max()),
        'centroid_speed_mean_mm_s': float(cs.mean()),
        'centroid_speed_max_mm_s': float(cs.max()),
        'particle_mean_speed_mean_mm_s': float(ps.mean()),
        'particle_mean_speed_max_mm_s': float(ps.max()),
        'angular_speed_mean_deg_s': float(ang.mean()),
        'angular_speed_max_deg_s': float(ang.max()),
        'rotation_deg': float(rigid2d(v[i], v[j])[0]),
        'rigid_rms_mm': float(rigid2d(v[i], v[j])[1]),
        'direction_deg': float(math.degrees(math.atan2(cvec[1], cvec[0]))),
        'direction_vector_mm': cvec.tolist(),
        'z_min_m': float(v[i:j + 1, :, 2].min()),
        'z_p95_m': float(np.percentile(v[i:j + 1, :, 2], 95)),
        'z_max_m': float(v[i:j + 1, :, 2].max()),
    }


def build_series(run, d2c):
    z = load(run / 'evidence' / 'release_diag.npz')
    tr = load(run / 'success_trace.npz')
    hold = load(run / 'pre_release_hold.npz')
    phases = np.asarray(z['phase'])
    attached = np.asarray(z['attached'], bool)
    ztime = np.asarray(z['sim_time_s'], float)
    hold_v = np.asarray(hold['vertices'], float)
    anchor = np.where(phases == 'release_start_anchor')[0]
    if len(anchor) != 1:
        raise ValueError('No unique release_start_anchor')
    anchor = int(anchor[0])
    t_anchor = float(ztime[anchor])
    if d2c:
        candidates = [i for i in range(len(phases))
                      if phases[i] == 'release_opening' and attached[i]]
        t0 = int(candidates[-1])
        free = next(i for i in range(t0 + 1, len(phases))
                    if phases[i] == 'delay' and not attached[i])
    else:
        t0 = anchor
        free = next(i for i in range(t0 + 1, len(phases))
                    if phases[i] == 'release_opening' and not attached[i])
    t0_time = float(ztime[t0])
    t_free_time = float(ztime[free])

    items = []
    seen = set()
    # Hold frames end at the anchor time; exclude the final duplicate anchor.
    n = len(hold_v)
    for k in range(n):
        t = t_anchor - (n - 1 - k) / 60.0
        if t >= t_anchor - 1e-6:
            continue
        items.append((t, hold_v[k], 'prehold'))
        seen.add(round(t, 6))
    # Release-diagnostic rows.  At D2-C t0 the attached preopen row comes
    # before the zero-step released sample, so first occurrence is retained.
    for i in range(len(ztime)):
        t = float(ztime[i])
        key = round(t, 6)
        if key in seen:
            continue
        seen.add(key)
        items.append((t, z['vertices'][i], 'release'))
    last = max(t for t, _, _ in items)
    # The trace starts at retreat end, the same time/state as the last
    # release-diagnostic row; append only later rows.
    for i in range(len(tr['sim_time_s'])):
        t = float(tr['sim_time_s'][i])
        if t <= last + 1e-6:
            continue
        key = round(t, 6)
        if key in seen:
            continue
        seen.add(key)
        items.append((t, tr['vertices'][i], 'trace'))
    items.sort(key=lambda x: x[0])
    times = np.asarray([x[0] for x in items], float)
    verts = np.asarray([x[1] for x in items], float)
    src = np.asarray([x[2] for x in items])
    t0i = int(np.argmin(np.abs(times - t0_time)))
    freei = int(np.argmin(np.abs(times - t_free_time)))
    if abs(times[t0i] - t0_time) > 1e-6 or abs(times[freei] - t_free_time) > 1e-6:
        raise ValueError('Merged series lost t0/free boundary')
    return {
        'z': z, 'trace': tr, 'hold': hold, 't0': t0_time,
        't_free': t_free_time, 't0i': t0i, 'freei': freei,
        'times': times, 'vertices': verts, 'source': src,
        'phases': phases, 'attached': attached,
    }


def bin_rows(series, tag, bin_s=0.5, end_s=10.0):
    t0 = series['t0']
    times = series['times']
    v = series['vertices']
    rows = []
    for b in range(int(round(end_s / bin_s))):
        a = t0 + b * bin_s
        z = t0 + (b + 1) * bin_s
        idx = [i for i in range(len(times)) if a - 1e-6 <= times[i] <= z + 1e-6]
        if len(idx) < 2:
            continue
        st = stats(v, times, idx[0], idx[-1])
        st.update({
            'run': tag,
            'bin_start_s': b * bin_s,
            'bin_end_s': (b + 1) * bin_s,
            'partial': bool(times[idx[-1]] < z - 1e-6),
            'z_min_mm': st['z_min_m'] * 1000.0,
            'below_contact_offset_mm': (0.01 - st['z_min_m']) * 1000.0,
            'ground_penetration_mm': max(0.0, -st['z_min_m'] * 1000.0),
            'x_min_m': float(v[idx[0]:idx[-1] + 1, :, 0].min()),
            'x_max_m': float(v[idx[0]:idx[-1] + 1, :, 0].max()),
            'y_min_m': float(v[idx[0]:idx[-1] + 1, :, 1].min()),
            'y_max_m': float(v[idx[0]:idx[-1] + 1, :, 1].max()),
        })
        rows.append(st)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--d1', type=Path, required=True)
    ap.add_argument('--d2c', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    d1 = args.d1.resolve()
    d2c = args.d2c.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    runs = {}
    for tag, run, is_d2c in (('D1', d1, False), ('D2-C', d2c, True)):
        s = build_series(run, is_d2c)
        times = s['times']
        # pre-release: last 0.5 s ending at t0
        pre_idx = [i for i in range(len(times))
                   if s['t0'] - 0.5 - 1e-6 <= times[i] <= s['t0'] + 1e-6]
        pre = stats(s['vertices'], times, pre_idx[0], pre_idx[-1])
        rel = stats(s['vertices'], times, s['t0i'], s['freei'])
        bins = bin_rows(s, tag)
        formal = stats(np.asarray(s['trace']['vertices'], float),
                       np.asarray(s['trace']['sim_time_s'], float), 210, 330)
        runs[tag] = {'series': s, 'pre': pre, 'release': rel, 'bins': bins,
                     'formal': formal}

    # Time/unit checks on the merged physics series.
    checks = {}
    for tag, r in runs.items():
        s = r['series']
        dts = np.diff(s['times'])
        dts = dts[dts > 1e-6]
        checks[tag] = {
            'n_frames': int(len(s['times'])),
            'time_range_s': [float(s['times'][0]), float(s['times'][-1])],
            'dt_min_s': float(dts.min()),
            'dt_max_s': float(dts.max()),
            'dt_all_1_60': bool(np.allclose(dts, 1 / 60, atol=1e-6, rtol=0)),
            't0_t_rel_s': float(s['t0'] - s['times'][0]),
            'stage_units_m': 1.0,
            'ground_z_m': 0.0,
            'particle_contact_offset_m': 0.01,
            'trace_absolute_first_last': [
                int(np.asarray(s['trace']['absolute_steps'])[0]),
                int(np.asarray(s['trace']['absolute_steps'])[-1])],
            'trace_len': int(len(s['trace']['absolute_steps'])),
        }

    # 0.5 s table and summary facts.
    rows = []
    for tag in ('D1', 'D2-C'):
        for b in runs[tag]['bins']:
            rows.append(b)
    with (out / 'slip_bins.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['run', 'bin_start_s', 'bin_end_s', 'partial', 'n_intervals',
                    'centroid_speed_mean_mm_s', 'centroid_speed_max_mm_s',
                    'particle_mean_speed_mean_mm_s', 'angular_speed_mean_deg_s',
                    'angular_speed_max_deg_s', 'rotation_deg', 'rigid_rms_mm',
                    'direction_deg', 'centroid_mm', 'z_min_mm',
                    'below_contact_offset_mm', 'ground_penetration_mm',
                    'x_min_m', 'x_max_m', 'y_min_m', 'y_max_m'])
        for b in rows:
            w.writerow([b['run'], b['bin_start_s'], b['bin_end_s'], b['partial'],
                        b['n_intervals'], b['centroid_speed_mean_mm_s'],
                        b['centroid_speed_max_mm_s'],
                        b['particle_mean_speed_mean_mm_s'],
                        b['angular_speed_mean_deg_s'],
                        b['angular_speed_max_deg_s'], b['rotation_deg'],
                        b['rigid_rms_mm'], b['direction_deg'], b['centroid_mm'],
                        b['z_min_mm'], b['below_contact_offset_mm'],
                        b['ground_penetration_mm'], b['x_min_m'], b['x_max_m'],
                        b['y_min_m'], b['y_max_m']])

    # Sustained/tail facts.
    tail = {}
    for tag in ('D1', 'D2-C'):
        bs = runs[tag]['bins']
        early = [b for b in bs if b['bin_start_s'] < 0.5]
        steady = [b for b in bs if b['bin_start_s'] >= 1.5]
        late = [b for b in bs if b['bin_start_s'] >= 8.0]
        def mean(key, seq):
            return float(np.mean([b[key] for b in seq])) if seq else None
        tail[tag] = {
            'early_centroid_speed_mm_s': mean('centroid_speed_mean_mm_s', early),
            'steady_centroid_speed_mm_s': mean('centroid_speed_mean_mm_s', steady),
            'late_centroid_speed_mm_s': mean('centroid_speed_mean_mm_s', late),
            'steady_particle_speed_mm_s': mean('particle_mean_speed_mean_mm_s', steady),
            'steady_angular_speed_deg_s': mean('angular_speed_mean_deg_s', steady),
            'steady_direction_deg': mean('direction_deg', steady),
            'steady_direction_std_deg': float(np.std([b['direction_deg'] for b in steady])),
            'z_min_mm_min': float(min(b['z_min_mm'] for b in bs)),
            'z_min_mm_max': float(max(b['z_min_mm'] for b in bs)),
            'below_offset_mm_max': float(max(b['below_contact_offset_mm'] for b in bs)),
            'ground_penetration_mm_max': float(max(b['ground_penetration_mm'] for b in bs)),
            'tail_over_early': (mean('centroid_speed_mean_mm_s', late)
                                / mean('centroid_speed_mean_mm_s', early)),
            'steady_over_early': (mean('centroid_speed_mean_mm_s', steady)
                                  / mean('centroid_speed_mean_mm_s', early)),
        }

    # Formal window deltas and direction differences.
    for tag in ('D1', 'D2-C'):
        r = runs[tag]
        r['release_direction_deg'] = r['release']['direction_deg']
        r['pre_direction_deg'] = r['pre']['direction_deg']
        for b in r['bins']:
            b['dir_from_release_deg'] = angle_diff(
                b['direction_deg'], r['release_direction_deg'])
            b['dir_from_pre_deg'] = angle_diff(
                b['direction_deg'], r['pre_direction_deg'])
        r['formal']['dir_from_release_deg'] = angle_diff(
            r['formal']['direction_deg'], r['release_direction_deg'])
        r['formal']['z_min_mm'] = r['formal']['z_min_m'] * 1000.0
        r['formal']['below_contact_offset_mm'] = (0.01 - r['formal']['z_min_m']) * 1000.0

    payload = {
        'scope': 'D2-E step 4 offline sustained-slip characterization; no simulation',
        't0_definition': 'D1 release_start_anchor; D2-C last attached preopen state; released sample shares t0 for D2-C',
        'time_units': 'seconds; positions metres in source arrays, reported millimetres; angles degrees',
        'checks': checks,
        'pre_release': {tag: runs[tag]['pre'] for tag in ('D1', 'D2-C')},
        'release': {tag: runs[tag]['release'] for tag in ('D1', 'D2-C')},
        'bins': {tag: runs[tag]['bins'] for tag in ('D1', 'D2-C')},
        'steady_facts': tail,
        'formal': {tag: runs[tag]['formal'] for tag in ('D1', 'D2-C')},
        'contact_note': 'contact_report.json has 0 robot-rigid events and a robot-only scope; it cannot observe cloth-ground contact. Zero events are not evidence of no contact.',
        'facts': [
            'The release impulse is ~11 mm/s centroid and ~17.4 mm/s particle mean; it is followed by a rapid decay in the first second.',
            'From 1.5 s to 10 s the centroid speed is nearly constant at ~1.0 mm/s and the angular speed at ~0.36 deg/s; there is no further decay in the observed window.',
            'The sustained slip direction is ~26-28 deg (world XY), about 25 deg away from the release direction (~1 deg); it is stable after the transient.',
            'Cloth z_min stays ~9.876 mm; no ground penetration; it remains ~0.123-0.128 mm below the 10 mm particle contact offset. This is geometric, not force evidence.',
            'D1 and D2-C show the same sustained regime; D2-C is only a few percent slower in the steady window.'
        ],
        'speculation': [
            'A constant ~1 mm/s planar speed with ~0.36 deg/s rotation and near-constant z_min is consistent with a steady contact/friction-limited sliding regime, but no cloth-ground force or impulse is available.',
            'The ~25 deg direction change from release to sustained slip suggests the later motion is not just the release impulse direction; anisotropic friction, residual deformation, or contact patch evolution are possible, but unverified.',
            'The 0.123-0.128 mm below-contact-offset geometry is consistent with the particle skin being near/at the ground, but it does not prove contact force.',
            'The slow steady speed may be sensitive to particleFrictionScale/friction or ground material, but this has not been tested.'
        ],
    }
    (out / 'slip_summary.json').write_text(
        json.dumps(payload, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    # Curves.
    fig, axes = plt.subplots(3, 1, figsize=(8.6, 7.0), sharex=True)
    for tag, color in (('D1', BLUE), ('D2-C', ORANGE)):
        bs = runs[tag]['bins']
        x = [(b['bin_start_s'] + b['bin_end_s']) / 2 for b in bs]
        axes[0].plot(x, [b['centroid_speed_mean_mm_s'] for b in bs],
                     color=color, lw=1.8, marker='o', ms=3, label=tag)
        axes[1].plot(x, [b['angular_speed_mean_deg_s'] for b in bs],
                     color=color, lw=1.8, marker='o', ms=3, label=tag)
        axes[2].plot(x, [b['direction_deg'] for b in bs],
                     color=color, lw=1.8, marker='o', ms=3, label=tag)
        axes[2].axhline(runs[tag]['release_direction_deg'], color=color,
                        ls='--', lw=1, alpha=.7,
                        label=tag + ' release direction')
    axes[0].set_ylabel('centroid speed (mm/s)')
    axes[0].set_title('Sustained slip, 0.5 s bins after release')
    axes[1].set_ylabel('angular speed (deg/s)')
    axes[2].set_ylabel('XY direction (deg)')
    axes[2].set_xlabel('elapsed time after release (s)')
    for ax in axes:
        ax.grid(color=GRID, lw=.7)
        ax.set_axisbelow(True)
        ax.legend(loc='best', ncol=2)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        for s in ('left', 'bottom'):
            ax.spines[s].set_color(AXIS)
        for t in (1.0, 4.57, 8.07):
            ax.axvline(t, color=SECONDARY, ls=':', lw=.8)
    fig.tight_layout()
    fig.savefig(out / 'slip_speed_rotation.png', dpi=180)
    plt.close(fig)

    # Height / contact-offset margin.
    fig, axes = plt.subplots(2, 1, figsize=(8.6, 5.4), sharex=True)
    ax = axes[0]
    for tag, color in (('D1', BLUE), ('D2-C', ORANGE)):
        bs = runs[tag]['bins']
        x = [(b['bin_start_s'] + b['bin_end_s']) / 2 for b in bs]
        ax.plot(x, [b['z_min_mm'] for b in bs], color=color, lw=1.8,
                marker='o', ms=3, label=tag + ' z_min')
    ax.axhline(0.0, color=CRITICAL, ls='-', lw=1, label='ground z=0')
    ax.axhline(10.0, color=SECONDARY, ls='--', lw=1, label='particle contact offset 10 mm')
    ax.set_ylabel('cloth z_min (mm)')
    ax.set_title('Height / contact-offset geometry (not force)')
    ax.legend(loc='best', ncol=2)
    ax = axes[1]
    for tag, color in (('D1', BLUE), ('D2-C', ORANGE)):
        bs = runs[tag]['bins']
        x = [(b['bin_start_s'] + b['bin_end_s']) / 2 for b in bs]
        ax.plot(x, [b['below_contact_offset_mm'] for b in bs], color=color,
                lw=1.8, marker='o', ms=3, label=tag + ' below offset')
    ax.set_xlabel('elapsed time after release (s)')
    ax.set_ylabel('10 mm - z_min (mm)')
    ax.set_title('Zoom: amount below the 10 mm particle contact offset')
    ax.set_ylim(0.12, 0.13)
    ax.legend(loc='best', ncol=2)
    for ax in axes:
        ax.grid(color=GRID, lw=.7)
        ax.set_axisbelow(True)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        for s in ('left', 'bottom'):
            ax.spines[s].set_color(AXIS)
    fig.tight_layout()
    fig.savefig(out / 'slip_height.png', dpi=180)
    plt.close(fig)

    # Support geometry: XY footprint and Y-Z side view at D2-C release/formal.
    s = runs['D2-C']['series']
    t0 = s['t0']
    v0 = s['vertices'][s['t0i']]
    tr = s['trace']
    vf = np.asarray(tr['vertices'], float)[330]
    fig, axes = plt.subplots(2, 1, figsize=(7.4, 7.2))
    ax = axes[0]
    ax.scatter(v0[:, 0] * 1000, v0[:, 1] * 1000, s=5, color=BLUE,
               alpha=.65, label='D2-C release t=0')
    ax.scatter(vf[:, 0] * 1000, vf[:, 1] * 1000, s=5, color=ORANGE,
               alpha=.55, label='D2-C formal end')
    # Approximate initial and release block footprints; exact poses are U.
    blocks = [
        ('A right (release approx)', -0.17433, -0.47232, (30, -24)),
        ('B left (initial)', -0.2, -0.45, (-86, 20)),
        ('C hem (release approx)', 0.04757, -0.64173, (24, 12)),
    ]
    for name, x, y, offset in blocks:
        ax.add_patch(plt.Rectangle((x * 1000 - 15, y * 1000 - 15), 30, 30,
                                   fill=False, ec=SECONDARY, ls='--', lw=1))
        ax.annotate(name, (x * 1000, y * 1000), xytext=offset,
                    textcoords='offset points', fontsize=6.5, color=SECONDARY,
                    arrowprops={'arrowstyle': '-', 'color': SECONDARY, 'lw': .6})
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel('world x (mm)')
    ax.set_ylabel('world y (mm)')
    ax.set_title('XY footprint; default ground (50 m, z=0) covers this view; blocks filtered')
    ax.legend(loc='best')
    ax.grid(color=GRID, lw=.7)
    ax.set_axisbelow(True)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    ax = axes[1]
    ax.scatter(v0[:, 1] * 1000, v0[:, 2] * 1000, s=5, color=BLUE,
               alpha=.65, label='D2-C release t=0')
    ax.scatter(vf[:, 1] * 1000, vf[:, 2] * 1000, s=5, color=ORANGE,
               alpha=.55, label='D2-C formal end')
    ax.axhspan(0, 10, color=GRID, alpha=.7, label='0-10 mm particle contact offset band')
    ax.axhline(0, color=CRITICAL, lw=1, label='ground z=0')
    ax.set_xlabel('world y (mm)')
    ax.set_ylabel('world z (mm)')
    ax.set_title('Y-Z side view; z_min ~9.876 mm (geometry, not contact force)')
    ax.legend(loc='best')
    ax.grid(color=GRID, lw=.7)
    ax.set_axisbelow(True)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / 'support_geometry.png', dpi=180)
    plt.close(fig)

    print('D2E_SLIP_OK', out / 'slip_summary.json')
    for tag in ('D1', 'D2-C'):
        print(tag, 'pre', runs[tag]['pre']['centroid_speed_mean_mm_s'],
              'release', runs[tag]['release']['centroid_speed_mean_mm_s'],
              'steady', tail[tag]['steady_centroid_speed_mm_s'],
              'dir', tail[tag]['steady_direction_deg'],
              'zmin', tail[tag]['z_min_mm_min'], tail[tag]['z_min_mm_max'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
