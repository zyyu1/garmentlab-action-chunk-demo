"""Offline audit of the three requested overhang=0.02 L1 development runs."""
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
ap.add_argument('batch', type=Path)
args = ap.parse_args()
batch = json.loads((args.batch / 'batch.json').read_text(encoding='utf-8'))
cases = [r for r in batch['cases'] if r.get('status') == 'download_verified']
if not cases:
    raise ValueError('No completed, downloaded cases')
fig, axes = plt.subplots(len(cases), 3, figsize=(13, 4*len(cases)), squeeze=False)
audit = []
phases = ['03_hold_end', '04_released', '05_release_stationary', '06_final_3s']
for i, case in enumerate(cases):
    directory = Path(case['local_dir'])
    r = json.loads((directory / 'result.json').read_text(encoding='utf-8'))
    snapshots = {}
    for phase in ['00_initial'] + phases:
        with np.load(directory / (phase + '.npz')) as d:
            snapshots[phase] = np.asarray(d['vertices'], dtype=float)
    with np.load(directory / 'cloth_constructed.npz') as d:
        local = np.asarray(d['points'], dtype=float)
    fd = r['fold_definition']
    yaw, width, index = r['fold_yaw'], fd['fold_width_m'], fd['pick_index']
    rotation = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
    initial = snapshots['00_initial']
    pick = initial[index]
    moving = local[:, 0] < local[index, 0] + width
    metrics = {}
    for phase in phases:
        v = snapshots[phase]
        q = (v-pick) @ rotation
        a, b = v[moving, :2], v[~moving, :2]
        distances = np.r_[cKDTree(b).query(a)[0], cKDTree(a).query(b)[0]]
        metrics[phase] = {
            'crossed_fraction': float(np.mean(q[moving, 0] > width)),
            'symmetric_alignment_m': float(distances.mean()),
            'z_p95_m': float(np.percentile(v[:, 2], 95)),
            'world_extent_m': np.ptp(v, axis=0).tolist(),
            'cloth_frame_extent_m': np.ptp(q, axis=0).tolist(),
        }
    final = snapshots['06_final_3s']
    delta = np.linalg.norm(final - snapshots['05_release_stationary'], axis=1)
    hold = [json.loads(line) for line in (directory/'hold_trace.jsonl').read_text().splitlines()]
    checks = {
        'seed_matches_requested': r['initial_case']['seed'] == case['seed'],
        'overhang_is_002': abs(fd['fold_overhang_m']-.02)<1e-12,
        'finite_441_vertices_all_phases': all(v.shape == (441, 3) and np.isfinite(v).all() for v in snapshots.values()),
        'seven_public_actions': len(r['actions']) == r['action_count'] == 7,
        'all_action_state_checks': all(all(a['checks'].values()) for a in r['actions']),
        'release_unattached': not r['actions'][-1]['attached'] and not r['actions'][-1]['holding'] and r['actions'][-1]['command']==0,
        'held_gate': bool(r['held_check']['accepted']),
        'hold_has_60_samples': len(hold)==60,
        'hold_attached_throughout': all(x['holding'] and x['attachment_enabled'] for x in hold),
        'crossed_matches_report': bool(np.isclose(metrics['06_final_3s']['crossed_fraction'], r['fold_metrics']['moving_half_crossed_fraction'],atol=1e-10)),
        'alignment_matches_report': bool(np.isclose(metrics['06_final_3s']['symmetric_alignment_m'], r['fold_metrics']['symmetric_xy_alignment_mean_m'],atol=1e-9)),
        'height_matches_report': bool(np.isclose(metrics['06_final_3s']['z_p95_m'], r['fold_metrics']['cloth_z_p95_m'],atol=1e-9)),
    }
    row = {'seed':case['seed'],'run':directory.name,'passed':r['passed'],'errors':r['errors'],
           'checks':checks,'action_count':r['action_count'],'yaw_rad':yaw,
           'reported_iou':r['fold_metrics']['particle_occupancy_iou'], 'phases':metrics,
           'stationary_to_final_displacement_mean_m':float(delta.mean()),
           'stationary_to_final_displacement_max_m':float(delta.max()),
           'scope':'Development only; no independent retreat or post-3s retention sample; geometric proxies, not material-quality certification.',
           'formal_success':False}
    audit.append(row)
    for j, phase in enumerate(['04_released','06_final_3s']):
        q=(snapshots[phase]-pick) @ rotation
        ax=axes[i,j]
        ax.scatter(q[~moving,0],q[~moving,1],s=10,c='#3974b6',label='Stationary half')
        ax.scatter(q[moving,0],q[moving,1],s=10,c='#dc732f',label='Moving half')
        ax.axvline(width,color='black',linestyle='--',linewidth=1)
        ax.set_aspect('equal');ax.set(xlabel='Cloth-frame x (m)',ylabel='Cloth-frame y (m)',title=f"{case['seed']}: {phase}")
        ax.legend(fontsize=8)
    q=(final-pick) @ rotation
    ax=axes[i,2]
    ax.scatter(q[~moving,0],final[~moving,2],s=10,c='#3974b6')
    ax.scatter(q[moving,0],final[moving,2],s=10,c='#dc732f')
    ax.set(xlabel='Cloth-frame x (m)',ylabel='World z (m)',title=f"crossed={metrics['06_final_3s']['crossed_fraction']:.3f}, IoU={row['reported_iou']:.3f}",ylim=(0,.10))
fig.suptitle('L1: requested overhang 0.02 m development runs')
fig.tight_layout(rect=(0,0,1,.97))
fig.savefig(args.batch/'l1_overhang_comparison.png',dpi=170)
plt.close(fig)
(args.batch/'independent_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
lines=['# L1 overhang 0.02: remaining three requested cases','','Development runs only. Full downloads were verified against remote SHA256 before each next run.','',
       '| Seed | Run | Runner passed | Actions | Crossed | Alignment (mm) | IoU proxy | zP95 (mm) | Checks |',
       '|---|---|---|---:|---:|---:|---:|---:|---|']
for row in audit:
    m=row['phases']['06_final_3s']
    lines.append(f"| {row['seed']} | {row['run']} | {row['passed']} | {row['action_count']} | {m['crossed_fraction']:.3f} | {m['symmetric_alignment_m']*1000:.3f} | {row['reported_iou']:.3f} | {m['z_p95_m']*1000:.3f} | {all(row['checks'].values())} |")
lines+=['','Snapshots cover hold end, release, 30 release ticks, and 180 settle steps. No separate retreat or later retention snapshot. This review does not freeze an acceptance threshold or count formal successes.','']
(args.batch/'review.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(audit,indent=2))
