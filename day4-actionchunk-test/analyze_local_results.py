"""Offline audit and point-cloud figures; never imports the simulator."""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation

BASE = Path(__file__).resolve().parent / 'results'
RUN = BASE / 'day4-prepared-actionchunk-20261024-204755-573715'
OUT = RUN / 'analysis'
OUT.mkdir(exist_ok=True)
r = json.loads((RUN / 'result.json').read_text())
manifest = json.loads((RUN / 'source/manifest.json').read_text())
hashes = {n: hashlib.sha256((RUN/'source'/n).read_bytes()).hexdigest() == v['sha256'] for n,v in manifest.items()}
assert len(hashes) == 9 and all(hashes.values()), hashes
assert r['passed'] is True
assert [a['horizon'] for a in r['action_audit']] == [1,1,4,1,1,1]
for a in r['action_audit']:
    assert len(a['checks']) == 8 and all(v is True for v in a['checks'].values())
    assert a['response']['executed_steps'] == a['horizon']
assert r['action_audit'][-1]['response']['info']['holding'] is False
labels = ['00_settled','01_approach','01b_before_close','02_grasp','03_lift','04_release']
frames = {}
for name in labels:
    with np.load(RUN/(name+'.npz'),allow_pickle=False) as f:
        d = {k:f[k].copy() for k in f.files}
    v, ids = d['vertices'],d['tracked_indices']
    assert v.shape == (9945,3) and np.isfinite(v).all()
    assert ids.ndim == 1 and np.issubdtype(ids.dtype,np.integer)
    assert len(ids) == len(np.unique(ids)) == 23 and ids.min() >= 0 and ids.max() < len(v)
    for k,size in [('block_position',3),('ee_position',3),('ee_quaternion',4)]:
        assert d[k].size == size and np.isfinite(d[k]).all()
        d[k] = d[k].reshape(size)
    assert abs(np.linalg.norm(d['ee_quaternion'])-1) < 1e-4
    frames[name] = d
ids = frames[labels[0]]['tracked_indices']
assert all(np.array_equal(f['tracked_indices'],ids) for f in frames.values())
tree = ast.parse((RUN/'source/Control.py').read_text())
offsets = [ast.literal_eval(n.value.args[0]) for n in ast.walk(tree)
           if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='grasp_offset' for t in n.targets)
           and isinstance(n.value,ast.Call)]
assert len(offsets) == 1
def target(d):
    return d['ee_position']+Rotation.from_quat(d['ee_quaternion'][[1,2,3,0]]).apply(offsets[0])
def mean_z(name):
    return float(frames[name]['vertices'][ids,2].mean())
lift,release = frames['03_lift'],frames['04_release']
metrics = {'cloth_rise':mean_z('03_lift')-mean_z('02_grasp'),
           'cloth_drop':mean_z('03_lift')-mean_z('04_release'),
           'release_block_drift':float(np.linalg.norm(release['block_position']-lift['block_position'])),
           'follow_error':float(np.linalg.norm(target(lift)-lift['block_position']))}
for k,value in metrics.items():
    assert np.isclose(value,r[k],rtol=1e-4,atol=1e-7),(k,value,r[k])
with np.load(BASE/'attachment-enable-jump-20261024-205242-730012.npz',allow_pickle=False) as f:
    jump = {k:f[k].copy() for k in f.files}
v,after = jump['before'],jump['after']
assert v.shape == after.shape == (9945,3)
assert np.array_equal(jump['tracked_indices'],ids)
assert all(np.isfinite(x).all() for x in jump.values())
mm = np.linalg.norm(after-v,axis=1)*1000
worst = int(mm.argmax())
summary = {'run':RUN.name,'source_hash_checks':hashes,'snapshot_count':6,'vertex_count':9945,'tracked_count':23,
           'chunk_horizons':[a['horizon'] for a in r['action_audit']],'action_count':9,'state_check_count':48,
           'recomputed_metrics_m':metrics,
           'activation':{'percentiles_mm':dict(zip(['p50','p95','p99','max'],np.percentile(mm,[50,95,99,100]).tolist())),
             'count_above_mm':{str(t):int((mm>t).sum()) for t in [1,5,10,20,30]},
             'tracked_mean_mm':float(mm[ids].mean()),'tracked_max_mm':float(mm[ids].max()),
             'worst_vertex':worst,'worst_in_tracked':bool(worst in ids),
             'block_motion_mm':float(np.linalg.norm(jump['block_after']-jump['block_before'])*1000)},
           'snapshots':{n:{'tracked_mean_z_mm':mean_z(n)*1000,'bbox_min_m':d['vertices'].min(0).tolist(),
              'bbox_max_m':d['vertices'].max(0).tolist(),
              'block_target_error_mm':float(np.linalg.norm(target(d)-d['block_position'])*1000)} for n,d in frames.items()},
           'limits':['No mesh faces: cannot measure mesh strain or prove absence of self-intersection.',
             'Tracked samples and displaced vertices do not identify actual attachment members.',
             'H=4 covers free descent; close, held lift and open are separate H=1 calls.',
             'Sparse snapshots do not validate reset, repeated grasp, yaw or folding quality.']}
(OUT/'audit.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
selected = labels[2:]
titles = ['Before close','Grasp','Lift','Released + 120 steps']
all_points = np.concatenate([np.vstack((frames[n]['vertices'],frames[n]['block_position'],frames[n]['ee_position'])) for n in selected])
fig,axs = plt.subplots(2,4,figsize=(16,6.3),layout='constrained')
for c,(name,title) in enumerate(zip(selected,titles)):
    d = frames[name]; points = d['vertices']
    for row,(a,b) in enumerate([(0,1),(0,2)]):
        ax = axs[row,c]
        ax.scatter(points[:,a],points[:,b],s=1.5,c='#8b9aaa',alpha=.42,rasterized=True)
        ax.scatter(points[ids,a],points[ids,b],s=15,c='#d42b45',label='23 tracked samples',zorder=3)
        for k,color,marker,label in [('block_position','#008568','s','Block centre'),('ee_position','#245de0','x','Measured EE')]:
            p = d[k]; ax.scatter(p[a],p[b],s=52,c=color,marker=marker,label=label,zorder=4)
        ax.set(xlim=(all_points[:,a].min()-.025,all_points[:,a].max()+.025),
               ylim=(all_points[:,b].min()-.025,all_points[:,b].max()+.025),xlabel='xyz'[a]+' (m)',ylabel='xyz'[b]+' (m)')
        ax.set_aspect('equal',adjustable='box'); ax.grid(alpha=.15)
        if row==0: ax.set_title(title+'\nTracked mean z = %.2f mm'%(mean_z(name)*1000))
        else: ax.axhline(0,c='black',lw=.7,alpha=.5)
handles, legend_labels = axs[0,0].get_legend_handles_labels()
fig.legend(handles,legend_labels,loc='outside lower center',ncol=3,fontsize=9)
fig.suptitle('Single-grasp ActionChunk run | top (XY) and side (XZ) views\nIdentical limits in each row; markers show positions, not robot/block geometry',fontsize=14)
fig.savefig(OUT/'snapshot_comparison.png',dpi=180); plt.close(fig)

fig,axs = plt.subplots(2,2,figsize=(13,9),layout='constrained')
ax = axs[0,0]
sc = ax.scatter(v[:,0],v[:,1],c=mm,s=4,cmap='magma',vmin=0,vmax=25,rasterized=True)
ax.scatter(v[ids,0],v[ids,1],s=28,facecolors='none',edgecolors='#00bca8',label='Tracked samples')
ax.scatter(v[worst,0],v[worst,1],s=80,marker='x',c='#36a8ff',label='Max-displacement vertex')
ax.set(xlabel='x (m)',ylabel='y (m)',title='Whole cloth: one-step displacement at activation')
ax.set_aspect('equal'); ax.legend(fontsize=8); fig.colorbar(sc,ax=ax,label='Vertex displacement (mm)')
roi = np.unique(np.r_[np.flatnonzero(mm>5),ids])
local = np.vstack((v[roi],after[roi],jump['block_before'].reshape(1,3),jump['block_after'].reshape(1,3)))
ax = axs[0,1]
ax.scatter(v[:,0],v[:,2],s=5,c='#c1c8d0',label='Before')
ax.scatter(after[:,0],after[:,2],s=7,c=mm,cmap='magma',vmin=0,vmax=25)
ax.scatter(after[ids,0],after[ids,2],s=28,facecolors='none',edgecolors='#00bca8',label='Tracked after')
ax.scatter(*after[worst,[0,2]],s=80,marker='x',c='#36a8ff')
ax.plot([v[worst,0],after[worst,0]],[v[worst,2],after[worst,2]],c='#36a8ff',lw=1.2,label='Max-displacement path')
ax.set(xlim=(local[:,0].min()-.012,local[:,0].max()+.012),ylim=(local[:,2].min()-.008,local[:,2].max()+.008),
       xlabel='x (m)',ylabel='z (m)',title='Local side view: before and one frame after')
ax.set_aspect('equal'); ax.legend(fontsize=8)
ax = axs[1,0]
ax.plot(np.sort(mm),np.arange(1,len(mm)+1)/len(mm)*100,c='#334b6e')
ax.set(xlabel='Displacement (mm)',ylabel='Vertices at or below (%)',title='All 9,945 vertices: cumulative distribution',ylim=(0,101))
for q in [95,99]:
    value=np.percentile(mm,q); ax.scatter(value,q,c='#d42b45')
    ax.annotate('P%d = %.3f mm'%(q,value),(value,q),xytext=(7,-20 if q==95 else -34),textcoords='offset points',fontsize=9)
ax.grid(alpha=.2)
ax = axs[1,1]
heights = [np.percentile(mm,95),np.percentile(mm,99),mm.max(),mm[ids].mean(),mm[ids].max()]
ax.bar(['All: P95','All: P99','All: max','Tracked: mean','Tracked: max'],heights,color=['#9aa9bc']*3+['#d42b45']*2)
ax.set(ylabel='Displacement (mm)',title='Local jump remains despite small whole-cloth P95',ylim=(0,28))
ax.tick_params(axis='x',labelrotation=16)
for i,h in enumerate(heights): ax.text(i,h+.4,'%.2f'%h,ha='center',fontsize=9)
fig.suptitle('Attachment activation | 5 mm overlap | a single simulation step\nDisplaced vertices and tracked samples do not identify actual attachment members',fontsize=14)
fig.savefig(OUT/'attachment_activation.png',dpi=180); plt.close(fig)
print(json.dumps(summary,indent=2))
print('FIGURES',OUT)
