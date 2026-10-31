"""Capture composed cloth mesh/topology BEFORE first World.reset, then exit.

No backend/control source files are edited; no grasp or physics step is run.
Run in a fresh process with the previously passed overlap/probe settings.
"""
import ast
from datetime import datetime
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import traceback
import numpy as np

PROJECT = Path('/root/autodl-tmp/garmentlab-action-chunk-demo')
BASELINE = Path('/root/autodl-tmp/day4-anchor-diagnostic-20261024-210929-786774')
OUTPUT = Path('/root/autodl-tmp') / ('day4-pre-reset-mesh-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
OUTPUT.mkdir()
print('OUTPUT_DIR', OUTPUT, flush=True)
sys.path.insert(0, str(PROJECT))
import backends.garmentlab_backend as backend_module


class CaptureComplete(BaseException):
    """Expected stop at first reset entry, before the real reset executes."""


def serial(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else str(value)
    if isinstance(value, np.integer):
        return int(value)
    try:
        return [serial(x) for x in value]
    except TypeError:
        return str(value)


result = {'passed': False, 'scope': 'pre-first-reset geometry capture only; no physics/grasp validation',
          'capture_phases': {}, 'world_reset_intercepted': False,
          'blocked_step_calls': 0, 'unexpected_reset_calls': 0}
b = backend_module.GarmentLabBackend(prepared_grasp=True)
restorations = []
state = {'env': None, 'prepared_finished': False}


def replace(obj, name, replacement):
    # Restore inherited attributes by deletion rather than shadowing them.
    own = name in vars(obj)
    previous = getattr(obj, name)
    restorations.append((obj, name, previous, own))
    setattr(obj, name, replacement)


try:
    if float(os.environ.get('GARMENTLAB_ATTACHMENT_OVERLAP', '0.02')) != .005:
        raise RuntimeError('Require GARMENTLAB_ATTACHMENT_OVERLAP=0.005')
    if os.environ.get('GARMENTLAB_DISABLED_ATTACHMENT_PROBE', '0') != '0':
        raise RuntimeError('Require GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0')
    manifest = json.loads((BASELINE/'source/manifest.json').read_text())
    source_dir = OUTPUT/'source'
    source_dir.mkdir()
    sources = {}
    for name, entry in manifest.items():
        if name in ('test.py', 'anchor_observer.py'):
            continue
        path = Path(entry['source'])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry['sha256']:
            raise RuntimeError('Source differs from passed anchor baseline: ' + name)
        shutil.copy2(path, source_dir/name)
        sources[name] = {'source': str(path), 'sha256': digest}
    test_path = Path(__file__).resolve()
    shutil.copy2(test_path, source_dir/'capture_test.py')
    sources['capture_test.py'] = {'source': str(test_path), 'sha256': hashlib.sha256(test_path.read_bytes()).hexdigest()}
    reference_path = BASELINE/'anchors/after_start.json'
    reference = json.loads(reference_path.read_text())
    shutil.copy2(reference_path, OUTPUT/'reference_after_start.json')
    result['reference_anchor_file'] = {'source': str(reference_path),
                                      'sha256': hashlib.sha256(reference_path.read_bytes()).hexdigest()}
    print('BASELINE_SOURCE_HASHES_OK', len(sources)-1, flush=True)

    FoldEnv, app = backend_module._import_garmentlab()
    b._simulation_app = app
    from omni.isaac.core import World, SimulationContext
    import omni.timeline
    from pxr import Usd, UsdGeom
    import backends.prepared_grasp_control as prepared_module

    for name, obj in [('FoldEnv.py', FoldEnv)]:
        path = Path(inspect.getsourcefile(obj))
        shutil.copy2(path, source_dir/name)
        sources[name] = {'source': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (source_dir/'manifest.json').write_text(json.dumps(sources, indent=2))

    def capture(env, label):
        if omni.timeline.get_timeline_interface().is_playing():
            raise RuntimeError('Timeline already playing; cannot certify pre-reset geometry')
        prim_path = env.garment[0].garment_mesh_prim_path
        prim = env.world.stage.GetPrimAtPath(prim_path)
        mesh = UsdGeom.Mesh(prim)
        if not prim.IsValid() or not prim.IsA(UsdGeom.Mesh):
            raise RuntimeError('Expected a valid cloth Mesh prim')
        def get_required(attr, dtype):
            value = attr.Get(Usd.TimeCode.Default())
            if value is None:
                raise RuntimeError('Missing mesh attribute: ' + attr.GetName())
            return np.asarray(value, dtype=dtype)
        points = get_required(mesh.GetPointsAttr(), np.float64)
        counts = get_required(mesh.GetFaceVertexCountsAttr(), np.int64)
        indices = get_required(mesh.GetFaceVertexIndicesAttr(), np.int64)
        holes_value = mesh.GetHoleIndicesAttr().Get()
        holes = np.asarray([] if holes_value is None else holes_value, dtype=np.int64)
        if points.shape != (9945, 3) or not np.isfinite(points).all():
            raise RuntimeError('Unexpected raw mesh vertex shape or nonfinite points')
        if counts.ndim != 1 or not len(counts) or np.any(counts < 3):
            raise RuntimeError('Invalid polygon vertex counts')
        if indices.ndim != 1 or counts.sum() != len(indices) or indices.min() < 0 or indices.max() >= len(points):
            raise RuntimeError('Invalid face indices')
        if len(holes) and (holes.min() < 0 or holes.max() >= len(counts)):
            raise RuntimeError('Invalid hole face indices')
        matrix = np.asarray(UsdGeom.XformCache().GetLocalToWorldTransform(prim), dtype=float)
        world = np.c_[points, np.ones(len(points))].dot(matrix)[:, :3]
        np.savez_compressed(OUTPUT/(label+'.npz'), points_local=points,
                            points_world_usd=world, face_vertex_counts=counts,
                            face_vertex_indices=indices, hole_indices=holes,
                            local_to_world_usd=matrix)
        time_info = {}
        for name in ('current_time', 'current_time_step_index'):
            try:
                value = getattr(env.world, name)
                time_info[name] = serial(value)
                if value is not None and float(value) != 0:
                    raise RuntimeError('Nonzero simulation clock before capture: ' + name)
            except AttributeError:
                time_info[name] = 'unavailable'
        attachment_prim = env.world.stage.GetPrimAtPath('/World/AttachmentConstraints/prepared_grasp')
        attachment = None
        if attachment_prim.IsValid():
            attachment = {
                'attributes': {a.GetName(): {'type': str(a.GetTypeName()), 'value': serial(a.Get())}
                               for a in attachment_prim.GetAttributes()},
                'relationships': {rel.GetName(): [str(p) for p in rel.GetForwardedTargets()]
                                  for rel in attachment_prim.GetRelationships()},
            }
        details = {'label': label, 'mesh_path': prim_path, 'point_count': len(points),
                   'face_count': len(counts), 'face_vertex_index_count': len(indices),
                   'polygon_sizes': {str(int(k)): int((counts == k).sum()) for k in np.unique(counts)},
                   'orientation': str(mesh.GetOrientationAttr().Get()),
                   'subdivision_scheme': str(mesh.GetSubdivisionSchemeAttr().Get()),
                   'stage_meters_per_unit': float(UsdGeom.GetStageMetersPerUnit(env.world.stage)),
                   'point_time_samples': mesh.GetPointsAttr().GetTimeSamples(),
                   'timeline_playing': False, 'simulation_clock': time_info,
                   'attachment': attachment,
                   'note': 'Composed USD mesh before first reset; not a live physics mesh or proof of pristine asset.'}
        (OUTPUT/(label+'.json')).write_text(json.dumps(details, indent=2, allow_nan=False))
        result['capture_phases'][label] = {k: details[k] for k in
            ('mesh_path', 'point_count', 'face_count', 'face_vertex_index_count', 'timeline_playing', 'simulation_clock')}
        # Candidate mapping against the previous run's USD-visible points0.
        # Keep all ambiguity indicators; do not assert material/solver identity.
        p0 = np.asarray(reference['attributes']['points0']['value'], dtype=float)
        if p0.shape != (28, 3) or reference['relationships']['actor0'] != [prim_path]:
            raise RuntimeError('Unexpected reference anchor shape or actor path')
        sq = ((p0[:, None, :] - points[None, :, :]) ** 2).sum(axis=2)
        candidates = np.argpartition(sq, 1, axis=1)[:, :2]
        candidates = np.take_along_axis(candidates, np.argsort(np.take_along_axis(sq, candidates, axis=1), axis=1), axis=1)
        distances = np.sqrt(np.take_along_axis(sq, candidates, axis=1))
        nearest_world = world[candidates[:, 0]]
        anchor_world = np.c_[p0, np.ones(len(p0))].dot(matrix)[:, :3]
        mapping = {'reference': result['reference_anchor_file'],
                   'nearest_vertex_indices': candidates[:, 0].tolist(),
                   'second_nearest_vertex_indices': candidates[:, 1].tolist(),
                   'nearest_distance_local_units': distances[:, 0].tolist(),
                   'nearest_world_distance_stage_units': np.linalg.norm(anchor_world-nearest_world, axis=1).tolist(),
                   'nearest_to_second_distance_margin_local_units': (distances[:, 1]-distances[:, 0]).tolist(),
                   'unique_nearest_count': int(len(np.unique(candidates[:, 0]))),
                   'max_nearest_distance_local_units': float(distances[:, 0].max()),
                   'min_neighbor_margin_local_units': float((distances[:, 1]-distances[:, 0]).min()),
                   'caution': 'Candidate rest-geometry match across runs; not certified solver vertex identity.'}
        (OUTPUT/(label+'-candidate-map.json')).write_text(json.dumps(mapping, indent=2))
        print('PRE_RESET_MESH_CAPTURE', label, 'POINTS', len(points), 'FACES', len(counts),
              'MAP_UNIQUE', mapping['unique_nearest_count'],
              'MAP_MAX_LOCAL_DISTANCE', mapping['max_nearest_distance_local_units'], flush=True)

    def blocked_step(*args, **kwargs):
        result['blocked_step_calls'] += 1
        raise RuntimeError('A physics step was requested before the capture boundary; refusing to proceed')

    def intercepted_world_reset(world, *args, **kwargs):
        env = state['env']
        if env is None or not state['prepared_finished'] or env.world is not world:
            result['unexpected_reset_calls'] += 1
            raise RuntimeError('Reset requested before expected prepared-controller boundary')
        capture(env, 'mesh_before_first_reset')
        result['world_reset_intercepted'] = True
        raise CaptureComplete()

    def unexpected_context_reset(*args, **kwargs):
        result['unexpected_reset_calls'] += 1
        raise RuntimeError('Unexpected context reset before the expected World.reset boundary')

    original_init = prepared_module.PreparedGraspControl.__init__
    def observed_init(control, env, *args, **kwargs):
        if state['env'] is not None:
            raise RuntimeError('Unexpected second prepared-controller construction')
        state['env'] = env
        capture(env, 'mesh_before_prepared')
        original_init(control, env, *args, **kwargs)
        capture(env, 'mesh_after_prepared')
        state['prepared_finished'] = True

    replace(World, 'step', blocked_step)
    replace(SimulationContext, 'step', blocked_step)
    replace(SimulationContext, 'reset', unexpected_context_reset)
    replace(World, 'reset', intercepted_world_reset)
    # Defensive guards for constructors that unexpectedly use asynchronous APIs.
    async def blocked_async(*args, **kwargs):
        raise RuntimeError('Unexpected asynchronous simulation call during pre-reset capture')
    for cls in (World, SimulationContext):
        for name in ('reset_async', 'step_async'):
            if hasattr(cls, name):
                replace(cls, name, blocked_async)
    replace(prepared_module.PreparedGraspControl, '__init__', observed_init)
    try:
        b.start()
    except CaptureComplete:
        if result['blocked_step_calls'] or result['unexpected_reset_calls']:
            raise RuntimeError('Pre-reset guards observed an unexpected call')
        for name in ('mesh_before_prepared', 'mesh_after_prepared'):
            with np.load(OUTPUT/(name+'.npz'), allow_pickle=False) as a, np.load(OUTPUT/'mesh_before_first_reset.npz', allow_pickle=False) as z:
                for key in ('points_local', 'face_vertex_counts', 'face_vertex_indices', 'hole_indices', 'local_to_world_usd'):
                    if not np.array_equal(a[key], z[key]):
                        raise RuntimeError('Mesh changed during pre-reset construction: ' + key)
        result['pre_reset_meshes_equal'] = True
        result['passed'] = True
        print('PRE_RESET_MESH_CAPTURE_OK', OUTPUT, flush=True)
    else:
        raise RuntimeError('Expected first reset interception did not occur')
except BaseException as exc:
    result['error'] = repr(exc)
    traceback.print_exc()
    raise
finally:
    for obj, name, previous, own in reversed(restorations):
        if own:
            setattr(obj, name, previous)
        else:
            delattr(obj, name)
    (OUTPUT/'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('RESULT_FILE', OUTPUT/'result.json', flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    b.stop()
