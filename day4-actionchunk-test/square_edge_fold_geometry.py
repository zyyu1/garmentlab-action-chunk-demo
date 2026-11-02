"""Square-cloth x-axis half-fold geometry.

The moving half is x < fold_line_x; the pick is the left-edge midpoint.
This is a development candidate and does not reuse the y-axis hem plan.
"""
import numpy as np


def edge_vertex(vertices):
    v = np.asarray(vertices, dtype=float)
    if v.ndim != 2 or v.shape[1] != 3 or not np.isfinite(v).all():
        raise ValueError('Invalid vertices')
    band = np.flatnonzero(v[:, 0] <= v[:, 0].min() + .015)
    mid_y = (v[:, 1].min() + v[:, 1].max()) / 2
    return int(band[np.argmin(np.abs(v[band, 1] - mid_y))])


def edge_plan(vertices, index):
    v = np.asarray(vertices, dtype=float)
    line = float((v[:, 0].min() + v[:, 0].max()) / 2)
    mask = v[:, 0] < line
    pick = v[index].copy()
    target = pick.copy()
    target[0] = 2 * line - pick[0]
    if not mask[index] or min(mask.sum(), (~mask).sum()) < 100:
        raise ValueError('Invalid left-half split')
    if abs(target[0]) > .45 or not -.85 < target[1] < -.10:
        raise ValueError('Target outside pilot workspace')
    if target[0] <= line:
        raise ValueError('Target must lie in the stationary half')
    return {'fold_axis': 'world_y', 'fold_line_x': line, 'source_mask': mask,
            'pick_reference': pick, 'target_reference': target, 'pick_index': index}


def square_edge_targets(pick, fold_line_x):
    """Four expert targets for an x-axis centre fold; backend straight segments only."""
    p = np.asarray(pick, dtype=float)
    radius = float(fold_line_x - p[0])
    if p.shape != (3,) or not np.isfinite(p).all() or not .15 < radius < .25:
        raise ValueError('Unexpected settled square geometry')
    angles = np.arange(1, 5) * np.pi / 4
    return np.column_stack([fold_line_x - radius * np.cos(angles),
                            np.full(4, p[1]),
                            p[2] + .02 * angles / np.pi + radius * np.sin(angles)])
