import sys,json,hashlib
from pathlib import Path
import numpy as np
from minimum_fold_geometry import support_summary
base=Path(__file__).resolve().parent
out=base/'results/day4-minimum-half-fold-20261031-070836-491946'
control=base/'results/day4-minimum-half-fold-20261031-065311-595489'
r=json.loads((out/'result.json').read_text());a=json.loads((control/'result.json').read_text())
print('READBACK',{k:v for k,v in r.items() if 'bend' in k or 'spring' in k})
hashes={n:hashlib.sha256((out/'source'/n).read_bytes()).hexdigest()==h for n,h in json.loads((out/'source/manifest.json').read_text()).items()};assert all(hashes.values())
assert r['requested_bend']==r['constructor_bend_applied']==10
s=np.load(out/'runtime_spring_stiffness_after_start.npy');end=np.load(out/'runtime_spring_stiffness_after_half_fold.npy');sa=np.load(control/'runtime_spring_stiffness_after_start.npy')
assert np.isfinite(s).all() and np.array_equal(s,end) and s.shape==sa.shape
v=np.load(out/'postcross_trace.npz')['vertices'];labels=json.loads((out/'postcross_trace_labels.json').read_text());assert len(v)==len(labels)==r['postcross_trace_frames'] and np.isfinite(v).all() and np.all(np.diff([x['step'] for x in labels])==1)
sys.path.insert(0,str(base/'.analysis-deps'));import imageio_ffmpeg
reader=imageio_ffmpeg.read_frames(str(out/'episode.mp4'),pix_fmt='rgb24');next(reader);n=sum(1 for _ in reader);assert n==r['video_frames']
rows={}
for key,d in [('100',control),('10',out)]:
 rr=json.loads((d/'result.json').read_text());p=dict(np.load(d/'fold_definition.npz'));mask=p['source_mask'];pick=int(p['pick_index']);stages={}
 for name in ['00_initial','06_supported_place','08_release_stationary','11_retention_4s']:
  x=np.load(d/(name+'.npz'))['vertices'];stages[name]={'pick':x[pick].tolist(),'support':support_summary(x,mask,pick)}
 h=np.load(d/'terminal_hold_trace.npz');speed=np.linalg.norm(np.diff(h['vertices'][-31:,mask],axis=0),axis=2)/float(h['dt'])
 rows[key]={'stages':stages,'source_speed_p95_m_s':float(np.percentile(speed,95)),'recoil_mm':float(np.linalg.norm(np.array(stages['08_release_stationary']['pick'])[:2]-np.array(stages['06_supported_place']['pick'])[:2])*1000),'retention_metrics':rr['retention_metrics'],'lifecycle_checks':rr['lifecycle_checks'],'errors':rr['errors'],'public_actions':len(rr['actions'])}
initial_delta=np.linalg.norm(np.load(out/'00_initial.npz')['vertices']-np.load(control/'00_initial.npz')['vertices'],axis=1)
u,c=np.unique(s,return_counts=True)
result={'hashes':hashes,'decoded_video_frames':n,'trace_frames':len(v),'spring_values':dict(zip(map(str,u.tolist()),map(int,c))),'spring_changed_count':int(np.count_nonzero(s!=sa)),'spring_transitions':[{'from':float(x),'to':float(y),'count':int(np.count_nonzero((sa==x)&(s==y)))} for x,y in np.unique(np.stack([sa.ravel(),s.ravel()],axis=1),axis=0)],'spring_unchanged_during_run':True,'initial_displacement_mean_max_mm':[float(initial_delta.mean()*1000),float(initial_delta.max()*1000)],'action_labels_equal':[x['label'] for x in r['actions']]==[x['label'] for x in a['actions']],'source_manifest_same':json.loads((out/'source/manifest.json').read_text())==json.loads((control/'source/manifest.json').read_text()),'groups':rows,'formal_success':False}
(out/'bend_pair_audit.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
