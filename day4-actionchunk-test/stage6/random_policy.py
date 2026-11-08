"""Order-independent random baseline policy for the L1 development evaluation.

Per-episode RNG: numpy.random.default_rng([base_seed, episode_seed]).
Per action draw order: dx, dy, dz, dyaw, gripper.
  xyz = current actual EE xyz + U(-0.05, 0.05) per axis
  yaw = current actual EE yaw + U(-0.2, 0.2)
  gripper = 0/1/2 with equal probability
No expert target, no prepared-region snapping, no automatic release.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation


class RandomPolicy:
    def __init__(self, backend, episode_seed, base_seed=0):
        self.backend = backend
        self.episode_seed = int(episode_seed)
        self.base_seed = int(base_seed)
        self.rng = np.random.default_rng([self.base_seed, self.episode_seed])
        self.calls = 0

    def _current_ee(self):
        ee, quat = self.backend._env.robots[0].get_cur_ee_pos()
        ee = np.asarray(ee, dtype=np.float64).reshape(3)
        quat = np.asarray(quat, dtype=np.float64).reshape(4)
        norm = np.linalg.norm(quat)
        if not np.isfinite(ee).all() or not np.isfinite(norm) or norm <= 0:
            raise RuntimeError('invalid current EE state')
        quat = quat / norm
        # get_cur_ee_pos()/BC observation metadata use wxyz.
        q_xyzw = quat[[1, 2, 3, 0]]
        yaw = float(Rotation.from_quat(q_xyzw).as_euler('xyz')[2])
        yaw = float(np.arctan2(np.sin(yaw), np.cos(yaw)))
        return ee, yaw

    def predict(self, obs=None):
        ee, yaw = self._current_ee()
        dx, dy, dz = self.rng.uniform(-0.05, 0.05, 3)
        dyaw = float(self.rng.uniform(-0.2, 0.2))
        gripper = int(self.rng.integers(0, 3))
        target = ee + np.asarray([dx, dy, dz], dtype=np.float64)
        target_yaw = float(np.arctan2(np.sin(yaw + dyaw),
                                      np.cos(yaw + dyaw)))
        self.calls += 1
        if not np.isfinite(target).all() or not np.isfinite(target_yaw):
            raise RuntimeError('nonfinite random action')
        return {
            'xyz': target.tolist(),
            'yaw': target_yaw,
            'gripper': gripper,
        }

    def identity(self):
        return {
            'kind': 'random',
            'checkpoint_used': False,
            'base_seed': self.base_seed,
            'episode_seed': self.episode_seed,
            'rng': 'numpy.random.default_rng([0, episode_seed])',
            'draw_order_per_action': ['dx', 'dy', 'dz', 'dyaw', 'gripper'],
            'xyz': 'current actual EE xyz + U(-0.05,0.05) per axis',
            'yaw': ('current actual EE yaw + U(-0.2,0.2) rad; '
                    'R.from_euler("xyz",[pi,0,yaw]) convention'),
            'gripper': '0/1/2 equal probability',
            'no_expert_target': True,
            'no_prepared_region_snap': True,
            'no_auto_release': True,
        }
