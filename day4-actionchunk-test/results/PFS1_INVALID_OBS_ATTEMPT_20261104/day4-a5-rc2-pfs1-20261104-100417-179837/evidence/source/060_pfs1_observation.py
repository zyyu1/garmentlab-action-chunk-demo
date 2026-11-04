"""Passive observation for a5-rc2-pfs1.

Adds no world.step, no control call and no cloth write.  Records the actual
cloth world positions and particle velocities, EE, gripper and attachment
state at the six registered stages.  Velocity readback is recorded separately
from a finite-difference fallback; if the view cannot provide velocities, the
stage is marked missing rather than fabricated.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

STAGE_DIR = 'pfs1_stages'


def _np(value):
    if hasattr(value, 'detach'):
        value = value.detach().cpu().numpy()
    return np.asarray(value, dtype=float)


def cloth_velocities(backend):
    view = backend._env.garment[0].garment_mesh._cloth_prim_view
    try:
        value = view.get_world_velocities(clone=True)
        value = _np(value).reshape(-1, 3)
        if value.shape != (441, 3) or not np.isfinite(value).all():
            raise ValueError('invalid cloth velocity readback')
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
    velocities, velocity_error = cloth_velocities(backend)
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
        'velocities': velocities,
        'velocity_error': velocity_error,
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


def save_stage(out, label, rec):
    out = Path(out)
    stage_dir = out / STAGE_DIR
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_dir / (label + '.npz')
    np.savez_compressed(
        path,
        label=np.asarray(label),
        sim_time_s=np.asarray(rec['sim_time_s']),
        absolute_step=np.asarray(rec['absolute_step']),
        backend_step=np.asarray(rec['backend_step']),
        vertices=rec['vertices'],
        velocities=(rec['velocities'] if rec['velocities'] is not None
                    else np.empty((0, 3), dtype=float)),
        velocity_present=np.asarray(rec['velocities'] is not None),
        velocity_error=np.asarray(rec['velocity_error'] or ''),
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
        'velocity_present': rec['velocities'] is not None,
        'velocity_error': rec['velocity_error'],
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
    """Read one passive stage snapshot and save it under pfs1_stages/."""
    return save_stage(out, label, snapshot(backend, label))


def save_records(out, name, records, metadata=None):
    """Save per-step records; write a JSON sidecar with the sampling details."""
    out = Path(out)
    if not records:
        raise ValueError('No records for ' + name)
    stages = [r['label'] for r in records]
    vertices = np.asarray([r['vertices'] for r in records], dtype=float)
    velocities = [r['velocities'] for r in records]
    velocity_present = np.asarray([v is not None for v in velocities], bool)
    vel_array = np.asarray([v if v is not None else np.zeros((441, 3)) for v in velocities], dtype=float)
    ee = np.asarray([r['ee_m'] for r in records], dtype=float)
    quat = [r['ee_quaternion_wxyz'] for r in records]
    quat_array = np.asarray([q if q is not None else np.zeros(4) for q in quat], dtype=float)
    joints = np.asarray([r['joint_positions'] for r in records], dtype=float)
    aperture = np.asarray([np.nan if r['gripper_aperture_m'] is None else r['gripper_aperture_m']
                           for r in records], dtype=float)
    path = out / (name + '.npz')
    np.savez_compressed(
        path,
        label=np.asarray(stages),
        sim_time_s=np.asarray([r['sim_time_s'] for r in records], float),
        absolute_step=np.asarray([r['absolute_step'] for r in records], int),
        backend_step=np.asarray([r['backend_step'] for r in records], int),
        vertices=vertices,
        velocities=vel_array,
        velocity_present=velocity_present,
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
        'velocity_present_count': int(velocity_present.sum()),
        'velocity_missing_count': int((~velocity_present).sum()),
        'velocity_errors': [r['velocity_error'] for r in records if r['velocity_error']],
        'labels': stages,
        'note': 'passive per-step reads; no extra world.step or control call',
    }
    if metadata:
        meta.update(metadata)
    _write_json(out / (name + '.json'), meta)
    return meta
