"""Capture composed physics attributes after normal startup; no grasp or parameter edits."""
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import traceback
from datetime import datetime
import numpy as np

ROOT = Path('/root/autodl-tmp')
sys.path.insert(0, str(ROOT / 'garmentlab-action-chunk-demo'))
from backends.garmentlab_backend import GarmentLabBackend

output = ROOT / ('day4-physics-config-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
output.mkdir()
source = output / 'source'
source.mkdir()
result = {'passed': False, 'audit_version': 2, 'scope': 'normal backend startup followed by read-only parameter capture; no grasp'}
arrays = {}


def serial(value):
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(value):
            return {'nonfinite_float': 'NaN' if np.isnan(value) else ('+Infinity' if value > 0 else '-Infinity')}
        return float(value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    if hasattr(value, 'detach'):
        value = value.detach().cpu().numpy()
    try:
        a = np.asarray(value)
        if a.dtype.kind in 'biuf' and a.size:
            if a.size <= 32:
                return serial(a.tolist())
            key = 'array_%05d' % len(arrays)
            arrays[key] = a.copy()
            with np.errstate(invalid='ignore', over='ignore'):
                stats = {'min': serial(float(a.min())), 'max': serial(float(a.max())),
                         'mean': serial(float(a.mean()))}
            return {'array_key': key, 'shape': list(a.shape), 'dtype': str(a.dtype),
                    **stats, 'nonfinite_count': int((~np.isfinite(a)).sum())}
    except (TypeError, ValueError):
        pass
    return str(value)


def backup(path, name):
    path = Path(path)
    dest = source / name
    shutil.copy2(path, dest)
    manifest[name] = {'source': str(path), 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest()}


manifest = {}
b = GarmentLabBackend(prepared_grasp=True)
print('OUTPUT_DIR', output, flush=True)
try:
    if os.environ.get('GARMENTLAB_ATTACHMENT_OVERLAP') != '0.005' or os.environ.get('GARMENTLAB_DISABLED_ATTACHMENT_PROBE') != '0':
        raise RuntimeError('Use overlap=0.005 and disabled probe=0')
    reference = ROOT / 'day4-aligned-measured-hold-20261025-044808-480399/source/manifest.json'
    expected = json.loads(reference.read_text())
    checks = {}
    for name in ('backend.py', 'prepared_grasp_control.py', 'MyFranka.py', 'BaseEnv.py', 'Control.py'):
        item = expected[name]
        checks[name] = hashlib.sha256(Path(item['source']).read_bytes()).hexdigest() == item['sha256']
        if not checks[name]:
            raise RuntimeError('Source differs from passed run: ' + name)
        backup(item['source'], name)
    result['baseline_source_checks'] = checks
    backup(Path(__file__).resolve(), 'audit_test.py')
    # These previously missing source files define cloth construction/defaults.
    garment_root = ROOT / 'garmentlab_workspace/GarmentLab'
    for relative in ('Env/Config/GarmentConfig.py', 'Env/Config/SceneConfig.py',
                     'Env/Config/FrankaConfig.py', 'Env/Garment/Garment.py', 'Env/env/FoldEnv.py'):
        backup(garment_root / relative, relative.replace('/', '__'))
    b.start()
    env = b._env
    world = env.world
    step_before = int(b._step_count['n'])
    time_before = float(world.current_time)
    # Preserve installed SDK implementations without importing another environment.
    garment = env.garment[0]
    for name, obj in [('cloth', garment.garment_mesh),
                      ('cloth_view', garment.garment_mesh._cloth_prim_view),
                      ('particle_system', garment.particle_system),
                      ('particle_material', garment.particle_material)]:
        backup(inspect.getfile(type(obj)), 'sdk__' + name + '.py')
    prims = []
    for prim in world.stage.Traverse():
        attrs = {}
        for attr in prim.GetAttributes():
            name = attr.GetName()
            if prim.GetTypeName() != 'PhysxParticleSystem' and not name.lower().startswith(('physics:', 'physx', 'drive:')):
                continue
            attrs[name] = {'value': serial(attr.Get()), 'type': str(attr.GetTypeName()),
                           'authored': bool(attr.HasAuthoredValueOpinion())}
        relationships = {rel.GetName(): [str(p) for p in rel.GetTargets()]
                         for rel in prim.GetRelationships()
                         if prim.GetTypeName() == 'PhysxParticleSystem' or rel.GetName().lower().startswith(('physics:', 'physx', 'material:'))}
        if attrs or relationships:
            prims.append({'path': str(prim.GetPath()), 'type': prim.GetTypeName(),
                          'schemas': list(prim.GetAppliedSchemas()),
                          'attributes': attrs, 'relationships': relationships})
    if not prims:
        raise RuntimeError('No physics properties captured')
    configs = {}
    for name, obj in [('scene', getattr(env, 'scene_config', None)),
                      ('garment', env.garment[0])]:
        if obj is None:
            continue
        configs[name] = {k: serial(v) for k, v in vars(obj).items()
                         if 'config' in k.lower() or isinstance(v, (str, bool, int, float, np.ndarray))}
        for key, value in vars(obj).items():
            if 'config' in key.lower() and hasattr(value, '__dict__'):
                configs[name][key] = serial(vars(value))
    # Copy imported project modules, including controller helpers, for later review.
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.suffix == '.py' and garment_root in path.parents:
            backup(path, 'module__' + str(path.relative_to(garment_root)).replace('/', '__'))
    (output / 'physics_attributes.json').write_text(json.dumps(prims, indent=2, allow_nan=False), encoding='utf-8')
    (output / 'object_configs.json').write_text(json.dumps(configs, indent=2, allow_nan=False), encoding='utf-8')
    np.savez_compressed(output / 'physics_arrays.npz', **arrays)
    result.update(physics_dt=float(world.get_physics_dt()),
                  stage_meters_per_unit=None,
                  garment_usd=b.garment_usd,
                  garment_usd_sha256=hashlib.sha256(Path(b.garment_usd).read_bytes()).hexdigest(),
                  physics_prim_count=len(prims), array_count=len(arrays),
                  no_steps_during_capture=(step_before == int(b._step_count['n']) and time_before == float(world.current_time)),
                  attachment_disabled=not bool(env.control.enabled.Get()),
                  nonfinite_encoding='JSON uses tagged objects: nonfinite_float = +Infinity, -Infinity or NaN; NPZ arrays preserve original values.',
                  note='Composed USD properties include schema fallbacks; these are not direct internal solver reads. Startup includes normal reset.')
    from pxr import UsdGeom
    result['stage_meters_per_unit'] = float(UsdGeom.GetStageMetersPerUnit(world.stage))
    from pxr import UsdPhysics
    get_mass_units = getattr(UsdPhysics, 'GetStageKilogramsPerUnit', None)
    result['stage_kilograms_per_unit'] = float(get_mass_units(world.stage)) if get_mass_units else None
    result['stage_authored_kilograms_per_unit'] = serial(world.stage.GetMetadata('kilogramsPerUnit')) if get_mass_units else None
    particle_record = next(p for p in prims if p['path'] == garment.particle_system_path)
    if not particle_record['attributes']:
        raise RuntimeError('Particle system attributes missing')
    if not result['no_steps_during_capture'] or not result['attachment_disabled']:
        raise RuntimeError('Capture changed simulation steps or attachment was active')
    result['passed'] = True
except BaseException as exc:
    result['error'] = repr(exc)
    traceback.print_exc()
finally:
    (source / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (output / 'result.json').write_text(json.dumps(serial(result), indent=2, allow_nan=False), encoding='utf-8')
    if result['passed']:
        print('PHYSICS_CONFIG_AUDIT_OK', flush=True)
    print('RESULT_FILE', output / 'result.json', flush=True)
    print('DOWNLOAD_DIR', output, flush=True)
    b.stop()
