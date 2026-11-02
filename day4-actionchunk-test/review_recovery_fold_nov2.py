"""Independent offline recovery/fold review; no acceptance thresholds are frozen here."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree

ap = argparse.ArgumentParser()
ap.add_argument('--root', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('runs', nargs='+')
args = ap.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
rows = []
fig, axes = plt.subplots(len(args.runs), 3, figsize=(13, 4 * len(args.runs)), squeeze=False)
for row_number, name in enumerate(args.runs):
    directory = args.root / name
    r = json.loads((directory / 'result.json').read_text(encoding='utf-8'))
    initial = args.root / Path(r['initial_dir']).name
    with np.load(initial / 'initial_geometry.npz') as d:
        flat = np.asarray(d['flat_settled'], dtype=float)
    with np.load(directory / 'recovered.npz') as d:
        recovered = np.asarray(d['vertices'], dtype=float)
    with np.load(directory / 'final.npz') as d:
        final = np.asarray(d['vertices'], dtype=float)
    with np.load(directory / 'cloth_constructed.npz') as d:
        local = np.asarray(d['points'], dtype=float)
    target = next(x for x in r['records'] if x['label'] == 'fold_targets')
    pick = np.asarray(target['pick_world'], dtype=float)
    edge = r['fold_edge']
    index = target['pick_index']
    width = target['width_m']
    moving = local[:, 0] < local[index, 0] + width if edge == 'left' else local[:, 0] > local[index, 0] - width
    yaw = r['fold_yaw']
    rotation = np.array([[np.cos(yaw), -np.sin(yaw)], [np.sin(yaw), np.cos(yaw)]])
    final_xy = (final[:, :2] - pick[:2]) @ rotation
    recovered_xy = (recovered[:, :2] - pick[:2]) @ rotation
    sign = 1 if edge == 'left' else -1
    crossed = float(np.mean(final_xy[moving, 0] * sign > width))
    a = flat[:, :2] - flat[:, :2].mean(0)
    b = recovered[:, :2] - recovered[:, :2].mean(0)
    u, _, vt = np.linalg.svd(a.T @ b)
    fit = vt.T @ u.T
    if np.linalg.det(fit) < 0:
        vt[-1] *= -1
        fit = vt.T @ u.T
    residual = np.linalg.norm(a @ fit.T - b, axis=1)
    moving_xy, fixed_xy = final[moving, :2], final[~moving, :2]
    distance = cKDTree(fixed_xy).query(moving_xy)[0]
    grid_a = set(map(tuple, np.floor(moving_xy / .01).astype(int)))
    grid_b = set(map(tuple, np.floor(fixed_xy / .01).astype(int)))
    # Fixed grid origin, no dilation; diagnostic only, not the frozen evaluator.
    iou = len(grid_a & grid_b) / len(grid_a | grid_b)
    actions = r['actions']
    held = r.get('fold_held_check', {})
    hold_rows = [json.loads(line) for line in (directory / 'fold_hold' / 'hold_trace.jsonl').read_text().splitlines()]
    checks = {
        'finite_441_vertices': final.shape == recovered.shape == (441, 3) and bool(np.isfinite(final).all() and np.isfinite(recovered).all()),
        '12_logged_actions': len(actions) == r.get('action_count') == 12,
        'all_action_checks': all(all(x['checks'].values()) for x in actions),
        'all_single_public_rows': all(x['response']['executed_steps'] == 1 for x in actions),
        'release_record_unattached': not actions[-1]['attached'] and not actions[-1]['holding'] and actions[-1]['command'] == 0,
        'held_gate': bool(held.get('accepted')),
        '60_hold_samples': len(hold_rows) == 60 and [x['hold_step'] for x in hold_rows] == list(range(1, 61)),
        'hold_attached_throughout': all(x['holding'] and x['attachment_enabled'] for x in hold_rows),
        'reported_crossed_matches': bool(np.isclose(crossed, r['fold_metrics']['crossed_fraction'], atol=1e-12)),
        'reported_extent_matches': bool(np.allclose(np.ptp(final, axis=0), r['fold_metrics']['extent'], atol=1e-12)),
        'reported_height_matches': bool(np.isclose(np.percentile(final[:, 2], 95), r['fold_metrics']['z_p95'], atol=1e-12)),
        # Saved live arrays are float32; this audit centers/fits in float64.
        # Allow 0.5 micrometers for the arithmetic difference (not a task gate).
        'reported_recovery_matches_float32_tolerance': bool(np.isclose(residual.max(), r['recovery_metrics']['rigid_residual_vs_flat_max_m'], atol=5e-7, rtol=0)),
    }
    summary = {
        'run': name, 'seed': r['initial_case']['seed'], 'edge': edge,
        'script_passed': r['passed'], 'errors': r['errors'], 'checks': checks,
        'action_count': len(actions), 'recovery_actions': sum(x['label'].startswith('rec_') for x in actions),
        'fold_actions': sum(x['label'].startswith('fold_') for x in actions),
        'crossed_fraction': crossed, 'world_extent_m': np.ptp(final, axis=0).tolist(),
        'cloth_frame_extent_m': np.ptp(final_xy, axis=0).tolist(),
        'z_p95_m': float(np.percentile(final[:, 2], 95)), 'recovery_residual_max_m': float(residual.max()),
        'hold_ee_drift_max_m': float(np.linalg.norm(np.array([x['ee_position'] for x in hold_rows]) - np.array(hold_rows[0]['ee_position']), axis=1).max()),
        'hold_anchor_gap_max_m': float(max(x['anchor_gap_max_m'] for x in hold_rows)),
        'moving_to_fixed_xy_mean_m': float(distance.mean()), 'moving_to_fixed_xy_p95_m': float(np.percentile(distance, 95)),
        'particle_grid_iou_10mm_no_dilation_diagnostic': iou,
        'final_image_present': (directory / 'final.png').exists(),
        'measurement': '180 settle steps after OPEN and 30 release ticks; no separate retreat or second retention snapshot',
        'formal_success': None,
        'file_sha256': {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file()},
    }
    rows.append(summary)
    for ax, xy, title in zip(axes[row_number, :2], (recovered_xy, final_xy), ('Recovered', 'Released + settled')):
        ax.scatter(xy[~moving, 0], xy[~moving, 1], s=9, c='#3974b6', label='Fixed half')
        ax.scatter(xy[moving, 0], xy[moving, 1], s=9, c='#dc732f', label='Moving half')
        ax.axvline(sign * width, color='black', linestyle='--', linewidth=1)
        ax.set_aspect('equal')
        ax.set(xlabel='Cloth-frame x (m)', ylabel='Cloth-frame y (m)', title=f"{r['initial_case']['seed']} {edge}: {title}")
        ax.legend(fontsize=8)
    ax = axes[row_number, 2]
    ax.scatter(final_xy[~moving, 0], final[~moving, 2], s=9, c='#3974b6')
    ax.scatter(final_xy[moving, 0], final[moving, 2], s=9, c='#dc732f')
    ax.set(xlabel='Cloth-frame x (m)', ylabel='World z (m)', title=f'crossed={crossed:.3f}, zP95={summary["z_p95_m"]:.4f} m')
    ax.set_ylim(0, .10)
fig.suptitle('Recovery + half-fold: independent geometric review (development runs)', fontsize=14)
fig.tight_layout(rect=(0, 0, 1, .97))
fig.savefig(args.output / 'recovery_fold_comparison.png', dpi=170)
plt.close(fig)
(args.output / 'audit.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
lines = ['# Recovery + half-fold review', '', 'Development runs only; no frozen formal success classification.', '',
         '| Run | Seed/edge | Actions | Crossed | Extent XY (m) | zP95 (m) | All checks |',
         '|---|---|---:|---:|---|---:|---|']
for row in rows:
    lines.append(f'| {row["run"]} | {row["seed"]}/{row["edge"]} | {row["action_count"]} | {row["crossed_fraction"]:.3f} | {row["world_extent_m"][:2]} | {row["z_p95_m"]:.5f} | {all(row["checks"].values())} |')
lines += ['', 'Final sampling follows OPEN, 30 release ticks and 180 settle steps. These runs do not include a separate retreat or a second retention sample. Geometric overlap is a diagnostic proxy, not certified triangle overlap or material quality.', '', 'See audit.json for all checks, file hashes and failure reasons.']
(args.output / 'review.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(json.dumps([{k: v for k, v in row.items() if k != 'file_sha256'} for row in rows], indent=2))
