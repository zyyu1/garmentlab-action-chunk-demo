"""Offline geometry check around vertex 91, the fold line and layer heights."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
DER = HERE / 'results' / 'RC8B_L2_DIAG_20261105' / 'day4-square-initial-stripfold-20261104-202215-l2posecontrol' / 'initial_geometry.npz'
NEW = HERE / 'results' / 'RC8B_INITIALS_20261105' / 'day4-square-initial-stripfold-20261105-015817-115841' / 'initial_geometry.npz'
OLD = Path(r'E:\learning\project\thesis\day4-actionchunk-test\results\A5_RC2_AUDIT_20261103T194913Z\day4-square-initial-stripfold-20261103-062710-242560\initial_geometry.npz')
OUT = HERE / 'results' / 'RC8B_L2_DIAG_20261105'
SURFACE = '#fcfcfb'; GRID = '#e1e0d9'; AXIS = '#c3c2b7'; BLUE = '#2a78d6'; ORANGE = '#eb6834'; RED = '#d03b3b'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
                     'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
                     'savefig.facecolor': SURFACE})

der = np.load(DER)['final']; new = np.load(NEW)['final']; old = np.load(OLD)['final']
delta = np.linalg.norm(der - new, axis=1) * 1000
i = int(np.argmax(delta))

# mesh-grid neighbours: 21x21 row-major, index i -> (row, col)
row, col = divmod(i, 21)
grid = [(row + dr) * 21 + (col + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)
        if 0 <= row + dr < 21 and 0 <= col + dc < 21 and (dr, dc) != (0, 0)]
# spatial neighbours within 25 mm xy, excluding the vertex itself
dxy = np.linalg.norm(new[:, :2] - new[i, :2], axis=1) * 1000
spatial = [int(k) for k in np.where(dxy <= 25.0)[0] if k != i]


def layers(idx, v=new):
    z = sorted(v[idx, 2] * 1000)
    out, cur = [], [z[0]]
    for v in z[1:]:
        if v - cur[-1] > 5.0:
            out.append({'n': len(cur), 'z_mean_mm': round(float(np.mean(cur)), 3),
                        'z_min_mm': round(float(min(cur)), 3), 'z_max_mm': round(float(max(cur)), 3)})
            cur = [v]
        else:
            cur.append(v)
    out.append({'n': len(cur), 'z_mean_mm': round(float(np.mean(cur)), 3),
                'z_min_mm': round(float(min(cur)), 3), 'z_max_mm': round(float(max(cur)), 3)})
    return out


sp = sorted(spatial, key=lambda k: dxy[k])
neigh = []
for k in sp:
    neigh.append({'index': int(k), 'xy_mm': [round(float(new[k, 0] * 1000), 3), round(float(new[k, 1] * 1000), 3)],
                  'xy_dist_mm': round(float(dxy[k]), 3),
                  'z_der_mm': round(float(der[k, 2] * 1000), 4), 'z_new_mm': round(float(new[k, 2] * 1000), 4),
                  'dz_mm': round(float((der[k, 2] - new[k, 2]) * 1000), 4)})

# fold line from the z transition along y (10 mm bins)
y = new[:, 1] * 1000; z = new[:, 2] * 1000
bins = []
for lo in np.arange(np.floor(y.min() / 10) * 10, y.max(), 10):
    m = (y >= lo) & (y < lo + 10)
    if m.sum():
        bins.append({'y_start_mm': float(lo), 'n': int(m.sum()),
                     'frac_z_gt20': float((z[m] > 20).mean()),
                     'z_median_mm': float(np.median(z[m]))})
cross = [b for b in bins if b['frac_z_gt20'] >= 0.5]
fold_y = max((b['y_start_mm'] for b in cross), default=float('nan'))

# projection overlap proxy on a 2 mm xy grid
def occ(v, cell=2.0, origin=None):
    if origin is None:
        origin = np.floor(np.minimum(der[:, :2].min(0), new[:, :2].min(0)) / (cell / 1000.0)).astype(int) - 1
    hi = np.ceil(np.maximum(der[:, :2].max(0), new[:, :2].max(0)) / (cell / 1000.0)).astype(int) + 1
    a = np.zeros((hi[0] - origin[0], hi[1] - origin[1]), bool)
    idx = np.floor(v[:, :2] / (cell / 1000.0)).astype(int) - origin
    a[idx[:, 0], idx[:, 1]] = True
    return a


oa, ob = occ(der, 2.0), occ(new, 2.0)
inter = np.logical_and(oa, ob).sum(); union = np.logical_or(oa, ob).sum()
iou2 = float(inter / union)
oa5, ob5 = occ(der, 5.0), occ(new, 5.0)
iou5 = float(np.logical_and(oa5, ob5).sum() / np.logical_or(oa5, ob5).sum())

summary = {
    'vertex': i,
    'position_der_m': der[i].tolist(), 'position_new_m': new[i].tolist(),
    'delta_mm': float(delta[i]),
    'mesh_grid_neighbours': {int(k): round(float((der[k, 2] - new[k, 2]) * 1000), 4) for k in grid},
    'spatial_neighbours_25mm': neigh,
    'layers_within_25mm_new': layers(sp, new),
    'layers_within_25mm_der': layers(sp, der),
    'fold_line_y_from_z_transition_mm': fold_y,
    'vertex_y_mm': float(new[i, 1] * 1000),
    'vertex_distance_to_fold_line_mm': float(new[i, 1] * 1000 - fold_y),
    'projection_overlap_iou_2mm': iou2,
    'projection_overlap_iou_5mm': iou5,
    'layer_gaps_new_mm': [round(float(b['z_mean_mm'] - a['z_mean_mm']), 3)
                          for a, b in zip(layers(sp, new)[:-1], layers(sp, new)[1:])],
    'z_histogram_counts': {str(v): int(((z >= v) & (z < v + 10)).sum()) for v in range(0, 80, 10)},
    'caveat': 'layer gaps and xy projection overlap are proxies; no mesh/contact solver data, so no claim of real penetration or contact state',
}
(OUT / 'geometry_check.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')

fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.2))
sc = axes[0].scatter(new[:, 0] * 1000, new[:, 1] * 1000, c=new[:, 2] * 1000, cmap='viridis', s=14)
axes[0].scatter([new[i, 0] * 1000], [new[i, 1] * 1000], s=80, facecolors='none', edgecolors=RED, linewidths=1.6, label='#91')
axes[0].axhline(fold_y, color=ORANGE, lw=1.0, ls='--', label='fold-line proxy')
axes[0].set_xlabel('x (mm)'); axes[0].set_ylabel('y (mm)'); axes[0].set_title('initial final: top view, colour = z')
axes[0].legend(fontsize=7); fig.colorbar(sc, ax=axes[0], label='z (mm)')
axes[1].hist(new[:, 2] * 1000, bins=np.arange(0, 80, 5), color=BLUE, alpha=.75, label='new')
axes[1].axvline(new[i, 2] * 1000, color=RED, lw=1.2, ls='--', label='#91 z')
axes[1].set_xlabel('z (mm)'); axes[1].set_ylabel('vertices'); axes[1].set_title('layer height histogram')
axes[1].legend(fontsize=7)
for ax in axes:
    ax.grid(color=GRID, lw=.7); ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(AXIS)
fig.tight_layout(); fig.savefig(OUT / 'geometry_check.png', dpi=180); plt.close(fig)

print('GEOMETRY_OK vertex', i, 'delta_mm', round(float(delta[i]), 4), 'fold_y', fold_y,
      'iou2', round(iou2, 6), 'iou5', round(iou5, 6))
print('layers', len(summary['layers_within_25mm_new']))
for L in summary['layers_within_25mm_new']:
    print(' ', L)
print('grid neighbours', summary['mesh_grid_neighbours'])
