"""Audit the complete lift plus target-hold trace; distinguish motion from hold."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import TwoSlopeNorm
from scipy.spatial.transform import Rotation

BASE=Path(__file__).resolve().parent/'results'
RUN=BASE/'day4-aligned-lift-hold-20261024-230123-728994'
OLD=BASE/'day4-aligned-lift-step-20261024-223712-756159'
OUT=RUN/'analysis';OUT.mkdir(exist_ok=True)
def load(path):
    with np.load(path,allow_pickle=False) as f:return {k:f[k].copy() for k in f.files}
def hashes(folder):
    m=json.loads((folder/'manifest.json').read_text())
    checks={k:hashlib.sha256((folder/k).read_bytes()).hexdigest()==item['sha256'] for k,item in m.items()}
    assert all(checks.values());return checks,m
r=json.loads((RUN/'result.json').read_text())
s=json.loads((RUN/'lift_hold_trace/summary.json').read_text())
assert r['passed'] is True and s['capture_complete'] is True and r['lift_hold_trace']==s
assert all(r['original_lift_trace_exact_checks'].values()) and all(r['reference_replay_exact_checks'].values())
src_checks,manifest=hashes(RUN/'source');ref_checks,_=hashes(RUN/'reference')
assert len(src_checks)==13 and len(ref_checks)==5
old_manifest=json.loads((OLD/'source/manifest.json').read_text())
assert all(manifest[k]['sha256']==entry['sha256'] for k,entry in old_manifest.items() if k!='test.py')
f=load(RUN/'lift_hold_trace/frames.npz');old=load(OLD/'lift_trace/frames.npz')
assert all(np.isfinite(v).all() for v in f.values())
assert f['vertices'].shape==(230,9945,3)
h=int(f['hold_start_frame']);assert h==49 and int(f['expected_hold_steps'])==180
assert np.array_equal(f['physics_steps'],np.arange(508,738))
assert np.array_equal(f['phase_code'],np.r_[np.zeros(50,dtype=int),np.ones(180,dtype=int)])
prefix_keys=['vertices','block_position','block_quaternion','block_scale','ee_position','ee_quaternion','anchor_targets','physics_steps','elapsed_sim_seconds']
for k in prefix_keys:assert np.array_equal(f[k][:50],old[k]),k
for k in ['edges','anchor_indices','edge_anchor_endpoint_count','rest_edge_lengths','lift_start_edge_lengths','lift_ee_target','points0','points1','tracked_indices']:
    assert np.array_equal(f[k],old[k]),k
for name in ['00_settled','01_approach','01b_before_close','02_grasp','03_lift']:
    a,b=load(RUN/(name+'.npz')),load(OLD/(name+'.npz'))
    assert all(np.array_equal(v,b[k]) for k,v in a.items())
old_result=json.loads((OLD/'result.json').read_text())
assert [a['horizon'] for a in r['action_audit']]==[1,1,4,1,1,1]
for i,a in enumerate(r['action_audit']):
    assert len(a['checks'])==8 and all(a['checks'].values())
    if i<5:assert a['matrix']==old_result['action_audit'][i]['matrix'] and a['physics_steps']==old_result['action_audit'][i]['physics_steps']
v=f['vertices'];e=f['edges'];ids=f['anchor_indices'];cls=f['edge_anchor_endpoint_count']
dt=float(s['physics_dt']);assert np.isclose(dt,1/60)
t=f['elapsed_sim_seconds'];assert np.allclose(t,np.arange(230)*dt)
ht=t-t[h]
lengths=np.linalg.norm(v[:,e[:,1]]-v[:,e[:,0]],axis=2)
ratios=lengths/f['rest_edge_lengths'];start_ratios=lengths/f['lift_start_edge_lengths']
assert np.array_equal(cls,np.isin(e,ids).sum(axis=1))
for key in ['block_quaternion','ee_quaternion']:assert np.allclose(np.linalg.norm(f[key],axis=1),1,atol=1e-4)
targets=np.stack([Rotation.from_quat(q[[1,2,3,0]]).apply(f['points1']*scale)+pos
                  for q,scale,pos in zip(f['block_quaternion'],f['block_scale'],f['block_position'])])
assert np.allclose(targets,f['anchor_targets'],atol=1e-10)
gaps=np.linalg.norm(v[:,ids]-targets,axis=2)*1000
ee=f['ee_position'];bp=f['block_position']
ee_speed=np.r_[0,np.linalg.norm(np.diff(ee,axis=0),axis=1)/dt]
block_speed=np.r_[0,np.linalg.norm(np.diff(bp,axis=0),axis=1)/dt]
particle_delta=np.linalg.norm(np.diff(v,axis=0),axis=2)*1000
max_delta=np.r_[0,particle_delta.max(axis=1)]
q=f['ee_quaternion']
block_targets=ee+Rotation.from_quat(q[:,[1,2,3,0]]).apply(np.tile([0,0,-.01],(230,1)))
follow=np.linalg.norm(block_targets-bp,axis=1)*1000
local=cls>0;class_max={c:ratios[:,cls==c].max(axis=1) for c in [0,1,2]}
global_arg=ratios.argmax(axis=1);local_indices=np.flatnonzero(local)
with (RUN/'lift_hold_trace/steps.csv').open(encoding='utf-8',newline='') as stream:rows=list(csv.DictReader(stream))
assert len(rows)==230
for i,row in enumerate(rows):
    assert row['phase']==('lift' if i<=h else 'hold') and int(row['physics_step'])==508+i
    expected={'elapsed_sim_seconds':t[i],'ee_speed_m_s':ee_speed[i],'block_speed_m_s':block_speed[i],
      'paired_gap_mean_mm':gaps[i].mean(),'paired_gap_max_mm':gaps[i].max(),
      'all_edge_ratio_max':ratios[i].max(),'anchor_edge_ratio_max':ratios[i,local].max(),
      'all_edge_ratio_p95':np.percentile(ratios[i],95),'all_edge_ratio_p99':np.percentile(ratios[i],99),
      'anchor_edge_ratio_p95':np.percentile(ratios[i,local],95),
      'all_edge_ratio_to_lift_start_max':start_ratios[i].max(),
      'anchor_edge_ratio_to_lift_start_max':start_ratios[i,local].max(),
      'ee_target_error_mm':np.linalg.norm(ee[i]-f['lift_ee_target'])*1000,
      'block_follow_error_mm':follow[i], 'max_vertex_displacement_mm':max_delta[i],
      'tracked_mean_z_mm':v[i,f['tracked_indices'],2].mean()*1000,
      'outside_edge_ratio_max':class_max[0][i],'boundary_edge_ratio_max':class_max[1][i],'internal_edge_ratio_max':class_max[2][i]}
    for k,value in expected.items():assert np.isclose(float(row[k]),value,rtol=1e-5,atol=2e-6),(i,k)
    assert int(row['all_worst_edge_index'])==global_arg[i]
    assert [int(row['all_worst_edge_u']),int(row['all_worst_edge_v'])]==e[global_arg[i]].tolist()
    local_arg=local_indices[ratios[i,local].argmax()]
    assert int(row['anchor_worst_edge_index'])==local_arg
assert np.allclose(np.diff([float(row['world_sim_time']) for row in rows]),dt,atol=1e-6)
for j,name in [(0,'02_grasp'),(h,'03_lift'),(-1,'03b_hold')]:
    d=load(RUN/'anchors'/(name+'.npz'))
    for k in ['vertices','ee_position','ee_quaternion','block_position','block_quaternion']:assert np.array_equal(f[k][j],d[k])
peak_frame,peak_edge=np.unravel_index(ratios.argmax(),ratios.shape)
assert peak_frame==s['global_peak']['frame'] and peak_edge==s['global_peak']['all_worst_edge_index']
assert cls[peak_edge]==1
tail=np.arange(200,230)
last_change=int(np.flatnonzero(np.linalg.norm(np.diff(bp,axis=0),axis=1)>0)[-1]+1)
hold_class_counts={str(c):int((cls[global_arg[h+1:]]==c).sum()) for c in [0,1,2]}
tracked_z=v[:,f['tracked_indices'],2].mean(axis=1)
audit={'run':RUN.name,'source_hash_checks':src_checks,'reference_hash_checks':ref_checks,
 'all_original_50_frames_exact':True,'all_recomputed_csv_metrics_match':True,'sample_count':230,
 'lift_frames':50,'hold_frames':180,'hold_seconds':3.,'phase_shared_frame':h,
 'peak':{'frame':int(peak_frame),'step':int(f['physics_steps'][peak_frame]),
   'hold_time_seconds':float(ht[peak_frame]),'edge_vertices':e[peak_edge].tolist(),
   'ratio_to_initial':float(ratios[peak_frame,peak_edge]),'length_mm':float(lengths[peak_frame,peak_edge]*1000),
   'initial_length_mm':float(f['rest_edge_lengths'][peak_edge]*1000)},
 'hold_start':{'max_edge_ratio':float(ratios[h].max()),'ee_z_m':float(ee[h,2])},
 'hold_end':{'max_edge_ratio':float(ratios[-1].max()),'peak_edge_ratio':float(ratios[-1,peak_edge]),
   'ee_additional_rise_mm':float((ee[-1,2]-ee[h,2])*1000),
   'block_additional_rise_mm':float((bp[-1,2]-bp[h,2])*1000),
   'tracked_additional_rise_mm':float((tracked_z[-1]-tracked_z[h])*1000)},
 'late_30_frames':{'first_hold_time_s':float(ht[tail[0]]),'last_hold_time_s':float(ht[tail[-1]]),
   'ee_speed_max_mm_s':float(ee_speed[tail].max()*1000),'block_speed_max_mm_s':float(block_speed[tail].max()*1000),
   'max_edge_ratio_min':float(ratios[tail].max(axis=1).min()),'max_edge_ratio_max':float(ratios[tail].max(axis=1).max()),
   'global_particle_step_displacement_max_mm':float(particle_delta[-30:].max()),
   'global_particle_step_displacement_mean_mm':float(particle_delta[-30:].mean()),
   'global_particle_step_displacement_p95_mm':float(np.percentile(particle_delta[-30:],95))},
 'block_last_saved_position_change':{'frame':last_change,'hold_time_seconds':float(ht[last_change]),
   'unchanged_remaining_seconds':float(t[-1]-t[last_change]),'note':'Same saved float values do not guarantee physical immobility below storage precision.'},
 'hold_global_worst_edge_class_frame_counts':hold_class_counts,
 'gaps':{'max_during_hold_mm':float(gaps[h+1:].max()),'late_mean_min_mm':float(gaps[tail].mean(axis=1).min()),
   'late_mean_max_mm':float(gaps[tail].mean(axis=1).max())},
 'interpretation':'Extension remains elevated during late low rigid motion. Early hold includes additional target approach, so extra extension is not solely a waiting-time effect. Particle motion persists and equilibrium is not established.',
 'limits':['Fixed target does not mean instantly fixed measured EE pose.',
   'Ratios are geometric lengths, not stress or material-quality acceptance.',
   'No internal PhysX substep sampling, no proof of final equilibrium beyond this 3-second window.']}
(OUT/'lift_hold_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
with (OUT/'hold_phase_summary.csv').open('w',newline='',encoding='utf-8-sig') as stream:
    writer=csv.writer(stream);writer.writerow(['hold_time_seconds','physics_step','max_edge_ratio','ee_additional_z_mm','block_additional_z_mm','tracked_additional_z_mm','ee_speed_mm_s','block_speed_mm_s','paired_mean_gap_mm'])
    for i in range(h,230):writer.writerow([ht[i],f['physics_steps'][i],ratios[i].max(),(ee[i,2]-ee[h,2])*1000,(bp[i,2]-bp[h,2])*1000,(tracked_z[i]-tracked_z[h])*1000,ee_speed[i]*1000,block_speed[i]*1000,gaps[i].mean()])

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(3,2,figsize=(14,12),layout='constrained')
for c,label,color in [(1,'Boundary','#ce582f'),(2,'Internal','#2378b6'),(0,'Outside','#8d97a8')]:
    axs[0,0].plot(ht,class_max[c],label=label,color=color)
axs[0,0].scatter(ht[peak_frame],ratios[peak_frame,peak_edge],c='black',s=25)
axs[0,0].set(ylabel='Maximum edge length / initial length',title='Boundary extension remains high through target hold');axs[0,0].legend()
for values,label,color in [(ee[:,2],'Measured EE','#2378b6'),(bp[:,2],'Measured block','#008568'),(tracked_z,'Tracked cloth','#ce582f')]:
    axs[0,1].plot(ht,(values-values[h])*1000,label=label,color=color)
axs[0,1].set(ylabel='Vertical change from hold start (mm)',title='Early hold includes extra upward motion');axs[0,1].legend()
axs[1,0].plot(ht[1:],ee_speed[1:]*1000,label='EE',color='#2378b6')
axs[1,0].plot(ht[1:],block_speed[1:]*1000,label='Block',color='#008568')
axs[1,0].set(ylabel='Finite-difference speed (mm/s)',title='Whole lift + hold speed profile');axs[1,0].legend()
axs[1,1].plot(ht,gaps.mean(axis=1),label='Paired anchors: mean',color='#2378b6')
axs[1,1].plot(ht,gaps.max(axis=1),label='Paired anchors: max',color='#ce582f')
axs[1,1].set(ylabel='Paired geometric separation (mm)',title='Anchor gaps remain at millimetre scale');axs[1,1].legend()
axs[2,0].plot(ht[tail],ee_speed[tail]*1000,label='EE',color='#2378b6')
axs[2,0].plot(ht[tail],block_speed[tail]*1000,label='Block',color='#008568')
axs[2,0].set(ylabel='Finite-difference speed (mm/s)',title='Late 30-frame window: very low rigid motion');axs[2,0].legend()
axs[2,1].plot(ht[tail],ratios[tail].max(axis=1),'-o',ms=3,color='#ce582f')
axs[2,1].set(ylabel='Maximum edge length / initial length',title='Late window: fluctuation near 1.76x, no large relaxation')
for ax in axs.ravel():
    ax.set_xlabel('Simulation time relative to hold start (s)');ax.grid(alpha=.15)
    if ax in axs[:2,:].ravel():ax.axvline(0,c='black',ls='--',lw=.8)
fig.suptitle('Matched original lift followed by 3-second fixed-target hold\n230 samples; original 50-frame lift prefix is identical. Near-static rigid poses do not establish whole-cloth equilibrium.',fontsize=13)
fig.savefig(OUT/'lift_hold_motion_and_extension.png',dpi=180);plt.close(fig)

# Local boundary geometry at lift end, observed global maximum, and hold end.
adj=[[] for _ in range(9945)]
for a,b in e:adj[a].append(b);adj[b].append(a)
distance=np.full(9945,-1,dtype=int);distance[ids]=0
front=list(ids)
for depth in [1,2]:
    next_front=[]
    for a in front:
        for b in adj[a]:
            if distance[b]<0:distance[b]=depth;next_front.append(b)
    front=next_front
near=(distance[e]>=0).all(axis=1)
chosen=[h,int(peak_frame),229]
all_points=np.concatenate([v[i,np.unique(e[near])] for i in chosen])
fig,axs=plt.subplots(1,3,figsize=(14,6))
fig.subplots_adjust(top=.78,bottom=.14,wspace=.35)
for ax,i,title in zip(axs,chosen,['Lift end / hold start','Observed peak','Hold end']):
    p=v[i]
    lc=LineCollection(p[e[near]][:,:,[0,2]],cmap='coolwarm',norm=TwoSlopeNorm(vmin=.8,vcenter=1,vmax=1.8),linewidths=1.3)
    lc.set_array(ratios[i,near]);ax.add_collection(lc)
    ax.scatter(p[ids,0],p[ids,2],s=12,c='#008568')
    uv=e[peak_edge];ax.plot(p[uv,0],p[uv,2],lw=2.5,c='black')
    ax.set(xlim=(all_points[:,0].min()-.004,all_points[:,0].max()+.004),ylim=(all_points[:,2].min()-.004,all_points[:,2].max()+.004),xlabel='x (m)',ylabel='z (m)',title=title+'\nt=%.3f s; peak-edge ratio %.3fx'%(ht[i],ratios[i,peak_edge]))
    ax.set_aspect('equal');ax.locator_params(axis='x',nbins=3);ax.grid(alpha=.15)
fig.colorbar(lc,ax=axs.tolist(),label='3D edge length / initial length',shrink=.8)
fig.suptitle('Same anchor patch and boundary edge 8958-9025 across target hold\nGreen: mapped anchors; black: the peak boundary edge. XZ is only a position projection.',fontsize=13)
fig.savefig(OUT/'hold_boundary_geometry.png',dpi=180,bbox_inches='tight');plt.close(fig)
print('LIFT_HOLD_AUDIT_OK');print(json.dumps(audit,indent=2));print('OUTPUT',OUT)
