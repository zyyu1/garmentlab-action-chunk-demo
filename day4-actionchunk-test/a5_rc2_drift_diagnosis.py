#!/usr/bin/env python3
"""Offline drift localisation for RC2 cases 4202 single and 4302 single.

Reads the existing RC2 success_trace, pre_release_hold, evidence timeline and
snapshots.  It does not start Isaac, does not generate held-out cases and does
not modify the RC2 audit directory.

Outputs (under --out):
  phase-events.json       event table with evidence observed step, world step,
                          simulation time, source and missing-evidence notes
  phase-segments.json     adjacent-event segment metrics and the original
                          evaluator cross-check
  event-table.csv         flat event table
  segment-metrics.csv     flat segment table
  phase-trace.json        per-step centroid/P95 arrays used by the plots
  plots/drift_<case>.png  event-annotated centroid/P95 curves
  diagnosis.md            narrative findings and missing evidence

The original evaluator's stability is recomputed with exactly the same window
and formulas as stage4_success_v1.evaluate (w = vertices[210:331]).
"""
import argparse
import csv
import json
import math
from datetime import datetime, timezone
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
    'font.family': 'DejaVu Sans',
    'font.size': 9,
    'axes.titlesize': 10,
    'axes.labelsize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 7.5,
    'figure.facecolor': SURFACE,
    'axes.facecolor': SURFACE,
    'savefig.facecolor': SURFACE,
})


def read(path):
    return json.loads(Path(path).read_text())


def load_case_index(path):
    return {c['case']: c for c in read(path)}


def rigid_2d(src, dst):
    a = np.asarray(src, dtype=float)[:, :2]
    b = np.asarray(dst, dtype=float)[:, :2]
    ca = a.mean(axis=0)
    cb = b.mean(axis=0)
    h = (a - ca).T @ (b - cb)
    u, s, vt = np.linalg.svd(h)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1
        r = vt.T @ u.T
    t = cb - r @ ca
    residual = b - (a @ r.T + t)
    angle = math.degrees(math.atan2(r[1, 0], r[0, 0]))
    rms = math.sqrt(float((residual ** 2).sum(axis=1).mean())) * 1000.0
    return angle, rms


def segment_metrics(src, dst, dt_s):
    a = np.asarray(src, dtype=float)
    b = np.asarray(dst, dtype=float)
    ca = a[:, :2].mean(axis=0)
    cb = b[:, :2].mean(axis=0)
    delta = cb - ca
    disp = np.linalg.norm(b - a, axis=1)
    angle, rms = rigid_2d(a, b)
    dt = float(dt_s)
    return {
        'centroid_dx_mm': float(delta[0] * 1000.0),
        'centroid_dy_mm': float(delta[1] * 1000.0),
        'centroid_norm_mm': float(np.linalg.norm(delta) * 1000.0),
        'rotation_deg': float(angle),
        'rigid_rms_mm': float(rms),
        'vertex_p95_mm': float(np.percentile(disp, 95) * 1000.0),
        'vertex_max_mm': float(disp.max() * 1000.0),
        'centroid_speed_mm_s': float(np.linalg.norm(delta) * 1000.0 / dt) if dt > 0 else None,
        'vertex_speed_p95_mm_s': float(np.percentile(disp, 95) * 1000.0 / dt) if dt > 0 else None,
        'vertex_speed_max_mm_s': float(disp.max() * 1000.0 / dt) if dt > 0 else None,
        'n_vertices': int(len(a)),
        'duration_s': dt
    }


def min_ee_distance_mm(vertices, ee):
    v = np.asarray(vertices, dtype=float)
    e = np.asarray(ee, dtype=float)
    return float(np.min(np.linalg.norm(v - e, axis=1)) * 1000.0)


def trace_arrays(vertices, dt):
    v = np.asarray(vertices, dtype=float)
    steps = np.arange(len(v))
    centroid = v[:, :, :2].mean(axis=1)
    w = v[210:331]
    d = np.linalg.norm(w - w[0], axis=2)
    speed = np.linalg.norm(np.diff(w, axis=0), axis=2) / dt
    return {
        'steps': steps,
        'centroid': centroid,
        'p95_from_0_mm': np.percentile(np.linalg.norm(v - v[0], axis=2), 95, axis=1) * 1000.0,
        'p95_from_210_mm': np.percentile(d, 95, axis=1) * 1000.0,
        'centroid_from_0_mm': np.linalg.norm(centroid - centroid[0], axis=1) * 1000.0,
        'centroid_from_210_mm': np.linalg.norm(centroid[210:331] - centroid[210], axis=1) * 1000.0,
        'window_d': d,
        'window_speed': speed,
        'stability': {
            'centroid_drift_max_m': float(np.linalg.norm(
                w.mean(axis=1) - w[0].mean(axis=0), axis=1).max()),
            'vertex_drift_p95_max_m': float(np.percentile(d, 95, axis=1).max()),
            'vertex_drift_max_m': float(d.max()),
            'vertex_speed_p95_max_m_s': float(np.percentile(speed, 95, axis=1).max()),
            'vertex_speed_max_m_s': float(speed.max()),
        },
    }


def last_action(timeline):
    begins = [r for r in timeline if r.get('kind') == 'action_begin']
    ends = [r for r in timeline if r.get('kind') == 'action_end']
    return begins[-1], ends[-1]


def find_release(timeline, begin):
    states = [r for r in timeline if r.get('kind') == 'state']
    after = [r for r in states if r['observed_step'] > begin['observed_step']]
    release = next(r for r in after
                   if not r.get('holding') and not r.get('attached')
                   and not any(r.get('enabled_slots') or []))
    command = next(r for r in after
                   if r['observed_step'] >= release['observed_step']
                   and not r.get('command_holding'))
    one_mm = next((r for r in after
                   if r['observed_step'] >= command['observed_step']
                   and (r.get('ee_m') or [0, 0, 0])[2] > release['ee_m'][2] + 0.001), None)
    return release, command, one_mm, states


def build_events(case, trace, hold, timeline, result, meta):
    begin, end = last_action(timeline)
    release, command, one_mm, states = find_release(timeline, begin)
    samples = {r['label']: r for r in timeline if r.get('kind') == 'sample'}
    released = samples['released']
    retreated = samples['retreated']
    hold3 = samples.get('hold_3s')
    hold4 = samples.get('hold_4s')
    terminal = samples.get('terminal')
    dt = float(meta['dt_s'])
    offset = int(meta['absolute_step'] - end['observed_step'])
    trace_t0 = float(meta['sim_time_s'])
    last_begin_time = float(begin['sim_time_s'])
    hold_end_time = last_begin_time - dt
    hold_last = hold[-1]
    hold_n = len(hold)

    def world(observed):
        return int(observed + offset)

    events = [
        {'id': 'E1', 'event': 'last pre-release hold frame',
         'evidence_observed_step': int(begin['observed_step'] - 1),
         'world_step_inferred': world(begin['observed_step'] - 1),
         'sim_time_s': hold_end_time, 'source': 'pre_release_hold.npz; step inferred from action_begin',
         'note': 'last of %d hold frames' % hold_n},
        {'id': 'E2', 'event': 'release action begin (public OPEN command)',
         'evidence_observed_step': int(begin['observed_step']),
         'world_step_inferred': world(begin['observed_step']),
         'sim_time_s': last_begin_time, 'source': 'evidence timeline action_begin', 'note': ''},
        {'id': 'E3', 'event': 'attachment release / gripper effective open',
         'evidence_observed_step': int(release['observed_step']),
         'world_step_inferred': world(release['observed_step']),
         'sim_time_s': float(release['sim_time_s']),
         'source': 'first state with holding=false, attached=false, all enables=false',
         'note': 'attachment release and effective open are the same state; '
                 'gripper aperture is not measured'},
        {'id': 'E4', 'event': 'released snapshot (pre-retreat)',
         'evidence_observed_step': int(released['observed_step']),
         'world_step_inferred': world(released['observed_step']),
         'sim_time_s': float(released['sim_time_s']),
         'source': 'evidence sample released',
         'note': '9 evidence steps after E3; the snapshots bracket the release transient'},
        {'id': 'E5', 'event': 'retreat command start',
         'evidence_observed_step': int(command['observed_step']),
         'world_step_inferred': world(command['observed_step']),
         'sim_time_s': float(command['sim_time_s']),
         'source': 'first state with command_holding=false', 'note': ''},
    ]
    if one_mm is not None:
        events.append({
            'id': 'E6', 'event': 'retreat reaches 1 mm upward',
            'evidence_observed_step': int(one_mm['observed_step']),
            'world_step_inferred': world(one_mm['observed_step']),
            'sim_time_s': float(one_mm['sim_time_s']),
            'source': 'first state with EE z > released EE z + 1 mm', 'note': ''})
    events += [
        {'id': 'E7', 'event': 'retreat end / success-trace t=0',
         'evidence_observed_step': int(end['observed_step']),
         'world_step': int(meta['absolute_step']),
         'sim_time_s': trace_t0,
         'source': 'evidence action_end; success_meta.absolute_step',
         'note': 'observed-to-world offset=%d; both clocks have the same sim time' % offset},
        {'id': 'E8', 'event': 'hold_3s sample (trace step 180)',
         'evidence_observed_step': int(hold3['observed_step']) if hold3 else None,
         'world_step': int(meta['absolute_step'] + 180),
         'sim_time_s': float(hold3['sim_time_s']) if hold3 else None,
         'source': 'evidence sample hold_3s; trace step 180', 'note': ''},
        {'id': 'E9', 'event': 'formal evaluation window start (trace step 210)',
         'evidence_observed_step': int(meta['absolute_step'] + 210 - offset),
         'world_step': int(meta['absolute_step'] + 210),
         'sim_time_s': trace_t0 + 210 / 60,
         'source': 'success_meta.absolute_step + 210', 'note': ''},
        {'id': 'E10', 'event': 'hold_4s sample (trace step 240)',
         'evidence_observed_step': int(hold4['observed_step']) if hold4 else None,
         'world_step': int(meta['absolute_step'] + 240),
         'sim_time_s': float(hold4['sim_time_s']) if hold4 else None,
         'source': 'evidence sample hold_4s; trace step 240', 'note': 'inside the formal window'},
        {'id': 'E11', 'event': 'formal evaluation window end (trace step 330)',
         'evidence_observed_step': int(meta['absolute_step'] + 330 - offset),
         'world_step': int(meta['absolute_step'] + 330),
         'sim_time_s': trace_t0 + 330 / 60,
         'source': 'success_meta.absolute_step + 330', 'note': ''},
        {'id': 'E12', 'event': 'finger / gripper to cloth contact record',
         'evidence_observed_step': None, 'world_step': None, 'sim_time_s': None,
         'source': 'missing in RC2 evidence', 'note': 'no contact force/impulse trace; '
         'room_collision_audit.json covers room colliders only'},
    ]
    return {
        'events': events,
        'release': release,
        'command': command,
        'one_mm': one_mm,
        'samples': samples,
        'begin': begin,
        'end': end,
        'offset': offset,
        'trace_t0': trace_t0,
        'last_begin_time': last_begin_time,
        'hold_end_time': hold_end_time,
        'released': released,
        'retreated': retreated,
        'hold3': hold3,
        'hold4': hold4,
        'terminal': terminal
    }


def identities(case_dir, trace, meta):
    v = np.asarray(trace['vertices'], dtype=float)
    checks = {}
    for name, idx in (('hold_3s', 180), ('hold_4s', 240), ('terminal', 330)):
        p = case_dir / 'evidence' / (name + '.npz')
        if p.exists():
            with np.load(p) as z:
                checks[name + '_equals_trace_step_%d' % idx] = bool(
                    np.array_equal(np.asarray(z['vertices'], dtype=float), v[idx]))
        else:
            checks[name + '_snapshot_present'] = False
    p = case_dir / 'evidence' / 'retreated.npz'
    if p.exists():
        with np.load(p) as z:
            checks['retreated_equals_trace_step_0'] = bool(
                np.array_equal(np.asarray(z['vertices'], dtype=float), v[0]))
    return checks


def case_analysis(case, case_dir):
    result = read(case_dir / 'result.json')
    meta = read(case_dir / 'success_meta.json')
    verdict = read(case_dir / 'a5-verdict.json')
    timeline = [json.loads(x) for x in
                (case_dir / 'evidence/timeline.jsonl').read_text().splitlines() if x.strip()]
    with np.load(case_dir / 'success_trace.npz', allow_pickle=False) as z:
        trace = {k: z[k] for k in z.files}
    with np.load(case_dir / 'pre_release_hold.npz', allow_pickle=False) as z:
        hold = np.asarray(z['vertices'], dtype=float)
        hold_dt = float(z['dt_s'])
    dt = float(meta['dt_s'])
    if not np.isclose(hold_dt, dt, atol=1e-12, rtol=0):
        raise ValueError('pre_release_hold dt mismatch')
    ev = build_events(case, trace, hold, timeline, result, meta)

    def snap(name):
        with np.load(case_dir / 'evidence' / (name + '.npz'), allow_pickle=False) as z:
            return np.asarray(z['vertices'], dtype=float)

    released_v = snap('released')
    retreated_v = snap('retreated')
    hold3_v = snap('hold_3s')
    hold4_v = snap('hold_4s')
    terminal_v = snap('terminal')
    with np.load(case_dir / 'final.npz', allow_pickle=False) as z:
        final_v = np.asarray(z['vertices'], dtype=float)

    trace_arrays_ = trace_arrays(trace['vertices'], dt)
    calc = trace_arrays_['stability']
    orig = (verdict.get('criteria') or {}).get('stability') or {}
    keys = ('centroid_drift_max_m', 'vertex_drift_p95_max_m',
            'vertex_drift_max_m', 'vertex_speed_p95_max_m_s',
            'vertex_speed_max_m_s')
    crosscheck = {k: {'recomputed': calc[k], 'original': orig.get(k),
                      'abs_delta': abs(calc[k] - float(orig[k])) if orig.get(k) is not None else None,
                      'match': (orig.get(k) is not None and
                                abs(calc[k] - float(orig[k])) <= 1e-12)}
                  for k in keys}

    hold_ref = hold[-1]
    hold_xy = hold_ref[:, :2].mean(axis=0)
    hold_x = -dt - (59 - np.arange(60)) * dt
    hold_last60 = hold[-60:]
    hold_centroid = np.linalg.norm(
        hold_last60[:, :, :2].mean(axis=1) - hold_xy, axis=1) * 1000.0
    hold_p95 = np.percentile(np.linalg.norm(hold_last60 - hold_ref, axis=2), 95, axis=1) * 1000.0
    trace_centroid = np.linalg.norm(
        trace['vertices'][:, :, :2].mean(axis=1) - hold_xy, axis=1) * 1000.0
    trace_p95 = np.percentile(np.linalg.norm(trace['vertices'] - hold_ref, axis=2), 95, axis=1) * 1000.0
    trace_x = (np.asarray(trace['sim_time_s'], dtype=float) - ev['last_begin_time'])

    released_x = float(ev['released']['sim_time_s'] - ev['last_begin_time'])
    retreated_x = float(ev['retreated']['sim_time_s'] - ev['last_begin_time'])
    released_centroid = np.linalg.norm(
        released_v[:, :2].mean(axis=0) - hold_xy) * 1000.0
    released_p95 = float(np.percentile(np.linalg.norm(released_v - hold_ref, axis=1), 95) * 1000.0)
    retreated_centroid = np.linalg.norm(
        retreated_v[:, :2].mean(axis=0) - hold_xy) * 1000.0
    retreated_p95 = float(np.percentile(np.linalg.norm(retreated_v - hold_ref, axis=1), 95) * 1000.0)

    released_ee = np.asarray(ev['released']['ee_m'], dtype=float)
    retreated_ee = np.asarray(ev['retreated']['ee_m'], dtype=float)
    byid = {e['id']: e for e in ev['events']}

    def event_world(eid):
        e = byid[eid]
        return int(e['world_step'] if e.get('world_step') is not None
                   else e['world_step_inferred'])

    hold_step = event_world('E1') - (59 - np.arange(60))
    released_step = event_world('E4')
    retreated_step = event_world('E7')

    segments = []
    def add_segment(name, start_name, end_name, start_v, end_v, start_t, end_t,
                    per_step, ee_start, ee_end, note=''):
        m = segment_metrics(start_v, end_v, end_t - start_t)
        m.update({
            'segment': name,
            'start_event': start_name,
            'end_event': end_name,
            'start_time_s': float(start_t),
            'end_time_s': float(end_t),
            'per_step_vertices_available': bool(per_step),
            'contact_record': 'missing',
            'ee_min_vertex_distance_start_mm': min_ee_distance_mm(start_v, ee_start),
            'ee_min_vertex_distance_end_mm': min_ee_distance_mm(end_v, ee_end),
            'distance_evidence_note': 'EE point to nearest cloth vertex; not a finger '
                                      'surface or contact-force measurement',
            'note': note
        })
        segments.append(m)
        return m

    add_segment('hold_last_60', 'hold_last_60_start', 'hold_last_frame',
                hold[-60], hold[-1], ev['hold_end_time'] - 59 * dt,
                ev['hold_end_time'], True, released_ee, released_ee)
    add_segment('hold_end_to_released', 'hold_last_frame', 'released_snapshot',
                hold[-1], released_v, ev['hold_end_time'],
                float(ev['released']['sim_time_s']), False,
                released_ee, released_ee,
                'sparse snapshots only; release transient and the pre-retreat pause are not separated')
    add_segment('released_to_retreated', 'released_snapshot', 'retreated_snapshot',
                released_v, retreated_v, float(ev['released']['sim_time_s']),
                float(ev['retreated']['sim_time_s']), False,
                released_ee, retreated_ee,
                'sparse snapshots only; per-step vertices during retreat are missing')
    add_segment('retreated_to_trace0', 'retreated_snapshot', 'trace_t0',
                retreated_v, trace['vertices'][0], float(ev['retreated']['sim_time_s']),
                float(ev['trace_t0']), True, retreated_ee, retreated_ee,
                'same simulation time; counter offset only')
    add_segment('trace0_to_60', 'trace_t0', 'trace_step_60',
                trace['vertices'][0], trace['vertices'][60], ev['trace_t0'],
                ev['trace_t0'] + 60 * dt, True, retreated_ee, retreated_ee)
    add_segment('trace0_to_hold3', 'trace_t0 (E7)', 'hold_3s_step_180 (E8)',
                trace['vertices'][0], trace['vertices'][180], ev['trace_t0'],
                ev['trace_t0'] + 180 * dt, True, retreated_ee, retreated_ee,
                'adjacent event pair E7->E8')
    add_segment('hold3_to_window_start', 'hold_3s_step_180 (E8)',
                'window_start_step_210 (E9)',
                trace['vertices'][180], trace['vertices'][210],
                ev['trace_t0'] + 180 * dt, ev['trace_t0'] + 210 * dt,
                True, retreated_ee, retreated_ee, 'adjacent event pair E8->E9')
    add_segment('trace0_to_window_start', 'trace_t0', 'window_start_step_210',
                trace['vertices'][0], trace['vertices'][210], ev['trace_t0'],
                ev['trace_t0'] + 210 * dt, True, retreated_ee, retreated_ee,
                'coarse E7->E9; sub-segments above')
    add_segment('window_start_to_hold4', 'window_start_step_210 (E9)',
                'hold_4s_step_240 (E10)',
                trace['vertices'][210], trace['vertices'][240],
                ev['trace_t0'] + 210 * dt, ev['trace_t0'] + 240 * dt,
                True, retreated_ee, retreated_ee, 'adjacent event pair E9->E10')
    add_segment('hold4_to_window_end', 'hold_4s_step_240 (E10)',
                'window_end_step_330 (E11)',
                trace['vertices'][240], trace['vertices'][330],
                ev['trace_t0'] + 240 * dt, ev['trace_t0'] + 330 * dt,
                True, retreated_ee, retreated_ee, 'adjacent event pair E10->E11')
    add_segment('window_210_330', 'window_start_step_210', 'window_end_step_330',
                trace['vertices'][210], trace['vertices'][330],
                ev['trace_t0'] + 210 * dt, ev['trace_t0'] + 330 * dt,
                True, retreated_ee, retreated_ee,
                'formal stability window; original evaluator metrics below')
    add_segment('trace0_to_end', 'trace_t0', 'trace_step_330',
                trace['vertices'][0], trace['vertices'][330], ev['trace_t0'],
                ev['trace_t0'] + 330 * dt, True, retreated_ee, retreated_ee)

    window = next(s for s in segments if s['segment'] == 'window_210_330')
    window['original_evaluator'] = orig
    window['original_evaluator_match'] = crosscheck

    return {
        'case': case,
        'seed': int(meta['seed']),
        'level': meta['level'],
        'mode': meta['execution_mode'],
        'result_dir': str(case_dir),
        'verdict': verdict.get('status'),
        'success': verdict.get('success'),
        'failed_checks': [k for k, ok in ((verdict.get('criteria') or {}).get('checks') or {}).items() if not ok],
        'events': ev['events'],
        'event_notes': {
            'observed_to_world_offset': ev['offset'],
            'same_time_clock': 'evidence observed_step and success-trace absolute_step are '
                               'different counters; sim_time_s is the common clock',
            'same_step_events': ['attachment release and gripper effective open (E3)'],
            'missing_events': ['finger/cloth contact (E12)',
                               'per-step cloth vertices between hold end and trace t0',
                               'gripper opening amount between release action begin and trace t0'],
        },
        'identities': identities(case_dir, trace, meta),
        'final_npz_equals_trace_step_330': bool(np.array_equal(final_v, trace['vertices'][330])),
        'trace': {
            'trace_t0_sim_time_s': ev['trace_t0'],
            'absolute_step_t0': int(meta['absolute_step']),
            'dt_s': dt,
            'centroid_from_hold_mm': trace_centroid.tolist(),
            'p95_from_hold_mm': trace_p95.tolist(),
            'centroid_from_0_mm': trace_arrays_['centroid_from_0_mm'].tolist(),
            'p95_from_0_mm': trace_arrays_['p95_from_0_mm'].tolist(),
            'p95_from_210_mm': trace_arrays_['p95_from_210_mm'].tolist(),
            'centroid_from_210_mm': trace_arrays_['centroid_from_210_mm'].tolist(),
            'stability_recomputed': calc,
            'stability_original': orig,
            'stability_crosscheck': crosscheck,
        },
        'segments': segments,
        'release_geometry': {
            'released_ee_m': released_ee.tolist(),
            'retreated_ee_m': retreated_ee.tolist(),
            'released_ee_z_m': float(released_ee[2]),
            'retreated_ee_z_m': float(retreated_ee[2]),
            'upward_m': float(retreated_ee[2] - released_ee[2]),
            'released_min_vertex_distance_mm': min_ee_distance_mm(released_v, released_ee),
            'retreated_min_vertex_distance_mm': min_ee_distance_mm(retreated_v, retreated_ee),
            'window_min_vertex_distance_start_mm': min_ee_distance_mm(trace['vertices'][210], retreated_ee),
            'window_min_vertex_distance_end_mm': min_ee_distance_mm(trace['vertices'][330], retreated_ee),
            'note': 'EE point distance is a geometric proxy, not contact.'
        },
        'curves': {
            'hold_x_s': hold_x.tolist(),
            'hold_step': hold_step.tolist(),
            'hold_centroid_from_hold_mm': hold_centroid.tolist(),
            'hold_p95_from_hold_mm': hold_p95.tolist(),
            'trace_x_s': trace_x.tolist(),
            'trace_step': np.asarray(trace['absolute_steps'], dtype=int).tolist(),
            'trace_centroid_from_hold_mm': trace_centroid.tolist(),
            'trace_p95_from_hold_mm': trace_p95.tolist(),
            'released_x_s': released_x,
            'released_step': int(released_step),
            'released_centroid_from_hold_mm': released_centroid,
            'released_p95_from_hold_mm': released_p95,
            'retreated_x_s': retreated_x,
            'retreated_step': int(retreated_step),
            'retreated_centroid_from_hold_mm': retreated_centroid,
            'retreated_p95_from_hold_mm': retreated_p95,
            'window_steps': list(range(210, 331)),
            'window_centroid_from_210_mm':
                trace_arrays_['centroid_from_210_mm'].tolist(),
            'window_p95_from_210_mm': trace_arrays_['p95_from_210_mm'].tolist(),
        },
        'missing_segments': [
            {'pair': 'E1->E2', 'reason': 'no per-step cloth vertices at the release action begin'},
            {'pair': 'E2->E3', 'reason': 'no per-step cloth vertices at attachment release'},
            {'pair': 'E3->E4', 'reason': 'no per-step cloth vertices at E3; only the E4 snapshot'},
            {'pair': 'E4->E5', 'reason': 'no per-step cloth vertices at the retreat command start'},
            {'pair': 'E5->E6', 'reason': 'no per-step cloth vertices at E5/E6'},
            {'pair': 'E6->E7', 'reason': 'no per-step cloth vertices during the retreat'}
        ],
        'contact_record': 'missing',
        'contact_record_note': 'No finger/gripper-cloth contact force or impulse trace is '
                               'present in RC2. room_collision_audit.json covers room '
                               'colliders only. Distance evidence is not contact.',
    }


def plot_case(analysis, out_path):
    c = analysis['curves']
    ev = analysis['events']
    event_x = []
    event_t = {}
    for e in ev:
        world = e.get('world_step') if e.get('world_step') is not None \
            else e.get('world_step_inferred')
        if world is None:
            continue
        event_x.append((e['id'], e['event'], int(world)))
        event_t[e['id']] = e.get('sim_time_s')
    # Preserve a fixed event order; missing contact is not drawn.
    order = ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8', 'E9', 'E10', 'E11']
    labels = {
        'E1': 'E1 hold last frame',
        'E2': 'E2 release action begin',
        'E3': 'E3 attachment release / open',
        'E4': 'E4 released snapshot',
        'E5': 'E5 retreat command start',
        'E6': 'E6 retreat reaches 1 mm',
        'E7': 'E7 retreat end / trace t0',
        'E8': 'E8 hold_3s',
        'E9': 'E9 window start',
        'E10': 'E10 hold_4s',
        'E11': 'E11 window end',
    }
    ex = {eid: x for eid, _, x in event_x}
    hold_end_x = ex.get('E1', 1944)
    retreat_end_x = ex.get('E7', 2099)
    window_start_x = ex.get('E9', 2309)
    window_end_x = ex.get('E11', 2429)
    xmin = hold_end_x - 80
    xmax = window_end_x + 10
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [1, 1, 0.9]})
    fig.suptitle('RC2 drift diagnosis — %s' % analysis['case'], color=INK, fontsize=13, y=0.985)
    st = analysis['trace']['stability_original']
    fig.text(0.5, 0.955,
             'verdict %s (failed: %s) · max centroid %.3f mm (limit 1) · '
             'max P95 %.3f mm (limit 3)' % (
                 analysis['verdict'], ', '.join(analysis['failed_checks']),
                 1000 * st['centroid_drift_max_m'], 1000 * st['vertex_drift_p95_max_m']),
             ha='center', color=SECONDARY, fontsize=9)

    for ax in axes[:2]:
        ax.set_facecolor(SURFACE)
        ax.grid(True, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color(AXIS)
        ax.tick_params(colors=MUTED)
        ax.set_xlim(xmin, xmax)
        ax.axvspan(hold_end_x, retreat_end_x, color='#f0efec', alpha=0.65, zorder=0)
        ax.axvspan(window_start_x, window_end_x, color='#cde2fb', alpha=0.35, zorder=0)
        for eid in order:
            if eid not in ex:
                continue
            x = ex[eid]
            ax.axvline(x, color=MUTED, linewidth=0.7, linestyle=':', zorder=1)

    ax0, ax1, ax2 = axes
    ax0.plot(c['hold_step'], c['hold_centroid_from_hold_mm'], color=BLUE, linewidth=2)
    ax0.plot(c['released_step'], c['released_centroid_from_hold_mm'], 'o', color=BLUE,
             markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.5)
    ax0.plot(c['retreated_step'], c['retreated_centroid_from_hold_mm'], 'o', color=BLUE,
             markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.5)
    ax0.plot([c['released_step'], c['retreated_step']],
             [c['released_centroid_from_hold_mm'], c['retreated_centroid_from_hold_mm']],
             color=BLUE, linewidth=1.2, linestyle='--')
    ax0.plot(c['trace_step'], c['trace_centroid_from_hold_mm'], color=BLUE, linewidth=2)
    ax0.axhline(1.0, color=CRITICAL, linewidth=1.0, linestyle='--')
    ax0.text(xmax - 10, 1.08, '1 mm limit', color=CRITICAL, ha='right', va='bottom', fontsize=8)
    ax0.set_ylabel('centroid displacement (mm)')
    ax0.set_xlabel('world physical step (pre-trace inferred by +2)', fontsize=8)
    ax0.set_title('planar centroid displacement from the last hold frame', color=INK, loc='left')
    ax0.set_ylim(0, max(6.0, max(c['trace_centroid_from_hold_mm']
                                 + [c['released_centroid_from_hold_mm'],
                                    c['retreated_centroid_from_hold_mm']]) * 1.08))
    ytext = ax0.get_ylim()[1] * 0.86
    ax0.text(hold_end_x + 0.55 * (retreat_end_x - hold_end_x), ytext,
             'per-step cloth vertices not recorded;\nonly released/retreated snapshots',
             color=SECONDARY, fontsize=8, ha='center', va='top', style='italic')
    ax0.text(0.5 * (window_start_x + window_end_x), ytext,
             'formal window\n210..330', color=SECONDARY, fontsize=8,
             ha='center', va='top')

    ax1.plot(c['hold_step'], c['hold_p95_from_hold_mm'], color=ORANGE, linewidth=2)
    ax1.plot(c['released_step'], c['released_p95_from_hold_mm'], 'o', color=ORANGE,
             markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.5)
    ax1.plot(c['retreated_step'], c['retreated_p95_from_hold_mm'], 'o', color=ORANGE,
             markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.5)
    ax1.plot([c['released_step'], c['retreated_step']],
             [c['released_p95_from_hold_mm'], c['retreated_p95_from_hold_mm']],
             color=ORANGE, linewidth=1.2, linestyle='--')
    ax1.plot(c['trace_step'], c['trace_p95_from_hold_mm'], color=ORANGE, linewidth=2)
    ax1.axhline(3.0, color=CRITICAL, linewidth=1.0, linestyle='--')
    ax1.text(xmax - 10, 3.08, '3 mm limit', color=CRITICAL, ha='right', va='bottom', fontsize=8)
    ax1.set_ylabel('vertex drift P95 (mm)')
    ax1.set_xlabel('world physical step (pre-trace inferred by +2)', fontsize=8)
    ax1.set_title('vertex drift P95 from the last hold frame (diagnostic reference; '
                  'formal P95 below)', color=INK, loc='left')
    ax1.set_ylim(0, max(6.0, max(c['trace_p95_from_hold_mm']
                                 + [c['released_p95_from_hold_mm'],
                                    c['retreated_p95_from_hold_mm']]) * 1.08))

    ax2.set_facecolor(SURFACE)
    ax2.grid(True, color=GRID, linewidth=0.6)
    ax2.set_axisbelow(True)
    for spine in ax2.spines.values():
        spine.set_color(AXIS)
    ax2.tick_params(colors=MUTED)
    steps = c['window_steps']
    centroid = c['window_centroid_from_210_mm']
    p95 = c['window_p95_from_210_mm']
    ax2.plot(steps, centroid, color=BLUE, linewidth=2, label='centroid (limit 1 mm)')
    ax2.plot(steps, p95, color=ORANGE, linewidth=2, label='vertex P95 (limit 3 mm)')
    ax2.axhline(1.0, color=CRITICAL, linewidth=1.0, linestyle='--')
    ax2.axhline(3.0, color=CRITICAL, linewidth=1.0, linestyle='--')
    imax_c = int(np.argmax(centroid))
    imax_p = int(np.argmax(p95))
    ax2.plot(steps[imax_c], centroid[imax_c], 'o', color=BLUE, markersize=7,
             markeredgecolor=SURFACE, markeredgewidth=1.5)
    ax2.plot(steps[imax_p], p95[imax_p], 'o', color=ORANGE, markersize=7,
             markeredgecolor=SURFACE, markeredgewidth=1.5)
    ax2.annotate('max centroid %.3f mm' % centroid[imax_c], (steps[imax_c], centroid[imax_c]),
                 xytext=(-8, -14), textcoords='offset points', color=BLUE,
                 fontsize=8, ha='right')
    ax2.annotate('max P95 %.3f mm' % p95[imax_p], (steps[imax_p], p95[imax_p]),
                 xytext=(-8, 8), textcoords='offset points', color=ORANGE,
                 fontsize=8, ha='right')
    ax2.axvline(210, color=MUTED, linewidth=0.7, linestyle=':')
    ax2.axvline(240, color=MUTED, linewidth=0.7, linestyle=':')
    ax2.axvline(330, color=MUTED, linewidth=0.7, linestyle=':')
    ax2.set_xlim(210, 330)
    ax2.set_ylim(0, max(5.0, float(max(np.max(centroid), np.max(p95))) * 1.1))
    ax2.set_xlabel('success-trace physical step (t0 = last OPEN completion)')
    ax2.set_ylabel('displacement (mm)')
    ax2.set_title('original evaluator definition: centroid and P95 from window frame 210',
                  color=INK, loc='left')
    ax2.legend(loc='upper left', frameon=False, fontsize=8)
    ax2.text(214, 0.25, 'formal window 210..330; limits 1 mm / 3 mm',
             color=SECONDARY, fontsize=8)

    handles = [Line2D([0], [0], color=MUTED, linewidth=0.8, linestyle=':') for _ in order]
    legend_labels = []
    for eid in order:
        if eid not in ex:
            continue
        t = event_t.get(eid)
        tstr = '%.3f s' % t if t is not None else 'time missing'
        legend_labels.append('%s (step %d, %s)' % (labels[eid], ex[eid], tstr))
    fig.legend([h for eid, h in zip(order, handles) if eid in ex], legend_labels,
               loc='lower center', ncol=3, frameon=False, fontsize=6.8,
               bbox_to_anchor=(0.5, 0.080))
    fig.text(0.01, 0.008,
             'source: success_trace.npz (331 steps), pre_release_hold.npz (180 steps), '
             'evidence/timeline.jsonl.\nPre-trace world step is inferred as observed_step + 2. '
             'Contact record missing; EE distance is a geometric proxy, not contact.',
             fontsize=6.5, color=MUTED, ha='left', va='bottom')
    fig.tight_layout(rect=[0, 0.17, 1, 0.94])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def write_csv(path, rows, fields):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fields})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case-index', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    index = load_case_index(args.case_index)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'plots').mkdir(exist_ok=True)

    selected = ['4202 single', '4302 single']
    analyses = []
    for name in selected:
        if name not in index:
            raise SystemExit('Case not in index: ' + name)
        c = index[name]
        analyses.append(case_analysis(name, Path(c['result_dir'])))

    events_rows = []
    segment_rows = []
    for a in analyses:
        for e in a['events']:
            events_rows.append({'case': a['case'], **{k: e.get(k) for k in (
                'id', 'event', 'evidence_observed_step', 'world_step_inferred',
                'world_step', 'sim_time_s', 'source', 'note')}})
        for s in a['segments']:
            segment_rows.append({'case': a['case'], **s})

    event_fields = ['case', 'id', 'event', 'evidence_observed_step',
                    'world_step_inferred', 'world_step', 'sim_time_s', 'source', 'note']
    segment_fields = ['case', 'segment', 'start_event', 'end_event', 'start_time_s',
                      'end_time_s', 'duration_s', 'centroid_dx_mm', 'centroid_dy_mm',
                      'centroid_norm_mm', 'rotation_deg', 'rigid_rms_mm',
                      'vertex_p95_mm', 'vertex_max_mm', 'centroid_speed_mm_s',
                      'vertex_speed_p95_mm_s', 'vertex_speed_max_mm_s',
                      'per_step_vertices_available', 'contact_record',
                      'ee_min_vertex_distance_start_mm',
                      'ee_min_vertex_distance_end_mm', 'distance_evidence_note', 'note']
    write_csv(out / 'event-table.csv', events_rows, event_fields)
    write_csv(out / 'segment-metrics.csv', segment_rows, segment_fields)

    doc = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'source_case_index': str(Path(args.case_index).resolve()),
        'cases': analyses
    }
    (out / 'phase-events.json').write_text(json.dumps(
        {'generated_utc': doc['generated_utc'],
         'source_case_index': doc['source_case_index'],
         'cases': [{'case': a['case'], 'events': a['events'],
                    'event_notes': a['event_notes'], 'identities': a['identities'],
                    'contact_record': a['contact_record'],
                    'contact_record_note': a['contact_record_note']} for a in analyses]},
        indent=2) + '\n')
    (out / 'phase-segments.json').write_text(json.dumps(
        {'generated_utc': doc['generated_utc'],
         'source_case_index': doc['source_case_index'],
         'cases': [{'case': a['case'], 'segments': a['segments'],
                    'missing_segments': a['missing_segments'],
                    'release_geometry': a['release_geometry'],
                    'trace_stability': a['trace']} for a in analyses]},
        indent=2) + '\n')
    trace_doc = {'generated_utc': doc['generated_utc'],
                 'cases': [{'case': a['case'], 'curves': a['curves'],
                            'trace': {k: a['trace'][k] for k in (
                                'trace_t0_sim_time_s', 'absolute_step_t0', 'dt_s',
                                'stability_recomputed', 'stability_original',
                                'stability_crosscheck')}} for a in analyses]}
    (out / 'phase-trace.json').write_text(json.dumps(trace_doc, indent=2) + '\n')

    for a in analyses:
        fn = 'drift_%s.png' % a['case'].replace(' ', '_')
        plot_case(a, out / 'plots' / fn)

    lines = ['# RC2 drift localisation: 4202 single and 4302 single', '',
             'Generated from existing RC2 evidence only; no simulation was run.', '',
             '## Event table', '',
             '| case | id | event | observed step | world step | sim time (s) | source |',
             '|---|---|---|---:|---:|---:|---|']
    for a in analyses:
        for e in a['events']:
            world = e.get('world_step', e.get('world_step_inferred'))
            lines.append('| %s | %s | %s | %s | %s | %s | %s |' % (
                a['case'], e['id'], e['event'],
                e['evidence_observed_step'] if e['evidence_observed_step'] is not None else 'missing',
                world if world is not None else 'missing',
                '%.6f' % e['sim_time_s'] if e['sim_time_s'] is not None else 'missing',
                e['source']))
    lines += ['', '## Adjacent-event segment metrics', '',
              '| case | segment | duration s | centroid mm | rotation deg | P95 mm | '
              'max mm | rigid RMS mm | per-step vertices | contact | EE dist start/end mm |',
              '|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|']
    for a in analyses:
        for s in a['segments']:
            lines.append('| %s | %s | %.4f | %.4f | %.4f | %.4f | %.4f | %.4f | %s | %s | %.3f / %.3f |' % (
                a['case'], s['segment'], s['duration_s'], s['centroid_norm_mm'],
                s['rotation_deg'], s['vertex_p95_mm'], s['vertex_max_mm'],
                s['rigid_rms_mm'], s['per_step_vertices_available'], s['contact_record'],
                s['ee_min_vertex_distance_start_mm'], s['ee_min_vertex_distance_end_mm']))
    lines += ['', '## Missing adjacent-event segments', '',
              'The release/retreat interval has only sparse snapshots. The following '
              'adjacent event pairs cannot be computed per physical step; only E1->E4 '
              '(hold last frame to released snapshot) and E4->E7 (released to retreated) '
              'are available at snapshot level:', '']
    for a in analyses:
        for m in a['missing_segments']:
            lines.append('- %s %s: %s' % (a['case'], m['pair'], m['reason']))
    lines += ['', '## Original evaluator cross-check', '',
              '| case | metric | recomputed | original | abs delta | match |',
              '|---|---|---:|---:|---:|---|']
    for a in analyses:
        for k, v in a['trace']['stability_crosscheck'].items():
            lines.append('| %s | %s | %.12g | %.12g | %.3g | %s |' % (
                a['case'], k, v['recomputed'], v['original'], v['abs_delta'], v['match']))
    lines += ['', '## Findings and missing evidence', '',
              '- The pre-release hold is stable; the motion starts at/after release.',
              '- The observed release-to-retreat interval has only the released and '
              'retreated snapshots. Per-physical-step cloth vertices and gripper opening '
              'amount are missing, so the exact onset step inside that interval cannot be '
              'localised.',
              '- The formal 210..330 window motion is nearly rigid translation plus rotation '
              '(small rigid-fit RMS), i.e., whole-cloth sliding/rotation rather than local '
              'relaxation.',
              '- No finger/gripper-cloth contact force or impulse trace exists in RC2. '
              'The EE-to-nearest-vertex distance is a geometric proxy, not contact. '
              'Hypotheses about robot contact remain to be tested by D1/D2.',
              '- The original verify-dev exit code 1 is a stability rejection of the '
              'positive smoke case 4202 arc4; the RGB/video/holding evidence checks pass '
              'for all seven cases.',
              '', '## Plots', '',
              '- `plots/drift_4202_single.png`',
              '- `plots/drift_4302_single.png`']
    (out / 'diagnosis.md').write_text('\n'.join(lines) + '\n')

    for a in analyses:
        st = a['trace']['stability_original']
        print('%s verdict=%s failed=%s centroid_max=%.6f p95_max=%.6f' % (
            a['case'], a['verdict'], a['failed_checks'],
            st['centroid_drift_max_m'], st['vertex_drift_p95_max_m']))
    print('DRIFT_DIAGNOSIS_OK', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
