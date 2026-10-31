"""Compare fresh mass branches without assuming equal settled states or step counts."""
import json
from pathlib import Path
import sys
import numpy as np
from mass_experiment import mass_readback_stats, MASS_READBACK_RTOL


def verify(run, mode):
    run = Path(run)
    r = json.loads((run/'result.json').read_text())
    assert r['passed'] is True and r['mass_mode'] == mode
    assert r['lift_hold_trace']['capture_complete'] is True
    assert all(all(a['checks'].values()) for a in r['action_audit'])
    assert set(r['mass_audit']['reads']) == {'after_start','before_actions','after_release'}
    expected = .01 if mode == 'baseline' else .0001
    assert r['particle_mass_requested_kg'] == expected
    for label in r['mass_audit']['reads']:
        masses = np.load(run/('particle_masses_'+label+'.npy'))
        stats = mass_readback_stats(masses, expected)
        assert all(stats['checks'].values()), stats
        assert r['mass_audit']['reads'][label] == stats
    if mode == 'baseline':
        for key in ('original_lift_trace_exact_checks','reference_replay_exact_checks','baseline_full_trace_checks'):
            assert r[key] and all(r[key].values()), key
    return r


def compare(baseline, light, output):
    runs = {'baseline':Path(baseline),'light':Path(light)}
    results = {mode:verify(path,mode) for mode,path in runs.items()}
    mass_ratio_checks = {}
    for label in ('after_start','before_actions','after_release'):
        base_mass = np.load(runs['baseline']/('particle_masses_'+label+'.npy'))
        light_mass = np.load(runs['light']/('particle_masses_'+label+'.npy'))
        ratio = light_mass.astype(float)/base_mass.astype(float)
        mass_ratio_checks[label] = {'min':float(ratio.min()), 'max':float(ratio.max()),
                                  'expected':0.01, 'relative_tolerance':2*MASS_READBACK_RTOL}
        assert np.allclose(ratio,0.01,rtol=2*MASS_READBACK_RTOL,atol=0), mass_ratio_checks[label]
    for directory in ('source','mass_source','reference'):
        manifests = [json.loads((p/directory/'manifest.json').read_text()) for p in runs.values()]
        assert {k:v['sha256'] for k,v in manifests[0].items()} == {k:v['sha256'] for k,v in manifests[1].items()}, directory
    with np.load(runs['baseline']/'cloth_constructed.npz') as a, np.load(runs['light']/'cloth_constructed.npz') as b:
        assert set(a.files)==set(b.files)
        initial = {k:bool(np.array_equal(a[k],b[k])) for k in a.files}
        assert all(initial.values()), initial
    assert results['baseline']['mass_audit']['particle_system']==results['light']['mass_audit']['particle_system']
    metrics = {}
    states = {}
    for mode,run in runs.items():
        r=results[mode]
        with np.load(run/'lift_hold_trace/frames.npz') as f:
            h=int(f['hold_start_frame']); v=f['vertices']; edges=f['edges']
            assert int(f['expected_hold_steps'])==180 and len(v)==h+181
            assert np.all(np.diff(f['physics_steps'])==1)
            assert np.all(f['phase_code'][:h+1]==0) and np.all(f['phase_code'][h+1:]==1)
            assert np.array_equal(f['hold_ee_target'],f['ee_position'][h])
            ratios=np.linalg.norm(v[:,edges[:,1]]-v[:,edges[:,0]],axis=2)/f['rest_edge_lengths']
            assert np.isfinite(ratios).all()
            peak_frame,peak_edge=np.unravel_index(ratios.argmax(),ratios.shape)
            gaps=np.linalg.norm(v[:,f['anchor_indices']]-f['anchor_targets'],axis=2)*1000
            delta=np.linalg.norm(np.diff(v[-31:],axis=0),axis=2)*1000
            metrics[mode]={'particle_mass_kg':r['particle_mass_requested_kg'],
              'total_mass_kg':r['mass_audit']['reads']['after_start']['total_kg'],
              'lift_world_steps':h, 'samples':len(v),
              'max_ratio_at_lift_start':float(ratios[0].max()),
              'max_ratio_at_hold_start':float(ratios[h].max()),
              'max_ratio_at_hold_end':float(ratios[-1].max()),
              'whole_trace_peak_ratio':float(ratios[peak_frame,peak_edge]),
              'peak_edge':edges[peak_edge].tolist(),
              'peak_edge_anchor_endpoints':int(f['edge_anchor_endpoint_count'][peak_edge]),
              'peak_time_relative_to_hold_s':float((peak_frame-h)*r['lift_hold_trace']['physics_dt']),
              'late_max_ratio_range':[float(ratios[-30:].max(axis=1).min()),float(ratios[-30:].max(axis=1).max())],
              'hold_ee_extra_z_mm':float((f['ee_position'][-1,2]-f['ee_position'][h,2])*1000),
              'actual_lift_ee_z_mm':float((f['ee_position'][h,2]-f['ee_position'][0,2])*1000),
              'hold_max_paired_gap_mm':float(gaps[h+1:].max()),
              'late_particle_step_displacement_max_mm':float(delta.max()),
              'cloth_rise_m':r['cloth_rise'],'release_drop_m':r['cloth_drop'],
              'release_block_drift_m':r['release_block_drift'],
              'anchor_indices':f['anchor_indices'].tolist(),
              'activation':r['alignment_metrics']['activation']}
        with np.load(run/'00_settled.npz') as f:
            states[mode]=f['vertices'].copy()
    displacement=np.linalg.norm(states['baseline']-states['light'],axis=1)*1000
    report={'constructed_geometry_and_springs_exact_checks':initial,'metrics':metrics,
      'measured_mass_ratio_checks':mass_ratio_checks,
      'settled_state_difference_mm':{'max':float(displacement.max()),'mean':float(displacement.mean())},
      'same_anchor_indices':metrics['baseline']['anchor_indices']==metrics['light']['anchor_indices'],
      'interpretation_limit':'Mass changed before first reset. Settled state, adaptive waypoints and actual motion may differ. This is a whole-policy mass sensitivity comparison, not matched-state isolation or real-cloth calibration.'}
    Path(output).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    print('MASS_PAIR_COMPARISON_OK',flush=True)


if __name__=='__main__':
    compare(*sys.argv[1:])
