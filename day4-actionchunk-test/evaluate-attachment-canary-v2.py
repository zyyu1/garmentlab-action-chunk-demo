"""Frozen diagnostic thresholds; these are not Day4 fold acceptance thresholds."""
import json
import sys
from pathlib import Path
import numpy as np

root = Path(sys.argv[1])
case = sys.argv[2]
r = json.loads((root/case/'result.json').read_text())
t = json.loads((root/case/'trace.json').read_text())
assert r['completed'] and not r['errors'] and len(t) == 181
assert [x['step'] for x in t] == list(range(181))
angles = np.array([x['angle_rad'] for x in t])
pivot = max(x['pivot_error_m'] for x in t)
checks = {'pivot_within_5mm': pivot < .005}
diagnosis = 'recording_or_configuration_failed'
if case == 'rigid':
    checks.update(rotation_over_0_1rad=angles[1:121].max() > .1,
                  early_positive_y_rotation=max(x['rotvec'][1] for x in t[1:61]) > .05)
    diagnosis = 'rigid_joint_valid' if all(checks.values()) else diagnosis
elif case == 'disabled':
    checks.update(no_attachment=all(not x['enabled'] for x in t),
                  carrier_stays_within_0_01rad=angles.max() < .01,
                  cloth_falls_over_0_1m=t[0]['anchor_z_mean']-t[60]['anchor_z_mean'] > .1)
    diagnosis = 'disabled_control_valid' if all(checks.values()) else diagnosis
else:
    checks.update(enabled_before_open=all(x['enabled'] for x in t[:121]),
                  disabled_after_open=all(not x['enabled'] for x in t[121:]),
                  held_anchor_error_within_5mm=max(x['anchor_error_m'] for x in t[1:121]) < .005)
    disabled = json.loads((root/'disabled'/'trace.json').read_text())
    reaction = max(x['rotvec'][1]-y['rotvec'][1] for x,y in zip(t[1:121],disabled[1:121])) > .05
    release = (t[120]['anchor_z_mean']-t[180]['anchor_z_mean'] > .05
               and t[180]['anchor_error_m'] > .05)
    checks.update(open_separation=release)
    diagnosis = ('attachment_reaction_and_open_supported' if reaction else 'valid_response_below_preregistered_threshold') if all(checks.values()) else diagnosis
    checks['positive_y_reaction_over_0_05rad'] = reaction
if case != 'rigid':
    reads = r.get('cloth_mass_readbacks', {})
    mass_valid = set(reads) == {'0', '120', '180'} and all(
        x['matches_authored_total_rtol_0_002'] and x['unchanged_from_start'] for x in reads.values())
    checks['runtime_cloth_mass_matches_authored_and_stable'] = mass_valid
    if not mass_valid:
        diagnosis = 'mass_configuration_mismatch_or_recording_failed'
checks = {name: bool(value) for name, value in checks.items()}
summary = {'case':case, 'checks':checks, 'diagnosis':diagnosis,
           'maximum_angle_rad':float(angles.max()), 'max_pivot_error_m':pivot,
           'passed':all(checks.values()), 'formal_day4_success':False,
           'limits':'One fixed synthetic configuration; negative result does not prove API universally one-way.'}
(root/case/'assessment.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print(json.dumps(summary,indent=2))
if not summary['passed']:
    raise SystemExit(2)
