"""Audit matched-state points1 control and plot both groups, without Isaac Sim."""
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
PAIR=BASE/'day4-anchor-pair-run-fhFIzk2Z'
OUT=PAIR/'analysis'; OUT.mkdir(exist_ok=True)
comparison=json.loads((PAIR/'comparison.json').read_text())
paths={mode:BASE/Path(p).parent.name for mode,p in comparison['result_paths'].items()}
groups={}
def load_npz(path):
    with np.load(path,allow_pickle=False) as f:
        return {k:f[k].copy() for k in f.files}
def check_hashes(folder):
    manifest=json.loads((folder/'manifest.json').read_text())
    checks={n:hashlib.sha256((folder/n).read_bytes()).hexdigest()==v['sha256'] for n,v in manifest.items()}
    assert all(checks.values()),checks
    return checks,manifest
def close(actual,expected):
    assert np.allclose(actual,expected,rtol=1e-5,atol=2e-6),(actual,expected)
for mode,path in paths.items():
    r=json.loads((path/'result.json').read_text());m=json.loads((path/'alignment_metrics.json').read_text())
    assert r['passed'] is True and r['experiment_mode']==mode and r['alignment_metrics']==m
    assert m['usd_readback_ok'] is True and m['usd_points1_written']==(mode=='aligned')
    assert [a['horizon'] for a in r['action_audit']]==[1,1,4,1,1,1]
    assert all(len(a['checks'])==8 and all(v is True for v in a['checks'].values()) for a in r['action_audit'])
    for k,v in m.items():
        if k.startswith('arrays_'): assert all(x is True for x in v.values())
    source_checks,source_manifest=check_hashes(path/'source')
    reference_checks,reference_manifest=check_hashes(path/'reference')
    assert len(source_checks)==11 and len(reference_checks)==5
    rest=load_npz(path/'reference/mesh_before_first_reset.npz')
    assert rest['points_local'].shape==(9945,3) and len(rest['face_vertex_counts'])==19756
    assert np.all(rest['face_vertex_counts']==3) and not len(rest['hole_indices'])
    faces=rest['face_vertex_indices'].reshape(-1,3)
    edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
    assert len(edges)==29703
    def lengths(v): return np.linalg.norm(v[edges[:,1]]-v[edges[:,0]],axis=1)
    rest_lengths=lengths(rest['points_world_usd']);assert np.all(rest_lengths>1e-8)
    op=load_npz(path/'alignment_operation.npz');ids=op['anchor_indices']
    assert len(ids)==len(np.unique(ids))==28
    assert np.array_equal(rest['points_local'][ids],op['points0'])
    assert np.array_equal(op['vertices_before'],op['vertices_after'])
    if mode=='baseline':assert np.array_equal(op['points1_original'],op['points1_readback'])
    else:
        assert not np.array_equal(op['points1_original'],op['points1_readback'])
        assert np.array_equal(op['points1_requested'].astype(np.float32).astype(float),op['points1_readback'])
    local=np.isin(edges,ids).any(axis=1);assert local.sum()==93
    labels=list(json.loads((path/'anchors/index.json').read_text()));assert len(labels)==11
    states={};stages={};records={};targets={};ratios={}
    prior_labels={'after_start','00_settled','01_approach','01b_before_close','aligned_original'}
    for n in labels:
        d=load_npz(path/'anchors'/(n+'.npz'));rec=json.loads((path/'anchors'/(n+'.json')).read_text())
        assert not rec['read_errors'] and d['vertices'].shape==(9945,3)
        assert all(np.isfinite(v).all() for v in d.values())
        assert len(d['tracked_indices'])==23 and len(np.intersect1d(d['tracked_indices'],ids))==23
        for key in ['block_quaternion','ee_quaternion']:assert abs(np.linalg.norm(d[key])-1)<1e-4
        p0=np.asarray(rec['attributes']['points0']['value'],float)
        p1=np.asarray(rec['attributes']['points1']['value'],float)
        assert np.array_equal(p0,op['points0'])
        expected=op['points1_original'] if n in prior_labels else op['points1_readback']
        assert np.array_equal(p1,expected),(mode,n)
        a1=rec['relationships']['actor1'][0]
        scale=np.linalg.norm(np.asarray(rec['usd_actors'][a1]['usd_local_to_world'])[:3,:3],axis=1)
        assert np.allclose(scale,op['block_scale'])
        q=d['block_quaternion'];target=Rotation.from_quat(q[[1,2,3,0]]).apply(p1*scale)+d['block_position']
        gap=np.linalg.norm(d['vertices'][ids]-target,axis=1)*1000
        ratio=lengths(d['vertices'])/rest_lengths
        stages[n]={'paired_gap_mean_mm':float(gap.mean()),'paired_gap_max_mm':float(gap.max()),
          'tracked_mean_z_mm':float(d['vertices'][d['tracked_indices'],2].mean()*1000),
          'all_edge_ratio_to_initial_p95_p99_max':np.percentile(ratio,[95,99,100]).tolist(),
          'anchor_incident_edge_ratio_to_initial_min_median_p95_max':np.percentile(ratio[local],[0,50,95,100]).tolist()}
        for k,v in m.get('stages',{}).get(n,{}).items():close(stages[n][k],v)
        states[n]=d;records[n]=rec;targets[n]=target;ratios[n]=ratio
    for n in ['00_settled','01_approach','01b_before_close','02_grasp','03_lift','04_release']:
        top=load_npz(path/(n+'.npz'))
        assert all(np.array_equal(top[k],states[n][k]) for k in top)
    for metric,stage in [('original','aligned_original'),('after_operation','aligned_disabled')]:
        for k,v in m[metric].items():close(stages[stage][k],v)
    if mode=='aligned':assert stages['aligned_disabled']['paired_gap_max_mm']<.001
    before='enabled_before_first_step';after='enabled_after_first_step'
    assert records[before]['physics_step']==491 and records[after]['physics_step']==492
    delta=np.linalg.norm(states[after]['vertices']-states[before]['vertices'],axis=1)*1000
    activation={'step_before':491,'step_after':492,'max_vertex_displacement_mm':float(delta.max()),
      'tracked_mean_displacement_mm':float(delta[states[before]['tracked_indices']].mean()),
      'count_over_5_mm':int((delta>5).sum()),
      'block_motion_mm':float(np.linalg.norm(states[after]['block_position']-states[before]['block_position'])*1000),
      **{k:v for k,v in stages[after].items() if k!='tracked_mean_z_mm'}}
    for expected in [m['activation'],comparison['activation'][mode]]:
        for k,v in expected.items():close(activation[k],v)
    def mean_z(n):return states[n]['vertices'][states[n]['tracked_indices'],2].mean()
    lift=states['03_lift'];q=lift['ee_quaternion']
    # Confirm the known archived controller offset rather than silently assume it.
    control=(path/'source/Control.py').read_text()
    assert 'self.grasp_offset=torch.tensor([0.,0.,-0.01])' in control
    offset=Rotation.from_quat(q[[1,2,3,0]]).apply([0,0,-.01])
    physical={'cloth_rise':float(mean_z('03_lift')-mean_z('02_grasp')),
      'cloth_drop':float(mean_z('03_lift')-mean_z('04_release')),
      'follow_error':float(np.linalg.norm(lift['ee_position']+offset-lift['block_position'])),
      'release_block_drift':float(np.linalg.norm(lift['block_position']-states['04_release']['block_position']))}
    for k,v in physical.items():close(v,r[k])
    groups[mode]={'path':path,'result':r,'metrics':m,'states':states,'records':records,'targets':targets,
      'ratios':ratios,'stages':stages,'op':op,'activation':activation,'delta':delta,'physical':physical,
      'source_checks':source_checks,'reference_checks':reference_checks,
      'source_manifest':source_manifest,'reference_manifest':reference_manifest,'edges':edges,'local':local}

b=groups['baseline'];a=groups['aligned']
pre_checks={k:bool(np.array_equal(b['op'][k],a['op'][k])) for k in
 ('anchor_indices','points0','points1_original','vertices_before','block_position','block_quaternion','block_scale')}
assert all(pre_checks.values()) and comparison['pre_intervention_exact_match'] is True
source_equal={k:b['source_manifest'][k]['sha256']==a['source_manifest'][k]['sha256'] for k in b['source_manifest']}
reference_equal={k:b['reference_manifest'][k]['sha256']==a['reference_manifest'][k]['sha256'] for k in b['reference_manifest']}
assert all(source_equal.values()) and all(reference_equal.values())
assert b['result']['settings']==a['result']['settings']=={'overlap':.005,'disabled_probe':'0','max_action_steps':15000}
actions_equal=[x['matrix']==y['matrix'] for x,y in zip(b['result']['action_audit'],a['result']['action_audit'])]
assert all(actions_equal)
steps_equal=[x['physics_steps']==y['physics_steps'] for x,y in zip(b['result']['action_audit'],a['result']['action_audit'])]
assert all(steps_equal)
max_reduction=(1-a['activation']['max_vertex_displacement_mm']/b['activation']['max_vertex_displacement_mm'])*100
tracked_reduction=(1-a['activation']['tracked_mean_displacement_mm']/b['activation']['tracked_mean_displacement_mm'])*100
audit={'pre_intervention_exact_checks':pre_checks,'source_hashes_identical':source_equal,
 'reference_hashes_identical':reference_equal,'action_matrices_identical':actions_equal,
 'execute_physics_step_counts_identical':steps_equal,'max_activation_displacement_reduction_pct':max_reduction,
 'tracked_mean_displacement_reduction_pct':tracked_reduction,
 'groups':{mode:{'run':g['path'].name,'source_hash_checks':g['source_checks'],
  'reference_hash_checks':g['reference_checks'],'phase_count':len(g['states']),
  'action_check_count':48,'activation':g['activation'],'physical_metrics_m':g['physical'],
  'stages':g['stages']} for mode,g in groups.items()},
 'conclusion':'Matched-state points1 alignment reduces the activation transient in this single scenario while preserving tested lift/release. Significant lift-stage geometric edge extension remains.',
 'limits':['One matched pair; no multi-seed, repeat-grasp, reset, yaw, or folding validation.',
 'USD array preservation does not expose internal solver data, but the matched intervention changes observed physics.',
 'Geometric edge ratios are not stress or a self-intersection test; sparse snapshots may miss temporal extrema.']}
(OUT/'pair_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
with (OUT/'stage_metrics.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.writer(f);writer.writerow(['group','phase','tracked_mean_z_mm','paired_gap_mean_mm','paired_gap_max_mm','anchor_edge_ratio_p95','anchor_edge_ratio_max'])
    for mode,g in groups.items():
        for n,s in g['stages'].items():writer.writerow([mode,n,s['tracked_mean_z_mm'],s['paired_gap_mean_mm'],s['paired_gap_max_mm'],*np.asarray(s['anchor_incident_edge_ratio_to_initial_min_median_p95_max'])[[2,3]]])

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
colors={'baseline':'#b32946','aligned':'#2378b6'}
fig,axs=plt.subplots(2,2,figsize=(13,9),layout='constrained')
before='enabled_before_first_step';after='enabled_after_first_step'
v=b['states'][before]['vertices'];ids=b['op']['anchor_indices']
roi=(v[:,0]<-.31)&(v[:,1]>-.34)&(v[:,1]<-.23)
for col,(mode,g) in enumerate(groups.items()):
    ax=axs[0,col];p=g['states'][after]['vertices']
    sc=ax.scatter(p[roi,0],p[roi,1],c=g['delta'][roi],cmap='magma',vmin=0,vmax=25,s=12)
    ax.scatter(p[ids,0],p[ids,1],s=25,facecolors='none',edgecolors='#00bca8',label='28 mapped anchors')
    ax.set(xlim=(-.405,-.31),ylim=(-.34,-.23),xlabel='x (m)',ylabel='y (m)',
      title=mode.capitalize()+' | activation max %.2f mm'%g['activation']['max_vertex_displacement_mm'])
    ax.set_aspect('equal');ax.legend(fontsize=8);ax.grid(alpha=.15)
fig.colorbar(sc,ax=axs[0,:].tolist(),label='Vertex displacement during first enabled step (mm)',shrink=.85)
ax=axs[1,0];x=np.arange(3)
for shift,(mode,g) in zip([-.18,.18],groups.items()):
    heights=[g['activation']['max_vertex_displacement_mm'],g['activation']['tracked_mean_displacement_mm'],np.percentile(g['delta'],99)]
    ax.bar(x+shift,heights,width=.36,color=colors[mode],label=mode.capitalize())
    for i,h in enumerate(heights):ax.text(i+shift,h+.4,'%.2f'%h,ha='center',fontsize=9)
ax.set(xticks=x,xticklabels=['All: max','Tracked: mean','All: P99'],ylabel='One-step displacement (mm)',ylim=(0,28),title='Activation displacement decreases')
ax.legend();ax.grid(axis='y',alpha=.15)
ax=axs[1,1]
for mode,g in groups.items():
    vals=np.sort(g['ratios'][after][g['local']]);ax.plot(vals,np.arange(1,94)/93*100,color=colors[mode],label=mode.capitalize())
ax.axvline(1,ls='--',lw=.8,color='black');ax.set(xlabel='Edge length / pre-reset length',ylabel='Anchor-incident edges at or below (%)',title='93 anchor-incident edges: first enabled step')
ax.legend();ax.grid(alpha=.15)
fig.suptitle('Matched-state control: original vs aligned points1\nIdentical pre-intervention vertices, rigid poses, original anchors, action matrices and step counts',fontsize=13)
fig.savefig(OUT/'activation_baseline_vs_aligned.png',dpi=180);plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(14,5.5),layout='constrained')
phases=[before,after,'02_grasp','03_lift','04_release']
phase_names=['Before ON','One step ON','Stable grasp','Lift','Released']
for mode,g in groups.items():
    z=[g['stages'][n]['tracked_mean_z_mm'] for n in phases]
    axs[0].plot(range(5),z,'-o',color=colors[mode],label=mode.capitalize())
    ratios=[g['stages'][n]['anchor_incident_edge_ratio_to_initial_min_median_p95_max'] for n in phases]
    axs[1].plot(range(5),[r[3] for r in ratios],'-o',color=colors[mode],label=mode.capitalize()+' max')
    axs[1].plot(range(5),[r[2] for r in ratios],'--',color=colors[mode],label=mode.capitalize()+' P95')
axs[0].set(ylabel='Tracked mean world z (mm)',title='Lift measured from stable grasp stays about 92.8 mm')
axs[1].set(ylabel='Edge length / pre-reset length',title='Lift-stage local edge extension remains')
axs[1].axhline(1,color='black',ls=':',lw=.8)
for ax in axs:
    ax.set_xticks(range(5),phase_names);ax.tick_params(axis='x',labelrotation=15);ax.legend(fontsize=9);ax.grid(alpha=.15)
fig.suptitle('Sparse phase snapshots | lower absolute lift height reflects removal of the initial cloth kick\nNo continuous-time maximum or material-quality certification',fontsize=13)
fig.savefig(OUT/'height_and_edge_ratios.png',dpi=180);plt.close(fig)

fig,axs=plt.subplots(2,2,figsize=(12,9),layout='constrained')
for row,(mode,g) in enumerate(groups.items()):
    for col,n in enumerate([after,'03_lift']):
        ax=axs[row,col];p=g['states'][n]['vertices'];e=g['edges'][g['local']]
        segments=p[e][:,:,[0,2]]
        lc=LineCollection(segments,cmap='coolwarm',norm=TwoSlopeNorm(vmin=-1,vcenter=0,vmax=1),linewidths=1.5)
        lc.set_array(np.log2(g['ratios'][n][g['local']]));ax.add_collection(lc)
        ax.scatter(p[ids,0],p[ids,2],s=10,c='black')
        both=np.vstack([other['states'][n]['vertices'][np.unique(e)] for other in groups.values()])
        ax.set(xlim=(both[:,0].min()-.005,both[:,0].max()+.005),ylim=(both[:,2].min()-.005,both[:,2].max()+.005),xlabel='x (m)',ylabel='z (m)',title=mode.capitalize()+' | '+('First enabled step' if col==0 else 'Lift')+'\nLocal max edge ratio %.3f'%g['ratios'][n][g['local']].max())
        ax.set_aspect('equal');ax.locator_params(axis='x',nbins=4);ax.grid(alpha=.15)
cb=fig.colorbar(lc,ax=axs.ravel().tolist(),label='3D edge length / pre-reset length',ticks=[-1,0,1],shrink=.75)
cb.ax.set_yticklabels(['0.5x','1x','2x'])
fig.suptitle('Local topology comparison | 93 edges incident to 28 anchors | XZ projection\nColour uses 3D lengths; large lift-stage extension persists in the aligned group',fontsize=13)
fig.savefig(OUT/'local_topology_comparison.png',dpi=180);plt.close(fig)
print('FULL_PAIR_AUDIT_OK')
print('MAX_ACTIVATION_REDUCTION_PCT',max_reduction)
print('TRACKED_MEAN_REDUCTION_PCT',tracked_reduction)
for mode,g in groups.items():print(mode,'ACTIVATION',g['activation'],'LIFT_LOCAL_MAX',g['stages']['03_lift']['anchor_incident_edge_ratio_to_initial_min_median_p95_max'][-1])
print('OUTPUT',OUT)
