"""Process-local constructor intervention and readback; never edits SDK/repository files."""
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import shutil
import numpy as np

AUDIT = Path('/root/autodl-tmp/day4-physics-config-20261025-053727-962061')
MASS_READBACK_RTOL = 1e-3  # 0.1% numerical agreement, not a physics-quality threshold.


def mass_readback_stats(masses, expected):
    masses = np.asarray(masses)
    valid_shape = masses.shape == (1, 9945)
    finite = bool(masses.size and np.isfinite(masses).all())
    positive = finite and bool((masses > 0).all())
    lo = float(masses.min()) if finite else None
    hi = float(masses.max()) if finite else None
    error = float(np.max(np.abs(masses.astype(float)/expected-1))) if finite else None
    checks = {'shape':valid_shape, 'finite':finite, 'positive':positive,
              'uniform':positive and bool(np.allclose(masses, masses.flat[0], rtol=1e-6, atol=0)),
              'requested_mass_agreement':finite and error <= MASS_READBACK_RTOL}
    return {'shape':list(masses.shape), 'min_kg':lo, 'max_kg':hi,
            'total_kg':float(masses.astype(float).sum()) if finite else None,
            'max_relative_error':error, 'relative_tolerance':MASS_READBACK_RTOL, 'checks':checks}


def start_with_iterations(backend, output, iterations):
    if iterations not in (16, 32):
        raise ValueError("Expected 16 or 32 iterations")
    particle_mass = 0.0001
    output = Path(output)
    dest = output / 'mass_source'
    dest.mkdir()
    manifest = json.loads((AUDIT / 'source/manifest.json').read_text())
    for name, item in manifest.items():
        if name == 'audit_test.py':
            continue
        path = Path(item['source'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise RuntimeError('Source changed since parameter audit: ' + name)
        shutil.copy2(path, dest / name)
    (dest / 'manifest.json').write_text(json.dumps({k:v for k,v in manifest.items() if k!='audit_test.py'}, indent=2))
    if hashlib.sha256(Path(backend.garment_usd).read_bytes()).hexdigest() != json.loads((AUDIT/'result.json').read_text())['garment_usd_sha256']:
        raise RuntimeError('Garment asset changed')
    from backends.garmentlab_backend import _import_garmentlab
    _import_garmentlab()  # Starts SimulationApp, but does not construct/reset FoldEnv.
    module = importlib.import_module('Env.Garment.Garment')
    original = module.ClothPrim
    signature = inspect.signature(original)
    calls = []

    def make_cloth(*args, **kwargs):
        bound = signature.bind_partial(*args, **kwargs)
        if 'particle_mass' in bound.arguments:
            raise RuntimeError('Garment unexpectedly supplies particle_mass already')
        kwargs['particle_mass'] = particle_mass
        cloth = original(*args, **kwargs)
        prim = cloth._prim
        names = ['points', 'faceVertexCounts', 'faceVertexIndices',
                 'physxParticle:springIndices', 'physxParticle:springRestLengths',
                 'physxParticle:springStiffnesses', 'physxParticle:springDampings']
        arrays = {}
        for name in names:
            value = prim.GetAttribute(name).Get()
            if value is not None:
                arrays[name.replace(':', '__')] = np.asarray(value)
        if arrays['points'].shape != (9945, 3):
            raise RuntimeError('Unexpected original mesh')
        np.savez_compressed(output / 'cloth_constructed.npz', **arrays)
        mass = float(prim.GetAttribute('physics:mass').Get())
        if not np.isclose(mass, 9945 * particle_mass, rtol=1e-5):
            raise RuntimeError('Constructed USD mass differs from request')
        calls.append({'particle_mass_requested_kg':particle_mass, 'usd_mass_before_reset_kg':mass,
                      'vertex_count':9945, 'supplied_argument':'particle_mass'})
        (output / 'mass_constructor.json').write_text(json.dumps(calls, indent=2))
        return cloth

    config_class = importlib.import_module('Env.Config.GarmentConfig').GarmentConfig
    original_config_init = config_class.__init__
    config_calls = []
    def configured_init(self, *args, **kwargs):
        original_config_init(self, *args, **kwargs)
        if self.solver_position_iteration_count != 16:
            raise RuntimeError('Unexpected default solver iteration count')
        self.solver_position_iteration_count = iterations
        config_calls.append(iterations)
    config_class.__init__ = configured_init
    module.ClothPrim = make_cloth
    try:
        backend.start()
    finally:
        module.ClothPrim = original
        config_class.__init__ = original_config_init
    if len(calls) != 1 or config_calls != [iterations]:
        raise RuntimeError('Expected exactly one cloth constructor call')
    env = backend._env
    garment = env.garment[0]
    stage = env.world.stage
    from pxr import UsdPhysics, UsdGeom
    units = float(UsdPhysics.GetStageKilogramsPerUnit(stage))
    if units != 1.0 or float(UsdGeom.GetStageMetersPerUnit(stage)) != 1.0:
        raise RuntimeError('Expected metre/kilogram stage')
    system = stage.GetPrimAtPath(garment.particle_system_path)
    params = {k:system.GetAttribute(k).Get() for k in ('solverPositionIterationCount',
              'particleContactOffset','enableCCD','globalSelfCollisionEnabled')}
    if params['solverPositionIterationCount'] != iterations or not np.isclose(params['particleContactOffset'],0.01):
        raise RuntimeError('Unexpected particle system configuration')
    data = {'constructor': calls[0], 'particle_system':params, 'stage_kilograms_per_unit':units,
            'physics_dt':float(env.world.get_physics_dt()), 'requested_iterations':iterations, 'iteration_readbacks':{}, 'reads':{}}
    if not np.isclose(data['physics_dt'],1/60):
        raise RuntimeError('Unexpected physics time step')

    def capture(label):
        view = garment.garment_mesh._cloth_prim_view
        import omni.timeline
        if view._physics_view is None or not omni.timeline.get_timeline_interface().is_playing():
            raise RuntimeError('Mass read requires live physics view')
        current_iterations = int(system.GetAttribute('solverPositionIterationCount').Get())
        data['iteration_readbacks'][label] = current_iterations
        if current_iterations != iterations:
            raise RuntimeError('Particle system iteration attribute changed')
        mesh = stage.GetPrimAtPath(garment.garment_mesh_prim_path)
        spring_arrays = {}
        for name in ('springIndices','springRestLengths','springStiffnesses','springDampings'):
            value = mesh.GetAttribute('physxParticle:' + name).Get()
            if value is None:
                raise RuntimeError('Missing cooked spring array: ' + name)
            array = np.asarray(value)
            if not array.size or not np.isfinite(array).all():
                raise RuntimeError('Invalid cooked spring array: ' + name)
            spring_arrays[name] = array
        count = len(spring_arrays['springIndices'])
        if spring_arrays['springIndices'].shape != (count,2) or any(spring_arrays[k].shape != (count,) for k in ('springRestLengths','springStiffnesses','springDampings')):
            raise RuntimeError('Inconsistent spring array shapes')
        np.savez_compressed(output / ('cooked_springs_' + label + '.npz'), **spring_arrays)
        raw = view.get_particle_masses(clone=True)
        masses = raw.detach().cpu().numpy() if hasattr(raw,'detach') else np.asarray(raw)
        np.save(output / ('particle_masses_' + label + '.npy'), masses)
        data['reads'][label] = mass_readback_stats(masses, particle_mass)
        (output / 'mass_audit.json').write_text(json.dumps(data,indent=2))
        if not all(data['reads'][label]['checks'].values()):
            raise RuntimeError('Physics particle mass check failed: ' + repr(data['reads'][label]))
        return data

    capture('after_start')
    return capture
