"""Offline controller tests with a stub backend (no Isaac Sim)."""
import json
import os
import tempfile
from pathlib import Path

from formal_driver import Controller, Pause

BASE = Path(tempfile.mkdtemp(prefix='formal_hold120_test_'))
results = []


def slots(seed_modes):
    initials = []
    matrix = []
    for i, (seed, level, modes) in enumerate(seed_modes):
        initials.append({'seed': seed, 'level': level,
                         'runner': 'run-square-initial.sh' if level == 'flat' else 'run-square-initial-stripfold.sh'})
        for mode in modes:
            matrix.append({'slot': len(matrix) + 1, 'seed': seed, 'level': level,
                           'mode': mode, 'initial_index': i})
    return {'schema': 'test', 'initials': initials, 'slots': matrix,
            'counts': {'initials': len(initials), 'slots': len(matrix)}}


class StubBackend:
    def __init__(self, plan, gate_ok=True):
        self.plan = plan; self.calls = []; self.gen = 0
        self.gate_ok = gate_ok

    def gate(self):
        self.calls.append('gate')
        return {'exit': 0 if self.gate_ok else 2, 'output': ''}

    def generate_initial(self, seed, level):
        self.calls.append(('init', seed)); self.gen += 1
        d = BASE / ('init-%d' % seed); d.mkdir(exist_ok=True)
        (d / 'result.json').write_text('{}')
        return {'exit': 0, 'dir': str(d)}

    def run_episode(self, initial, seed, mode):
        self.calls.append(('run', seed, mode))
        spec = self.plan[(seed, mode)]
        d = BASE / ('run-%d-%s' % (seed, mode)); d.mkdir(exist_ok=True)
        actions = [{'label': 'fold_approach', 'target_pose': [0.0, 0.0, 1.0, 0.0]}]
        if spec.get('missing'):
            rp = d / 'result.json'
            if rp.exists(): rp.unlink()
        else:
            (d / 'result.json').write_text(json.dumps({'actions': actions}))
        if seed >= 4200:
            (d / 'recovery_hold_metadata.json').write_text(json.dumps(
                {'completed_steps': spec.get('hold', 120), 'frames': 121, 'duration_s': 2.0}))
        (d / 'a5-verdict.json').write_text(json.dumps({'runner_exit': spec.get('entry', 0), 'status': spec.get('quality', 'accepted')}))
        return {'exit': spec.get('entry', 0), 'dir': str(d)}

    def audit(self, result_dir, seed, mode, single_dir=None):
        self.calls.append(('audit', seed, mode))
        spec = self.plan[(seed, mode)]
        sem = {'quality_status': spec.get('quality', 'accepted'),
               'file_complete': True, 'observation_semantics_valid': True,
               'overall_valid': True, 'hold_applicable': seed >= 4200,
               'recovery_hold': True}
        return {'exit': spec.get('audit', 0), 'semantics': sem}

    def pair_ok(self, single_dir, arc_dir, seed):
        spec = self.plan[(seed, 'arc4')]
        return spec.get('pair', True)


def run_case(name, data, plan, total=None, prestarted=None, lock=False, gate_ok=True):
    d = BASE / name; d.mkdir(exist_ok=True)
    sp = d / 'slots.json'; sp.write_text(json.dumps(data))
    state = d if lock else d / 'state'
    state.mkdir(parents=True, exist_ok=True)
    if prestarted:
        with (state / 'attempts.jsonl').open('w') as f:
            f.write(json.dumps(prestarted) + '\n')
    if lock:
        (d / 'driver.lock').mkdir()
    b = StubBackend(plan, gate_ok)
    c = Controller(sp, state, b, total_slots=total or len(data['slots']))
    try:
        s = c.run(); return {'case': name, 'paused': False, 'summary': s, 'calls': b.calls}
    except Pause as exc:
        return {'case': name, 'paused': True, 'error': str(exc), 'calls': b.calls}


# 1 gate failure: no generation/rollout
mat = slots([(4110, 'flat', ['single']), (4210, 'perturbed', ['single'])])
plan = {(4110, 'single'): {}, (4210, 'single'): {}}
r = run_case('gate_fail', mat, plan, gate_ok=False)
assert r['paused'] and r['calls'] == ['gate']
results.append(r)

# 2 normal two-seed, same initial reused by two modes
mat = slots([(4110, 'flat', ['single', 'arc4']), (4210, 'perturbed', ['single', 'arc4'])])
plan = {(4110, 'single'): {}, (4110, 'arc4'): {}, (4210, 'single'): {}, (4210, 'arc4'): {}}
r = run_case('normal_reuse', mat, plan)
assert not r['paused'] and r['summary']['accepted'] == 4 and r['summary']['attempts'] == 4
assert r['calls'].count(('init', 4110)) == 1 and r['calls'].count(('init', 4210)) == 1
results.append(r)

# 3 rejected saved, continue
plan = {(4110, 'single'): {'quality': 'rejected'}, (4110, 'arc4'): {}}
mat = slots([(4110, 'flat', ['single', 'arc4'])])
r = run_case('rejected_continue', mat, plan)
assert not r['paused'] and r['summary']['rejected'] == 1 and r['summary']['accepted'] == 1
results.append(r)

# 4 audit anomaly pauses
plan = {(4110, 'single'): {'audit': 5}, (4110, 'arc4'): {}}
mat = slots([(4110, 'flat', ['single', 'arc4'])])
r = run_case('audit_pause', mat, plan)
assert r['paused'] and not any(c[0] == 'run' and c[2] == 'arc4' for c in r['calls'] if isinstance(c, tuple))
results.append(r)

# 5 missing result pauses
plan = {(4110, 'single'): {'missing': True}, (4110, 'arc4'): {}}
mat = slots([(4110, 'flat', ['single', 'arc4'])])
r = run_case('missing_result', mat, plan)
assert r['paused']
results.append(r)

# 6 unfinished attempt pauses without new run
plan = {(4110, 'single'): {}}
mat = slots([(4110, 'flat', ['single'])])
r = run_case('unfinished', mat, plan, prestarted={'state': 'started', 'seed': 4110, 'mode': 'single'})
assert r['paused'] and ('run', 4110, 'single') not in r['calls']
results.append(r)

# 7 lock prevents concurrent driver
mat = slots([(4110, 'flat', ['single'])])
r = run_case('locked', mat, {(4110, 'single'): {}}, lock=True)
assert r['paused'] and 'LOCKED' in r['error']
results.append(r)

# 8 pair mismatch pauses
plan = {(4110, 'flat', ['single', 'arc4'])} if False else {(4110, 'single'): {}, (4110, 'arc4'): {'pair': False}}
mat = slots([(4110, 'flat', ['single', 'arc4'])])
r = run_case('pair_mismatch', mat, plan)
assert r['paused'] and 'PAIR_MISMATCH' in r['error']
results.append(r)

# 9 summary null rate for zero attempts
mat = slots([(4110, 'flat', ['single'])])
(BASE / 'empty_slots.json').write_text(json.dumps(mat))
c = Controller(BASE / 'empty_slots.json', BASE / 'empty_state', StubBackend({}), total_slots=1)
s = c.summary()
assert s['attempts'] == 0 and s['rejection_rate'] is None and s['not_attempted'] == 1
results.append({'case': 'summary_null_rate', 'summary': s})


# 10 completed failed slot is skipped on rerun
mat = slots([(4110, 'flat', ['single', 'arc4'])])
state = BASE / 'skip_completed' / 'state'; state.mkdir(parents=True)
(state / 'attempts.jsonl').write_text(json.dumps({'state': 'finished', 'slot': 1, 'seed': 4110,
    'level': 'flat', 'mode': 'single', 'quality_status': 'rejected', 'result_dir': str(BASE / 'run-4110-single')}) + '\n')
sp = BASE / 'skip_completed' / 'slots.json'; sp.write_text(json.dumps(mat))
b = StubBackend({(4110, 'single'): {'quality': 'rejected'}, (4110, 'arc4'): {}})
c = Controller(sp, state, b, total_slots=2)
s = c.run()
assert not any(x == ('run', 4110, 'single') for x in b.calls if isinstance(x, tuple))
assert s['rejected'] == 1 and s['accepted'] == 1
results.append({'case': 'skip_completed_failure', 'summary': s, 'calls': b.calls})

print(json.dumps(results, indent=2))
print('FORMAL_DRIVER_TESTS_OK', len(results))
