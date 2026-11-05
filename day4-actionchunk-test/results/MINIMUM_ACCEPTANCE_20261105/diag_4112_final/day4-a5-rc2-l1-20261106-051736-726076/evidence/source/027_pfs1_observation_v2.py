"""Passive observation for a5-rc2-pfs1-observation-v2.

This module changes observation semantics only; it adds no world.step, no
control call and no cloth write.

Velocity policy:
  * The raw ClothPrimView.get_velocities() readback is retained separately and
    marked unvalidated.  It is never used as a physical speed.
  * Physical per-step velocities are backward finite differences of world
    vertices, with dt from successive unique world.current_time values.
  * Single-frame stage snapshots do not have a physical finite-difference
    velocity; they retain the raw readback only with an explicit invalid flag.

Material policy:
  * Read the actual particle material object, particle system binding, cloth
    particle attributes and ground collider bindings at construction, after
    reset, after recovery and before release.
  * The readback is a scene/USD readback, not a solver-effective proof; the
    solver-effective boundary is recorded explicitly.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

STAGE_DIR = 'pfs1_stages'
MATERIAL_FILE = 'material_readbacks.json'
CONTACT_FILE = 'contact_capability.json'

FD_METHOD = 'backward_difference_world_vertices'
FD_TIME_SOURCE = 'world.current_time at each passive post-step snapshot'
FD_INTERVAL = 'dt = sim_time_s[k] - sim_time_s[previous distinct frame]'
RAW_VELOCITY_API = 'ClothPrimView.get_velocities(clone=True)'
RAW_VELOCITY_STATUS = 'unvalidated; not used as physical velocity'
EXPECTED_FRICTION = 0.3
EXPECTED_PARTICLE_FRICTION_SCALE = 1.0


def _np(value):
    if hasattr(value, 'detach'):
        value = value.cpu().numpy()
    return np.asarray(value, dtype=float)


def _jsonable(value):
    """Make USD values JSON-safe; keep non-finite markers readable."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if hasattr(value, 'tolist'):
        return _jsonable(value.tolist())
    if isinstance(value, (tuple, list)):
        return [_jsonable(x) for x in value]
    try:
        return [_jsonable(float(x)) for x in value]
    except Exception:
        return repr(value)


def _call(obj, name):
    try:
        return {'ok': True, 'value': _jsonable(getattr(obj, name)())}
    except Exception as exc:
        return {'ok': False, 'error': repr(exc)}


def _attr_rows(prim, needles=None):
    rows = {}
    try:
        for attr in prim.GetAttributes():
            name = attr.GetName()
            if needles and not any(n.lower() in name.lower() for n in needles):
                continue
            try:
                rows[name] = _jsonable(attr.Get())
            except Exception as exc:
                rows[name] = {'read_error': repr(exc)}
    except Exception as exc:
        rows['__error__'] = repr(exc)
    return rows


def _material_rows(prim):
    rows = []
    try:
        from pxr import UsdShade
        api = UsdShade.MaterialBindingAPI(prim)
        for purpose in ('physics', 'all'):
            try:
                rel = api.GetDirectBindingRel(purpose) if purpose != 'all' else api.GetDirectBindingRel()
            except Exception:
                rel = None
            targets = [str(t) for t in rel.GetTargets()] if rel else []
            if targets:
                rows.append({'purpose': purpose, 'relationship': str(rel.GetName()),
                             'targets': targets})
        for rel in prim.GetRelationships():
            if 'material' in rel.GetName().lower():
                targets = [str(t) for t in rel.GetTargets()]
                if targets:
                    rows.append({'relationship': str(rel.GetName()), 'targets': targets})
    except Exception as exc:
        rows.append({'error': repr(exc)})
    return rows


def cloth_velocities_raw(backend):
    """Read the API buffer, but never label it a validated physical velocity."""
    view = backend._env.garment[0].garment_mesh._cloth_prim_view
    try:
        value = view.get_velocities(clone=True)
        value = _np(value).reshape(-1, 3)
        if value.shape != (441, 3) or not np.isfinite(value).all():
            raise ValueError('invalid raw velocity readback shape/finite')
        return value, None
    except Exception as exc:
        return None, repr(exc)


def snapshot(backend, label):
    world = backend._env.world
    control = backend._env.control
    robot = backend._env.robots[0]
    vertices = np.asarray(backend._garment_world_positions(), dtype=float)
    if vertices.shape != (441, 3) or not np.isfinite(vertices).all():
        raise ValueError('Invalid cloth positions at ' + label)
    raw_velocities, raw_error = cloth_velocities_raw(backend)
    ee, quat = robot.get_cur_ee_pos()
    ee = _np(ee).reshape(-1)
    quat = None if quat is None else _np(quat).reshape(-1)
    joints = _np(robot._robot.get_joint_positions()).reshape(-1)
    dofs = list(getattr(robot._robot, 'dof_names', []) or [])
    finger_idx = [i for i, name in enumerate(dofs) if 'finger' in str(name).lower()]
    if len(finger_idx) == 2 and len(joints) > max(finger_idx):
        aperture = float(joints[finger_idx].sum())
        aperture_note = 'sum of finger joint positions'
    elif len(joints) >= 9:
        finger_idx = [len(joints) - 2, len(joints) - 1]
        aperture = float(joints[finger_idx].sum())
        aperture_note = 'last two joint positions assumed fingers'
    else:
        aperture = None
        aperture_note = 'finger joints unavailable'
    enabled = [bool(slot.attachment_enabled()) for slot in control.slots]
    return {
        'label': label,
        'sim_time_s': float(world.current_time),
        'absolute_step': int(world.current_time_step_index),
        'backend_step': int(backend._step_count['n']),
        'vertices': vertices,
        'readback_velocities': raw_velocities,
        'readback_velocity_error': raw_error,
        'velocity_readback_validated': False,
        'velocity_policy': 'raw readback only; physical velocity is finite-difference in release records',
        'ee_m': ee,
        'ee_quaternion_wxyz': quat,
        'joint_positions': joints,
        'dof_names': dofs,
        'finger_joint_indices': finger_idx,
        'gripper_aperture_m': aperture,
        'gripper_aperture_note': aperture_note,
        'gripper_state': int(getattr(backend, '_gripper_state', -1)),
        'holding': bool(backend._holding),
        'enabled_slots': enabled,
        'logical_attached': bool(control.attachlist != [None]),
        'command_holding': bool(backend._command_holding),
        'attachment_enabled_any': bool(any(enabled)),
    }


def _write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n',
                    encoding='utf-8')


def _load_material(out, expected_scale=EXPECTED_PARTICLE_FRICTION_SCALE):
    path = Path(out) / MATERIAL_FILE
    if path.is_file():
        return json.loads(path.read_text(encoding='utf-8'))
    return {
        'schema_version': 2,
        'expected': {'friction': EXPECTED_FRICTION,
                     'particle_friction_scale': float(expected_scale)},
        'task_protocol': 'rc8 task-scoped: L1 particleFrictionScale=0.0, L2/L3=1.0',
        'solver_effective': 'unverified; values below are scene/USD readbacks',
        'velocity_policy': {'physical_source': FD_METHOD, 'time_source': FD_TIME_SOURCE,
                            'interval': FD_INTERVAL, 'raw_api': RAW_VELOCITY_API,
                            'raw_status': RAW_VELOCITY_STATUS},
        'stages': {},
    }


def _save_material(out, data):
    _write_json(Path(out) / MATERIAL_FILE, data)


def capture_material_object(mat, out, label, expected_scale=EXPECTED_PARTICLE_FRICTION_SCALE):
    """Read the material object at construction, before the episode reset.

    ``expected_scale`` is the task-scoped protocol value (L1 0.0, L2/L3 1.0);
    the construction argument and this expectation are set before reset/physics.
    """
    stage = None
    try:
        import omni.usd
        stage = omni.usd.get_context().get_stage()
    except Exception:
        pass
    prim = None
    prim_path = None
    try:
        prim_path = str(mat.prim_path)
        if stage is not None:
            prim = stage.GetPrimAtPath(prim_path)
    except Exception:
        pass
    rec = {
        'label': label,
        'readback_scope': 'material object immediately after construction',
        'prim_path': prim_path,
        'prim_valid': bool(prim and prim.IsValid()),
        'friction': _call(mat, 'get_friction'),
        'particle_friction_scale': _call(mat, 'get_particle_friction_scale'),
        'damping': _call(mat, 'get_damping') if hasattr(mat, 'get_damping') else {
            'ok': False, 'error': 'method_missing'},
        'attrs': _attr_rows(prim, ('friction', 'damping', 'material')) if prim is not None and prim.IsValid() else {},
        'bindings': _material_rows(prim) if prim is not None and prim.IsValid() else [],
        'solver_effective': 'unverified; construction-time USD readback only',
    }
    friction = rec['friction'].get('value') if rec['friction'].get('ok') else None
    scale = rec['particle_friction_scale'].get('value') if rec['particle_friction_scale'].get('ok') else None
    rec['expected_particle_friction_scale'] = float(expected_scale)
    rec['expected_ok'] = bool(
        isinstance(friction, (int, float)) and abs(float(friction) - EXPECTED_FRICTION) <= 1e-5
        and isinstance(scale, (int, float)) and abs(float(scale) - float(expected_scale)) <= 1e-6
    )
    rec['expected_reasons'] = [] if rec['expected_ok'] else [
        'friction expected %.6f, got %r' % (EXPECTED_FRICTION, friction),
        'particleFrictionScale expected %.6f, got %r' % (float(expected_scale), scale),
    ]
    data = _load_material(out, expected_scale)
    data['stages'][label] = rec
    _save_material(out, data)
    # Construction-time readback is evidence, not a stop gate: some USD
    # material views are not fully readable until the scene reset completes.
    # The after_reset/pre_release stages are the stop gates.
    return rec


def _find_support_colliders(stage):
    rows = []
    try:
        from pxr import UsdPhysics
        for prim in stage.Traverse():
            if not prim.HasAPI(UsdPhysics.CollisionAPI):
                continue
            path = str(prim.GetPath())
            if not any(k in path.lower() for k in ('ground', 'floor', 'table')):
                continue
            try:
                enabled = UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()
            except Exception as exc:
                enabled = {'read_error': repr(exc)}
            rows.append({
                'path': path,
                'type': str(prim.GetTypeName()),
                'collision_enabled': enabled,
                'attrs': _attr_rows(prim, ('collision', 'contact', 'offset', 'friction', 'filter', 'particle')),
                'bindings': _material_rows(prim),
            })
    except Exception as exc:
        rows.append({'error': repr(exc)})
    return rows


def record_material_stage(backend, out, label, expected_scale=EXPECTED_PARTICLE_FRICTION_SCALE):
    """Read the live particle material/system/binding after a state change."""
    world = backend._env.world
    stage = world.stage
    garment = backend._env.garment[0]
    ps = garment.particle_system
    pm = garment.particle_material
    cloth_path = str(garment.garment_mesh_prim_path)
    cloth_prim = stage.GetPrimAtPath(cloth_path)
    pm_path = str(pm.prim_path)
    pm_prim = stage.GetPrimAtPath(pm_path)
    ps_bindings = _material_rows(ps.prim)
    cloth_bindings = _material_rows(cloth_prim) if cloth_prim and cloth_prim.IsValid() else []
    binding_targets = []
    for row in ps_bindings:
        for target in row.get('targets', []):
            if target not in binding_targets:
                binding_targets.append(target)
    friction = _call(pm, 'get_friction')
    scale = _call(pm, 'get_particle_friction_scale')
    self_collision = _call(ps, 'get_global_self_collision_enabled')
    non_particle = _call(ps, 'get_non_particle_collision_enabled')
    contact_offset = _call(ps, 'get_particle_contact_offset')
    ps_attrs = _attr_rows(ps.prim, ('particle', 'collision', 'contact', 'offset', 'friction', 'filter'))
    cloth_attrs = _attr_rows(cloth_prim, ('particle', 'collision', 'contact', 'offset', 'friction', 'filter')) \
        if cloth_prim and cloth_prim.IsValid() else {}
    # The method for non-particle collision is absent in this SDK; the raw
    # PhysX attribute is the authoritative scene readback.
    non_particle_value = non_particle.get('value') if non_particle.get('ok') else ps_attrs.get('nonParticleCollisionEnabled')
    self_value = self_collision.get('value') if self_collision.get('ok') else ps_attrs.get('globalSelfCollisionEnabled')
    friction_value = friction.get('value') if friction.get('ok') else None
    scale_value = scale.get('value') if scale.get('ok') else None
    support = _find_support_colliders(stage)
    rec = {
        'label': label,
        'readback_scope': 'live particle material/system/binding after state change',
        'particle_material': {
            'prim_path': pm_path,
            'prim_valid': bool(pm_prim and pm_prim.IsValid()),
            'friction': friction,
            'particle_friction_scale': scale,
            'damping': _call(pm, 'get_damping') if hasattr(pm, 'get_damping') else {
                'ok': False, 'error': 'method_missing'},
            'attrs': _attr_rows(pm_prim, ('friction', 'damping', 'material')) if pm_prim and pm_prim.IsValid() else {},
            'bindings_from_particle_system': ps_bindings,
            'bindings_from_material_prim': _material_rows(pm_prim) if pm_prim and pm_prim.IsValid() else [],
        },
        'particle_system': {
            'prim_path': str(ps.prim_path),
            'particle_contact_offset': contact_offset,
            'global_self_collision_enabled': self_collision,
            'non_particle_collision_enabled': non_particle,
            'attrs': ps_attrs,
            'bindings': ps_bindings,
        },
        'cloth_mesh': {
            'prim_path': cloth_path,
            'attrs': cloth_attrs,
            'bindings': cloth_bindings,
        },
        'binding_targets': binding_targets,
        'support_colliders': support,
        'self_collision_value': self_value,
        'non_particle_collision_value': non_particle_value,
        'filter_readback': 'raw attrs above; filter/group attributes are not exposed on all colliders' if not any(
            'filter' in str(k).lower() for k in list(ps_attrs) + list(cloth_attrs)) else 'filter attrs present in raw readback',
        'particle_group': cloth_attrs.get('physxParticle:particleGroup'),
        'solver_effective': 'unverified; scene/USD readback only',
    }
    reasons = []
    if not (isinstance(friction_value, (int, float)) and abs(float(friction_value) - EXPECTED_FRICTION) <= 1e-5):
        reasons.append('friction expected %.6f, got %r' % (EXPECTED_FRICTION, friction_value))
    if not (isinstance(scale_value, (int, float)) and abs(float(scale_value) - float(expected_scale)) <= 1e-6):
        reasons.append('particleFrictionScale expected %.6f, got %r' % (float(expected_scale), scale_value))
    if pm_path not in binding_targets:
        reasons.append('particle system does not bind particle material %s; targets=%r' % (pm_path, binding_targets))
    if self_value is not True:
        reasons.append('globalSelfCollisionEnabled expected true, got %r' % (self_value,))
    if non_particle_value is not True:
        reasons.append('nonParticleCollisionEnabled expected true, got %r' % (non_particle_value,))
    rec['expected_ok'] = not reasons
    rec['expected_reasons'] = reasons
    rec['expected_particle_friction_scale'] = float(expected_scale)
    data = _load_material(out, expected_scale)
    data['stages'][label] = rec
    _save_material(out, data)
    _write_contact_capability(out)
    if not rec['expected_ok'] and label in ('after_reset', 'after_initial_settle', 'after_recovery', 'pre_release'):
        raise RuntimeError('PFS1_V2_MATERIAL_STAGE_MISMATCH ' + label + ' ' + json.dumps(reasons))
    return rec


def _write_contact_capability(out):
    path = Path(out) / CONTACT_FILE
    if path.is_file():
        return
    payload = {
        'schema_version': 2,
        'supported_scope': 'robot-rigid contacts only (existing ContactRecorder/report channel)',
        'cloth_ground_force_impulse': False,
        'reason': ('D2-B showed the existing ContactRecorder captured 0 events for a particle cloth '
                   'falling to the 10 mm particle contact offset; the current channel does not expose '
                   'cloth-particle contacts.'),
        'zero_events_interpretation': '0 events is not evidence of no contact',
        'required_for_acceptance': False,
        'physical_evidence_used': ['world vertex positions', 'z_min', 'world-position finite-difference velocities'],
        'note': ('Cloth-ground force/impulse remains a mechanism-interpretation limit, not a new '
                 'acceptance gate for this observation revision.'),
    }
    _write_json(path, payload)


def _fd_records(records):
    n = len(records)
    fd = np.zeros((n, 441, 3), dtype=float)
    valid = np.zeros(n, dtype=bool)
    interval = np.zeros(n, dtype=float)
    reasons = []
    times = [float(r['sim_time_s']) for r in records]
    for i, rec in enumerate(records):
        if i == 0:
            reasons.append('no_previous_unique_frame')
            continue
        j = i - 1
        while j >= 0 and times[i] - times[j] <= 1e-9:
            j -= 1
        if j < 0:
            reasons.append('no_previous_distinct_time')
            continue
        dt = times[i] - times[j]
        if dt <= 0:
            reasons.append('nonpositive_dt')
            continue
        if bool(rec['attachment_enabled_any']) != bool(records[j]['attachment_enabled_any']):
            reasons.append('crosses_attachment_boundary')
            continue
        d = np.asarray(rec['vertices'], float) - np.asarray(records[j]['vertices'], float)
        if not np.isfinite(d).all():
            reasons.append('nonfinite_vertices')
            continue
        fd[i] = d / dt
        valid[i] = True
        interval[i] = dt
        reasons.append(None)
    return fd, valid, interval, reasons


def save_stage(out, label, rec):
    out = Path(out)
    stage_dir = out / STAGE_DIR
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_dir / (label + '.npz')
    raw = rec['readback_velocities']
    np.savez_compressed(
        path,
        label=np.asarray(label),
        sim_time_s=np.asarray(rec['sim_time_s']),
        absolute_step=np.asarray(rec['absolute_step']),
        backend_step=np.asarray(rec['backend_step']),
        vertices=rec['vertices'],
        readback_velocities=(raw if raw is not None else np.empty((0, 3), dtype=float)),
        readback_velocity_present=np.asarray(raw is not None),
        readback_velocity_validated=np.asarray(False),
        readback_velocity_error=np.asarray(rec['readback_velocity_error'] or ''),
        fd_velocities=np.empty((0, 441, 3), dtype=float),
        fd_velocity_valid=np.asarray(False),
        fd_method=np.asarray(FD_METHOD),
        ee_m=rec['ee_m'],
        ee_quaternion_wxyz=(rec['ee_quaternion_wxyz'] if rec['ee_quaternion_wxyz'] is not None
                            else np.empty((0,), dtype=float)),
        joint_positions=rec['joint_positions'],
        gripper_aperture_m=np.asarray(rec['gripper_aperture_m'] if rec['gripper_aperture_m'] is not None else np.nan),
        gripper_state=np.asarray(rec['gripper_state']),
        holding=np.asarray(rec['holding']),
        enabled_slots=np.asarray(rec['enabled_slots'], bool),
        logical_attached=np.asarray(rec['logical_attached']),
        command_holding=np.asarray(rec['command_holding']),
        attachment_enabled_any=np.asarray(rec['attachment_enabled_any']),
    )
    index_path = out / 'pfs1_stage_index.json'
    index = json.loads(index_path.read_text()) if index_path.is_file() else []
    index.append({
        'label': label,
        'file': str(path.relative_to(out)),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'sim_time_s': rec['sim_time_s'],
        'absolute_step': rec['absolute_step'],
        'readback_velocity_present': raw is not None,
        'readback_velocity_validated': False,
        'physical_velocity_method': 'not_computed_single_frame',
        'fd_method': FD_METHOD,
        'ee_m': rec['ee_m'].tolist(),
        'gripper_state': rec['gripper_state'],
        'gripper_aperture_m': rec['gripper_aperture_m'],
        'holding': rec['holding'],
        'enabled_slots': rec['enabled_slots'],
        'logical_attached': rec['logical_attached'],
        'command_holding': rec['command_holding'],
    })
    _write_json(index_path, index)
    return rec


def record_stage(backend, out, label):
    return save_stage(out, label, snapshot(backend, label))


def save_records(out, name, records, metadata=None):
    out = Path(out)
    if not records:
        raise ValueError('No records for ' + name)
    labels = [r['label'] for r in records]
    V = np.asarray([r['vertices'] for r in records], float)
    raw = [r['readback_velocities'] for r in records]
    raw_present = np.asarray([v is not None for v in raw], bool)
    raw_array = np.asarray([v if v is not None else np.zeros((441, 3)) for v in raw], float)
    fd, fd_valid, fd_interval, fd_reasons = _fd_records(records)
    ee = np.asarray([r['ee_m'] for r in records], float)
    quat = [r['ee_quaternion_wxyz'] for r in records]
    quat_array = np.asarray([q if q is not None else np.zeros(4) for q in quat], float)
    joints = np.asarray([r['joint_positions'] for r in records], float)
    aperture = np.asarray([np.nan if r['gripper_aperture_m'] is None else r['gripper_aperture_m']
                           for r in records], float)
    path = out / (name + '.npz')
    np.savez_compressed(
        path,
        label=np.asarray(labels),
        sim_time_s=np.asarray([r['sim_time_s'] for r in records], float),
        absolute_step=np.asarray([r['absolute_step'] for r in records], int),
        backend_step=np.asarray([r['backend_step'] for r in records], int),
        vertices=V,
        readback_velocities=raw_array,
        readback_velocity_present=raw_present,
        readback_velocity_validated=np.asarray(False),
        fd_velocities=fd,
        fd_velocity_valid=fd_valid,
        fd_interval_s=fd_interval,
        fd_method=np.asarray(FD_METHOD),
        fd_time_source=np.asarray(FD_TIME_SOURCE),
        ee_m=ee,
        ee_quaternion_wxyz=quat_array,
        joint_positions=joints,
        gripper_aperture_m=aperture,
        gripper_state=np.asarray([r['gripper_state'] for r in records], int),
        holding=np.asarray([r['holding'] for r in records], bool),
        enabled_slots=np.asarray([r['enabled_slots'] for r in records], bool),
        logical_attached=np.asarray([r['logical_attached'] for r in records], bool),
        command_holding=np.asarray([r['command_holding'] for r in records], bool),
        attachment_enabled_any=np.asarray([r['attachment_enabled_any'] for r in records], bool),
    )
    meta = {
        'file': str(path.relative_to(out)),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'count': len(records),
        'first_time_s': records[0]['sim_time_s'],
        'last_time_s': records[-1]['sim_time_s'],
        'first_step': records[0]['absolute_step'],
        'last_step': records[-1]['absolute_step'],
        'readback_velocity_present_count': int(raw_present.sum()),
        'readback_velocity_missing_count': int((~raw_present).sum()),
        'readback_velocity_validated': False,
        'readback_velocity_status': RAW_VELOCITY_STATUS,
        'fd_method': FD_METHOD,
        'fd_time_source': FD_TIME_SOURCE,
        'fd_interval': FD_INTERVAL,
        'fd_velocity_valid_count': int(fd_valid.sum()),
        'fd_velocity_invalid_count': int((~fd_valid).sum()),
        'fd_invalid_reasons': [x for x in fd_reasons if x],
        'labels': labels,
        'note': 'passive per-step reads; no extra world.step or control call',
    }
    if metadata:
        meta.update(metadata)
    _write_json(out / (name + '.json'), meta)
    return meta
