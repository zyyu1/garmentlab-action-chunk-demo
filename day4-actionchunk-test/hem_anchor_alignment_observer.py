"""Single-variable points1 alignment intervention; import after SimulationApp.

baseline never writes USD. aligned changes only points1 while attachment is OFF.
USD persistence is measured separately from the observed physics response.
"""
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from pxr import Gf, UsdGeom, Vt
from anchor_observer import AnchorObserver, serial


def rigid_local_to_world(local, position, quaternion_wxyz, scale):
    return Rotation.from_quat(np.asarray(quaternion_wxyz)[[1, 2, 3, 0]]).apply(
        np.asarray(local) * np.asarray(scale)) + np.asarray(position)


def world_to_rigid_local(world, position, quaternion_wxyz, scale):
    scale = np.asarray(scale, dtype=float)
    if scale.shape != (3,) or not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError('Expected three positive rigid scale values')
    return Rotation.from_quat(np.asarray(quaternion_wxyz)[[1, 2, 3, 0]]).inv().apply(
        np.asarray(world) - np.asarray(position)) / scale


class PairedAlignmentObserver(AnchorObserver):
    def __init__(self, backend, output, mode):
        super().__init__(backend, output)
        if mode not in ('baseline', 'aligned'):
            raise ValueError('mode must be baseline or aligned')
        self.mode = mode
        self.run_output = Path(output)
        self.metrics = {'mode': mode, 'intervention_attempted': False,
                        'usd_points1_written': False,
                        'note': 'Pipeline success is not proof of improvement or internal solver adoption.'}
        reference = Path('/root/autodl-tmp/day4-pre-reset-mesh-20261024-212943-485691')
        reference_result = json.loads((reference/'result.json').read_text())
        if reference_result.get('passed') is not True or not reference_result.get('world_reset_intercepted'):
            raise RuntimeError('Expected passed pre-reset mesh capture')
        self.reference_output = self.run_output/'reference'
        self.reference_output.mkdir()
        names = ['mesh_before_first_reset.npz', 'mesh_before_first_reset.json',
                 'mesh_before_first_reset-candidate-map.json', 'reference_after_start.json', 'result.json']
        manifest = {}
        for name in names:
            path = reference/name
            shutil.copy2(path, self.reference_output/name)
            manifest[name] = {'source': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        (self.reference_output/'manifest.json').write_text(json.dumps(manifest, indent=2))
        with np.load(reference/'mesh_before_first_reset.npz', allow_pickle=False) as f:
            self.rest = {k:f[k].copy() for k in f.files}
        meta = json.loads((reference/'mesh_before_first_reset.json').read_text())
        if meta['stage_meters_per_unit'] != 1.0 or not np.all(self.rest['face_vertex_counts'] == 3):
            raise RuntimeError('Expected metre-stage triangular mesh')
        faces = self.rest['face_vertex_indices'].reshape(-1, 3)
        self.edges = np.unique(np.sort(np.concatenate(
            [faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
        self.rest_lengths = self.edge_lengths(self.rest['points_world_usd'])
        if not np.isfinite(self.rest_lengths).all() or np.any(self.rest_lengths <= 1e-8):
            raise RuntimeError('Invalid rest edge lengths')
        self.original_points0 = None
        self.expected_points1 = None
        self.anchor_ids = None
        self.pre = None
        self.write_metrics()

    def write_metrics(self):
        (self.run_output/'alignment_metrics.json').write_text(
            json.dumps(self.metrics, indent=2, allow_nan=False), encoding='utf-8')

    def edge_lengths(self, vertices):
        return np.linalg.norm(vertices[self.edges[:, 1]]-vertices[self.edges[:, 0]], axis=1)

    def live_state(self):
        c = self.control
        prim = self.stage.GetPrimAtPath(c.block.attachment_path)
        points0 = np.asarray(prim.GetAttribute('points0').Get(), dtype=float)
        points1 = np.asarray(prim.GetAttribute('points1').Get(), dtype=float)
        if points0.ndim != 2 or points0.shape[1] != 3 or not len(points0) or points1.shape != points0.shape:
            raise RuntimeError('Expected nonempty paired Nx3 local anchors')
        pos, quat = c.block.move_block_controller.get_world_poses()
        position = np.asarray(serial(pos), dtype=float).reshape(-1, 3)[0]
        quaternion = np.asarray(serial(quat), dtype=float).reshape(-1, 4)[0]
        matrix = np.asarray(UsdGeom.XformCache().GetLocalToWorldTransform(
            self.stage.GetPrimAtPath(c.block.block_path)), dtype=float)
        scale = np.linalg.norm(matrix[:3, :3], axis=1)
        if not np.allclose(scale, [.03]*3, rtol=1e-6):
            raise RuntimeError('Unexpected block authored scale')
        vertices = self.b._garment_world_positions()
        for value in (points0, points1, position, quaternion, vertices):
            if not np.isfinite(value).all():
                raise RuntimeError('Nonfinite alignment data')
        if abs(np.linalg.norm(quaternion)-1) > 1e-4:
            raise RuntimeError('Invalid rigid quaternion')
        return {'points0': points0, 'points1': points1, 'position': position,
                'quaternion': quaternion, 'scale': scale, 'vertices': vertices,
                'step': int(self.b._step_count['n'])}

    def paired_summary(self, state):
        targets = rigid_local_to_world(state['points1'], state['position'], state['quaternion'], state['scale'])
        gaps = np.linalg.norm(state['vertices'][self.anchor_ids]-targets, axis=1)*1000
        ratios = self.edge_lengths(state['vertices']) / self.rest_lengths
        local = np.isin(self.edges, self.anchor_ids).any(axis=1)
        return {'paired_gap_mean_mm': float(gaps.mean()), 'paired_gap_max_mm': float(gaps.max()),
                'all_edge_ratio_to_initial_p95_p99_max': np.percentile(ratios, [95,99,100]).tolist(),
                'anchor_incident_edge_ratio_to_initial_min_median_p95_max':
                    np.percentile(ratios[local], [0,50,95,100]).tolist()}

    def align_once(self):
        c = self.control
        if c.attachment_enabled() or c.holding or self.b._holding:
            raise RuntimeError('Alignment must occur before attachment activation')
        self.capture('aligned_original')
        before = self.live_state()
        # Exact rest-geometry identity, including a positive second-neighbor margin.
        sq = ((before['points0'][:, None, :] - self.rest['points_local'][None, :, :])**2).sum(axis=2)
        ids = sq.argmin(axis=1)
        if len(np.unique(ids)) != len(before['points0']) or not np.array_equal(self.rest['points_local'][ids], before['points0']):
            raise RuntimeError('Current points0 does not match unique exact rest vertices')
        if not np.all((sq == 0).sum(axis=1) == 1):
            raise RuntimeError('Ambiguous rest vertex mapping')
        self.anchor_ids = ids
        self.original_points0 = before['points0'].copy()
        self.metrics.update(anchor_vertex_indices=ids.tolist(), original=self.paired_summary(before))
        desired = world_to_rigid_local(before['vertices'][ids], before['position'], before['quaternion'], before['scale'])
        self.metrics['intervention_attempted'] = self.mode == 'aligned'
        self.write_metrics()
        if self.mode == 'aligned':
            attr = self.stage.GetPrimAtPath(c.block.attachment_path).GetAttribute('points1')
            value = Vt.Vec3fArray([Gf.Vec3f(*map(float, row)) for row in desired])
            if not attr.Set(value):
                raise RuntimeError('USD rejected points1 update')
            self.metrics['usd_points1_written'] = True
        after = self.live_state()
        if after['step'] != before['step'] or not np.array_equal(after['vertices'], before['vertices']):
            raise RuntimeError('Physics advanced or mesh changed during the attribute operation')
        if not np.array_equal(after['position'], before['position']) or not np.array_equal(after['quaternion'], before['quaternion']):
            raise RuntimeError('Rigid pose changed during the attribute operation')
        if not np.array_equal(after['points0'], self.original_points0):
            raise RuntimeError('points0 changed during the points1 operation')
        if c.attachment_enabled():
            raise RuntimeError('Attachment became enabled during alignment')
        expected = np.asarray(desired, dtype=np.float32).astype(float) if self.mode == 'aligned' else before['points1']
        if not np.array_equal(after['points1'], expected):
            raise RuntimeError('points1 readback does not match requested values')
        self.expected_points1 = after['points1'].copy()
        self.metrics['usd_readback_ok'] = True
        self.metrics['after_operation'] = self.paired_summary(after)
        if self.mode == 'aligned' and self.metrics['after_operation']['paired_gap_max_mm'] > .001:
            raise RuntimeError('Aligned target reconstruction error exceeds 0.001 mm')
        np.savez(self.run_output/'alignment_operation.npz', anchor_indices=ids,
                 points0=before['points0'], points1_original=before['points1'],
                 points1_requested=desired, points1_readback=after['points1'],
                 vertices_before=before['vertices'], vertices_after=after['vertices'],
                 block_position=before['position'], block_quaternion=before['quaternion'], block_scale=before['scale'])
        self.write_metrics()
        print('ANCHOR_ALIGNMENT_OPERATION', self.mode, 'ORIGINAL_MEAN_GAP_MM',
              self.metrics['original']['paired_gap_mean_mm'], 'READBACK_MEAN_GAP_MM',
              self.metrics['after_operation']['paired_gap_mean_mm'], flush=True)

    def verify_arrays(self, state, label):
        checks = {'points0_unchanged': np.array_equal(state['points0'], self.original_points0),
                  'points1_preserved': np.array_equal(state['points1'], self.expected_points1)}
        self.metrics[label] = checks
        self.write_metrics()
        if not all(checks.values()):
            raise RuntimeError('Anchor arrays changed at ' + label + ': ' + repr(checks))

    def capture(self, label):
        super().capture(label)
        if getattr(self, 'anchor_ids', None) is not None:
            state = self.live_state()
            self.metrics.setdefault('stages', {})[label] = self.paired_summary(state)
            self.verify_arrays(state, 'arrays_at_' + label)

    def install(self):
        c = self.control
        original_drive, original_tick = c._drive, c._tick
        def drive(target, ori, follow=False, limit=1000):
            value = original_drive(target, ori, follow=follow, limit=limit)
            if follow and not c.holding and not c.attachment_enabled() and not self.aligned_captured:
                self.align_once()
                self.capture('aligned_disabled')
                self.aligned_captured = True
            return value
        def tick(target, ori, follow=False):
            first = c.attachment_enabled() and not self.first_enabled_step_captured
            if first:
                if self.expected_points1 is None:
                    raise RuntimeError('Enabled before alignment/control operation')
                self.capture('enabled_before_first_step')
                self.pre = self.live_state()
            value = original_tick(target, ori, follow=follow)
            if first:
                # Save raw data before checking persistence, so failures remain inspectable.
                super(PairedAlignmentObserver, self).capture('enabled_after_first_step')
                post = self.live_state()
                delta = np.linalg.norm(post['vertices']-self.pre['vertices'], axis=1)*1000
                self.metrics['activation'] = {'step_before': self.pre['step'], 'step_after': post['step'],
                    'max_vertex_displacement_mm': float(delta.max()),
                    'tracked_mean_displacement_mm': float(delta[c.tracked].mean()),
                    'count_over_5_mm': int((delta > 5).sum()),
                    'block_motion_mm': float(np.linalg.norm(post['position']-self.pre['position'])*1000),
                    **self.paired_summary(post)}
                self.write_metrics()
                print('ANCHOR_ALIGNMENT_FIRST_STEP', self.mode, json.dumps(self.metrics['activation']), flush=True)
                if post['step'] != self.pre['step'] + 1:
                    raise RuntimeError('Activation capture did not span exactly one physics step')
                self.verify_arrays(post, 'arrays_after_first_step')
                self.first_enabled_step_captured = True
            return value
        c._drive, c._tick = drive, tick

    def finish(self):
        base = super().finish()
        self.metrics['grasp_lift_release_checks_reached_end'] = True
        self.write_metrics()
        base['alignment_metrics'] = self.metrics
        return base
