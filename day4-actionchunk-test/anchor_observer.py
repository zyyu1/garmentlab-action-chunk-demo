"""Read-only USD/physics snapshots around the first attachment activation.

Import after SimulationApp starts. USD transforms are recorded as USD values;
with GPU suppressReadback they must not be assumed to be current physics poses.
Missing auto-generated points do not imply absence of internal PhysX anchors.
"""
import json
from pathlib import Path
import numpy as np
from pxr import UsdGeom


def serial(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else str(value)
    if isinstance(value, np.integer):
        return int(value)
    if hasattr(value, 'detach'):
        value = value.detach().cpu().numpy()
    try:
        return [serial(x) for x in value]
    except TypeError:
        return str(value)


class AnchorObserver:
    def __init__(self, backend, output):
        self.b = backend
        self.control = backend._env.control
        self.stage = backend._env.world.stage
        self.output = Path(output) / 'anchors'
        self.output.mkdir()
        self.records = {}
        self.first_enabled_step_captured = False
        self.aligned_captured = False

    def capture(self, label):
        c = self.control
        prim = self.stage.GetPrimAtPath(c.block.attachment_path)
        if not prim.IsValid():
            raise RuntimeError('Attachment prim is unavailable')
        attrs, errors = {}, []
        for attr in prim.GetAttributes():
            name = attr.GetName()
            item = {'type': str(attr.GetTypeName()),
                    'authored': bool(attr.HasAuthoredValueOpinion())}
            try:
                item['value'] = serial(attr.Get())
            except Exception as exc:
                item['read_error'] = repr(exc)
                errors.append({'attribute': name, 'error': repr(exc)})
            attrs[name] = item
        rels = {rel.GetName(): [str(p) for p in rel.GetForwardedTargets()]
                for rel in prim.GetRelationships()}
        paths = {c.block.block_path, c.garment.garment_mesh_prim_path}
        for targets in rels.values():
            paths.update(targets)
        cache = UsdGeom.XformCache()
        usd_actors = {}
        for path in sorted(paths):
            actor = self.stage.GetPrimAtPath(path)
            if actor.IsValid():
                usd_actors[path] = {
                    'type': str(actor.GetTypeName()),
                    'usd_local_to_world': serial(cache.GetLocalToWorldTransform(actor)),
                    'transform_warning': 'USD value may lag GPU physics; not a live-pose guarantee',
                }
        view = c.block.move_block_controller
        pos, quat = view.get_world_poses()
        block_pos = np.asarray(serial(pos), dtype=float).reshape(-1, 3)
        block_quat = np.asarray(serial(quat), dtype=float).reshape(-1, 4)
        vertices = self.b._garment_world_positions()
        ee, ee_quat = c.robot.get_cur_ee_pos()
        for value in (block_pos, block_quat, vertices, ee, ee_quat):
            if not np.isfinite(np.asarray(value)).all():
                raise RuntimeError('Non-finite live diagnostic data')
        np.savez(self.output / (label + '.npz'), vertices=vertices,
                 tracked_indices=c.tracked, block_position=block_pos[0],
                 block_quaternion=block_quat[0], ee_position=ee,
                 ee_quaternion=ee_quat, attachment_target=c.block_target())
        counts = {}
        for name, item in attrs.items():
            if name.split(':')[-1].lower() in ('points0', 'points1'):
                value = item.get('value')
                counts[name] = len(value) if isinstance(value, list) else None
        record = {'label': label, 'physics_step': int(self.b._step_count['n']),
                  'attachment_path': c.block.attachment_path,
                  'enabled': bool(c.enabled.Get()), 'control_holding': bool(c.holding),
                  'backend_holding': bool(self.b._holding),
                  'state_note': 'Transient during CLOSE: control and backend holding can differ before execute returns.',
                  'applied_schemas': list(prim.GetAppliedSchemas()),
                  'attributes': attrs, 'relationships': rels, 'usd_actors': usd_actors,
                  'visible_point_array_counts': counts, 'read_errors': errors,
                  'limits': 'USD-visible arrays may omit internal generated anchors; empty arrays are inconclusive.'}
        (self.output / (label + '.json')).write_text(
            json.dumps(record, indent=2, allow_nan=False), encoding='utf-8')
        self.records[label] = {'visible_point_array_counts': counts, 'read_errors': errors}
        (self.output / 'index.json').write_text(
            json.dumps(self.records, indent=2), encoding='utf-8')
        print('ANCHOR_CAPTURE', label, 'POINT_ARRAY_COUNTS', counts,
              'ATTRIBUTE_READ_ERRORS', len(errors), flush=True)

    def install(self):
        c = self.control
        original_drive = c._drive
        original_tick = c._tick

        def drive(target, ori, follow=False, limit=1000):
            value = original_drive(target, ori, follow=follow, limit=limit)
            # grasp() aligns the block with follow=True before enabling it.
            if follow and not c.holding and not bool(c.enabled.Get()) and not self.aligned_captured:
                self.capture('aligned_disabled')
                self.aligned_captured = True
            return value

        def tick(target, ori, follow=False):
            first = bool(c.enabled.Get()) and not self.first_enabled_step_captured
            if first:
                self.capture('enabled_before_first_step')
            value = original_tick(target, ori, follow=follow)
            if first:
                self.capture('enabled_after_first_step')
                self.first_enabled_step_captured = True
            return value

        c._drive = drive
        c._tick = tick

    def finish(self):
        if not self.aligned_captured or not self.first_enabled_step_captured:
            raise RuntimeError('Required activation diagnostic phases were not captured')
        print('ANCHOR_DIAGNOSTIC_CAPTURE_OK', self.output, flush=True)
        return {'captured': True, 'path': str(self.output), 'phases': self.records,
                'anchors_exposed': 'Inspect raw point arrays; capture success does not establish anchor visibility.'}
