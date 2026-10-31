"""Audit a new GPU result against the original-target hold; no Isaac imports."""
import json
import sys
from pathlib import Path
import numpy as np


def compare(current, reference):
    runs = [Path(current), Path(reference)]
    results = [json.loads((p / 'result.json').read_text()) for p in runs]
    for r in results:
        assert r['passed'] is True
        assert r['lift_hold_trace']['capture_complete'] is True
        for key in ('original_lift_trace_exact_checks', 'reference_replay_exact_checks'):
            assert r[key] and all(r[key].values()), key
    with np.load(runs[0] / 'lift_hold_trace/frames.npz') as a, np.load(runs[1] / 'lift_hold_trace/frames.npz') as b:
        boundary = int(a['hold_start_frame'])
        assert boundary == int(b['hold_start_frame']) == 49
        assert len(a['vertices']) == len(b['vertices']) == 230
        keys = ('vertices', 'block_position', 'block_quaternion', 'block_scale',
                'ee_position', 'ee_quaternion', 'anchor_targets', 'physics_steps')
        prefix = {k: bool(np.array_equal(a[k][:50], b[k][:50])) for k in keys}
        assert all(prefix.values()), prefix
        assert np.array_equal(a['hold_ee_target'], a['ee_position'][boundary])
        assert np.array_equal(a['lift_ee_target'], b['lift_ee_target'])
        metrics = {}
        for name, data, result in zip(('measured_target', 'original_target'), (a, b), results):
            metrics[name] = {
                'ee_extra_z_mm': float((data['ee_position'][-1, 2]-data['ee_position'][boundary, 2])*1000),
                'block_extra_z_mm': float((data['block_position'][-1, 2]-data['block_position'][boundary, 2])*1000),
                'last_hold_window': result['lift_hold_trace']['last_hold_window'],
                'cloth_rise_m': result['cloth_rise'],
                'release_drop_m': result['cloth_drop'],
                'release_block_drift_m': result['release_block_drift'],
            }
    report = {'prefix_exact_checks': prefix, 'metrics': metrics,
              'note': 'Measured position is a controller target, not a rigid lock or proof of cloth equilibrium.'}
    (runs[0] / 'measured_hold_comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('MEASURED_HOLD_COMPARISON_OK')


if __name__ == '__main__':
    compare(*sys.argv[1:])
