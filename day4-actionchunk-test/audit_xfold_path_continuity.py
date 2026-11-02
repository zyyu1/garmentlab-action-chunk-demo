"""Offline continuity audit for the x-axis L1 candidate.

URDF numerical IK only; no GPU, robot commands or physics.  Uses the actual
settled cloth geometry from the v5 initial snapshot when available.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit_l1_path_continuity import NOMINAL, load_urdf, make_fk, orientation  # noqa: E402
from multi_grasp_geometry import select_regions  # noqa: E402
from square_edge_fold_geometry import edge_plan, square_edge_targets  # noqa: E402
from square_pose_contract import grasp_to_ee  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--urdf', default=os.environ.get('DAY4_FRANKA_URDF',
                    'E:/learning/project/thesis/day4-actionchunk-test/frame_audit/lula_franka_gen.urdf'))
    ap.add_argument('--initial', default=os.environ.get(
        'DAY4_XFOLD_INITIAL',
        'E:/learning/project/thesis/day4-actionchunk-test/results/'
        'day4-square-grasp-hold-v5-20261031-113930-047613/00_initial.npz'))
    ap.add_argument('--step', type=float, default=.005)
    ap.add_argument('--branches', type=int, default=8)
    args = ap.parse_args()
    chain, lo, hi = load_urdf(args.urdf)
    fk = make_fk(chain)
    rot = orientation(0.)
    with np.load(args.initial) as data:
        vertices = np.asarray(data['vertices'])
    regions = select_regions(vertices)
    slot_label, pick_index = regions[1]
    if slot_label != 'left_sleeve':
        raise RuntimeError('Unexpected region order')
    pick = vertices[pick_index].copy()
    plan = edge_plan(vertices, pick_index)
    material = square_edge_targets(pick, plan['fold_line_x'])
    public = [('approach', pick + [0, 0, .15]), ('descend', grasp_to_ee(pick, 0.))]
    public += [(name, grasp_to_ee(point, 0.)) for name, point in
               zip(('arc45', 'arc90', 'arc135', 'place'), material)]
    subs = []
    prev_point = None
    for phase_label, goal in public:
        if prev_point is None:
            pts = [goal]
        else:
            count = max(1, int(np.ceil(np.linalg.norm(goal - prev_point) / args.step)))
            pts = [prev_point + (goal - prev_point) * i / count for i in range(1, count + 1)]
        subs += [(phase_label, i, point) for i, point in enumerate(pts)]
        prev_point = goal
    descend_index = max(i for i, (phase_label, _, _) in enumerate(subs) if phase_label == 'descend')

    def residual(q, target):
        T = fk(q)
        return np.r_[T[:3, 3] - target, .2 * R.from_matrix(rot @ T[:3, :3].T).as_rotvec()]

    def step(q, target, radius):
        lower = np.maximum(lo, q - radius)
        upper = np.minimum(hi, q + radius)
        if np.any(lower >= upper):
            return None
        try:
            opt = least_squares(lambda x: residual(x, target), q, bounds=(lower, upper),
                                max_nfev=120, ftol=1e-9, xtol=1e-9, gtol=1e-9)
        except Exception:
            return None
        q_new = opt.x
        T = fk(q_new)
        pe = float(np.linalg.norm(T[:3, 3] - target))
        re = float(R.from_matrix(rot @ T[:3, :3].T).magnitude())
        return (q_new, pe, re) if pe < 5e-4 and re < 5e-3 else None

    rng = np.random.default_rng(7)
    seeds = [NOMINAL] + [rng.uniform(lo, hi) for _ in range(64)]
    start_solutions = []
    descend_target = subs[descend_index][2]
    for seed in seeds:
        seed = np.clip(seed, lo + 1e-6, hi - 1e-6)
        try:
            opt = least_squares(lambda q: residual(q, descend_target), seed, bounds=(lo, hi),
                                max_nfev=120, ftol=1e-9, xtol=1e-9, gtol=1e-9)
        except Exception:
            continue
        q = opt.x
        T = fk(q)
        pe = float(np.linalg.norm(T[:3, 3] - descend_target))
        re = float(R.from_matrix(rot @ T[:3, :3].T).magnitude())
        if pe < 5e-4 and re < 5e-3 and not any(np.max(np.abs(q - s['q'])) < 5e-3 for s in start_solutions):
            start_solutions.append({'q': q, 'margin': float(np.minimum(q - lo, hi - q).min())})
    start_solutions.sort(key=lambda s: -s['margin'])

    results = []
    for k, start in enumerate(start_solutions[:args.branches]):
        q = start['q'].copy()
        prev = q.copy()
        max_delta = 0.
        min_margin = float('inf')
        fail = None
        for i in range(descend_index + 1, len(subs)):
            phase_label, sub, target = subs[i]
            found = None
            for radius in (.10, .20, .35):
                out = step(prev, target, radius)
                if out is not None:
                    found = out
                    break
            if found is None:
                fail = {'index': i, 'label': phase_label, 'subtarget': sub,
                        'target': target.tolist(), 'joint_limit_margin_rad': float(
                            np.minimum(prev - lo, hi - prev).min())}
                break
            q = found[0]
            max_delta = max(max_delta, float(np.max(np.abs(q - prev))))
            min_margin = min(min_margin, float(np.minimum(q - lo, hi - q).min()))
            prev = q.copy()
        results.append({'branch': k, 'descend_margin_rad': start['margin'],
                        'max_adjacent_delta_rad': max_delta,
                        'min_limit_margin_rad': min_margin if np.isfinite(min_margin) else None,
                        'completed': fail is None, 'fail': fail,
                        'final_q': q.tolist() if fail is None else None,
                        'final_margin_rad': float(np.minimum(q - lo, hi - q).min()) if fail is None else None})
        print(json.dumps(results[-1]), flush=True)
    report = {
        'urdf': str(args.urdf), 'initial_snapshot': str(args.initial),
        'region_order': [name for name, _ in regions], 'fold_slot': slot_label,
        'pick_index': int(pick_index), 'pick': pick.tolist(),
        'fold_line_x': plan['fold_line_x'], 'material_targets': material.tolist(),
        'ee_targets': [grasp_to_ee(point, 0.).tolist() for point in material],
        'subtarget_step_m': args.step, 'subtargets': len(subs),
        'descend_solutions': len(start_solutions), 'branches_tested': len(results),
        'branches_completed': sum(1 for r in results if r['completed']),
        'max_adjacent_delta_rad_completed': max(
            [r['max_adjacent_delta_rad'] for r in results if r['completed']], default=None),
        'results': results,
        'scope': 'URDF numerical IK/FK only; no robot commands or GPU simulation; branch continuity is not a dynamics or contact certification',
    }
    out = HERE / 'frame_audit' / 'xfold_path_continuity.json'
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('WROTE', out, flush=True)


if __name__ == '__main__':
    main()
