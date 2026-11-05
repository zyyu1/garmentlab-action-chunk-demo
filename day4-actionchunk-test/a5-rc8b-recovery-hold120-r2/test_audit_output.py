"""Offline check for the HOLD120 audit output contract (no simulation)."""
import importlib.util
import json
from pathlib import Path

root = Path(__file__).resolve().parent
path = root / 'audit_hold120_case.py'
spec = importlib.util.spec_from_file_location('audit_hold120_case', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

dummy = {'seed': 4202, 'mode': 'single', 'level': 'perturbed',
         'recovery_hold': True, 'file_complete': True,
         'observation_semantics_valid': True, 'quality_status': 'accepted',
         'overall_valid': True}
assert mod.check_output_contract(dummy) is True
bad = dict(dummy); bad.pop('recovery_hold')
try:
    mod.check_output_contract(bad)
except KeyError as exc:
    print('MISSING_KEY_REJECTED', exc)
else:
    raise SystemExit('missing recovery_hold was not rejected')
wrong_type = dict(dummy); wrong_type['recovery_hold'] = 'yes'
try:
    mod.check_output_contract(wrong_type)
except TypeError as exc:
    print('WRONG_TYPE_REJECTED', exc)
else:
    raise SystemExit('non-bool recovery_hold was not rejected')

out = {'required_keys': list(mod.REQUIRED_OUT_KEYS),
       'accepts_complete_output': True,
       'rejects_missing_key': True,
       'rejects_non_bool': True}
(root / 'audit_output_check.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
print('AUDIT_OUTPUT_CHECK_OK')
