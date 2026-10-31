"""Contact diagnostics v2 for the square grasp-hold candidate.

Difference from v4: the PhysxContactReportAPI is authored before env.reset()
by square_contact_reporting.py.  This recorder only verifies that setup,
subscribes to contact events, and samples net contact forces from the early
RigidPrimView as an independent positive control.  It does not author the API
after reset (v4 did, and PhysX reported zero events).
"""
import json
from pathlib import Path
import numpy as np

FORCE_EPS = 1e-6


class BlockContactRecorderV2:
    def __init__(self, world, control, out, phase):
        from pxr import PhysxSchema
        from omni.physx import get_physx_simulation_interface
        self.world = world
        self.control = control
        self.out = Path(out)
        self.phase = phase
        self.pre = getattr(control, 'contact_report_early', None)
        self.post = getattr(control, 'contact_report_after_reset', None)
        self.meta = {
            'scope': 'Rigid contacts for robot links and attachment blocks; cloth particle contacts not certified',
            'pre_reset_setup': self.pre,
            'after_reset_verify': self.post,
            'robot_bodies': [], 'attachment_bodies': [],
            'callback_count': 0, 'event_count': 0, 'counts': {}, 'type_counts': {},
            'errors': [], 'subscription_created': False,
            'api_verified': {},
            'force_samples': 0, 'force_positive_samples': 0, 'force_max_norm': 0.0,
            'force_view_error': None, 'force_rows': 0,
            'event_positive_control': False, 'force_positive_control': False,
            'event_channel_valid': False, 'force_channel_valid': False,
            'positive_control_valid': False,
        }
        self.path = self.out / 'block_contacts.jsonl'
        self.path.touch()
        self.force_path = self.out / 'contact_force_trace.jsonl'
        self.force_path.touch()
        self.force_rows = []
        # Verify the pre-reset setup survived; never re-apply it here.
        verified = {'blocks': [], 'robot_bodies': []}
        if self.pre:
            for group in ('blocks', 'robot_bodies'):
                for record in self.pre.get(group, []):
                    path = record['path']
                    prim = world.stage.GetPrimAtPath(path)
                    api_ok = bool(prim.IsValid() and prim.HasAPI(PhysxSchema.PhysxContactReportAPI))
                    threshold = None
                    if api_ok:
                        attr = prim.GetAttribute('physxContactReport:threshold')
                        if attr.IsValid():
                            threshold = float(attr.Get())
                    verified[group].append({'path': path, 'api': api_ok,
                                            'threshold': threshold})
        self.meta['api_verified'] = verified
        self.meta['robot_bodies'] = [x['path'] for x in verified['robot_bodies']]
        self.meta['attachment_bodies'] = [x['path'] for x in verified['blocks']]
        if not verified['blocks']:
            self.meta['errors'].append('No attachment contact-report bodies')

        def classify(actors):
            robot = any(a.startswith('/World/Franka/') for a in actors)
            block = any(a.startswith('/World/Attachment/') for a in actors)
            ground = any(a.startswith('/World/defaultGroundPlane') or a.startswith('/World/Room/')
                         for a in actors)
            if robot and block: return 'robot_block'
            if robot and ground: return 'robot_ground'
            if block and ground: return 'block_ground'
            if robot: return 'robot_other'
            if block: return 'block_other'
            return 'other'

        def callback(headers, data):
            self.meta['callback_count'] += 1
            try:
                from pxr import PhysicsSchemaTools
                for h in headers:
                    actors = [str(PhysicsSchemaTools.intToSdfPath(h.actor0)),
                              str(PhysicsSchemaTools.intToSdfPath(h.actor1))]
                    if not any(a.startswith('/World/Franka/') or a.startswith('/World/Attachment/')
                               for a in actors):
                        continue
                    points = []
                    for j in range(h.contact_data_offset, h.contact_data_offset + h.num_contact_data):
                        c = data[j]
                        points.append({'position': [float(v) for v in c.position],
                                       'normal': [float(v) for v in c.normal],
                                       'impulse': [float(v) for v in c.impulse]})
                    category = classify(actors)
                    event_type = str(h.type)
                    row = {'step': int(world.current_time_step_index), 'phase': self.phase(),
                           'type': event_type, 'category': category, 'actors': actors,
                           'colliders': [str(PhysicsSchemaTools.intToSdfPath(h.collider0)),
                                         str(PhysicsSchemaTools.intToSdfPath(h.collider1))],
                           'contacts': points}
                    with self.path.open('a', encoding='utf8') as f:
                        f.write(json.dumps(row) + '\n')
                    self.meta['event_count'] += 1
                    self.meta['counts'][category] = self.meta['counts'].get(category, 0) + 1
                    self.meta['type_counts'][event_type] = self.meta['type_counts'].get(event_type, 0) + 1
            except Exception as exc:
                if len(self.meta['errors']) < 20:
                    self.meta['errors'].append(repr(exc))

        self.callback = callback
        self.subscription = get_physx_simulation_interface().subscribe_contact_report_events(callback)
        self.meta['subscription_created'] = self.subscription is not None
        if not self.meta['subscription_created']:
            raise RuntimeError('No contact report subscription')

    def sample_force(self):
        view = getattr(self.control, 'contact_force_view', None)
        if view is None:
            self.meta['force_view_error'] = 'no contact force view'
            return None
        try:
            forces = view.get_net_contact_forces()
            if forces is None:
                raise RuntimeError('get_net_contact_forces returned None')
            arr = forces.detach().cpu().numpy() if hasattr(forces, 'detach') else np.asarray(forces)
            arr = np.asarray(arr, dtype=float).reshape(-1, 3)
            if not np.isfinite(arr).all():
                raise RuntimeError('Non-finite contact forces')
            norms = np.linalg.norm(arr, axis=1)
            row = {'step': int(self.world.current_time_step_index), 'phase': self.phase(),
                   'prim_paths': list(getattr(view, 'prim_paths', [])),
                   'forces': arr.tolist(), 'norms': norms.tolist(),
                   'max_norm': float(norms.max()) if norms.size else 0.0}
            self.meta['force_samples'] += 1
            if row['max_norm'] > FORCE_EPS:
                self.meta['force_positive_samples'] += 1
            self.meta['force_max_norm'] = max(self.meta['force_max_norm'], row['max_norm'])
            self.force_rows.append(row)
            return row
        except Exception as exc:
            self.meta['force_view_error'] = repr(exc)
            return None

    def save(self):
        m = self.meta
        if self.force_rows:
            self.force_path.write_text(
                '\n'.join(json.dumps(row) for row in self.force_rows) + '\n', encoding='utf-8')
        m['force_rows'] = len(self.force_rows)
        m['event_positive_control'] = int(m['counts'].get('block_ground', 0)) > 0
        m['force_positive_control'] = int(m['force_positive_samples']) > 0
        m['event_channel_valid'] = bool(m['event_positive_control'])
        m['force_channel_valid'] = bool(m['force_positive_control'])
        # Pre-registered v4 control is the event channel; keep it strict and
        # expose the independent force channel separately.
        m['positive_control_valid'] = bool(m['event_positive_control'])
        m['independent_force_positive_control'] = bool(m['force_positive_control'])
        m['unexpected_robot_block_contacts'] = int(m['counts'].get('robot_block', 0))
        m['diagnosis'] = ('recording_failed' if m['errors'] else
                          'block_ground_events_recorded' if m['event_positive_control'] else
                          'force_only_positive_control' if m['force_positive_control'] else
                          'no_positive_control_channel_not_validated')
        (self.out / 'block_contact_report.json').write_text(
            json.dumps(m, indent=2, default=str), encoding='utf8')
        return m
