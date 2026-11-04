"""Passive release-window diagnostic recorder for the RC2 recovery runner.

Adds, without changing physics stepping, control frequency or action targets:

  * per-physical-step cloth vertices from release action start through retreat;
  * EE position and quaternion;
  * all joint positions, DOF names, finger-joint aperture and gripper state;
  * holding / logical attachment / three-slot enable / command latch;
  * EE-to-nearest-vertex and finger-link-to-nearest-vertex distances;
  * named ungrasp/delay/retreat events and released/retreated sample labels;
  * per-step phase labels so delay and retreat rows are separable.

The parent EpisodeEvidence remains the video/state recorder.  This subclass only
observes after each world.step and writes a separate release_diag.npz/json.
Contact is a separate best-effort channel (square_contact_recorder.py); a
geometric distance is explicitly distance evidence, never a contact record.
"""
import csv
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np

from episode_evidence import EpisodeEvidence

REQUIRED_EVENTS = ['ungrasp_return', 'delay_begin', 'delay_end',
                   'retreat_begin', 'retreat_end']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _to_np(value):
    if hasattr(value, 'detach'):
        value = value.detach().cpu().numpy()
    return np.asarray(value, dtype=float).reshape(-1)


def _to_np2(value):
    if hasattr(value, 'detach'):
        value = value.detach().cpu().numpy()
    return np.asarray(value, dtype=float)


class DiagnosticEpisodeEvidence(EpisodeEvidence):
    def __init__(self, *args, **kwargs):
        # Set the hooks before the parent __init__ emits its start row.
        self.release_active = False
        self.release_rows = []
        self.release_errors = []
        self.release_action_begin = None
        self.release_action_end = None
        self.events = []
        self.current_phase = 'release_opening'
        self.finger_link_names = []
        self.finger_link_distance_available = False
        super().__init__(*args, **kwargs)

    def _extra_state(self):
        robot = self.b._env.robots[0]
        ee, q = robot.get_cur_ee_pos()
        ee = np.asarray(ee, dtype=float).reshape(-1)
        q = None if q is None else np.asarray(q, dtype=float).reshape(-1)
        jp = _to_np(robot._robot.get_joint_positions())
        dofs = list(getattr(robot._robot, 'dof_names', []) or [])
        finger_idx = [i for i, n in enumerate(dofs)
                      if 'finger' in str(n).lower()]
        aperture = None
        aperture_note = 'finger joint names not found; aperture missing'
        if len(finger_idx) == 2 and len(jp) > max(finger_idx):
            aperture = float(jp[finger_idx].sum())
            aperture_note = ('sum of the two finger joint positions; '
                             'not a calibrated fingertip gap')
        elif len(jp) >= 9:
            finger_idx = [len(jp) - 2, len(jp) - 1]
            aperture = float(jp[finger_idx].sum())
            aperture_note = ('last two joint positions assumed to be fingers; '
                             'not a calibrated fingertip gap')
        return {
            'ee_m': ee.tolist(),
            'ee_quaternion_wxyz': q.tolist() if q is not None else None,
            'joint_positions': jp.tolist(),
            'dof_names': dofs,
            'finger_joint_indices': finger_idx,
            'gripper_aperture_m': aperture,
            'gripper_aperture_note': aperture_note,
            'gripper_state': int(getattr(self.b, '_gripper_state', -1)),
        }

    def state(self):
        s = super().state()
        s.update(self._extra_state())
        return s

    def emit(self, kind, **data):
        row = super().emit(kind, **data)
        if self.release_active:
            if kind in ('state', 'sample', 'release_anchor'):
                self._capture_release_row(row)
            elif kind == 'event':
                self._capture_event(row)
            elif kind == 'action_begin':
                self.release_action_begin = row
            elif kind == 'action_end':
                self.release_action_end = row
        return row

    def start_release_diag(self):
        if self.release_active:
            raise RuntimeError('Release diagnostic already active')
        self.release_active = True
        self.release_rows = []
        self.release_errors = []
        self.events = []
        self.current_phase = 'release_opening'
        self.release_action_begin = None
        self.release_action_end = None
        # Anchor the last pre-release state without advancing physics.  It is
        # deliberately not a ``state`` row: the original evidence timeline must
        # keep its one-state-per-physics-step audit, and the anchor is captured
        # in release_diag instead.
        self.emit('release_anchor', phase='release_start_anchor', **self.state())

    def record_event(self, event, phase=None):
        """Emit one named event with the full current robot/cloth summary."""
        if not self.release_active:
            return None
        if event not in REQUIRED_EVENTS:
            raise ValueError('Unregistered D1 event: ' + str(event))
        return self.emit('event', event=str(event), phase=str(phase or event),
                         **self.state())

    def _finger_links(self):
        robot = self.b._env.robots[0]
        names = getattr(robot._robot, 'link_names', None)
        if names is None:
            names = getattr(robot._robot, 'body_names', None)
        if names is None:
            return None, None
        names = list(names)
        positions = _to_np2(robot._robot.get_link_positions())
        idx = [i for i, n in enumerate(names) if 'finger' in str(n).lower()]
        if len(idx) != 2 or positions.ndim != 2 or positions.shape[0] <= max(idx):
            return None, None
        self.finger_link_names = [str(names[i]) for i in idx]
        return positions[idx], self.finger_link_names

    def _capture_release_row(self, row):
        try:
            vertices = np.asarray(self.b._garment_world_positions(), dtype=float)
            if vertices.shape != (441, 3) or not np.isfinite(vertices).all():
                raise ValueError('Invalid cloth vertices in release diagnostic')
            ee = np.asarray(row['ee_m'], dtype=float)
            ee_dist = float(np.min(np.linalg.norm(vertices - ee, axis=1)) * 1000.0)
            finger_dist = None
            links = None
            try:
                links, names = self._finger_links()
            except Exception as exc:
                self.release_errors.append('finger link distance: ' + repr(exc))
            if links is not None:
                finger_dist = float(min(
                    np.min(np.linalg.norm(vertices - link, axis=1)) for link in links
                ) * 1000.0)
                self.finger_link_distance_available = True
            self.release_rows.append({
                'sim_time_s': float(row['sim_time_s']),
                'observed_step': int(row['observed_step']),
                'backend_step': int(row.get('backend_step', -1)),
                'call_id': row.get('call_id'),
                'phase': row.get('phase') or self.current_phase,
                'sample_label': row.get('label', ''),
                'holding': bool(row['holding']),
                'attached': bool(row['attached']),
                'enabled_slots': [bool(x) for x in row['enabled_slots']],
                'logical_attached': bool(row['logical_attached']),
                'command_holding': bool(row['command_holding']),
                'ee_m': [float(x) for x in row['ee_m']],
                'ee_quaternion_wxyz': row.get('ee_quaternion_wxyz'),
                'joint_positions': [float(x) for x in row['joint_positions']],
                'gripper_aperture_m': row.get('gripper_aperture_m'),
                'gripper_aperture_note': row.get('gripper_aperture_note'),
                'finger_joint_indices': row.get('finger_joint_indices'),
                'gripper_state': int(row.get('gripper_state', -1)),
                'vertices': vertices,
                'ee_min_vertex_distance_mm': ee_dist,
                'finger_min_vertex_distance_mm': finger_dist,
            })
        except Exception as exc:
            self.release_errors.append('release row: ' + repr(exc))

    def _capture_event(self, row):
        try:
            vertices = np.asarray(self.b._garment_world_positions(), dtype=float)
            if vertices.shape != (441, 3) or not np.isfinite(vertices).all():
                raise ValueError('Invalid cloth vertices in release event')
            self.events.append({
                'sequence': len(self.events) + 1,
                'event': str(row.get('event')),
                'phase': str(row.get('phase', row.get('event'))),
                'sim_time_s': float(row['sim_time_s']),
                'observed_step': int(row['observed_step']),
                'backend_step': int(row.get('backend_step', -1)),
                'call_id': row.get('call_id'),
                'holding': bool(row['holding']),
                'attached': bool(row['attached']),
                'enabled_slots': [bool(x) for x in row['enabled_slots']],
                'logical_attached': bool(row['logical_attached']),
                'command_holding': bool(row['command_holding']),
                'ee_m': [float(x) for x in row['ee_m']],
                'ee_quaternion_wxyz': row.get('ee_quaternion_wxyz'),
                'joint_positions': [float(x) for x in row['joint_positions']],
                'gripper_aperture_m': row.get('gripper_aperture_m'),
                'gripper_state': int(row.get('gripper_state', -1)),
                'cloth_centroid_m': vertices.mean(axis=0).tolist(),
                'cloth_vertices_sha256': hashlib.sha256(
                    np.ascontiguousarray(vertices, dtype=np.float64).tobytes()
                ).hexdigest(),
            })
        except Exception as exc:
            self.release_errors.append('release event: ' + repr(exc))

    def _write_events_csv(self, events):
        path = self.out / 'release_diag_events.csv'
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(['sequence', 'event', 'phase', 'sim_time_s',
                             'observed_step', 'backend_step', 'holding', 'attached',
                             'command_holding', 'ee_x_m', 'ee_y_m', 'ee_z_m',
                             'gripper_aperture_m', 'cloth_cx_m', 'cloth_cy_m',
                             'cloth_cz_m', 'cloth_vertices_sha256'])
            for event in events:
                ee = event['ee_m']
                cloth = event['cloth_centroid_m']
                writer.writerow([
                    event['sequence'], event['event'], event['phase'],
                    event['sim_time_s'], event['observed_step'],
                    event['backend_step'], event['holding'], event['attached'],
                    event['command_holding'], ee[0], ee[1], ee[2],
                    event['gripper_aperture_m'], cloth[0], cloth[1], cloth[2],
                    event['cloth_vertices_sha256']])

    def finish_release_diag(self, failed=False):
        if not self.release_active:
            return None
        self.release_active = False
        rows = list(self.release_rows)
        events = list(self.events)
        if not rows:
            doc = {'protocol': 'stage4-a5-rc2-d1-120',
                   'failed': bool(failed), 'count': 0,
                   'events': events, 'event_count': len(events),
                   'required_events': REQUIRED_EVENTS,
                   'events_complete': [e['event'] for e in events] == REQUIRED_EVENTS,
                   'errors': self.release_errors + ['no release rows captured'],
                   'contact_channel': 'not sampled', 'distance_evidence': False}
            (self.out / 'release_diag.json').write_text(
                json.dumps(doc, indent=2), encoding='utf-8')
            self._write_events_csv(events)
            return doc
        vertices = np.stack([r['vertices'] for r in rows])
        ee = np.asarray([r['ee_m'] for r in rows], dtype=float)
        quat = np.asarray([
            r['ee_quaternion_wxyz'] if r['ee_quaternion_wxyz'] is not None
            else [np.nan] * 4 for r in rows], dtype=float)
        joints = np.asarray([r['joint_positions'] for r in rows], dtype=float)
        aperture = np.asarray([
            r['gripper_aperture_m'] if r['gripper_aperture_m'] is not None
            else np.nan for r in rows], dtype=float)
        finger_dist = np.asarray([
            r['finger_min_vertex_distance_mm']
            if r['finger_min_vertex_distance_mm'] is not None else np.nan
            for r in rows], dtype=float)
        labels = np.asarray([str(r['sample_label']) for r in rows], dtype='U32')
        phases = np.asarray([str(r['phase']) for r in rows], dtype='U32')
        np.savez_compressed(
            self.out / 'release_diag.npz',
            vertices=vertices,
            ee_m=ee,
            ee_quaternion_wxyz=quat,
            joint_positions=joints,
            gripper_aperture_m=aperture,
            gripper_state=np.asarray([r['gripper_state'] for r in rows], dtype=int),
            holding=np.asarray([r['holding'] for r in rows], dtype=bool),
            attached=np.asarray([r['attached'] for r in rows], dtype=bool),
            enabled_slots=np.asarray([r['enabled_slots'] for r in rows], dtype=bool),
            logical_attached=np.asarray([r['logical_attached'] for r in rows], dtype=bool),
            command_holding=np.asarray([r['command_holding'] for r in rows], dtype=bool),
            sim_time_s=np.asarray([r['sim_time_s'] for r in rows], dtype=float),
            observed_step=np.asarray([r['observed_step'] for r in rows], dtype=int),
            backend_step=np.asarray([r['backend_step'] for r in rows], dtype=int),
            call_id=np.asarray([(-1 if r['call_id'] is None else r['call_id'])
                                for r in rows], dtype=int),
            ee_min_vertex_distance_mm=np.asarray(
                [r['ee_min_vertex_distance_mm'] for r in rows], dtype=float),
            finger_min_vertex_distance_mm=finger_dist,
            sample_label=labels,
            phase=phases,
        )
        dt = float(self.world.get_physics_dt())
        begin = self.release_action_begin or {}
        end = self.release_action_end or {}
        doc = {
            'protocol': 'stage4-a5-rc2-d1-120',
            'failed': bool(failed),
            'count': len(rows),
            'dt_s': dt,
            'start_sim_time_s': rows[0]['sim_time_s'],
            'end_sim_time_s': rows[-1]['sim_time_s'],
            'start_observed_step': rows[0]['observed_step'],
            'end_observed_step': rows[-1]['observed_step'],
            'sample_labels': [str(r['sample_label']) for r in rows
                              if r['sample_label']],
            'events': events,
            'event_count': len(events),
            'required_events': REQUIRED_EVENTS,
            'events_complete': [e['event'] for e in events] == REQUIRED_EVENTS,
            'action_begin': {k: begin.get(k) for k in
                             ('sim_time_s', 'observed_step', 'targets', 'commands', 'horizon')},
            'action_end': {k: end.get(k) for k in
                           ('sim_time_s', 'observed_step', 'executed_steps')},
            'recording': {
                'cloth_vertices': 'vertices[N,441,3]',
                'gripper_pose': 'ee_m + ee_quaternion_wxyz',
                'gripper_aperture': 'gripper_aperture_m from finger joint positions',
                'attachment': 'holding/attached/enabled_slots/logical_attached/command_holding',
                'distances': 'ee_min_vertex_distance_mm; finger_min_vertex_distance_mm if available',
                'samples': 'released/retreated labels in sample_label',
                'events': 'ungrasp_return/delay_begin/delay_end/retreat_begin/retreat_end in release_diag.json and release_diag_events.csv',
                'phases': 'per-step phase labels: release_opening, released, delay, retreat, retreat_done'
            },
            'physics_control_actions': {
                'mode': 'passive post-step reads only',
                'physics_dt_s': dt,
                'no_extra_world_step': True,
                'no_control_call': True,
                'action_targets_from_parent': True,
                'action_begin_targets': begin.get('targets'),
                'action_begin_commands': begin.get('commands'),
                'action_begin_horizon': begin.get('horizon'),
            },
            'joint_names': rows[0].get('dof_names') if rows else [],
            'finger_joint_indices': rows[0].get('finger_joint_indices') if rows else [],
            'finger_link_names': self.finger_link_names,
            'gripper_aperture_note': rows[0].get('gripper_aperture_note') if rows else None,
            'contact_channel': ('square_contact_recorder.ContactRecorder; robot rigid '
                                'contacts only; may be zero; not cloth-particle '
                                'certification; see contact_report.json'),
            'distance_evidence': {
                'ee_min_vertex_distance_mm': True,
                'finger_min_vertex_distance_mm': bool(self.finger_link_distance_available),
                'note': 'geometric proxies, not a contact record or force measurement'
            },
            'errors': self.release_errors,
            'notes': [
                'release_start_anchor is the last pre-release state; the first '
                'release-action step follows it',
                'released/retreated sample rows are included by label',
                'named events: ' + ', '.join(REQUIRED_EVENTS),
                'state phase labels distinguish delay (120 rows) from retreat',
                'per-step cloth vertices now cover the release/opening/delay/retreat interval',
                'contact force/impulse is only whatever the robot rigid contact '
                'channel reports; absence of events is not evidence of no contact'
            ]
        }
        (self.out / 'release_diag.json').write_text(
            json.dumps(doc, indent=2, allow_nan=False), encoding='utf-8')
        self._write_events_csv(events)
        return doc


def attach_evidence_diag(backend, output, runner, code_files):
    base = Path(runner).resolve().parent
    sources = [Path(__file__), Path(__file__).with_name('episode_evidence.py'),
               Path(runner)]
    for name, expected in code_files.items():
        path = base / name
        if not path.is_file():
            path = base.parent.parent / name
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError('Source manifest mismatch: ' + name)
        sources.append(path)
    for obj in (type(backend), type(backend._env), type(backend._env.control),
                type(backend._env.robots[0])):
        sources.append(Path(inspect.getfile(obj)))
    recorder = DiagnosticEpisodeEvidence(backend, output,
                                         list(dict.fromkeys(sources)))
    try:
        recorder.install()
    except Exception:
        recorder.finish({'passed': False, 'errors': ['Recorder startup failed']})
        raise
    return recorder
