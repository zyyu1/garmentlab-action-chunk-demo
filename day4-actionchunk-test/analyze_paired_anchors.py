"""Rest-mesh anchor identity, live paired distances and geometric edge changes.

No simulator imports or state mutations. Edge ratios are geometry diagnostics,
not stress, material-parameter estimates or a self-intersection test.
"""
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
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

BASE=Path(__file__).resolve().parent/'results'
REST=BASE/'day4-pre-reset-mesh-20261024-212943-485691'
RUN=BASE/'day4-anchor-diagnostic-20261024-210929-786774'
OUT=REST/'analysis'
OUT.mkdir(exist_ok=True)
result=json.loads((REST/'result.json').read_text())
assert result['passed'] is True and result['world_reset_intercepted'] is True
assert result['blocked_step_calls']==result['unexpected_reset_calls']==0
assert result['pre_reset_meshes_equal'] is True
for record in result['capture_phases'].values():
    assert record['timeline_playing'] is False
    assert record['simulation_clock']=={'current_time':0,'current_time_step_index':0}
manifest=json.loads((REST/'source/manifest.json').read_text())
hashes={n:hashlib.sha256((REST/'source'/n).read_bytes()).hexdigest()==v['sha256'] for n,v in manifest.items()}
assert all(hashes.values())
reference_path=REST/'reference_after_start.json'
assert hashlib.sha256(reference_path.read_bytes()).hexdigest()==result['reference_anchor_file']['sha256']
assert reference_path.read_bytes()==(RUN/'anchors/after_start.json').read_bytes()
with np.load(REST/'mesh_before_first_reset.npz',allow_pickle=False) as f:
    rest={k:f[k].copy() for k in f.files}
for n in ['mesh_before_prepared','mesh_after_prepared']:
    with np.load(REST/(n+'.npz'),allow_pickle=False) as f:
        assert all(np.array_equal(f[k],v) for k,v in rest.items())
assert rest['points_local'].shape==(9945,3)
assert len(rest['face_vertex_counts'])==19756 and np.all(rest['face_vertex_counts']==3)
assert len(rest['hole_indices'])==0
faces=rest['face_vertex_indices'].reshape(-1,3)
assert faces.min()>=0 and faces.max()<9945
edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
reference=json.loads(reference_path.read_text())
p0=np.asarray(reference['attributes']['points0']['value'],float)
distance,candidates=cKDTree(rest['points_local']).query(p0,k=2)
ids=candidates[:,0]
assert len(np.unique(ids))==28 and np.all(distance[:,0]==0)
assert np.min(distance[:,1])>0
saved_map=json.loads((REST/'mesh_before_first_reset-candidate-map.json').read_text())
assert ids.tolist()==saved_map['nearest_vertex_indices']
local_edges=np.isin(edges,ids).any(axis=1)
def lengths(v):
    return np.linalg.norm(v[edges[:,1]]-v[edges[:,0]],axis=1)
rest_lengths=lengths(rest['points_world_usd'])
assert np.all(rest_lengths>1e-8)
labels=list(json.loads((RUN/'anchors/index.json').read_text()))
data={}; records={}; targets={}; gaps={}; edge_lengths={}; nearest_matches={}
for n in labels:
    records[n]=json.loads((RUN/'anchors'/(n+'.json')).read_text())
    with np.load(RUN/'anchors'/(n+'.npz'),allow_pickle=False) as f:
        data[n]={k:f[k].copy() for k in f.files}
    d=data[n]; rec=records[n]
    assert d['vertices'].shape==(9945,3) and np.isfinite(d['vertices']).all()
    assert np.array_equal(np.asarray(rec['attributes']['points0']['value']),p0)
    a1=rec['relationships']['actor1'][0]
    scale=np.linalg.norm(np.asarray(rec['usd_actors'][a1]['usd_local_to_world'])[:3,:3],axis=1)
    assert np.allclose(scale,[.03]*3,rtol=1e-6)
    p1=np.asarray(rec['attributes']['points1']['value'],float)
    q=d['block_quaternion'].reshape(4)
    targets[n]=Rotation.from_quat(q[[1,2,3,0]]).apply(p1*scale)+d['block_position']
    gaps[n]=np.linalg.norm(d['vertices'][ids]-targets[n],axis=1)*1000
    edge_lengths[n]=lengths(d['vertices'])
    nearest_matches[n]=int((cKDTree(d['vertices']).query(targets[n])[1]==ids).sum())
before='enabled_before_first_step'; after='enabled_after_first_step'
assert records[after]['physics_step']-records[before]['physics_step']==1
vb=data[before]['vertices']; va=data[after]['vertices']
movement=va[ids]-vb[ids]; toward=targets[before]-vb[ids]
cosine=np.sum(movement*toward,axis=1)/(np.linalg.norm(movement,axis=1)*np.linalg.norm(toward,axis=1))
tracked=data[before]['tracked_indices']
assert len(np.intersect1d(ids,tracked))==len(tracked)==23
stage_stats={}
for n in labels:
    ratio=edge_lengths[n]/rest_lengths
    stage_stats[n]={'paired_gap_mean_mm':float(gaps[n].mean()),'paired_gap_max_mm':float(gaps[n].max()),
      'mapped_identity_matches_nearest_target_vertex':nearest_matches[n],
      'all_edge_ratio_to_initial_p95_p99_max':np.percentile(ratio,[95,99,100]).tolist(),
      'anchor_incident_edge_ratio_to_initial_min_median_p95_max':np.percentile(ratio[local_edges],[0,50,95,100]).tolist()}
frame_ratio=edge_lengths[after]/edge_lengths[before]
summary={'rest_capture_run':REST.name,'physics_run':RUN.name,'source_hash_checks':hashes,
 'vertex_count':9945,'triangle_count':19756,'unique_edge_count':len(edges),'anchor_incident_edge_count':int(local_edges.sum()),
 'anchor_vertex_indices':ids.tolist(),'anchor_mapping_max_local_distance':float(distance[:,0].max()),
 'anchor_mapping_min_second_neighbor_local_distance':float(distance[:,1].min()),
 'tracked_subset_of_mapped_anchors':True,'stage_metrics':stage_stats,
 'first_step_direction_cosine_min_median_max':np.percentile(cosine,[0,50,100]).tolist(),
 'first_step_anchor_incident_edge_ratio_to_pre_step_min_median_p95_max':np.percentile(frame_ratio[local_edges],[0,50,95,100]).tolist(),
 'first_step_all_edge_ratio_to_pre_step_min_median_p95_p99_max':np.percentile(frame_ratio,[0,50,95,99,100]).tolist(),
 'limits':['Exact rest geometry mapping across matched-source runs; live solver ordering is supported by all 28 nearest-target matches after activation, not by an exposed internal solver membership API.',
 'Paired distances are geometric separations; they are not promised solver residuals or a zero-error requirement.',
 'Mesh edge ratios measure geometric change; no stress, strain-energy, self-intersection or material-quality certification.',
 'Array identity and direction evidence support stored-layout correction; causal proof requires an anchor intervention.']}
(OUT/'paired_anchor_audit.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
rows=[]
for i,idx in enumerate(ids):
    rows.append({'pair':i,'vertex_index':int(idx),'tracked':bool(idx in tracked),
      'gap_before_mm':float(gaps[before][i]),'gap_after_mm':float(gaps[after][i]),
      'vertex_motion_mm':float(np.linalg.norm(movement[i])*1000),
      'direction_cosine_to_pre_step_target':float(cosine[i])})
with (OUT/'anchor_pairs.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
region=np.vstack([vb[ids],va[ids],targets[before],targets[after]])
roi=(vb[:,0]>region[:,0].min()-.025)&(vb[:,0]<region[:,0].max()+.025)&(vb[:,1]>region[:,1].min()-.025)&(vb[:,1]<region[:,1].max()+.025)
for col,n in enumerate([before,after]):
    v=data[n]['vertices']; p=targets[n]
    for row,(a,b) in enumerate([(0,1),(0,2)]):
        ax=axs[row,col]
        ax.scatter(v[roi,a],v[roi,b],s=7,color='#c7ced6',alpha=.7)
        segments=np.stack([v[ids][:,[a,b]],p[:,[a,b]]],axis=1)
        ax.add_collection(LineCollection(segments,colors='#dd8c54',linewidths=1,alpha=.75,label='Rest-mapped vertex to its paired target'))
        ax.scatter(v[ids,a],v[ids,b],s=20,color='#b32946' if col==0 else '#286ac5',label='28 rest-mapped cloth vertices',zorder=3)
        ax.scatter(p[:,a],p[:,b],s=45,marker='+',color='#008568',label='Paired rigid anchor targets',zorder=4)
        ax.set(xlim=(region[:,a].min()-.012,region[:,a].max()+.012),ylim=(region[:,b].min()-.008,region[:,b].max()+.008),xlabel='xyz'[a]+' (m)',ylabel='xyz'[b]+' (m)')
        ax.set_aspect('equal');ax.grid(alpha=.15)
        if row==0: ax.set_title(('Before step 492' if col==0 else 'After step 492')+'\nPaired mean / max = %.2f / %.2f mm'%(gaps[n].mean(),gaps[n].max()))
handles,names=axs[0,0].get_legend_handles_labels()
fig.legend(handles,names,loc='outside lower center',ncol=1,fontsize=9)
fig.suptitle('Rest mesh identifies 28 unique anchor vertices | XY and XZ views\nLines use corresponding anchor pairs, not nearest-cloth substitutions',fontsize=13)
fig.savefig(OUT/'paired_anchor_geometry.png',dpi=180);plt.close(fig)

fig=plt.figure(figsize=(14,9),layout='constrained');gs=fig.add_gridspec(2,2)
ax=fig.add_subplot(gs[0,:]);x=np.arange(28)
ax.bar(x-.18,gaps[before],width=.36,color='#b32946',label='Before')
ax.bar(x+.18,gaps[after],width=.36,color='#286ac5',label='One step after')
ax.set(xticks=x,xticklabels=[str(i) for i in ids],ylabel='Paired geometric separation (mm)',title='All 28 paired distances contract in the first enabled step')
ax.tick_params(axis='x',labelrotation=65);ax.legend();ax.grid(axis='y',alpha=.15)
ax=fig.add_subplot(gs[1,0])
for n,color,label in [(before,'#929eaf','Before activation'),(after,'#b32946','One step after'),('03_lift','#008568','Lift')]:
    ratios=np.sort((edge_lengths[n]/rest_lengths)[local_edges])
    ax.plot(ratios,np.arange(1,len(ratios)+1)/len(ratios)*100,label=label,color=color)
ax.axvline(1,color='black',lw=.8,ls='--')
ax.set(xlabel='Edge length / pre-reset edge length',ylabel='Anchor-incident edges at or below (%)',title='93 edges incident to the mapped anchors')
ax.legend();ax.grid(alpha=.15)
ax=fig.add_subplot(gs[1,1])
segments=va[edges[local_edges]][:,:,[0,2]]
col=LineCollection(segments,cmap='coolwarm',norm=TwoSlopeNorm(vmin=-1,vcenter=0,vmax=1),linewidths=1.8)
col.set_array(np.log2((edge_lengths[after]/rest_lengths)[local_edges]));ax.add_collection(col)
ax.scatter(va[ids,0],va[ids,2],s=9,color='black',zorder=3)
local_points=va[np.unique(edges[local_edges])]
ax.set(xlim=(local_points[:,0].min()-.005,local_points[:,0].max()+.005),ylim=(local_points[:,2].min()-.005,local_points[:,2].max()+.005),xlabel='x (m)',ylabel='z (m)',title='One-step-after local edge lengths (XZ projection)')
ax.set_aspect('equal');ax.grid(alpha=.15)
ax.locator_params(axis='x',nbins=4)
cb=fig.colorbar(col,ax=ax,label='Edge length / initial length',ticks=[-1,0,1],shrink=.8)
cb.ax.set_yticklabels(['0.5x','1x','2x'])
fig.suptitle('Paired anchor correction and mesh edge deformation\nEdge ratios are geometric diagnostics; no stress or self-intersection claim',fontsize=14)
fig.savefig(OUT/'paired_gaps_and_edge_deformation.png',dpi=180);plt.close(fig)
print(json.dumps(summary,indent=2));print('OUTPUT',OUT)
