"""Audit every saved aligned-lift World.step and locate geometric edge peaks."""
from collections import Counter, deque
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
RUN=BASE/'day4-aligned-lift-step-20261024-223712-756159'
REFERENCE=BASE/'day4-anchor-pair-aligned-20261024-215858-281289'
OUT=RUN/'analysis';OUT.mkdir(exist_ok=True)
def load(path):
    with np.load(path,allow_pickle=False) as f:return {k:f[k].copy() for k in f.files}
def hash_check(folder):
    manifest=json.loads((folder/'manifest.json').read_text())
    checked={n:hashlib.sha256((folder/n).read_bytes()).hexdigest()==v['sha256'] for n,v in manifest.items()}
    assert all(checked.values())
    return checked
r=json.loads((RUN/'result.json').read_text())
summary=json.loads((RUN/'lift_trace/summary.json').read_text())
assert r['passed'] is True and summary['capture_complete'] is True and r['lift_trace']==summary
assert len(r['reference_replay_exact_checks'])==8 and all(r['reference_replay_exact_checks'].values())
source_hashes=hash_check(RUN/'source');reference_hashes=hash_check(RUN/'reference')
assert len(source_hashes)==12 and len(reference_hashes)==5
current_sources=json.loads((RUN/'source/manifest.json').read_text())
previous_sources=json.loads((REFERENCE/'source/manifest.json').read_text())
assert all(current_sources[k]['sha256']==entry['sha256'] for k,entry in previous_sources.items() if k!='test.py')
for name in ['00_settled','01_approach','01b_before_close','02_grasp','03_lift','04_release']:
    a,b=load(RUN/(name+'.npz')),load(REFERENCE/(name+'.npz'))
    assert all(np.array_equal(v,b[k]) for k,v in a.items())
previous=json.loads((REFERENCE/'result.json').read_text())
assert [a['horizon'] for a in r['action_audit']]==[1,1,4,1,1,1]
for a,b in zip(r['action_audit'],previous['action_audit']):
    assert a['matrix']==b['matrix'] and a['physics_steps']==b['physics_steps']
    assert len(a['checks'])==8 and all(a['checks'].values())
f=load(RUN/'lift_trace/frames.npz')
assert all(np.isfinite(x).all() for x in f.values())
v=f['vertices'];edges=f['edges'];steps=f['physics_steps'];t=f['elapsed_sim_seconds']
assert v.shape==(50,9945,3) and np.array_equal(steps,np.arange(508,558))
dt=summary['physics_dt'];assert np.isclose(dt,1/60)
assert np.allclose(t,np.arange(50)*dt) and r['action_audit'][4]['physics_steps']==49
for key in ['ee_quaternion','block_quaternion']:assert np.allclose(np.linalg.norm(f[key],axis=1),1,atol=1e-4)
ids=f['anchor_indices'];assert len(np.unique(ids))==28
rest=load(RUN/'reference/mesh_before_first_reset.npz')
assert np.array_equal(rest['points_local'][ids],f['points0'])
faces=rest['face_vertex_indices'].reshape(-1,3)
expected_edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
assert np.array_equal(edges,expected_edges) and len(edges)==29703
cls=np.isin(edges,ids).sum(axis=1);assert np.array_equal(cls,f['edge_anchor_endpoint_count'])
rest_lengths=np.linalg.norm(rest['points_world_usd'][edges[:,1]]-rest['points_world_usd'][edges[:,0]],axis=1)
assert np.allclose(rest_lengths,f['rest_edge_lengths']) and np.all(rest_lengths>1e-8)
lengths=np.linalg.norm(v[:,edges[:,1]]-v[:,edges[:,0]],axis=2)
assert np.array_equal(lengths[0],f['lift_start_edge_lengths'])
ratios=lengths/rest_lengths
start_ratios=lengths/lengths[0]
targets=np.empty_like(f['anchor_targets'])
for i in range(50):
    q=f['block_quaternion'][i]
    targets[i]=Rotation.from_quat(q[[1,2,3,0]]).apply(f['points1']*f['block_scale'][i])+f['block_position'][i]
assert np.allclose(targets,f['anchor_targets'],atol=1e-10)
gaps=np.linalg.norm(v[:,ids]-targets,axis=2)*1000
ee_speed=np.r_[0,np.linalg.norm(np.diff(f['ee_position'],axis=0),axis=1)/dt]
block_speed=np.r_[0,np.linalg.norm(np.diff(f['block_position'],axis=0),axis=1)/dt]
delta=np.r_[0,np.linalg.norm(np.diff(v,axis=0),axis=2).max(axis=1)*1000]
ee_error=np.linalg.norm(f['ee_position']-f['lift_ee_target'],axis=1)*1000
command_target=f['ee_position']+Rotation.from_quat(f['ee_quaternion'][:,[1,2,3,0]]).apply(np.tile([0,0,-.01],(50,1)))
follow_error=np.linalg.norm(command_target-f['block_position'],axis=1)*1000
local=cls>0
with (RUN/'lift_trace/steps.csv').open(encoding='utf-8',newline='') as stream:rows=list(csv.DictReader(stream))
assert len(rows)==50
class_max={c:ratios[:,cls==c].max(axis=1) for c in [0,1,2]}
global_arg=ratios.argmax(axis=1)
for i,row in enumerate(rows):
    assert int(row['physics_step'])==steps[i] and int(row['frame'])==i
    expected={'elapsed_sim_seconds':t[i],'ee_speed_m_s':ee_speed[i],'block_speed_m_s':block_speed[i],
      'paired_gap_mean_mm':gaps[i].mean(),'paired_gap_max_mm':gaps[i].max(),
      'all_edge_ratio_max':ratios[i].max(),'anchor_edge_ratio_max':ratios[i,local].max(),
      'all_edge_ratio_p95':np.percentile(ratios[i],95),'all_edge_ratio_p99':np.percentile(ratios[i],99),
      'anchor_edge_ratio_p95':np.percentile(ratios[i,local],95),
      'all_edge_ratio_to_lift_start_max':start_ratios[i].max(),
      'anchor_edge_ratio_to_lift_start_max':start_ratios[i,local].max(),
      'ee_target_error_mm':ee_error[i],'block_follow_error_mm':follow_error[i],
      'max_vertex_displacement_mm':delta[i],
      'tracked_mean_z_mm':v[i,f['tracked_indices'],2].mean()*1000}
    for c,label in [(0,'outside'),(1,'boundary'),(2,'internal')]:expected[label+'_edge_ratio_max']=class_max[c][i]
    for k,value in expected.items():assert np.isclose(float(row[k]),value,rtol=1e-5,atol=2e-6),(i,k,row[k],value)
    assert int(row['all_worst_edge_index'])==global_arg[i]
    assert [int(row['all_worst_edge_u']),int(row['all_worst_edge_v'])]==edges[global_arg[i]].tolist()
    assert int(row['all_worst_edge_anchor_endpoints'])==cls[global_arg[i]]
    local_indices=np.flatnonzero(local)
    local_worst=local_indices[ratios[i,local].argmax()]
    assert int(row['anchor_worst_edge_index'])==local_worst
    assert [int(row['anchor_worst_edge_u']),int(row['anchor_worst_edge_v'])]==edges[local_worst].tolist()
    assert np.allclose([float(row['ee_x']),float(row['ee_y']),float(row['ee_z'])],f['ee_position'][i],atol=1e-12)
    expected_displacement_vertex=int(np.linalg.norm(v[i]-v[i-1],axis=1).argmax()) if i else -1
    assert int(row['worst_displacement_vertex'])==expected_displacement_vertex
assert np.allclose(np.diff([float(row['world_sim_time']) for row in rows]),dt,atol=1e-6)
for frame,name in [(0,'02_grasp'),(-1,'03_lift')]:
    d=load(RUN/'anchors'/(name+'.npz'))
    for key in ['vertices','block_position','block_quaternion','ee_position','ee_quaternion']:
        assert np.array_equal(f[key][frame],d[key])

# Graph distance from any mapped anchor, without interpreting it as surface metres.
adj=[[] for _ in range(9945)]
for a,b in edges:adj[a].append(b);adj[b].append(a)
hops=np.full(9945,-1,dtype=int);hops[ids]=0;q=deque(ids.tolist())
while q:
    a=q.popleft()
    for b in adj[a]:
        if hops[b]<0:hops[b]=hops[a]+1;q.append(b)
hop_min=hops[edges].min(axis=1)
peak_frame,peak_edge=np.unravel_index(ratios.argmax(),ratios.shape)
assert peak_frame==summary['global_peak']['frame'] and peak_edge==summary['global_peak']['all_worst_edge_index']
labels={0:'Outside',1:'Boundary',2:'Internal'}
class_stats={}
for c in [0,1,2]:
    mask=cls==c
    class_stats[labels[c]]={'edge_count':int(mask.sum()),'max_ratio_over_capture':float(ratios[:,mask].max()),
      'ratio_p95_at_peak_frame':float(np.percentile(ratios[peak_frame,mask],95)),
      'count_over_at_peak':{str(th):int((ratios[peak_frame,mask]>th).sum()) for th in [1.2,1.3,1.5]},
      'fraction_over_at_peak':{str(th):float((ratios[peak_frame,mask]>th).mean()) for th in [1.2,1.3,1.5]}}
pk_ee=int(ee_speed.argmax());pk_block=int(block_speed.argmax());pk_gap=np.unravel_index(gaps.argmax(),gaps.shape)
peak={'frame':int(peak_frame),'step':int(steps[peak_frame]),'time_since_lift_start_seconds':float(t[peak_frame]),
 'edge_index':int(peak_edge),'edge_vertices':edges[peak_edge].tolist(),'class':labels[int(cls[peak_edge])],
 'anchor_membership':[bool(x in ids) for x in edges[peak_edge]],'endpoint_graph_hops':hops[edges[peak_edge]].tolist(),
 'ratio_to_pre_reset':float(ratios[peak_frame,peak_edge]),'ratio_to_lift_start':float(start_ratios[peak_frame,peak_edge]),
 'pre_reset_length_mm':float(rest_lengths[peak_edge]*1000),'lift_start_length_mm':float(lengths[0,peak_edge]*1000),
 'peak_length_mm':float(lengths[peak_frame,peak_edge]*1000)}
audit={'run':RUN.name,'source_hash_checks':source_hashes,'reference_hash_checks':reference_hashes,
 'sample_count':50,'world_steps':49,'physics_dt':dt,'duration_seconds':float(t[-1]),
 'reference_replay_exact':True,'all_recomputed_csv_metrics_match':True,'peak':peak,'classes':class_stats,
 'global_worst_class_frame_counts':{labels[c]:int((cls[global_arg]==c).sum()) for c in [0,1,2]},
 'highest_tail_at_peak':{'cutoff_ratio':1.5,'edge_count':int((ratios[peak_frame]>1.5).sum()),
   'min_endpoint_graph_hop_counts':{str(k):int(value) for k,value in Counter(hop_min[ratios[peak_frame]>1.5].tolist()).items()}},
 'speeds':{'ee_peak_m_s':float(ee_speed[pk_ee]),'ee_peak_step':int(steps[pk_ee]),
   'ee_peak_elapsed_seconds':float(t[pk_ee]),'block_peak_m_s':float(block_speed[pk_block]),
   'block_peak_step':int(steps[pk_block]),'block_peak_elapsed_seconds':float(t[pk_block]),
   'ee_at_edge_peak_m_s':float(ee_speed[peak_frame]),'block_at_edge_peak_m_s':float(block_speed[peak_frame])},
 'gaps':{'global_max_mm':float(gaps.max()),'global_max_step':int(steps[pk_gap[0]]),
   'mean_min_mm':float(gaps.mean(axis=1).min()),'mean_max_mm':float(gaps.mean(axis=1).max()),
   'mean_at_edge_peak_mm':float(gaps[peak_frame].mean()),'max_at_edge_peak_mm':float(gaps[peak_frame].max())},
 'interpretation':'The sampled global maximum is a cut edge at the anchor patch boundary. The most extreme tail is confined to this cut and its immediate graph neighborhood, while less severe extension also exists farther away. The maximum is at the last captured frame, long after the speed peaks; causal attribution or equilibrium requires another controlled experiment.',
 'limits':['Boundary means one anchored endpoint, not the garment outer boundary.',
   'Ratios describe geometry, not stress or self-intersection.',
   'Only explicit World.step endpoints during lift are sampled; no internal substeps or post-lift hold.',
   'The 1.2/1.3/1.5 cutoffs are descriptive summaries, not acceptance thresholds.']}
(OUT/'lift_step_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
edge_peak_frames=ratios.argmax(axis=0);edge_peaks=ratios.max(axis=0)
ranking=np.argsort(edge_peaks)[::-1]
with (OUT/'top_100_edges.csv').open('w',newline='',encoding='utf-8-sig') as stream:
    writer=csv.writer(stream);writer.writerow(['rank','edge_index','u','v','class','max_ratio_to_initial','peak_step','initial_length_mm','length_at_peak_mm','u_graph_hops','v_graph_hops'])
    for rank,e in enumerate(ranking[:100],1):
        j=edge_peak_frames[e];writer.writerow([rank,e,*edges[e],labels[int(cls[e])],edge_peaks[e],steps[j],rest_lengths[e]*1000,lengths[j,e]*1000,*hops[edges[e]]])

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
colors={0:'#8d97a8',1:'#ce582f',2:'#2378b6'}
fig,axs=plt.subplots(2,2,figsize=(14,9),layout='constrained')
ax=axs[0,0]
for c in [0,1,2]:ax.plot(t,class_max[c],color=colors[c],label=labels[c]+' (%d edges)'%(cls==c).sum(),lw=2 if c==1 else 1.5)
ax.scatter(t[peak_frame],peak['ratio_to_pre_reset'],color='black',s=28,zorder=4)
ax.annotate('Peak %.3fx\nstep %d'%(peak['ratio_to_pre_reset'],steps[peak_frame]),(t[peak_frame],peak['ratio_to_pre_reset']),xytext=(-80,-36),textcoords='offset points')
ax.set(ylabel='Maximum edge length / pre-reset length',title='Boundary edge reaches the final sampled maximum');ax.legend(fontsize=9)
ax=axs[0,1]
ax.plot(t[1:],ee_speed[1:],color='#2378b6',label='Measured EE')
ax.plot(t[1:],block_speed[1:],color='#008568',label='Measured block')
ax.scatter(t[pk_ee],ee_speed[pk_ee],color='#2378b6');ax.scatter(t[pk_block],block_speed[pk_block],color='#008568')
ax.set(ylabel='Finite-difference speed (m/s)',title='Speed peaks early; edge extension peaks late');ax.legend()
ax=axs[1,0]
ax.plot(t,gaps.mean(axis=1),label='Paired anchors: mean',color='#2378b6')
ax.plot(t,gaps.max(axis=1),label='Paired anchors: max',color='#ce582f')
ax.plot(t,follow_error,label='Block to EE-offset target',color='#008568',ls='--')
ax.set(ylabel='Geometric distance (mm)',title='Anchor gaps stay small during the lift');ax.legend(fontsize=9)
ax=axs[1,1]
tracked_z=v[:,f['tracked_indices'],2].mean(axis=1)
ax.plot(t,(tracked_z-tracked_z[0])*1000,label='Tracked cloth mean rise',color='#ce582f')
ax.plot(t,(f['ee_position'][:,2]-f['ee_position'][0,2])*1000,label='Measured EE rise',color='#2378b6')
ax.set(ylabel='Rise from lift start (mm)',title='The captured maximum is at the final lift sample');ax.legend()
for ax in axs.ravel():
    ax.set_xlabel('Simulation time since lift start (s)');ax.axvline(t[peak_frame],lw=.8,ls=':',color='black');ax.grid(alpha=.15)
fig.suptitle('Aligned lift: 50 samples across 49 World.step calls (60 Hz)\nBoundary = one anchor endpoint; internal = two; outside = zero. No post-lift hold sampled.',fontsize=13)
fig.savefig(OUT/'lift_edge_speed_gap_curves.png',dpi=180);plt.close(fig)

fig,axs=plt.subplots(2,2,figsize=(14,10),layout='constrained')
p=v[peak_frame];last_ratios=ratios[peak_frame]
ax=axs[0,0];ax.scatter(p[:,0],p[:,1],s=1,c='#c3c9d1',alpha=.4)
hot=last_ratios>1.3
lc=LineCollection(p[edges[hot]][:,:,[0,1]],cmap='YlOrRd',norm=plt.Normalize(1.3,1.65),linewidths=1.5)
lc.set_array(last_ratios[hot]);ax.add_collection(lc)
ax.scatter(p[ids,0],p[ids,1],s=12,facecolors='none',edgecolors='#008568',label='28 anchor vertices')
ax.plot(p[edges[peak_edge],0],p[edges[peak_edge],1],color='black',lw=2.5,label='Global peak edge')
ax.set(xlabel='x (m)',ylabel='y (m)',title='Whole cloth XY: edges above 1.3x at peak frame');ax.set_aspect('equal');ax.legend(fontsize=8)
fig.colorbar(lc,ax=ax,label='3D edge length / initial length',shrink=.75)
ax=axs[0,1];near=(hops[edges].max(axis=1)<=2)
lc=LineCollection(p[edges[near]][:,:,[0,2]],cmap='coolwarm',norm=TwoSlopeNorm(vmin=.8,vcenter=1,vmax=1.65),linewidths=1.5)
lc.set_array(last_ratios[near]);ax.add_collection(lc)
ax.scatter(p[ids,0],p[ids,2],s=14,c='#008568',label='Anchored')
uv=edges[peak_edge];ax.plot(p[uv,0],p[uv,2],color='black',lw=3,label='Peak: %d-%d'%tuple(uv))
for vertex in uv:ax.annotate(str(vertex),p[vertex,[0,2]],xytext=(5,5),textcoords='offset points',fontsize=9)
near_points=p[np.unique(edges[near])]
ax.set(xlim=(near_points[:,0].min()-.005,near_points[:,0].max()+.005),ylim=(near_points[:,2].min()-.005,near_points[:,2].max()+.005),xlabel='x (m)',ylabel='z (m)',title='Local XZ: anchor patch and two graph rings')
ax.set_aspect('equal');ax.locator_params(axis='x',nbins=4);ax.legend(fontsize=8)
fig.colorbar(lc,ax=ax,label='3D edge length / initial length',shrink=.75)
ax=axs[1,0]
for shift,th,color in [(-.18,1.3,'#edb17f'),(.18,1.5,'#ce582f')]:
    values=[class_stats[labels[c]]['fraction_over_at_peak'][str(th)]*100 for c in [1,2,0]]
    ax.bar(np.arange(3)+shift,values,width=.36,color=color,label='Ratio > %.1f'%th)
    for j,c in enumerate([1,2,0]):
        count=class_stats[labels[c]]['count_over_at_peak'][str(th)]
        ax.text(j+shift,values[j]+.5,'%d/%d'%(count,(cls==c).sum()),ha='center',fontsize=8,rotation=25)
ax.set(xticks=np.arange(3),xticklabels=['Boundary','Internal','Outside'],ylabel='Fraction within each edge class (%)',ylim=(0,35),title='Extreme extension is enriched at the patch boundary');ax.legend()
ax=axs[1,1];ax.axis('off')
rows_table=[]
for e in np.argsort(last_ratios)[-6:][::-1]:
    rows_table.append(['%d-%d'%tuple(edges[e]),labels[int(cls[e])],'%d / %d'%tuple(hops[edges[e]]),'%.3f'%last_ratios[e]])
table=ax.table(cellText=rows_table,colLabels=['Edge vertices','Class','Endpoint hops','Length ratio'],loc='center',cellLoc='center')
table.auto_set_font_size(False);table.set_fontsize(9);table.scale(1,1.8)
ax.set_title('Top 6 edges at step %d\nHops = graph distance to the nearest anchor'%steps[peak_frame])
fig.suptitle('Peak localization | last sample, %.3f s after lift start\nOnly the highest tail is confined to the boundary and immediate neighborhood; moderate extension is broader.'%t[peak_frame],fontsize=13)
fig.savefig(OUT/'lift_peak_boundary_localization.png',dpi=180);plt.close(fig)
print('LIFT_TRAJECTORY_AUDIT_OK');print(json.dumps(audit,indent=2));print('OUTPUT',OUT)
