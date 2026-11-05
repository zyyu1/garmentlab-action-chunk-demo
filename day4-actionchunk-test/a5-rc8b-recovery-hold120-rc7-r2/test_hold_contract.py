"""Offline tests for the hold applicability contract (no simulation)."""
import importlib.util
import json
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('hold_contract', root / 'hold_contract.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

trace = {
    'vertices': np.zeros((121, 441, 3)),
    'fd_velocities': np.zeros((120, 441, 3)),
    'fd_interval_s': np.full(120, 1 / 60),
    'absolute_step': np.arange(1000, 1121),
    'sim_time_s': np.arange(121) / 60,
    'control_target': np.repeat(np.array([[0.0, 0.0, 0.0, 0.0]]), 121, axis=0),
    'holding': np.zeros(121, bool),
    'logical_attached': np.zeros(121, bool),
    'command_holding': np.zeros(121, bool),
    'attachment_enabled_any': np.zeros(121, bool),
    'enabled_slots': np.zeros((121, 3), bool),
}
hold = {'schema': 'recovery-hold-v1', 'steps_requested': 120, 'completed_steps': 120,
        'frames': 121, 'dt_s': 1 / 60, 'duration_s': 2.0, 'error': None,
        'checks': {'all_frames_ok': True, 'all_time_ok': True}}

cases = []
ok, app, err = m.evaluate('flat', {}, False)
cases.append({'case': 'valid_l1_na', 'ok': ok, 'applicable': app, 'error': err})
assert ok is True and app is False and err is None
ok, app, err = m.evaluate('flat', {'recovery_hold': hold}, True)
assert ok is False and app is False
cases.append({'case': 'l1_unexpected_hold_rejected', 'ok': ok, 'applicable': app, 'error': err})
ok, app, err = m.evaluate('perturbed', {'recovery_hold': hold}, True, trace)
cases.append({'case': 'valid_l2_hold', 'ok': ok, 'applicable': app, 'error': err})
assert ok is True and app is True and err is None
bad = dict(hold); bad['completed_steps'] = 119
ok, app, err = m.evaluate('crumpled', {'recovery_hold': bad}, True, trace)
assert ok is False and app is True
cases.append({'case': 'l2_wrong_steps_rejected', 'ok': ok, 'applicable': app, 'error': err})
ok, app, err = m.evaluate('perturbed', {}, False)
assert ok is False and app is True
cases.append({'case': 'l2_missing_hold_rejected', 'ok': ok, 'applicable': app, 'error': err})
ok, app, err = m.evaluate('perturbed', {'recovery_hold': hold}, False)
assert ok is False and app is True
cases.append({'case': 'l2_missing_trace_rejected', 'ok': ok, 'applicable': app, 'error': err})

(root / 'hold_contract_test.json').write_text(json.dumps(cases, indent=2) + '\n', encoding='utf-8')
print('HOLD_CONTRACT_TEST_OK', [c['case'] for c in cases])
