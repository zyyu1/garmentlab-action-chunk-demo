"""Yaw-aware x-axis half-fold geometry and provisional metrics for L1.

The cloth is treated as a rigidly posed 0.4 m square: the fold line is the
cloth-local centre line, not world x.  All axis-dependent quantities are
evaluated after rotating into the cloth-local frame, so the same plan applies
to the yawed L1 initial cases.  Metrics remain particle projection proxies,
not certified triangle overlap or material quality.
"""
import numpy as np
from scipy.ndimage import binary_dilation
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation


def rigid_fit_2d(source, target):
    """Best-fit rotation/translation taking source xy onto target xy."""
    a = np.asarray(source, dtype=float)
    b = np.asarray(target, dtype=float)
    if a.ndim != 2 or b.ndim != 2 or a.shape[0] != b.shape[0] or a.shape[1] < 2 or b.shape[1] < 2:
        raise ValueError('Invalid rigid-fit inputs')
    if not np.isfinite(a[:, :2]).all() or not np.isfinite(b[:, :2]).all():
        raise ValueError('Nonfinite rigid-fit inputs')
    ca, cb = a[:, :2].mean(0), b[:, :2].mean(0)
    H = (a[:, :2] - ca).T @ (b[:, :2] - cb)
    U, _, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T
    return R, cb - R @ ca


def measure_yaw(local_points, vertices):
    """Measured world yaw of a settled cloth relative to its mesh local frame."""
    lp = np.asarray(local_points, dtype=float)
    v = np.asarray(vertices, dtype=float)
    if lp.shape != v.shape or lp.ndim != 2 or lp.shape[1] != 3:
        raise ValueError('Unexpected local/vertex arrays')
    R, t = rigid_fit_2d(lp, v)
    pred = lp[:, :2] @ R.T + t
    residual = np.linalg.norm(v[:, :2] - pred, axis=1)
    yaw = float(np.arctan2(R[1, 0], R[0, 0]))
    return yaw, float(residual.max()), float(np.percentile(residual, 95))


def local_arc(pick, yaw, lateral_local, width, overhang=0.):
    """Four material targets for a half fold in the cloth-local frame.

    ``overhang`` extends only the final (place) target laterally past the
    nominal half-fold point, so the flap's free edge ends up beyond the
    stationary half's far edge.  It defaults to 0, which reproduces the
    nominal half fold exactly.
    """
    p = np.asarray(pick, dtype=float)
    lateral = np.asarray(lateral_local, dtype=float)
    if p.shape != (3,) or lateral.shape != (3,) or not np.isfinite(p).all():
        raise ValueError('Invalid arc inputs')
    if not .15 < float(width) < .25:
        raise ValueError('Unexpected fold width')
    if not 0. <= float(overhang) <= .04:
        raise ValueError('Unexpected fold overhang')
    R = Rotation.from_euler('z', float(yaw)).as_matrix()
    targets = []
    for index, angle in enumerate(np.arange(1, 5) * np.pi / 4):
        local = lateral * (width - width * np.cos(angle))
        local[2] = .02 * angle / np.pi + width * np.sin(angle)
        if index == 3:
            local = local + lateral * float(overhang)
        targets.append(p + R @ local)
    return np.asarray(targets)


def fold_metrics_yaw(initial, final, local_points, pick_index, yaw, width=.2,
                     lateral_local=(1., 0., 0.)):
    """Provisional fold metrics with the fold axis recovered from the real yaw.

    ``lateral_local`` is the cloth-local fold direction: ``+x`` for the L1/L2/L3
    left fold and ``-x`` for the mirrored right fold.  The default reproduces the
    original left-fold metrics exactly.
    """
    initial = np.asarray(initial, dtype=float)
    final = np.asarray(final, dtype=float)
    lp = np.asarray(local_points, dtype=float)
    if initial.shape != final.shape or initial.ndim != 2 or initial.shape[1] != 3:
        raise ValueError('Invalid fold geometry')
    if lp.shape != initial.shape or not np.isfinite(initial).all() or not np.isfinite(final).all():
        raise ValueError('Invalid fold geometry')
    lateral_local = np.asarray(lateral_local, dtype=float)
    if lateral_local.shape != (3,) or not np.isfinite(lateral_local).all():
        raise ValueError('Invalid fold lateral')
    if abs(abs(float(lateral_local[0])) - 1.) > 1e-9 or np.any(np.abs(lateral_local[1:]) > 1e-12):
        raise ValueError('Fold lateral must be +/- cloth-local x')
    sign = float(lateral_local[0])
    pick_index = int(pick_index)
    R = Rotation.from_euler('z', float(yaw)).as_matrix()
    lateral = R @ lateral_local
    pick = initial[pick_index]
    pick_local = lp[pick_index]
    fold_line_local_x = float(pick_local[0] + sign * width)
    moving = (lp[:, 0] - fold_line_local_x) * sign < 0
    if not 100 <= int(moving.sum()) <= 341:
        raise ValueError('Degenerate fold split')
    crossed = float((((final[moving] - pick) @ lateral) > width).mean())
    # Rotate into the pick-centred cloth-local frame: q = R^T (v - pick).
    q0 = (initial - pick) @ R
    q1 = (final - pick) @ R
    line_q = float(fold_line_local_x - pick_local[0])
    desired = q0[moving].copy()
    desired[:, 0] = 2 * line_q - desired[:, 0]
    reflected_error = float(np.linalg.norm(q1[moving, :2] - desired[:, :2], axis=1).mean())
    moving_xy = final[moving, :2]
    stationary_xy = final[~moving, :2]
    distances = np.r_[cKDTree(stationary_xy).query(moving_xy)[0],
                      cKDTree(moving_xy).query(stationary_xy)[0]]
    # Occupancy proxy in the cloth-local frame; the cell grid is translation
    # and rotation invariant with respect to the fold axis only in this frame.
    cell = .01
    a = q0[:, :2]
    b = q1[:, :2]
    lo = np.minimum(a.min(axis=0), b.min(axis=0)) - .02
    hi = np.maximum(a.max(axis=0), b.max(axis=0)) + .02
    shape = np.ceil((hi - lo) / cell).astype(int) + 1
    if np.any(shape > 1000):
        raise ValueError('Geometry escaped occupancy grid workspace')
    grids = []
    for points in (q1[moving, :2], q1[~moving, :2]):
        ij = np.floor((points - lo) / cell).astype(int)
        grid = np.zeros(tuple(shape), dtype=bool)
        grid[ij[:, 0], ij[:, 1]] = True
        grids.append(binary_dilation(grid, iterations=1))
    overlap = float(np.logical_and(*grids).sum() / max(1, np.logical_or(*grids).sum()))
    return {'symmetric_xy_alignment_mean_m': float(distances.mean()),
            'particle_occupancy_iou': overlap,
            'occupancy_cell_m': cell,
            'occupancy_dilation_cells': 1,
            'moving_half_crossed_fraction': crossed,
            'moving_material_reflected_target_mean_error_m': reflected_error,
            'cloth_z_p95_m': float(np.percentile(final[:, 2], 95)),
            'fold_yaw_rad': float(yaw),
            'fold_width_m': float(width),
            'fold_lateral_local': lateral_local.tolist(),
            'fold_line_local_x': fold_line_local_x,
            'pick_index': pick_index,
            'moving_count': int(moving.sum()),
            'fold_frame': 'cloth-local',
            'metric_scope': 'Particle projection proxies; not certified triangle overlap, self-intersection or material quality.'}
