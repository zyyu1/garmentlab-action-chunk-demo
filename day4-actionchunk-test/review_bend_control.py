import sys,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
base=Path(__file__).resolve().parent
out=base/'results/day4-minimum-half-fold-20261031-065311-595489'
old=base/'results/day4-minimum-half-fold-20261031-060323-618705'
r=json.loads((out/'result.json').read_text());prior=json.loads((old/'result.json').read_text())
p=dict(np.load(out/'fold_definition.npz'));initial=p['initial_vertices'];mask=p['source_mask'];band=np.abs(initial[:,1]-float(p['fold_line_y']))<.01
v=np.load(out/'postcross_trace.npz')['vertices'];labels=json.loads((out/'postcross_trace_labels.json').read_text());steps=np.array([x['step'] for x in labels])
assert len(v)==len(labels)==r['postcross_trace_frames'] and np.all(np.diff(steps)==1) and np.isfinite(v).all()
hashes={n:hashlib.sha256((out/'source'/n).read_bytes()).hexdigest()==h for n,h in json.loads((out/'source/manifest.json').read_text()).items()};assert all(hashes.values())
common={f.stem:bool(np.array_equal(np.load(f)['vertices'],np.load(out/f.name)['vertices'])) for f in old.glob('*.npz') if f.name[:2].isdigit() and (out/f.name).exists()}
actions_equal=[(a['label'],a['matrix']) for a in r['actions']]==[(a['label'],a['matrix']) for a in prior['actions']]
def metrics(x):
 return {'fixed_centroid_dy_mm':float((x[~mask,1]-initial[~mask,1]).mean()*1000),'fold_band_y_mm':float(x[band,1].mean()*1000),'fold_band_z_mm':float(x[band,2].mean()*1000),'source_z_median_mm':float(np.median(x[mask,2])*1000)}
rows=[]
for name in ['04_cross_line','04b_arrived_before_hold','05_original_place','06_supported_place','11_retention_4s']:
 rows.append({'stage':name,**metrics(np.load(out/(name+'.npz'))['vertices'])})
phases=[]
for name in dict.fromkeys(x['phase'] for x in labels):
 ix=[i for i,x in enumerate(labels) if x['phase']==name]
 phases.append({'phase':name,'first_step':int(steps[ix[0]]),'last_step':int(steps[ix[-1]]),'frames':len(ix),'end':metrics(v[ix[-1]])})
sys.path.insert(0,str(base/'.analysis-deps'));import imageio_ffmpeg
reader=imageio_ffmpeg.read_frames(str(out/'episode.mp4'),pix_fmt='rgb24');next(reader);count=sum(1 for _ in reader);assert count==r['video_frames']
audit={'version':r['probe_version'],'frames':len(v),'contiguous_steps':True,'finite_vertices':True,'hashes':hashes,'common_snapshots_exact':common,'actions_exact':actions_equal,'decoded_video_frames':count,'public_actions':len(r['actions']),'stages':rows,'phase_endpoints':phases,'formal_success':False}
(out/'independent_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
series=np.array([[metrics(x)[k] for k in ['fixed_centroid_dy_mm','fold_band_z_mm']] for x in v]);hold=next(i for i,x in enumerate(labels) if x['phase']=='original_place_hold_60')
fig,axs=plt.subplots(1,2,figsize=(11,4))
for i,ax in enumerate(axs):
 ax.plot(steps,series[:,i]);ax.axvline(steps[hold],color='red',linestyle='--',label='60-step hold begins');ax.set(xlabel='simulation step',ylabel=['fixed-half centroid y displacement (mm)','fold-band mean z (mm)'][i]);ax.legend()
fig.tight_layout();fig.savefig(out/'postcross_timing.png',dpi=150);plt.close(fig)
print(json.dumps({k:audit[k] for k in ['frames','common_snapshots_exact','actions_exact','decoded_video_frames','public_actions','stages','phase_endpoints']},indent=2))

assert r['requested_bend']==100 and r['constructor_bend_applied']==100
assert actions_equal and all(common.values())
a=np.load(out/'runtime_spring_stiffness_after_start.npy');z=np.load(out/'runtime_spring_stiffness_after_half_fold.npy')
assert a.shape==(1,58160) and np.isfinite(a).all() and np.array_equal(a,z)
values,counts=np.unique(a,return_counts=True)
summary={'requested_bend':100,'all_common_snapshots_exact_to_v5':all(common.values()),'actions_exact_to_v5':actions_equal,'spring_arrays_unchanged':True,'spring_value_counts':dict(zip(map(str,values.tolist()),map(int,counts))),'baseline_valid':True,'fold_success':False}
(out/'bend_control_audit.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('BEND_CONTROL_AUDIT',summary)
