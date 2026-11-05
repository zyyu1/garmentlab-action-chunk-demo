"""Static audit for the recovery-hold120 candidate (no simulation)."""
import difflib
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
app = root / 'app'
base = root.parent / 'a5-rc2-pfs1-observation-v2-rc8b' / 'app'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

a = (base / 'a5_recovery.py').read_text(encoding='utf-8').splitlines()
b = (app / 'a5_recovery.py').read_text(encoding='utf-8').splitlines()
diff = list(difflib.unified_diff(a, b, fromfile='rc8b/a5_recovery.py', tofile='hold120/a5_recovery.py', n=3))
added = [line[1:] for line in diff if line.startswith('+') and not line.startswith('+++')]
removed = [line[1:] for line in diff if line.startswith('-') and not line.startswith('---')]
added_text = '\n'.join(added)
forbidden = ['_set_garment_world_positions', '_clear_garment_velocities', 'ParticleMaterial',
             'control.move', 'control.grasp', 'control.ungrasp', 'GripperCommand',
             'robot_goto_position', 'set_velocities', 'b._settle(']
forbidden_hits = [x for x in forbidden if x in added_text]
step_calls = added_text.count('b._env.step()')
config = json.loads((app / 'a5-rc2-pfs1-observation-v2.json').read_text())

check = {
    'removed_lines': len(removed),
    'added_lines': len(added),
    'forbidden_hits': forbidden_hits,
    'physics_step_calls_in_added': step_calls,
    'has_run_recovery_hold': 'def run_recovery_hold' in added_text,
    'default_steps_120': 'steps=120' in added_text,
    'call_with_default': 'run_recovery_hold(b, out, result, retreat_end)' in added_text,
    'no_removed_action_logic': len(removed) == 0,
    'hold_steps_config': config['recovery_hold']['steps'],
    'hold_dt_config': config['recovery_hold']['dt_s'],
    'action_count_unchanged': 'result[\'call_horizons\']' not in added_text,
    'core_files_identical': {n: sha(app / n) == sha(base / n) for n in
                             ('a5_capture.py', 'pfs1_observation_v2.py', 'stage4_success_v1.py',
                              'stage4-success-v1.json', 'square-initial-plan.json')},
    'source_diff': diff,
}
ok = bool(len(removed) == 0 and not forbidden_hits and step_calls == 1
          and check['has_run_recovery_hold'] and check['default_steps_120']
          and check['call_with_default'] and check['hold_steps_config'] == 120
          and abs(check['hold_dt_config'] - 1 / 60) < 1e-12
          and all(check['core_files_identical'].values()))
check['result'] = 'pass' if ok else 'fail'
(root / 'static-audit.json').write_text(json.dumps(check, indent=2) + '\n', encoding='utf-8')
print('STATIC_AUDIT', check['result'], 'removed', len(removed), 'added', len(added),
      'step_calls', step_calls, 'forbidden', forbidden_hits)
print('core', check['core_files_identical'])
