"""Generate the Stage 5 demo initial-state plan (deterministic).

Same sampling rule as Stage 4 held-out registration:
  dx, dy, yaw = first three draws of default_rng(seed) over the frozen ranges;
  L2 bottom strip width = 4th draw U(0.16, 0.18) rounded to 6 decimals;
  L3 left strip width = 0.20.
Writes stage5-demo-initial-plan.json next to this file.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
APP = Path('/root/autodl-tmp/stage5-trial/app')

RANGES = {
    'flat': {'translate': (0.0, 0.03), 'yaw': (-0.1745, 0.1745), 'settle': 120,
             'strip': None},
    'perturbed': {'translate': (0.0, 0.03), 'yaw': (-0.1745, 0.1745), 'settle': 180,
                  'strip': 'bottom'},
    'crumpled': {'translate': (0.0, 0.05), 'yaw': (-0.3491, 0.3491), 'settle': 240,
                 'strip': 'left'},
}
SEEDS = {'flat': (6100, 6219), 'perturbed': (6300, 6419), 'crumpled': (6500, 6619)}
STATUS = 'stage5_demo_registered_v1'


def case(seed, level):
    cfg = RANGES[level]
    rng = np.random.default_rng(seed)
    dx = float(rng.uniform(*cfg['translate']))
    dy = float(rng.uniform(*cfg['translate']))
    yaw = float(rng.uniform(*cfg['yaw']))
    row = {'level': level, 'seed': seed, 'translation_xy_m': [dx, dy],
           'yaw_rad': yaw, 'settle_steps': cfg['settle'], 'status': STATUS}
    if level == 'flat':
        row['lift_drop_cycles'] = []
    elif level == 'perturbed':
        row['strips'] = [{'edge': 'bottom', 'width_m': round(float(rng.uniform(0.16, 0.18)), 6)}]
    else:
        row['strips'] = [{'edge': 'left', 'width_m': 0.2}]
    return row


def main():
    episodes = []
    for level, (lo, hi) in SEEDS.items():
        episodes.extend(case(s, level) for s in range(lo, hi + 1))
    plan = {
        'version': 'stage5-demo-v1',
        'config_sha256': hashlib.sha256((APP / 'square-difficulty.yaml').read_bytes()).hexdigest(),
        'asset_sha256': hashlib.sha256((APP / 'square_cloth_40cm.usda').read_bytes()).hexdigest(),
        'sampling': 'default_rng(seed) first 3 draws (dx,dy,yaw); L2 4th draw width U(0.16,0.18); L3 width 0.20',
        'episodes': episodes,
    }
    out = HERE / 'stage5-demo-initial-plan.json'
    out.write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    print('DEMO_PLAN_WRITTEN', out, 'episodes', len(episodes))


if __name__ == '__main__':
    main()
