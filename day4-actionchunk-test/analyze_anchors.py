"""Analyze saved USD-visible anchors using live rigid poses, without Isaac Sim.

No exact cloth vertex membership is inferred: rest mesh points were not saved.
Nearest-cloth distances are geometric diagnostics, not paired solver residuals.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

BASE = Path(__file__).resolve().parent / 'results'
RUN = BASE / 'day4-anchor-diagnostic-20261024-210929-786774'
ROOT = RUN / 'anchors'
OUT = RUN / 'analysis'
OUT.mkdir(exist_ok=True)
index = json.loads((ROOT/'index.json').read_text())
labels = list(index)
records = {n:json.loads((ROOT/(n+'.json')).read_text()) for n in labels}
data = {}
for n in labels:
    with np.load(ROOT/(n+'.npz'),allow_pickle=False) as f:
        data[n] = {k:f[k].copy() for k in f.files}
    assert data[n]['vertices'].shape == (9945,3)
    assert all(np.isfinite(v).all() for v in data[n].values())
    assert not records[n]['read_errors']
r = json.loads((RUN/'result.json').read_text())
assert r['passed'] is True and r['anchor_diagnostic']['captured'] is True
assert all(all(x['checks'].values()) for x in r['action_audit'])
manifest = json.loads((RUN/'source/manifest.json').read_text())
hashes = {n:hashlib.sha256((RUN/'source'/n).read_bytes()).hexdigest()==v['sha256'] for n,v in manifest.items()}
assert len(hashes)==10 and all(hashes.values())

def points(n,k):
    p=np.asarray(records[n]['attributes'][k]['value'],dtype=float)
    assert p.shape == (28,3) and np.isfinite(p).all()
    return p
def usd_transform(p,m):
    return np.c_[p,np.ones(len(p))].dot(np.asarray(m,dtype=float))[:,:3]
first=records[labels[0]]
a0=first['relationships']['actor0'][0]
a1=first['relationships']['actor1'][0]
m0=np.asarray(first['usd_actors'][a0]['usd_local_to_world'],float)
m1=np.asarray(first['usd_actors'][a1]['usd_local_to_world'],float)
scale=np.linalg.norm(m1[:3,:3],axis=1)
assert np.allclose(scale,[.03]*3,rtol=1e-6)
assert np.allclose(m1[:3,:3],np.diag(scale))
p0w=usd_transform(points(labels[0],'points0'),m0)
p1w=usd_transform(points(labels[0],'points1'),m1)
initial_pair_gap=np.linalg.norm(p0w-p1w,axis=1)*1000
world_targets={}
stats={}
for n in labels:
    d=data[n]; rec=records[n]
    assert rec['relationships']==first['relationships']
    current_m1=np.asarray(rec['usd_actors'][a1]['usd_local_to_world'],float)
    assert np.allclose(np.linalg.norm(current_m1[:3,:3],axis=1),scale)
    q=d['block_quaternion'].reshape(4)
    assert abs(np.linalg.norm(q)-1)<1e-4
    # Actor1's local anchors include the authored rigid scale. Apply scale,
    # then current rotation (wxyz -> xyzw) and translation from physics view.
    world_targets[n]=Rotation.from_quat(q[[1,2,3,0]]).apply(points(n,'points1')*scale)+d['block_position']
    distances,nearest=cKDTree(d['vertices']).query(world_targets[n])
    stats[n]={
        'step':rec['physics_step'],'enabled':rec['enabled'],
        'point0_max_abs_change_local_units':float(np.abs(points(n,'points0')-points(labels[0],'points0')).max()),
        'point1_max_abs_change_local_units':float(np.abs(points(n,'points1')-points(labels[0],'points1')).max()),
        'changed_attributes':[k for k,v in rec['attributes'].items() if v!=first['attributes'].get(k)],
        'target_to_nearest_cloth_mean_mm':float(distances.mean()*1000),
        'target_to_nearest_cloth_max_mm':float(distances.max()*1000),
        'target_to_nearest_cloth_median_mm':float(np.median(distances)*1000),
        'usd_block_vs_live_translation_mm':float(np.linalg.norm(current_m1[3,:3]-d['block_position'])*1000),
        'nearest_vertices_unique_count':int(len(np.unique(nearest))),
    }
before='enabled_before_first_step'; after='enabled_after_first_step'; aligned='aligned_disabled'
assert stats[after]['step']-stats[before]['step']==1
assert np.array_equal(data[aligned]['vertices'],data[before]['vertices'])
assert np.array_equal(data[aligned]['block_position'],data[before]['block_position'])
mm=np.linalg.norm(data[after]['vertices']-data[before]['vertices'],axis=1)*1000
worst=int(mm.argmax())
block_motion=float(np.linalg.norm(data[after]['block_position']-data[before]['block_position'])*1000)
target_motion=np.linalg.norm(world_targets[after]-world_targets[before],axis=1)*1000
# An attempted nearest match to the first live cloth is explicitly ambiguous.
initial_d,initial_i=cKDTree(data[labels[0]]['vertices']).query(p0w,k=2)
previous=BASE/'day4-prepared-actionchunk-20261024-204755-573715'
replay={}
for n in ['00_settled','01_approach','01b_before_close','02_grasp','03_lift','04_release']:
    with np.load(previous/(n+'.npz'),allow_pickle=False) as f:
        replay[n]=float(np.linalg.norm(f['vertices']-data[n]['vertices'],axis=1).max()*1000)
summary={
    'run':RUN.name,'source_hash_checks':hashes,'phase_count':len(labels),'anchor_pair_count':28,
    'stage_metrics':stats,'initial_usd_anchor_pair_gap_max_mm':float(initial_pair_gap.max()),
    'activation':{'step_before':stats[before]['step'],'step_after':stats[after]['step'],
      'max_vertex_displacement_mm':float(mm.max()),'worst_vertex':worst,
      'count_over_5_mm':int((mm>5).sum()),'block_motion_mm':block_motion,
      'max_rigid_anchor_target_motion_mm':float(target_motion.max()),
      'aligned_vs_enabled_before_vertices_equal':True},
    'initial_live_nearest_match_not_identity':{'max_distance_mm':float(initial_d[:,0].max()*1000),
      'unique_nearest_vertices_for_28_points':int(len(np.unique(initial_i[:,0]))),
      'minimum_first_to_second_neighbor_distance_margin_mm':float((initial_d[:,1]-initial_d[:,0]).min()*1000)},
    'previous_run_snapshot_max_displacement_mm':replay,
    'interpretation':'Unchanged USD-visible local arrays preserve the initial anchor pattern. Live block-side targets are geometrically inconsistent with settled cloth before activation; the nearest-cloth gap shrinks in the first enabled step. This supports a constraint-correction explanation, but does not prove internal anchor regeneration behavior or identify exact cloth-side material anchors.',
    'limits':['Cloth actor0 USD transform cannot locate its current deforming material anchors.',
      'No rest mesh points/faces saved; exact cloth-side vertex mapping is unresolved.',
      'Nearest-cloth distances are unsigned geometric distances, not paired constraint errors.',
      'USD arrays may differ from internal solver data; no causal intervention was performed.']}
(OUT/'anchor_audit.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
all_targets=np.vstack([world_targets[before],world_targets[after]])
for col,n in enumerate([before,after]):
    v=data[n]['vertices']; p=world_targets[n]
    for row,(a,b) in enumerate([(0,1),(0,2)]):
        ax=axs[row,col]
        in_roi=(v[:,0]>all_targets[:,0].min()-.035)&(v[:,0]<all_targets[:,0].max()+.035)&(v[:,1]>all_targets[:,1].min()-.035)&(v[:,1]<all_targets[:,1].max()+.035)
        sc=ax.scatter(v[in_roi,a],v[in_roi,b],c=mm[in_roi],cmap='magma',vmin=0,vmax=25,s=13,label='Cloth (colour = one-step displacement)')
        ax.scatter(p[:,a],p[:,b],s=45,marker='+',c='#00a789',linewidths=1.5,label='28 live block-side anchor targets')
        ax.scatter(v[worst,a],v[worst,b],s=60,marker='x',c='#2783e8',label='Max-displacement vertex')
        ax.set(xlim=(all_targets[:,a].min()-.025,all_targets[:,a].max()+.025),
          ylim=(min(data[before]['vertices'][in_roi,b].min(),all_targets[:,b].min())-.008,
                max(data[after]['vertices'][in_roi,b].max(),all_targets[:,b].max())+.008),
          xlabel='xyz'[a]+' (m)',ylabel='xyz'[b]+' (m)')
        ax.set_aspect('equal'); ax.grid(alpha=.15)
        if row==0: ax.set_title(('Before: step 491' if col==0 else 'After: step 492')+'\nNearest-cloth mean gap = %.2f mm'%stats[n]['target_to_nearest_cloth_mean_mm'])
handles,legend_labels=axs[0,0].get_legend_handles_labels()
fig.legend(handles,legend_labels,loc='outside lower center',ncol=1,fontsize=9)
fig.colorbar(sc,ax=axs.ravel().tolist(),label='Cloth vertex displacement during activation (mm)',shrink=.75)
fig.suptitle('First enabled physics step | XY (top) and XZ (bottom) local views\nTargets reconstructed using live rigid pose + authored scale; no cloth-side vertex identity assumed',fontsize=12)
fig.savefig(OUT/'anchor_activation_geometry.png',dpi=180); plt.close(fig)

fig,axs=plt.subplots(1,3,figsize=(16,5),layout='constrained')
short=['Start','Settled','Approach','Pre-close','Aligned','ON pre-step','ON post-step','Grasp','Lift','Release']
x=np.arange(len(labels))
ax=axs[0]
ax.plot(x,[stats[n]['point0_max_abs_change_local_units'] for n in labels],'-o',label='points0',lw=2)
ax.plot(x,[stats[n]['point1_max_abs_change_local_units'] for n in labels],'--x',label='points1',lw=1.5)
ax.set(xticks=x,xticklabels=short,ylabel='Max absolute array change (local units)',title='USD-visible arrays: unchanged in all 10 phases',ylim=(-.001,.001))
ax.tick_params(axis='x',labelrotation=65); ax.legend(); ax.grid(alpha=.15)
phases=[aligned,before,after,'02_grasp','03_lift']
ax=axs[1]
ax.plot(range(5),[stats[n]['target_to_nearest_cloth_mean_mm'] for n in phases],'-o',label='Mean')
ax.plot(range(5),[stats[n]['target_to_nearest_cloth_max_mm'] for n in phases],'-s',label='Max')
ax.set(xticks=range(5),xticklabels=['Aligned\nOFF','ON\npre-step','ON\npost-step','Grasp','Lift'],ylabel='Nearest-cloth geometric distance (mm)',title='Cloth approaches stored rigid anchor targets')
ax.legend(); ax.grid(alpha=.15)
ax=axs[2]
bar=[float(mm.max()),float(mm[data[before]['tracked_indices']].mean()),block_motion,float(target_motion.max())]
ax.bar(range(4),bar,color=['#bd2943','#d96978','#008568','#4aa992'])
ax.set(xticks=range(4),xticklabels=['Cloth\nmax','Tracked\nmean','Block\nmotion','Rigid targets\nmax motion'],ylabel='One-step displacement (mm)',title='Large cloth correction with nearly static targets',ylim=(0,28))
for i,value in enumerate(bar): ax.text(i,value+.5,'%.3f'%value,ha='center')
fig.suptitle('Activation evidence | 28 paired local anchors | unsigned nearest-cloth gap is not a solver residual',fontsize=13)
fig.savefig(OUT/'anchor_changes_summary.png',dpi=180); plt.close(fig)
print(json.dumps(summary,indent=2))
print('ANALYSIS_OUTPUT',OUT)
