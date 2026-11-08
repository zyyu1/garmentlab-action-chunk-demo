"""H=4 policy adapter for the Stage 7 L1 development run."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import torch

from train_bc import BCNet


class H4Policy:
    def __init__(self, checkpoint, stats_path):
        self.checkpoint = Path(checkpoint)
        self.stats = json.loads(Path(stats_path).read_text(encoding='utf-8'))
        ck = torch.load(self.checkpoint, map_location='cpu')
        if ck.get('mode') != 'h4':
            raise ValueError('checkpoint is not h4 mode')
        if int(ck.get('in_dim', -1)) != 1340 or int(ck.get('hidden', -1)) != 512:
            raise ValueError('unexpected H4 checkpoint dimensions')
        self.model = BCNet(1340, 512, 'h4')
        self.model.load_state_dict(ck['state'])
        self.model.eval()
        self.obs_mean = np.asarray(self.stats['obs_mean'], np.float32)
        self.obs_std = np.asarray(self.stats['obs_std'], np.float32)
        self.c_mean = np.asarray(self.stats['cont_mean'], np.float64)
        self.c_std = np.asarray(self.stats['cont_std'], np.float64)
        if self.stats.get('holding_normalization') != 'identity':
            raise ValueError('H4 stats must use identity holding')
        if abs(float(self.obs_mean[1339])) > 1e-12 or abs(
                float(self.obs_std[1339]) - 1.0) > 1e-12:
            raise ValueError('H4 holding stats are not identity')
        self.epoch = int(ck.get('epoch', -1))

    @staticmethod
    def build_obs(vertices, ee, quat_wxyz, joints, holding):
        v = np.asarray(vertices, np.float32).reshape(-1)
        if v.shape != (441 * 3,):
            raise ValueError('vertices shape')
        q = np.asarray(quat_wxyz, np.float32).reshape(-1)
        if q.shape != (4,):
            raise ValueError('quat shape')
        j = np.asarray(joints, np.float32).reshape(-1)
        if j.shape != (9,):
            raise ValueError('joints shape')
        h = np.asarray([float(bool(holding))], np.float32)
        return np.concatenate([v, np.asarray(ee, np.float32).reshape(3), q, j, h])

    def predict_chunk(self, obs):
        x = (np.asarray(obs, np.float32) - self.obs_mean) / self.obs_std
        t0 = time.perf_counter()
        with torch.no_grad():
            pc, pg = self.model(torch.tensor(x[None], dtype=torch.float32))
        inference_ms = (time.perf_counter() - t0) * 1000.0
        if tuple(pc.shape) != (1, 4, 4) or tuple(pg.shape) != (1, 4, 3):
            raise ValueError('unexpected H4 output shape: %r %r'
                             % (tuple(pc.shape), tuple(pg.shape)))
        cont = pc[0].numpy().astype(np.float64) * self.c_std + self.c_mean
        grip = pg[0].argmax(-1).numpy().astype(np.int64)
        actions = [
            {
                'xyz': cont[k, :3].tolist(),
                'yaw': float(cont[k, 3]),
                'gripper': int(grip[k]),
            }
            for k in range(4)
        ]
        return {
            'actions': actions,
            'inference_ms': float(inference_ms),
            'cont_shape': list(pc.shape),
            'gripper_logits_shape': list(pg.shape),
        }
