"""Single-step BC policy wrapper for Stage 6 closed-loop rollouts.

Loads a trained checkpoint plus its train-only stats, builds the 1340-dim
observation in the training order (vertices, ee, quat, joints, holding),
denormalizes the continuous dims back to metres/radians and maps the gripper
class back to the original command integer (0/1/2).
"""
import json
from pathlib import Path

import numpy as np
import torch

from train_bc import BCNet


class BCPolicy:
    def __init__(self, run_dir, dataset_dir):
        run_dir = Path(run_dir)
        ck = torch.load(run_dir / 'best.pt', map_location='cpu')
        self.stats = json.loads((Path(dataset_dir) / 'stats.json').read_text())
        self.model = BCNet(int(ck['in_dim']), int(ck['hidden']), ck['mode'])
        self.model.load_state_dict(ck['state'])
        self.model.eval()
        self.obs_mean = np.asarray(self.stats['obs_mean'], np.float32)
        self.obs_std = np.asarray(self.stats['obs_std'], np.float32)
        self.c_mean = np.asarray(self.stats['cont_mean'], np.float64)
        self.c_std = np.asarray(self.stats['cont_std'], np.float64)
        assert ck['mode'] == 'single'
        assert self.obs_mean.shape == (1340,)
        self.holding_normalization = self.stats.get(
            'holding_normalization', 'legacy')
        if self.holding_normalization == 'identity':
            index = int(self.stats.get('holding_index', 1339))
            if (index != 1339
                    or abs(float(self.obs_mean[index])) > 1e-12
                    or abs(float(self.obs_std[index]) - 1.0) > 1e-12):
                raise ValueError('Invalid identity holding normalization stats')

    @staticmethod
    def build_obs(vertices, ee, quat_wxyz, joints, holding):
        v = np.asarray(vertices, np.float32).reshape(-1)
        assert v.shape == (441 * 3,), v.shape
        q = np.asarray(quat_wxyz, np.float32).reshape(-1)
        assert q.shape == (4,), q.shape
        j = np.asarray(joints, np.float32).reshape(-1)
        assert j.shape == (9,), j.shape
        h = np.asarray([float(bool(holding))], np.float32)
        return np.concatenate([v, np.asarray(ee, np.float32).reshape(3), q, j, h])

    def predict(self, obs):
        x = (np.asarray(obs, np.float32) - self.obs_mean) / self.obs_std
        with torch.no_grad():
            pc, pg = self.model(torch.tensor(x[None], dtype=torch.float32))
        cont = pc[0].numpy().astype(np.float64) * self.c_std + self.c_mean
        grip = int(pg[0].argmax().item())
        return {'xyz': cont[:3].tolist(), 'yaw': float(cont[3]), 'gripper': grip}
