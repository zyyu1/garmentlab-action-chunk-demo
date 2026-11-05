"""Offline tests for the minimum acceptance driver (no Isaac Sim)."""
import json
import tempfile
from pathlib import Path

from minimum_driver import MinimumController, Pause

BASE = Path(tempfile.mkdtemp(prefix='minimum_hold120_test_'))
LEVELS = [('flat', list(range(4110, 4130))), ('perturbed', list(range(4210, 4230))),
          ('crumpled', list(range(4310, 4330)))]


def make_slots():
    slots = []; screens = []
    for level, seeds in LEVELS:
        for i, seed in enumerate(seeds, 1):
            slots.append({'slot': len(slots) + 1, 'seed': seed, 'level': level,
                          'mode': 'single', 'level_index': i})
            if i <= 10:
                screens.append({'level': level, 'seed': seed, 'level_index': i})
    return {'initials': 60, 'slots': slots, 'screenshot_seeds': screens}


class StubBackend:
    def __init__(self, quality=None, audit_fail=None, gate_ok=True):
        self.quality = quality or {}
        self.audit_fail = audit_fail or set()
        self.gate_ok = gate_ok
        self.calls = []

    def gate(self):
        self.calls.append('gate')
        return {'exit': 0 if self.gate_ok else 2, 'output': ''}

    def generate_initial(self, seed, level):
        self.calls.append(('init', seed))
        d = BASE / 'inits' / ('%s-%s' % (level, seed)); d.mkdir(parents=True, exist_ok=True)
        (d / 'result.json').write_text('{}')
        (d / 'initial.png').write_bytes(b'png-%d' % seed)
        (d / 'initial_geometry.npz').write_bytes(b'geom-%d' % seed)
        return {'exit': 0, 'dir': str(d)}

    def run_episode(self, initial, seed, mode):
        self.calls.append(('run', seed))
        d = BASE / 'runs' / ('%s-%s' % (seed, mode)); d.mkdir(parents=True, exist_ok=True)
        (d / 'result.json').write_text(json.dumps({'actions': [{'label': 'fold_approach',
                                                                'target_pose': [0, 0, 1, 0]}]}))
        (d / 'a5-verdict.json').write_text(json.dumps({'runner_exit': 0, 'status': 'x'}))
        return {'exit': 0, 'dir': str(d)}

    def audit(self, result_dir, seed, mode):
        self.calls.append(('audit', seed))
        q = self.quality.get(seed, 'accepted')
        rc = 5 if seed in self.audit_fail else 0
        return {'exit': rc, 'semantics': {'quality_status': q, 'file_complete': True,
                                          'observation_semantics_valid': True,
                                          'overall_valid': True, 'hold_applicable': seed >= 4200,
                                          'recovery_hold': True}}


def run_case(name, backend, slots=None, lock=False):
    d = BASE / name; d.mkdir(parents=True, exist_ok=True)
    state = d / 'state'; state.mkdir(exist_ok=True)
    sp = d / 'slots.json'; sp.write_text(json.dumps(slots or make_slots()))
    if lock:
        (state / 'driver.lock').mkdir()
    ctl = MinimumController(sp, state, backend)
    try:
        return {'case': name, 'paused': False, 'result': ctl.run(), 'calls': backend.calls}
    except Pause as e:
        return {'case': name, 'paused': True, 'error': str(e), 'calls': backend.calls}


results = []

r = run_case('normal', StubBackend())
assert not r['paused'] and r['result']['passed']
assert all(x['successes'] == 5 and x['attempts'] == 5 for x in r['result']['levels'])
assert r['calls'].count('gate') == 1
assert len([c for c in r['calls'] if isinstance(c, tuple) and c[0] == 'init']) == 30
assert len([c for c in r['calls'] if isinstance(c, tuple) and c[0] == 'run']) == 15
results.append({'case': 'five_success_stop', 'levels': r['result']['levels']})

q = {}
for _, seeds in LEVELS:
    q[seeds[0]] = 'rejected'; q[seeds[1]] = 'rejected'
r = run_case('rejected_continue', StubBackend(q))
assert not r['paused'] and r['result']['passed']
assert all(x['successes'] == 5 and x['attempts'] == 7 for x in r['result']['levels'])
results.append({'case': 'rejected_continue', 'levels': r['result']['levels']})

q = {s: 'rejected' for _, seeds in LEVELS for s in seeds}
r = run_case('max_attempts_fail', StubBackend(q))
assert not r['paused'] and not r['result']['passed']
assert all(x['attempts'] == 20 and x['stop_reason'] == 'attempt_limit_20' for x in r['result']['levels'])
results.append({'case': 'attempt_limit_fail', 'levels': r['result']['levels']})

b = StubBackend(audit_fail={4110})
r = run_case('audit_error', b)
assert r['paused'] and 'AUDIT_FAILED' in r['error']
assert not any(c[0] == 'run' and c[1] == 4111 for c in r['calls'] if isinstance(c, tuple))
results.append({'case': 'audit_error_pause', 'error': r['error']})

b = StubBackend(gate_ok=False)
r = run_case('gate_fail', b)
assert r['paused'] and r['calls'] == ['gate']
results.append({'case': 'gate_fail_no_work'})

b = StubBackend()
r = run_case('locked', b, lock=True)
assert r['paused'] and 'LOCKED' in r['error'] and r['calls'] == []
results.append({'case': 'lock_blocks'})

print(json.dumps(results, indent=2))
print('MINIMUM_DRIVER_TESTS_OK', len(results))
