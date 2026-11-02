"""Offline L1 path continuity audit (URDF numerical IK only).

No GPU / no robot commands. Checks whether the planned square half-fold
Cartesian path has a continuous 7-joint solution branch, and whether the
terminal place target is reachable with joint-limit margin.

Usage:
  python audit_l1_path_continuity.py [--urdf PATH] [--mode final|path]

The installed lula_franka_gen.urdf is not stored in this repository; pass the
path or set DAY4_FRANKA_URDF.  Results are written next to this script under
frame_audit/l1_path_continuity.json.
"""
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from square_geometry import square_targets  # noqa: E402
from square_pose_contract import GRASP_OFFSET_LOCAL, grasp_to_ee  # noqa: E402

NAMES = ['panda_joint%d' % i for i in range(1, 8)]
NOMINAL = np.array([0, -.785, 0, -2.356, 0, 1.571, .785])


def load_urdf(path):
    root = ET.parse(path).getroot()
    chain = {j.find('child').get('link'): j for j in root.findall('joint')}
    by_name = {j.get('name'): j for j in chain.values()}
    lo = np.array([float(by_name[n].find('limit').get('lower')) for n in NAMES])
    hi = np.array([float(by_name[n].find('limit').get('upper')) for n in NAMES])
    return chain, lo, hi


def make_fk(chain):
    def vec(el, tag, default):
        return np.fromstring(el.get(tag, default), sep=' ')

    def fk(q, link='right_gripper', finger=.04):
        cache = {}
        base = np.eye(4)
        base[:3, :3] = R.from_euler('z', -np.pi / 2).as_matrix()

        def walk(link_name):
            if link_name not in chain:
                return base
            if link_name in cache:
                return cache[link_name]
            j = chain[link_name]
            o = j.find('origin')
            T = np.eye(4)
            if o is not None:
                T[:3, :3] = R.from_euler('xyz', vec(o, 'rpy', '0 0 0')).as_matrix()
                T[:3, 3] = vec(o, 'xyz', '0 0 0')
            M = np.eye(4)
            name = j.get('name')
            typ = j.get('type')
            if typ in ('revolute', 'continuous'):
                M[:3, :3] = R.from_rotvec(
                    vec(j.find('axis'), 'xyz', '1 0 0') * q[NAMES.index(name)]).as_matrix()
            elif typ == 'prismatic':
                M[:3, 3] = vec(j.find('axis'), 'xyz', '1 0 0') * finger
            out = walk(j.find('parent').get('link')) @ T @ M
            cache[link_name] = out
            return out

        return walk(link)
    return fk


def orientation(yaw):
    return R.from_euler('xyz', [np.pi, 0., float(yaw)]).as_matrix()


def solve_ik(fk, lo, hi, target, rot, seeds, max_nfev=80):
    def residual(q):
        T = fk(q)
        return np.r_[T[:3, 3] - target, .2 * R.from_matrix(rot @ T[:3, :3].T).as_rotvec()]

    out = []
    for seed in seeds:
        seed = np.clip(np.asarray(seed, dtype=float), lo + 1e-6, hi - 1e-6)
        try:
            opt = least_squares(residual, seed, bounds=(lo, hi), max_nfev=max_nfev,
                                ftol=1e-8, xtol=1e-8, gtol=1e-8)
        except Exception:
            continue
        q = opt.x
        T = fk(q)
        pe = float(np.linalg.norm(T[:3, 3] - target))
        re = float(R.from_matrix(rot @ T[:3, :3].T).magnitude())
        if pe < 5e-4 and re < 5e-3:
            if not any(np.max(np.abs(q - s['q'])) < 5e-3 for s in out):
                out.append({'q': q, 'position_error_m': pe, 'orientation_error_rad': re,
                            'min_limit_margin_rad': float(np.minimum(q - lo, hi - q).min())})
    out.sort(key=lambda s: s['position_error_m'] + .2 * s['orientation_error_rad'])
    return out


def make_seeds(rng, lo, hi, count, extra=()):
    seeds = [NOMINAL, *extra]
    seeds += [rng.uniform(lo, hi) for _ in range(count)]
    return seeds


def place_target(material_point, yaw):
    return grasp_to_ee(material_point, yaw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--urdf', default=os.environ.get('DAY4_FRANKA_URDF',
                    'E:/learning/project/thesis/day4-actionchunk-test/frame_audit/lula_franka_gen.urdf'))
    ap.add_argument('--mode', default='final', choices=['final', 'path'])
    ap.add_argument('--seeds', type=int, default=16)
    ap.add_argument('--max-nfev', type=int, default=80)
    args = ap.parse_args()
    chain, lo, hi = load_urdf(args.urdf)
    fk = make_fk(chain)
    rng = np.random.default_rng(0)
    report = {'urdf': str(args.urdf), 'mode': args.mode, 'seeds': args.seeds,
              'scope': 'URDF numerical IK only; no robot commands or physics'}

    if args.mode == 'final':
        point0 = np.array([0., -.25, .0299])
        rows = []
        for yaw in (0., .6, -.6, 1.2, -1.2):
            for dz in (0., .02, .05, .08):
                point = point0 + [0., 0., dz]
                target = place_target(point, yaw)
                sols = solve_ik(fk, lo, hi, target, orientation(yaw),
                                make_seeds(rng, lo, hi, args.seeds, [NOMINAL]), args.max_nfev)
                if sols:
                    best = max(sols, key=lambda s: s['min_limit_margin_rad'])
                    row = {'yaw_rad': yaw, 'material_point': point.tolist(),
                           'solutions': len(sols),
                           'best_min_limit_margin_rad': best['min_limit_margin_rad'],
                           'best_q': best['q'].tolist(), 'q4': float(best['q'][3]),
                           'q4_margin_rad': float(min(best['q'][3] - lo[3], hi[3] - best['q'][3])),
                           'position_error_m': best['position_error_m'],
                           'orientation_error_rad': best['orientation_error_rad']}
                else:
                    row = {'yaw_rad': yaw, 'material_point': point.tolist(), 'solutions': 0}
                rows.append(row)
                print(json.dumps(row), flush=True)
        report['final_target_sweep'] = rows

    if args.mode == 'path':
        # Legacy audit target path: nominal pick and the true cloth centre line.
        pick = np.array([0., -.65, .0099])
        material = square_targets(pick, -.45)
        public = [('approach', pick + [0, 0, .15]), ('descend', grasp_to_ee(pick, 0.))]
        public += [(label, grasp_to_ee(v, 0.)) for label, v in
                   zip(('arc45', 'arc90', 'arc135', 'place'), material)]
        rows = []
        previous = NOMINAL
        prev_point = None
        for label, goal in public:
            if prev_point is None:
                sub = [goal]
            else:
                count = max(1, int(np.ceil(np.linalg.norm(goal - prev_point) / .025)))
                sub = [prev_point + (goal - prev_point) * i / count for i in range(1, count + 1)]
            for i, tgt in enumerate(sub):
                seeds = make_seeds(rng, lo, hi, args.seeds, [previous])
                sols = solve_ik(fk, lo, hi, tgt, orientation(0.), seeds, args.max_nfev)
                if not sols:
                    rows.append({'label': label, 'subtarget': i, 'target': tgt.tolist(),
                                 'solutions': 0, 'all_q': []})
                    break
                nearest = min(sols, key=lambda s: float(np.max(np.abs(s['q'] - previous))))
                delta = float(np.max(np.abs(nearest['q'] - previous)))
                rows.append({'label': label, 'subtarget': i, 'target': tgt.tolist(),
                             'solutions': len(sols), 'nearest_q': nearest['q'].tolist(),
                             'nearest_delta_rad': delta,
                             'min_limit_margin_rad': nearest['min_limit_margin_rad'],
                             'all_q': [s['q'].tolist() for s in sols]})
                previous = nearest['q']
                prev_point = goal
        report['path_rows'] = rows

        # Bottleneck (minimax) joint-space path over all branches found.
        if rows and all(r.get('all_q') for r in rows):
            qs = [[np.asarray(q) for q in r['all_q']] for r in rows]
            dp = [0.0] * len(qs[0])
            back = [[None] * len(qs[0])]
            for i in range(1, len(qs)):
                ndp = []
                nback = []
                for j, q in enumerate(qs[i]):
                    best = None
                    best_k = None
                    for k, prev_q in enumerate(qs[i - 1]):
                        edge = float(np.max(np.abs(q - prev_q)))
                        cost = max(dp[k], edge)
                        if best is None or cost < best:
                            best, best_k = cost, k
                    ndp.append(best)
                    nback.append(best_k)
                dp = ndp
                back.append(nback)
            best_end = int(np.argmin(dp))
            chosen = [best_end]
            for i in range(len(qs) - 1, 0, -1):
                chosen.append(back[i][chosen[-1]])
            chosen.reverse()
            path = []
            for i, j in enumerate(chosen):
                q = qs[i][j]
                path.append({'index': i, 'label': rows[i]['label'],
                             'subtarget': rows[i]['subtarget'],
                             'q': q.tolist(),
                             'min_limit_margin_rad': float(np.minimum(q - lo, hi - q).min())})
            deltas = [float(np.max(np.abs(qs[i][chosen[i]] - qs[i - 1][chosen[i - 1]])))
                      for i in range(1, len(qs))]
            report['minimax_path'] = {
                'max_adjacent_delta_rad': float(max(deltas)) if deltas else 0.,
                'deltas_rad': deltas, 'chosen': path}
            print('MINIMAX_MAX_DELTA_RAD', max(deltas) if deltas else 0., flush=True)

    out = HERE / 'frame_audit' / ('l1_path_continuity_%s.json' % args.mode)
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('WROTE', out, flush=True)


if __name__ == '__main__':
    main()
