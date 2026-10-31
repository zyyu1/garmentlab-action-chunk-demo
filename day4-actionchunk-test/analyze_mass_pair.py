"""Offline audit of downloaded mass branches and scientific comparison plots."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from compare_mass_pair import compare

root=Path(__file__).resolve().parent/'results/day4-mass-pair-V0AIYmBy'
out=root/'analysis'
out.mkdir(exist_ok=True)
runs={mode:next(root.glob('day4-mass-'+mode+'-*')) for mode in ('baseline','light')}
checks={}
for mode,run in runs.items():
    checks[mode]={}
    for folder in ('source','mass_source','reference'):
        manifest=json.loads((run/folder/'manifest.json').read_text())
        ok={k:hashlib.sha256((run/folder/k).read_bytes()).hexdigest()==v['sha256'] for k,v in manifest.items()}
        assert all(ok.values()),(mode,folder)
        checks[mode][folder]=ok
compare(runs['baseline'],runs['light'],out/'recomputed_comparison.json')
previous=json.loads((root/'comparison.json').read_text())
recomputed=json.loads((out/'recomputed_comparison.json').read_text())
assert previous==recomputed
old=root.parent/'day4-aligned-measured-hold-20261025-044808-480399/lift_hold_trace/frames.npz'
with np.load(old) as a,np.load(runs['baseline']/'lift_hold_trace/frames.npz') as b:
    assert all(np.array_equal(a[k],b[k]) for k in a.files)
details={}
fig,axs=plt.subplots(2,2,figsize=(11,8),layout='constrained')
for mode,run in runs.items():
    result=json.loads((run/'result.json').read_text())
    with np.load(run/'lift_hold_trace/frames.npz') as src:
        f={k:src[k].copy() for k in src.files}
    h=int(f['hold_start_frame']);dt=result['lift_hold_trace']['physics_dt']
    v=f['vertices'];e=f['edges'];cls=f['edge_anchor_endpoint_count']
    assert all(np.isfinite(a).all() for a in f.values())
    lengths=np.linalg.norm(v[:,e[:,1]]-v[:,e[:,0]],axis=2)
    ratios=lengths/f['rest_edge_lengths']
    gaps=np.linalg.norm(v[:,f['anchor_indices']]-f['anchor_targets'],axis=2)*1000
    speed=np.r_[0,np.linalg.norm(np.diff(f['ee_position'],axis=0),axis=1)/dt]*1000
    particle=np.linalg.norm(np.diff(v,axis=0),axis=2)*1000
    t=(np.arange(len(v))-h)*dt
    with (run/'lift_hold_trace/steps.csv').open() as stream:rows=list(csv.DictReader(stream))
    assert len(rows)==len(v)
    for i,row in enumerate(rows):
        assert int(row['physics_step'])==f['physics_steps'][i]
        for key,val in {'all_edge_ratio_max':ratios[i].max(),
                        'paired_gap_max_mm':gaps[i].max(),
                        'ee_speed_m_s':speed[i]/1000}.items():
            assert np.isclose(float(row[key]),val,rtol=1e-5,atol=2e-6),(mode,i,key)
    edge=int(np.flatnonzero(np.all(e==[8958,9025],axis=1))[0])
    details[mode]={'mass_readback':result['mass_audit']['reads'],
       'source_hashes_verified':True,'recomputed_csv_metrics_match':True,
       'boundary_peak_ratio':float(ratios[:,cls==1].max()),
       'internal_peak_ratio':float(ratios[:,cls==2].max()),
       'outside_peak_ratio':float(ratios[:,cls==0].max()),
       'worst_edge_hold_end_length_mm':float(lengths[-1,edge]*1000),
       'late_ee_speed_max_mm_s':float(speed[-30:].max()),
       'late_particle_step_mean_mm':float(particle[-30:].mean()),
       'late_particle_step_max_mm':float(particle[-30:].max()),
       'hold_end_to_start_max_ratio_change':float(ratios[-1].max()-ratios[h].max())}
    label='Baseline (~99.46 kg)' if mode=='baseline' else 'Light (~0.995 kg)'
    axs[0,0].plot(t,ratios.max(axis=1),label=label)
    axs[0,1].plot(t,(f['ee_position'][:,2]-f['ee_position'][0,2])*1000,label=label)
    axs[1,0].plot(t,gaps.max(axis=1),label=label)
    axs[1,1].plot(t[-30:],ratios[-30:].max(axis=1),label=label)
for ax,title,ylabel in zip(axs.flat,['Largest edge length ratio','Measured end-effector lift',
                                  'Largest paired anchor gap','Final 30 hold samples'],
                                  ['Length / initial length','Vertical change (mm)','Geometric gap (mm)','Length / initial length']):
    ax.set(title=title,xlabel='Time relative to hold start (s)',ylabel=ylabel)
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    if ax!=axs[1,1]:ax.axvline(0,color='gray',linestyle='--',linewidth=.8)
fig.suptitle('Mass sensitivity: same control policy, different settled cloth states\nMass ratio verified in physics readback; not real-cloth calibration')
fig.savefig(out/'mass_comparison.png',dpi=160)
plt.close(fig)
audit={'hash_checks':checks,'baseline_full_trace_matches_previous':True,
       'saved_comparison_matches_recomputation':True,'details':details,
       'constructed_arrays_present':list(previous['constructed_geometry_and_springs_exact_checks']),
       'spring_array_caveat':'Only points and topology were present at constructor capture. No cross-branch cooked spring-array identity claim.'}
(out/'mass_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
print('OFFLINE_MASS_AUDIT_OK')
print(json.dumps(details,indent=2))
