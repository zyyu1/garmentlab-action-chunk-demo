import json,hashlib,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
base=Path(__file__).resolve().parent;out=base/'results/day4-minimum-half-fold-20261031-062447-146263'
r=json.loads((out/'result.json').read_text());manifest=json.loads((out/'source/manifest.json').read_text());checks={n:hashlib.sha256((out/'source'/n).read_bytes()).hexdigest()==h for n,h in manifest.items()};assert all(checks.values())
p=dict(np.load(out/'fold_definition.npz'));d=np.load(out/'99_failure.npz');act=np.load(out/'activation_hem.npz');ids=d['anchors_2'];assert ids.tolist()==[1547]
# Archived AttachmentBlock.create uses scale=[.03,.03,.03]. Verify before reconstructing.
source=(out/'runtime_source/original_control.py').read_text();assert 'scale=np.array([0.03, 0.03, 0.03])' in source
pos=d['block_position_2'].reshape(3);q=d['block_quaternion_2'].reshape(4);desired=Rotation.from_quat(q[[1,2,3,0]]).apply(act['points1']*.03)+pos
gap=float(np.linalg.norm(d['vertices'][ids]-desired,axis=1).max())
v=np.load(out/'postcross_trace.npz')['vertices'];labels=json.loads((out/'postcross_trace_labels.json').read_text());steps=np.array([x['step'] for x in labels]);assert len(v)==len(labels)==r['postcross_trace_frames'] and np.isfinite(v).all() and np.all(np.diff(steps)==1)
sys.path.insert(0,str(base/'.analysis-deps'));import imageio_ffmpeg
reader=imageio_ffmpeg.read_frames(str(out/'episode.mp4'),pix_fmt='rgb24');next(reader);count=sum(1 for _ in reader);assert count==r['video_frames']
mask=p['source_mask'];a={'version':r['probe_version'],'source_hash_checks':checks,'trace_frames':len(v),'trace_first_last_step':[int(steps[0]),int(steps[-1])],'last_phase':labels[-1]['phase'],'decoded_video_frames':count,'completed_actions':len(r['actions']),'pending_action':r.get('pending_action'),'errors':r['errors'],'failure_gap_mm':gap*1000,'gap_reconstruction':'activation points1, failure block pose, archived block scale .03; same constraint frame; no further steps after exception','anchor_ids':ids.tolist(),'failure_status':json.loads((out/'99_failure.json').read_text())['status'],'source_crossed_fraction_at_failure':float(np.mean(d['vertices'][mask,1]>float(p['fold_line_y']))),'release_completed':any(x['label']=='hem_release' for x in r['actions']),'formal_success':False}
(out/'independent_audit.json').write_text(json.dumps(a,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in a.items() if k!='source_hash_checks'},indent=2))
