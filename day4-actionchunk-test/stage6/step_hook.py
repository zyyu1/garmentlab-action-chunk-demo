"""Stage 6 read-only ``world.step`` hook.

Contract (matches the Stage 6 hand-off requirement):

* ``install()`` replaces ``backend._env.world.step`` with a wrapper that calls
  the previously installed step **exactly once**, with the same positional and
  keyword arguments.
* The previous step's return value is returned unchanged.  Exceptions are
  re-raised unchanged (the hook never swallows or substitutes one).
* After the step returns -- or after it raises, best effort -- the hook reads
  only: simulation time/step indices, holding/attachment state, gripper state,
  EE pose and the 441 cloth vertices.  It never calls ``world.step`` itself,
  never calls a mutating control method, and never writes inside the frozen
  candidate/app tree.
* ``save_npz``/``save_json`` write only to the caller-provided output path.

This module intentionally has no Isaac/GarmentLab import so it can be tested
with plain stubs on a CPU-only machine.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class StepHook:
    """Passive per-step observer installed around ``backend._env.world.step``."""

    def __init__(self, backend):
        self.backend = backend
        self.world = backend._env.world
        self._original = None
        self._wrapper = None
        self._installed = False
        self.records = []
        self.observation_errors = []
        self.step_calls = 0

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    def install(self):
        if self._installed:
            raise RuntimeError('StepHook is already installed')
        self._original = self.world.step
        if not callable(self._original):
            raise TypeError('world.step is not callable')

        def observed_step(*args, **kwargs):
            # Exactly one call to the previously installed step.
            self.step_calls += 1
            try:
                value = self._original(*args, **kwargs)
            except BaseException as exc:
                self._safe_record(step_error=repr(exc))
                raise
            self._safe_record()
            return value

        self._wrapper = observed_step
        self.world.step = observed_step
        self._installed = True
        return self

    def close(self):
        if not self._installed:
            return
        if self.world.step is self._wrapper:
            self.world.step = self._original
        else:
            # A later wrapper replaced us; do not clobber an unknown chain.
            self.observation_errors.append(
                'world.step was replaced by another wrapper before StepHook.close')
        self._installed = False

    def __enter__(self):
        return self.install()

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # ------------------------------------------------------------------
    # passive reads
    # ------------------------------------------------------------------
    def _read_state(self):
        b = self.backend
        world = b._env.world
        control = b._env.control
        robot = b._env.robots[0]

        vertices = np.asarray(b._garment_world_positions(), dtype=np.float64)
        if vertices.shape != (441, 3) or not np.isfinite(vertices).all():
            raise ValueError('Invalid cloth vertices: %r' % (vertices.shape,))

        ee, quat = robot.get_cur_ee_pos()
        ee = np.asarray(ee, dtype=np.float64).reshape(-1)
        if ee.shape != (3,) or not np.isfinite(ee).all():
            raise ValueError('Invalid EE position: %r' % (ee.shape,))
        if quat is None:
            quat_wxyz = None
        else:
            quat_wxyz = np.asarray(quat, dtype=np.float64).reshape(-1)
            if quat_wxyz.shape != (4,) or not np.isfinite(quat_wxyz).all():
                raise ValueError('Invalid EE quaternion: %r' % (quat_wxyz.shape,))

        enabled = tuple(bool(slot.attachment_enabled()) for slot in control.slots)
        return {
            'sim_time_s': float(world.current_time),
            'absolute_step': int(world.current_time_step_index),
            'backend_step': int(b._step_count['n']),
            'holding': bool(b._holding),
            'enabled_slots': enabled,
            'attachment_enabled_any': bool(any(enabled)),
            'logical_attached': bool(
                getattr(control, 'attachlist', [None]) != [None]),
            'command_holding': bool(getattr(b, '_command_holding', False)),
            'gripper_state': int(getattr(b, '_gripper_state', -1)),
            'gripper_open': int(getattr(b, '_gripper_state', -1)) == 0,
            'ee_m': ee,
            'ee_quaternion_wxyz': quat_wxyz,
            'vertices': vertices,
        }

    def _record(self, step_error=None):
        try:
            row = self._read_state()
            row['ok'] = step_error is None
            row['step_error'] = step_error
            self.records.append(row)
        except BaseException as exc:
            self.observation_errors.append(repr(exc))
            self.records.append({
                'ok': False,
                'step_error': step_error,
                'observation_error': repr(exc),
            })

    def _safe_record(self, step_error=None):
        # An observation failure must never replace the step's return value or
        # its original exception.
        try:
            self._record(step_error=step_error)
        except BaseException as exc:
            self.observation_errors.append('record failed: ' + repr(exc))

    # ------------------------------------------------------------------
    # serialization
    # ------------------------------------------------------------------
    def _readable_rows(self):
        return [row for row in self.records if 'vertices' in row]

    def summary(self):
        rows = self._readable_rows()
        first = rows[0] if rows else None
        last = rows[-1] if rows else None
        return {
            'installed': bool(self._installed),
            'step_calls': int(self.step_calls),
            'records': len(self.records),
            'readable_records': len(rows),
            'observation_errors': list(self.observation_errors),
            'first_time_s': None if first is None else float(first['sim_time_s']),
            'last_time_s': None if last is None else float(last['sim_time_s']),
            'first_step': None if first is None else int(first['absolute_step']),
            'last_step': None if last is None else int(last['absolute_step']),
            'scope': 'read-only post-step time/holding/attachment/gripper/EE/vertices',
        }

    def arrays(self):
        rows = self._readable_rows()
        if not rows:
            raise ValueError('No readable step records to save')
        n = len(rows)
        enabled = np.asarray([row['enabled_slots'] for row in rows], dtype=bool)
        if enabled.shape != (n, len(rows[0]['enabled_slots'])):
            raise ValueError('Inconsistent attachment slot count')
        quat = np.asarray([
            row['ee_quaternion_wxyz'] if row['ee_quaternion_wxyz'] is not None
            else np.full(4, np.nan) for row in rows], dtype=np.float64)
        return {
            'sim_time_s': np.asarray([row['sim_time_s'] for row in rows], dtype=np.float64),
            'absolute_step': np.asarray([row['absolute_step'] for row in rows], dtype=np.int64),
            'backend_step': np.asarray([row['backend_step'] for row in rows], dtype=np.int64),
            'holding': np.asarray([row['holding'] for row in rows], dtype=bool),
            'enabled_slots': enabled,
            'attachment_enabled_any': np.asarray(
                [row['attachment_enabled_any'] for row in rows], dtype=bool),
            'logical_attached': np.asarray(
                [row['logical_attached'] for row in rows], dtype=bool),
            'command_holding': np.asarray(
                [row['command_holding'] for row in rows], dtype=bool),
            'gripper_state': np.asarray(
                [row['gripper_state'] for row in rows], dtype=np.int64),
            'gripper_open': np.asarray(
                [row['gripper_open'] for row in rows], dtype=bool),
            'ee_m': np.asarray([row['ee_m'] for row in rows], dtype=np.float64),
            'ee_quaternion_wxyz': quat,
            'vertices': np.asarray([row['vertices'] for row in rows], dtype=np.float64),
        }

    def save_npz(self, path):
        path = Path(path)
        arrays = self.arrays()
        np.savez_compressed(path, **arrays)
        return self.summary()

    def save_json(self, path):
        path = Path(path)
        path.write_text(
            json.dumps(self.summary(), indent=2, allow_nan=False) + '\n',
            encoding='utf-8')
        return self.summary()
