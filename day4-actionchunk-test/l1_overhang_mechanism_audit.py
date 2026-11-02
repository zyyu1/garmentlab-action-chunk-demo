"""Offline audit: is the L1 place overhang trajectory compensation or a final-target offset?

Reads the downloaded ``day4-l1-xfold-yaw-aware-*`` result directories and
measures, in the pick-centred cloth-local frame used by
``l1_yaw_fold_geometry.fold_metrics_yaw``:

* where the grasped pick particle actually ends up at ``03_place`` versus the
  commanded place target (0.20 local without overhang, 0.22 with +2 cm),
* where the flap free edge and the stationary far edge sit at every snapshot,
* whether the released geometry matches an ideal 20/20 half fold shifted as a
  rigid body, or a different shape (tent / drape).

No simulation, no writes outside the review directory. The verdict has to come
from the released geometry, not from the commanded numbers.
"""
import json
import os
import sys

import numpy as np
from scipy.spatial.transform import Rotation

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import l1_yaw_fold_geometry as geo  # noqa: E402

RESULTS = os.path.join(REPO, 'results')
OUT = os.path.join(RESULTS, 'L1_OVERHANG_MECHANISM_20261102')
WIDTH = 0.2
SNAPS = ['03_place', '03_hold_end', '04_released', '05_release_stationary', '06_final_3s']


def load_snap(d, name):
    p = os.path.join(d, name + '.npz')
    if not os.path.exists(p):
        return None
    return np.asarray(np.load(p)['vertices'], dtype=float)


def analyse(dirname):
    d = os.path.join(RESULTS, dirname)
    res = json.load(open(os.path.join(d, 'result.json'), encoding='utf-8'))
    fd = res['fold_definition']
    yaw = float(fd['fold_yaw_rad'])
    overhang = fd.get('fold_overhang_m')
    overhang = 0.0 if overhang is None else float(overhang)
    pick_index = int(fd['pick_index'])
    lp = np.asarray(np.load(os.path.join(d, 'cloth_constructed.npz'))['points'], dtype=float)
    initial = load_snap(d, '00_initial')
    R = Rotation.from_euler('z', yaw).as_matrix()
    pick = initial[pick_index]
    q0 = (initial - pick) @ R
    fold_line_q = float(lp[pick_index][0] + WIDTH - lp[pick_index][0])  # = WIDTH
    moving = lp[:, 0] < lp[pick_index][0] + WIDTH
    # Ideal nominal (overhang 0) half fold: reflect the moving half about the fold line.
    desired = q0[moving].copy()
    desired[:, 0] = 2 * fold_line_q - desired[:, 0]
    # Columns of the 21x21 grid, keyed by local x, for a readable profile.
    xs = np.round(lp[:, 0], 6)
    out = {'dir': dirname, 'seed': res.get('initial_case', {}).get('seed'),
           'overhang_m': overhang, 'passed': res.get('passed'),
           'fold_yaw_rad': yaw,
           'commanded_place_target_local_x': float(fd['target_reference_local'][0]),
           'commanded_place_pick_qx': float(fd['target_reference_local'][0] - lp[pick_index][0]),
           'snapshots': {}}
    for name in SNAPS:
        v = load_snap(d, name)
        if v is None:
            continue
        q1 = (v - pick) @ R
        # pick particle (the grasped material point) position in the local frame
        pick_qx = float(q1[pick_index, 0])
        flap_edge_qx = float(q1[moving, 0].max())
        stat_far_qx = float(q1[~moving, 0].max())
        crest_qx = float(q1[moving, 0].min())
        crest_z = float(v[moving][np.argmin(q1[moving, 0]), 2])
        # rigid transform taking the ideal nominal fold onto the observed moving half
        Rf, t = geo.rigid_fit_2d(desired[:, :2], q1[moving, :2])
        resid = np.linalg.norm((desired[:, :2] @ Rf.T + t) - q1[moving, :2], axis=1)
        profile = {}
        for x in (-0.2, -0.12, -0.04, 0.04, 0.12, 0.2):
            sel = np.abs(xs - x) < 1e-5
            if sel.any():
                profile[f'{x:+.2f}'] = round(float(q1[sel, 0].mean()), 4)
        metrics = geo.fold_metrics_yaw(initial, v, lp, pick_index, yaw, WIDTH)
        table_z = float(np.median(v[~moving, 2]))
        edge_row = np.abs(xs + 0.2) < 1e-5
        out['snapshots'][name] = {
            'pick_qx': round(pick_qx, 4),
            'flap_edge_qx': round(flap_edge_qx, 4),
            'stationary_far_edge_qx': round(stat_far_qx, 4),
            'over_edge_m': round(flap_edge_qx - stat_far_qx, 4),
            'flap_edge_row_qx': round(float(q1[edge_row, 0].mean()), 4),
            'flap_edge_row_above_table_m': round(float(v[edge_row, 2].mean() - table_z), 4),
            'flap_edge_row_min_above_table_m': round(float(v[edge_row, 2].min() - table_z), 4),
            'crest_above_table_m': round(float(v[moving, 2].max() - table_z), 4),
            'crest_qx': round(crest_qx, 4),
            'crest_z_m': round(crest_z, 4),
            'shift_vs_nominal_fold_dx_m': round(float(t[0]), 4),
            'shift_vs_nominal_fold_resid_mean_m': round(float(resid.mean()), 4),
            'shift_vs_nominal_fold_resid_p95_m': round(float(np.percentile(resid, 95)), 4),
            'reflected_target_error_m': round(metrics['moving_material_reflected_target_mean_error_m'], 4),
            'crossed': metrics['moving_half_crossed_fraction'],
            'iou': round(metrics['particle_occupancy_iou'], 4),
            'z_p95_m': round(metrics['cloth_z_p95_m'], 4),
            'qx_profile': profile,
        }
    return out


def main():
    dirs = sorted(n for n in os.listdir(RESULTS)
                  if n.startswith('day4-l1-xfold-yaw-aware-')
                  and os.path.exists(os.path.join(RESULTS, n, 'result.json')))
    rows = [analyse(n) for n in dirs]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'overhang_mechanism.json'), 'w', encoding='utf-8') as f:
        json.dump({'snapshot_order': SNAPS, 'frame': 'pick-centred cloth-local (q = R^T (v - pick))',
                   'cases': rows}, f, ensure_ascii=False, indent=1)
    for r in rows:
        print(f"\nseed {r['seed']} overhang {r['overhang_m']:.2f} passed {r['passed']}  {r['dir']}")
        print(f"  commanded place target: local x {r['commanded_place_target_local_x']:.3f} "
              f"(pick qx {r['commanded_place_pick_qx']:.3f})")
        print("  snapshot          pick_qx  flap_edge  stat_far  over_edge  crest_qx  crest_z  "
              "dx_vs_nominal  resid_mean  p95   crossed   IoU")
        for name in SNAPS:
            s = r['snapshots'].get(name)
            if not s:
                continue
            print(f"  {name:16s} {s['pick_qx']:7.4f} {s['flap_edge_qx']:9.4f} "
                  f"{s['stationary_far_edge_qx']:9.4f} {s['over_edge_m']:9.4f} "
                  f"{s['crest_qx']:9.4f} {s['crest_z_m']:7.4f} "
                  f"{s['shift_vs_nominal_fold_dx_m']:13.4f} {s['shift_vs_nominal_fold_resid_mean_m']:10.4f} "
                  f"{s['shift_vs_nominal_fold_resid_p95_m']:6.4f} {s['crossed']:8.3f} {s['iou']:6.3f}")
    print('\nwrote', os.path.join(OUT, 'overhang_mechanism.json'))


if __name__ == '__main__':
    main()
