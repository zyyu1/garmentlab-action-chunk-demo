#!/usr/bin/env python3
"""Offline D2-C release-order comparison against D1-120.

No simulation.  The pre-release state (last attached state) is release t=0 for
both runs; the first detached *physics* state is one step later.  D2-C also has
a zero-step `released` sample at the boundary, which is reported separately but
is not used as a physics state.  Post-release windows are measured from the
first detached physics state, so the one-step boundary sampling interval is
explicit rather than hidden.
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


def displacement(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    d = np.linalg.norm(b - a, axis=1) * 1000.0
    rot, rms = rigid2d(a, b)
    return {
        'centroid_mm': float(np.linalg.norm(b.mean(0) - a.mean(0)) * 1000.0),
        'p95_mm': float(np.percentile(d, 95)),
        'max_mm': float(d.max()),
        'rotation_deg': float(rot),
        'rigid_rms_mm': float(rms),
    }


def endpoint(v, times, i, j):
    out = displacement(v[i], v[j])
    dt = float(times[j] - times[i])
    out.update({
        'start_index': int(i), 'end_index': int(j),
        'start_step': int(i), 'end_step': int(j),
        'duration_s': dt,
        'centroid_speed_mm_s': out['centroid_mm'] / dt if dt > 0 else None,
    })
    return out


def speed_stats(v, dt, i, j, times=None):
    ps, cs, ws = [], [], []
    for k in range(int(i), int(j)):
        step_dt = float(times[k + 1] - times[k]) if times is not None else float(dt)
        if step_dt <= 0:
            # D2-C has a zero-time released sample between t0 and the first
            # free state; it is a state read, not a physics interval.
            continue
        d = np.linalg.norm(v[k + 1] - v[k], axis=1) * 1000.0
        ps.append(float(d.mean()) / step_dt)
        cs.append(float(np.linalg.norm(v[k + 1].mean(0) - v[k].mean(0)) * 1000.0) / step_dt)
        ws.append(abs(rigid2d(v[k], v[k + 1])[0]) / step_dt)
    ps = np.asarray(ps)
    cs = np.asarray(cs)
    ws = np.asarray(ws)
    return {
        'n_intervals': int(len(ps)),
        'particle_mean_speed_mean_mm_s': float(ps.mean()) if len(ps) else None,
        'particle_mean_speed_max_mm_s': float(ps.max()) if len(ps) else None,
        'centroid_speed_mean_mm_s': float(cs.mean()) if len(cs) else None,
        'centroid_speed_max_mm_s': float(cs.max()) if len(cs) else None,
        'angular_speed_mean_deg_s': float(ws.mean()) if len(ws) else None,
        'angular_speed_max_deg_s': float(ws.max()) if len(ws) else None,
    }


def window(name, v, times, i, j):
    out = endpoint(v, times, i, j)
    out.update(speed_stats(v, None, i, j, times=times))
    out['label'] = name
    return out


def phase_bounds(z, phase):
    key = 'phase' if 'phase' in z else 'phases'
    idx = np.where(np.asarray(z[key]) == phase)[0]
    if len(idx) == 0:
        raise ValueError('Missing phase ' + phase)
    return int(idx[0]), int(idx[-1])


def find_release(z, result, d2c):
    phases = np.asarray(z['phase'])
    labels = np.asarray(z['sample_label'])
    attached = np.asarray(z['attached'], bool)
    holding = np.asarray(z['holding'], bool)
    observed = np.asarray(z['observed_step'], int)
    times = np.asarray(z['sim_time_s'], float)
    released = np.where(labels == 'released')[0]
    released = int(released[0]) if len(released) else None
    if d2c:
        if released is None:
            raise ValueError('D2-C has no released sample')
        candidates = [i for i in range(released)
                      if phases[i] == 'release_opening' and attached[i]]
        if not candidates:
            raise ValueError('D2-C has no attached preopen state')
        t0 = int(candidates[-1])
        free_candidates = [i for i in range(released + 1, len(phases))
                           if phases[i] == 'delay' and not attached[i]]
        if not free_candidates:
            raise ValueError('D2-C has no first free delay state')
        free = int(free_candidates[0])
        ro = result.get('release_order') or {}
        boundary = {
            'release_t0_kind': 'last attached preopen state',
            'release_sample_kind': 'zero-step released sample immediately after disable',
            'boundary_lo_step': int(observed[t0]),
            'boundary_hi_step': int(observed[released]),
            'boundary_step_delta': int(observed[released] - observed[t0]),
            'first_free_step': int(observed[free]),
            'first_free_delta_from_sample': int(observed[free] - observed[released]),
            'recorded_boundary_delta': ro.get('release_boundary_sample_step_delta'),
            'recorded_last_preopen_step': ro.get('preopen_last_state_observed_step'),
            'recorded_released_sample_step': ro.get('released_sample_observed_step'),
            'recorded_first_wait_step': ro.get('first_wait_state_observed_step'),
        }
        t0_time = float(times[t0])
        sample_time = float(times[released])
    else:
        anchor = np.where(phases == 'release_start_anchor')[0]
        if len(anchor) != 1:
            raise ValueError('D1 has no unique release_start_anchor')
        t0 = int(anchor[0])
        free_candidates = [i for i in range(t0 + 1, len(phases))
                           if phases[i] == 'release_opening' and not attached[i]]
        if not free_candidates:
            raise ValueError('D1 has no first detached state')
        free = int(free_candidates[0])
        boundary = {
            'release_t0_kind': 'release_start_anchor (last attached state)',
            'release_sample_kind': 'released sample is 10 steps after t0 in D1 and is not used as t0',
            'boundary_lo_step': int(observed[t0]),
            'boundary_hi_step': int(observed[free]),
            'boundary_step_delta': int(observed[free] - observed[t0]),
            'first_free_step': int(observed[free]),
            'first_free_delta_from_sample': (int(observed[free] - observed[released])
                                             if released is not None else None),
            'recorded_boundary_delta': None,
            'recorded_last_preopen_step': None,
            'recorded_released_sample_step': int(observed[released]) if released is not None else None,
            'recorded_first_wait_step': (int(z['observed_step'][phase_bounds(z, 'delay')[0]])
                                         if 'delay' in phases else None),
        }
        t0_time = float(times[t0])
        sample_time = float(times[released]) if released is not None else None
    return {
        't0_index': t0, 'released_index': released, 'first_free_index': free,
        't0_time_s': t0_time, 'released_sample_time_s': sample_time,
        'boundary': boundary,
        'preopen_state_rows': (len(candidates) if d2c else 0),
        'released_attached': (bool(attached[released])
                              if released is not None else None),
        't0_attached': bool(attached[t0]), 't0_holding': bool(holding[t0]),
        'first_free_attached': bool(attached[free]),
        'times': times, 'vertices': np.asarray(z['vertices'], float),
        'observed': observed, 'phases': phases, 'labels': labels,
    }


def pre_release_velocity(d2c, info, run_dir):
    if d2c:
        i = info['t0_index']
        v = info['vertices']
        dt = float(info['times'][i] - info['times'][i - 1])
        return speed_stats(v, dt, i - 1, i), 'last two attached preopen state rows'
    h = load(Path(run_dir) / 'pre_release_hold.npz')
    vh = np.asarray(h['vertices'], float)
    dt = float(h['dt_s'])
    return speed_stats(vh, dt, len(vh) - 2, len(vh) - 1), 'last two pre-release hold frames'


def action_compare(r1, r2):
    a1, a2 = r1.get('actions') or [], r2.get('actions') or []
    n = min(len(a1), len(a2))
    labels = commands = targets = True
    target_max = 0.0
    ee_max = 0.0
    for i in range(n):
        labels = labels and a1[i].get('label') == a2[i].get('label')
        commands = commands and int(a1[i].get('command', -1)) == int(a2[i].get('command', -2))
        x = np.asarray(a1[i].get('target_pose'), float)
        y = np.asarray(a2[i].get('target_pose'), float)
        if x.shape != y.shape:
            targets = False
        else:
            target_max = max(target_max, float(np.max(np.abs(x - y))))
            targets = targets and np.array_equal(x, y)
        if 'ee' in a1[i] and 'ee' in a2[i]:
            ee_max = max(ee_max, float(np.max(np.abs(
                np.asarray(a1[i]['ee'], float) - np.asarray(a2[i]['ee'], float)))))
    pre = all(a1[i].get('label') == a2[i].get('label')
              and int(a1[i].get('command', -1)) == int(a2[i].get('command', -2))
              and np.array_equal(np.asarray(a1[i].get('target_pose'), float),
                                 np.asarray(a2[i].get('target_pose'), float))
              for i in range(min(11, n)))
    return {
        'count_match': len(a1) == len(a2) == 12,
        'labels_identical': labels,
        'commands_identical': commands,
        'targets_identical': targets,
        'target_max_abs_diff': target_max,
        'action_ee_max_abs_diff_m': ee_max,
        'action_ee_identical': ee_max == 0.0,
        'first_11_identical': pre,
        'action_count': [len(a1), len(a2)],
        'call_horizons': [r1.get('call_horizons'), r2.get('call_horizons')],
        'horizon_sum': [sum(r1.get('call_horizons') or []),
                        sum(r2.get('call_horizons') or [])],
    }


def step_info(result, meta, trace):
    return {
        'release_clock_absolute_step': (result.get('release_clock') or {}).get('absolute_step'),
        'meta_absolute_step': meta.get('absolute_step'),
        'internal_delay': {
            'start': (result.get('internal_delay') or {}).get('start_step'),
            'end': (result.get('internal_delay') or {}).get('end_step'),
            'elapsed': (result.get('internal_delay') or {}).get('elapsed_steps'),
        },
        'trace_absolute_first': int(np.asarray(trace['absolute_steps'])[0]),
        'trace_absolute_last': int(np.asarray(trace['absolute_steps'])[-1]),
        'trace_len': int(len(trace['absolute_steps'])),
    }


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

    r1 = read(d1 / 'result.json')
    r2 = read(d2c / 'result.json')
    m1 = read(d1 / 'success_meta.json')
    m2 = read(d2c / 'success_meta.json')
    z1 = load(d1 / 'evidence' / 'release_diag.npz')
    z2 = load(d2c / 'evidence' / 'release_diag.npz')
    t1 = load(d1 / 'success_trace.npz')
    t2 = load(d2c / 'success_trace.npz')
    h1 = load(d1 / 'pre_release_hold.npz')
    h2 = load(d2c / 'pre_release_hold.npz')
    i1 = find_release(z1, r1, False)
    i2 = find_release(z2, r2, True)

    # Pre-intervention identity: the whole prefix must be byte-identical.
    phase1 = np.asarray(z1['phase'])
    phase2 = np.asarray(z2['phase'])
    anchor1 = np.where(phase1 == 'release_start_anchor')[0]
    anchor2 = np.where(phase2 == 'release_start_anchor')[0]
    anchor1 = int(anchor1[0]) if len(anchor1) else None
    anchor2 = int(anchor2[0]) if len(anchor2) else None
    pre = action_compare(r1, r2)
    pre.update({
        'anchor_present': anchor1 is not None and anchor2 is not None,
        'anchor_vertex_max_abs_m': (float(np.max(np.abs(
            z1['vertices'][anchor1] - z2['vertices'][anchor2])))
            if anchor1 is not None and anchor2 is not None else None),
        'anchor_ee_max_abs_m': (float(np.max(np.abs(
            np.asarray(z1['ee_m'])[anchor1] - np.asarray(z2['ee_m'])[anchor2])))
            if anchor1 is not None and anchor2 is not None else None),
        'anchor_joint_max_abs': (float(np.max(np.abs(
            np.asarray(z1['joint_positions'])[anchor1]
            - np.asarray(z2['joint_positions'])[anchor2])))
            if anchor1 is not None and anchor2 is not None else None),
        'anchor_time_diff_s': (float(z1['sim_time_s'][anchor1] - z2['sim_time_s'][anchor2])
                               if anchor1 is not None and anchor2 is not None else None),
        'anchor_step_diff': (int(z1['observed_step'][anchor1] - z2['observed_step'][anchor2])
                             if anchor1 is not None and anchor2 is not None else None),
        'd1_hold_last_equals_anchor': (bool(np.array_equal(
            np.asarray(h1['vertices'])[-1], z1['vertices'][anchor1]))
            if anchor1 is not None else None),
        'd2c_hold_last_equals_anchor': (bool(np.array_equal(
            np.asarray(h2['vertices'])[-1], z2['vertices'][anchor2]))
            if anchor2 is not None else None),
    })

    # Release t=0 state and velocity (last attached state for each run).
    v1 = i1['vertices']
    v2 = i2['vertices']
    vel1, method1 = pre_release_velocity(False, i1, d1)
    vel2, method2 = pre_release_velocity(True, i2, d2c)
    release = {
        'd1': {
            't0_step': int(i1['observed'][i1['t0_index']]),
            't0_time_s': i1['t0_time_s'],
            't0_kind': i1['boundary']['release_t0_kind'],
            'z_min_m': float(v1[i1['t0_index']][:, 2].min()),
            'z_max_m': float(v1[i1['t0_index']][:, 2].max()),
            'centroid_m': v1[i1['t0_index']].mean(0).tolist(),
            'velocity': vel1, 'velocity_method': method1,
            'released_sample_step': i1['boundary']['recorded_released_sample_step'],
            'released_sample_is_t0': False,
            'preopen_state_rows': i1['preopen_state_rows'],
            't0_attached': i1['t0_attached'],
            'released_attached': i1['released_attached'],
            'first_free_attached': i1['first_free_attached'],
            'boundary': i1['boundary'],
        },
        'd2c': {
            't0_step': int(i2['observed'][i2['t0_index']]),
            't0_time_s': i2['t0_time_s'],
            't0_kind': i2['boundary']['release_t0_kind'],
            'z_min_m': float(v2[i2['t0_index']][:, 2].min()),
            'z_max_m': float(v2[i2['t0_index']][:, 2].max()),
            'centroid_m': v2[i2['t0_index']].mean(0).tolist(),
            'velocity': vel2, 'velocity_method': method2,
            'released_sample_step': i2['boundary']['recorded_released_sample_step'],
            'released_sample_is_t0': True,
            'preopen_state_rows': i2['preopen_state_rows'],
            't0_attached': i2['t0_attached'],
            'released_attached': i2['released_attached'],
            'first_free_attached': i2['first_free_attached'],
            'released_sample_to_t0_max_abs_m': float(np.max(np.abs(
                v2[i2['released_index']] - v2[i2['t0_index']]))),
            'boundary': i2['boundary'],
        },
        'difference': displacement(v1[i1['t0_index']], v2[i2['t0_index']]),
    }

    # Post-release windows: first free state is release+0 for kinematics.
    def w(name, info, i, j):
        return window(name, info['vertices'], info['times'], i, j)

    free1, free2 = i1['first_free_index'], i2['first_free_index']
    windows = {}
    for tag, info, free in (('d1', i1, free1), ('d2c', i2, free2)):
        t0 = info['t0_index']
        windows[tag] = {
            'release_transition': w('release_transition', info, t0, free),
            'free_0_30': w('free_0_30', info, free, free + 30),
            'free_30_120': w('free_30_120', info, free + 30, free + 120),
            'free_0_120': w('free_0_120', info, free, free + 120),
        }
        a, b = phase_bounds(info, 'delay')
        windows[tag]['wait_phase'] = w('wait_phase', info, a, b)
        a, b = phase_bounds(info, 'retreat')
        windows[tag]['retreat_phase'] = w('retreat_phase', info, a, b)
        # Legacy sample-aligned window (D1's released sample is 9-10 steps
        # after its actual release); kept separate from release-elapsed windows.
        sample = info['released_index']
        if sample is not None:
            windows[tag]['sample_0_30'] = w('sample_0_30', info, sample, sample + 30)
            windows[tag]['sample_30_120'] = w('sample_30_120', info, sample + 30, sample + 120)
            windows[tag]['sample_0_120'] = w('sample_0_120', info, sample, sample + 120)
    windows['formal'] = {
        'd1': w('formal_210_330', {'vertices': np.asarray(t1['vertices'], float),
                                   'times': np.asarray(t1['sim_time_s'], float)}, 210, 330),
        'd2c': w('formal_210_330', {'vertices': np.asarray(t2['vertices'], float),
                                    'times': np.asarray(t2['sim_time_s'], float)}, 210, 330),
    }

    steps = {'d1': step_info(r1, m1, t1), 'd2c': step_info(r2, m2, t2)}
    steps['identical_absolute_step'] = (
        steps['d1']['release_clock_absolute_step'] == steps['d2c']['release_clock_absolute_step'])
    steps['identical_internal_delay'] = steps['d1']['internal_delay'] == steps['d2c']['internal_delay']
    steps['identical_trace_len'] = steps['d1']['trace_len'] == steps['d2c']['trace_len'] == 331

    # Quality verdicts if present.
    verdict = {}
    for tag, d in (('d1', d1), ('d2c', d2c)):
        for name in ('diag-verdict.json', 'diag-verdict-postfix.json'):
            p = d / name
            if p.is_file():
                verdict[tag] = {'file': name, 'data': read(p)}
                break

    payload = {
        'protocol': 'stage4-a5-rc2-d2c-release-order-comparison',
        'd1': str(d1), 'd2c': str(d2c),
        'pre_intervention': pre,
        'release': release,
        'windows': windows,
        'steps': steps,
        'verdicts': verdict,
        'notes': [
            'Release t=0 is the last attached state (D1 anchor; D2-C last preopen state), not the D1 released sample.',
            'D2-C released sample is a zero-step state read immediately after disable; its delta from t0 is reported.',
            'First free state is one physics step after t0; post-release windows start there.',
            'No contact force/impulse is available; only geometric and kinematic evidence is reported.',
            'This comparison does not upgrade any run to formal Stage 4 success.',
        ],
    }

    (out / 'comparison.json').write_text(
        json.dumps(payload, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    with (out / 'windows.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['run', 'window', 'start_step', 'end_step', 'duration_s',
                    'centroid_mm', 'p95_mm', 'max_mm', 'rotation_deg',
                    'rigid_rms_mm', 'particle_mean_speed_mean_mm_s',
                    'centroid_speed_mean_mm_s', 'angular_speed_mean_deg_s'])
        for tag in ('d1', 'd2c'):
            for name, row in windows[tag].items():
                w.writerow([tag, name, row['start_step'], row['end_step'],
                            row['duration_s'], row['centroid_mm'], row['p95_mm'],
                            row['max_mm'], row['rotation_deg'], row['rigid_rms_mm'],
                            row['particle_mean_speed_mean_mm_s'],
                            row['centroid_speed_mean_mm_s'],
                            row['angular_speed_mean_deg_s']])
        for tag in ('d1', 'd2c'):
            row = windows['formal'][tag]
            w.writerow([tag, 'formal_210_330', 210, 330, row['duration_s'],
                        row['centroid_mm'], row['p95_mm'], row['max_mm'],
                        row['rotation_deg'], row['rigid_rms_mm'],
                        row['particle_mean_speed_mean_mm_s'],
                        row['centroid_speed_mean_mm_s'],
                        row['angular_speed_mean_deg_s']])

    # Curves from first free state; the one-step boundary is explicit.
    fig, axes = plt.subplots(3, 1, figsize=(8.4, 6.4), sharex=True)
    for tag, info, free, color in (('D1', i1, free1, BLUE), ('D2-C', i2, free2, ORANGE)):
        v = info['vertices']
        n = min(120, len(v) - free - 1)
        ref = v[free]
        d = np.linalg.norm(v[free:free + n + 1] - ref, axis=2) * 1000.0
        cent = np.linalg.norm(v[free:free + n + 1].mean(1) - ref.mean(0), axis=1) * 1000.0
        axes[0].plot(np.arange(n + 1), cent, color=color, lw=1.8, label=tag)
        axes[1].plot(np.arange(n + 1), np.percentile(d, 95, axis=1), color=color, lw=1.8, label=tag)
        ps = []
        for k in range(free, free + n):
            ps.append(float(np.linalg.norm(v[k + 1] - v[k], axis=1).mean() * 1000.0) * 60.0)
        axes[2].plot(np.arange(n), ps, color=color, lw=1.8, label=tag)
    for ax, title, ylabel in zip(
            axes[:2], ('Centroid drift from first free state', 'Vertex P95 from first free state'),
            ('mm', 'mm')):
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.legend(loc='upper left')
        ax.axvline(30, color=SECONDARY, ls=':', lw=1)
        ax.axvline(120, color=CRITICAL, ls='--', lw=1)
        ax.grid(color=GRID, lw=.7)
        ax.set_axisbelow(True)
    axes[2].set_title('Particle mean speed (backward differences)')
    axes[2].set_ylabel('mm/s')
    axes[2].set_xlabel('physics steps after first free state (release + 1)')
    axes[2].legend(loc='upper right')
    axes[2].grid(color=GRID, lw=.7)
    axes[2].set_axisbelow(True)
    for ax in axes:
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        for s in ('left', 'bottom'):
            ax.spines[s].set_color(AXIS)
    fig.tight_layout()
    fig.savefig(out / 'd2c_release_compare.png', dpi=180)
    plt.close(fig)

    print('D2C_COMPARE_OK', out / 'comparison.json')
    print('pre_intervention', json.dumps(pre, indent=1))
    print('release_difference', json.dumps(release['difference'], indent=1))
    print('steps', json.dumps(steps, indent=1))
    for tag in ('d1', 'd2c'):
        print(tag, 'wait', windows[tag]['wait_phase']['centroid_mm'],
              windows[tag]['wait_phase']['p95_mm'],
              'retreat', windows[tag]['retreat_phase']['centroid_mm'],
              windows[tag]['retreat_phase']['p95_mm'],
              'formal', windows['formal'][tag]['centroid_mm'],
              windows['formal'][tag]['p95_mm'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
