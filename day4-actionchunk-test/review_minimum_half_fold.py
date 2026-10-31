import sys,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from minimum_fold_geometry import support_summary
from hem_fold_geometry import hem_metrics
base=Path(__file__).resolve().parent
out=base/'results/day4-minimum-half-fold-20261031-043028-240166'
r=json.loads((out/'result.json').read_text())
plan=dict(np.load(out/'fold_definition.npz'));initial=plan['initial_vertices'];mask=plan['source_mask'];pick=int(plan['pick_index'])
sel=json.loads((out/'terminal_placement.json').read_text());goal=np.array(sel['material_target_xyz'])
a=np.load(out/'05_original_place.npz')['vertices']
patch=np.flatnonzero((~mask)&(np.linalg.norm(a[:,:2]-goal[:2],axis=1)<.015))
stages=['05_original_place','06_supported_place','07_released','08_release_stationary','09_retreated','10_final_3s','11_retention_4s']
rows=[]
fig,axs=plt.subplots(2,4,figsize=(15,7))
for ax,n in zip(axs.flat,stages):
 v=np.load(out/(n+'.npz'))['vertices'];s=support_summary(v,mask,pick);m=hem_metrics(initial,v,plan)
 status=json.loads((out/(n+'.json')).read_text())['status']
 rows.append(dict(stage=n,support=s,metrics=m,pick_xyz=v[pick].tolist(),
  selected_patch_centroid_displacement_m=(v[patch]-a[patch]).mean(axis=0).tolist(),
  fixed_centroid_displacement_m=(v[~mask]-initial[~mask]).mean(axis=0).tolist(),status=status))
 ax.scatter(v[~mask,1],v[~mask,2],s=1,c='steelblue');ax.scatter(v[mask,1],v[mask,2],s=1,c='orange')
 ax.scatter(v[pick,1],v[pick,2],s=20,c='red');ax.set(xlim=(-.9,-.1),ylim=(0,.18),title=n,xlabel='world y (m)',ylabel='z (m)')
axs.flat[-1].axis('off');fig.tight_layout();fig.savefig(out/'material_side_views.png',dpi=140);plt.close(fig)
h=np.load(out/'terminal_hold_trace.npz');speeds=np.linalg.norm(np.diff(h['vertices'][-31:,mask],axis=0),axis=2)/float(h['dt'])
manifest=json.loads((out/'source/manifest.json').read_text())
checks={n:hashlib.sha256((out/'source'/n).read_bytes()).hexdigest()==digest for n,digest in manifest.items()}
assert all(checks.values())
sys.path.insert(0,str(base/'.analysis-deps'))
import imageio_ffmpeg
reader=imageio_ffmpeg.read_frames(str(out/'episode.mp4'),pix_fmt='rgb24');meta=next(reader);count=sum(1 for _ in reader)
assert count==r['video_frames']
audit=dict(stages=rows,selected_patch_count=len(patch),source_hash_checks=checks,decoded_video_frames=count,
 pre_release_speed_p50_p95_p99_max=np.percentile(speeds,[50,95,99,100]).tolist(),
 material_goal_error_m=float(np.linalg.norm(np.array(rows[1]['pick_xyz'])-goal)),
 pick_release_recoil_xy_m=float(np.linalg.norm(np.array(rows[-1]['pick_xyz'])[:2]-np.array(rows[1]['pick_xyz'])[:2])),
 public_action_count=r['public_action_count'],formal_success=False)
(out/'independent_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
for row in rows:print(row['stage'],'near layer',round(row['support']['source_near_layer_xy10mm_z0to30mm_fraction'],3),'cross',round(row['metrics']['moving_half_crossed_fraction'],3),'patch drift mm',np.round(np.array(row['selected_patch_centroid_displacement_m'])*1000,2))
print({k:v for k,v in audit.items() if k not in ['stages','source_hash_checks']})
