"""Offline Stage 6 checks: step hook, BC model I/O, adapter, runner syntax.

No simulator, GPU, Isaac or GarmentLab import is used.  The step hook is tested
with stubs; the BC wrapper is tested against the real Stage 5 reduced dataset,
stats and checkpoint bytes with a deterministic fake torch/train_bc.  The
adapter check uses a real saved accepted trace when scipy is available.

Run with the repository Python (numpy required; scipy optional for the adapter
section).
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import types
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TRAINING = HERE.parent / 'training'
RESULTS = HERE.parent / 'results' / 'STAGE5_REDUCED_50_10_10'
APP = HERE.parent / 'a5-rc8b-recovery-hold120-rc7-r2' / 'app'
TRACE_DIR = (HERE.parent / 'results' / 'STAGE5_FORMAL_6115_20261106'
             / 'day4-a5-rc2-l1-20261107-053657-097239')
CKPT = RESULTS / 'runs' / 'single' / 'best.pt'
STATS = RESULTS / 'dataset' / 'stats.json'
TEMP_ROOT = HERE.parents[2]

EXPECTED_CKPT_PREFIX = '5bff9e67'
EXPECTED_STATS_PREFIX = '8f1788d1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ----------------------------------------------------------------------
# stubs for the step hook
# ----------------------------------------------------------------------
class StubSlot:
    def __init__(self, enabled):
        self._enabled = bool(enabled)

    def attachment_enabled(self):
        return self._enabled


class StubRobot:
    def get_cur_ee_pos(self):
        return (np.array([0.1, 0.2, 0.3], dtype=float),
                np.array([1.0, 0.0, 0.0, 0.0], dtype=float))


class StubControl:
    def __init__(self):
        self.slots = [StubSlot(True), StubSlot(False), StubSlot(False)]
        self.attachlist = [object(), None]


class StubWorld:
    def __init__(self):
        self.current_time = 0.0
        self.current_time_step_index = 0
        self.calls = []
        self.raise_error = False
        self.backend = None

    def step(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.backend is not None:
            self.backend._step_count['n'] += 1
        if self.raise_error:
            raise RuntimeError('boom')
        self.current_time += 1.0 / 60.0
        self.current_time_step_index += 1
        return {'step': self.current_time_step_index, 'args': args,
                'kwargs': kwargs}


class StubBackend:
    def __init__(self):
        self._env = types.SimpleNamespace(
            world=StubWorld(), control=StubControl(), robots=[StubRobot()])
        self._env.world.backend = self
        self._holding = True
        self._gripper_state = 1
        self._command_holding = True
        self._step_count = {'n': 0}

    def _garment_world_positions(self):
        return np.arange(441 * 3, dtype=np.float64).reshape(441, 3) / 1000.0


def check_step_hook():
    from step_hook import StepHook

    backend = StubBackend()
    world = backend._env.world
    hook = StepHook(backend).install()
    result = world.step(True, render=True, foo=7)
    assert result == {'step': 1, 'args': (True,),
                      'kwargs': {'render': True, 'foo': 7}}
    assert world.calls == [((True,), {'render': True, 'foo': 7})]
    assert hook.step_calls == 1 and len(hook.records) == 1
    row = hook.records[0]
    assert row['ok'] is True
    assert abs(row['sim_time_s'] - 1.0 / 60.0) < 1e-12
    assert row['absolute_step'] == 1 and row['backend_step'] == 1
    assert row['holding'] is True
    assert row['enabled_slots'] == (True, False, False)
    assert row['attachment_enabled_any'] is True
    assert row['logical_attached'] is True
    assert row['gripper_state'] == 1 and row['gripper_open'] is False
    assert row['ee_m'].shape == (3,)
    assert row['ee_quaternion_wxyz'].shape == (4,)
    assert row['vertices'].shape == (441, 3)
    assert len(world.calls) == 1  # the hook added no extra step
    world.step(False)
    assert hook.step_calls == 2 and len(hook.records) == 2
    assert len(world.calls) == 2
    hook.close()
    assert world.step.__func__ is StubWorld.step
    print('STEP_HOOK_BASIC_OK calls=%d records=%d'
          % (hook.step_calls, len(hook.records)))

    # A pre-existing wrapper must still see exactly one call.
    backend = StubBackend()
    world = backend._env.world
    original = world.step
    outer = []

    def outer_step(*args, **kwargs):
        outer.append(1)
        return original(*args, **kwargs)

    world.step = outer_step
    hook = StepHook(backend).install()
    world.step()
    assert len(outer) == 1 and len(world.calls) == 1
    assert hook.step_calls == 1 and len(hook.records) == 1
    hook.close()
    assert world.step is outer_step
    print('STEP_HOOK_NESTED_OK outer_calls=%d' % len(outer))

    # Exceptions must pass through unchanged, with one call and one record.
    backend = StubBackend()
    backend._env.world.raise_error = True
    hook = StepHook(backend).install()
    try:
        backend._env.world.step()
    except RuntimeError as exc:
        assert str(exc) == 'boom'
    else:
        raise AssertionError('StepHook swallowed the step exception')
    assert len(backend._env.world.calls) == 1
    assert hook.step_calls == 1 and len(hook.records) == 1
    assert hook.records[0]['ok'] is False
    assert 'boom' in (hook.records[0]['step_error'] or '')
    hook.close()
    print('STEP_HOOK_EXCEPTION_OK')

    # Save/readback shape.  Write the file directly beside the workspace root
    # (not inside a new child directory): the local DSH sandbox grants writes
    # to the root file namespace but not to freshly created subdirectories.
    path = TEMP_ROOT / '_stage6_step_hook_test.npz'
    try:
        backend = StubBackend()
        hook = StepHook(backend).install()
        backend._env.world.step()
        backend._env.world.step()
        hook.close()
        hook.save_npz(path)
        with np.load(path, allow_pickle=False) as data:
            assert data['vertices'].shape == (2, 441, 3)
            assert data['ee_m'].shape == (2, 3)
            assert data['enabled_slots'].shape == (2, 3)
            assert data['holding'].tolist() == [True, True]
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    print('STEP_HOOK_SAVE_OK')


# ----------------------------------------------------------------------
# BC policy I/O against real data with a deterministic fake torch
# ----------------------------------------------------------------------
class FakeTensor:
    def __init__(self, value):
        self.a = np.asarray(value)

    @property
    def shape(self):
        return self.a.shape

    def __getitem__(self, index):
        return FakeTensor(self.a[index])

    def numpy(self):
        return self.a

    def argmax(self, axis=None):
        return FakeTensor(np.argmax(self.a, axis=axis))

    def item(self):
        return self.a.item()


class FakeNoGrad:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeBCNet:
    def __init__(self, in_dim, hidden, mode):
        self.in_dim = in_dim
        self.hidden = hidden
        self.mode = mode
        self.out = None

    def load_state_dict(self, state):
        return None

    def eval(self):
        return self

    def __call__(self, x):
        cont, logits = self.out
        return FakeTensor(cont[None]), FakeTensor(logits[None])


def check_model_io():
    torch_module = types.ModuleType('torch')
    torch_module.float32 = np.float32
    torch_module.tensor = lambda value, dtype=None: FakeTensor(value)
    torch_module.load = lambda path, map_location=None: {
        'in_dim': 1340, 'hidden': 512, 'mode': 'single', 'state': {}}
    torch_module.no_grad = FakeNoGrad
    sys.modules['torch'] = torch_module

    train_bc_module = types.ModuleType('train_bc')
    train_bc_module.BCNet = FakeBCNet
    sys.modules['train_bc'] = train_bc_module

    if str(TRAINING) not in sys.path:
        sys.path.insert(0, str(TRAINING))
    from bc_policy import BCPolicy

    assert CKPT.is_file(), 'missing checkpoint: %s' % CKPT
    assert STATS.is_file(), 'missing stats: %s' % STATS
    assert sha(CKPT).startswith(EXPECTED_CKPT_PREFIX), (
        'unexpected checkpoint hash ' + sha(CKPT))
    assert sha(STATS).startswith(EXPECTED_STATS_PREFIX), (
        'unexpected stats hash ' + sha(STATS))

    stats = json.loads(STATS.read_text())
    assert stats['obs_dim'] == 1340
    assert len(stats['obs_mean']) == 1340
    assert len(stats['obs_std']) == 1340
    assert len(stats['cont_mean']) == 4
    assert len(stats['cont_std']) == 4

    policy = BCPolicy(CKPT.parent, STATS.parent)
    with np.load(RESULTS / 'dataset' / 'dataset_single.npz',
                 allow_pickle=True) as data:
        index = 0
        obs = policy.build_obs(
            data['obs_vertices'][index], data['obs_ee'][index],
            data['obs_quat'][index], data['obs_joints'][index],
            data['obs_holding'][index])
        ground_truth = np.asarray(data['action'][index], dtype=np.float64)
    assert obs.shape == (1340,), obs.shape
    assert np.isfinite(obs).all()

    normalized = (ground_truth[:4] - policy.c_mean) / policy.c_std
    logits = np.full(3, -10.0, dtype=np.float32)
    logits[int(ground_truth[4])] = 10.0
    policy.model.out = (normalized.astype(np.float32), logits)
    prediction = policy.predict(obs)
    recovered = np.r_[prediction['xyz'], prediction['yaw']]
    assert np.allclose(recovered, ground_truth[:4], atol=1e-5, rtol=0), (
        recovered, ground_truth[:4])
    assert prediction['gripper'] == int(ground_truth[4])
    assert np.isfinite(prediction['yaw'])
    assert len(prediction['xyz']) == 3
    print('MODEL_IO_OK obs_dim=%d ckpt=%s stats=%s pred=%s'
          % (obs.shape[0], sha(CKPT)[:12], sha(STATS)[:12],
             json.dumps(prediction)))


# ----------------------------------------------------------------------
# adapter against a real accepted trace
# ----------------------------------------------------------------------
def check_adapter():
    if not (TRACE_DIR / 'success_trace.npz').is_file():
        print('ADAPTER_SKIP missing local trace: %s' % TRACE_DIR)
        return False
    if str(APP) not in sys.path:
        sys.path.insert(0, str(APP))
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    try:
        from bc_eval_adapter import physical_verdict
    except ImportError as exc:
        print('ADAPTER_SKIP import: %r' % (exc,))
        return False

    meta = json.loads((TRACE_DIR / 'success_meta.json').read_text())
    with np.load(TRACE_DIR / 'success_trace.npz', allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    accepted = physical_verdict(meta, arrays)
    assert accepted['accepted'] is True, accepted
    assert accepted['physics_ok'] is True, accepted
    assert accepted['budget_ok'] is True, accepted
    over = copy.deepcopy(meta)
    over['action_count'] = 8
    rejected = physical_verdict(over, arrays)
    assert rejected['accepted'] is False, rejected
    print('ADAPTER_OK accepted=%s budget_limit=%s over_budget=%s'
          % (accepted['accepted'], accepted['budget_limit'],
             rejected['budget_ok']))
    return True


# ----------------------------------------------------------------------
# policy-loop terminal/budget logic with stubs (no simulator)
# ----------------------------------------------------------------------
def check_policy_loop():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import a5_bc_single as runner

    commands = []
    terminal_calls = []

    class Cmd:
        OPEN = 0
        CLOSE = 1
        HOLD = 2

    class FakeSlot:
        def __init__(self, label):
            self.label = label
            self.pick_index = 0
            self._enabled = False

        def attachment_enabled(self):
            return bool(self._enabled)

    fold_slot = FakeSlot('left_sleeve')
    right_slot = FakeSlot('right_sleeve')
    bottom_slot = FakeSlot('bottom_sleeve')
    control = types.SimpleNamespace(
        fold_slot=fold_slot,
        slots=[right_slot, fold_slot, bottom_slot],
        active=None,
        attachlist=[None])

    def fake_observe(rt, backend):
        return {
            'obs': np.zeros(1340, dtype=np.float32),
            'vertices': np.zeros((441, 3), dtype=np.float64),
            'ee': np.zeros(3, dtype=np.float64),
            'quat': np.array([1.0, 0.0, 0.0, 0.0]),
            'joints': np.zeros(9, dtype=np.float32),
            'holding': bool(backend._holding),
            'sim_time_s': float(backend._env.world.current_time),
            'absolute_step': 0,
            'backend_step': int(backend._step_count['n']),
        }

    def fake_predict(rt, policy, observation):
        return {'xyz': np.array([0.0, 0.0, 0.1]),
                'yaw': 0.0, 'gripper': int(commands.pop(0))}

    def fake_execute(rt, backend, result, target, yaw, command, label, **kwargs):
        backend._step_count['n'] += 1
        if int(command) == int(Cmd.CLOSE):
            fold_slot._enabled = True
            control.attachlist = [fold_slot, None]
            control.active = fold_slot
            backend._holding = True
            backend._command_holding = True
            backend._gripper_state = 1
        elif int(command) == int(Cmd.OPEN):
            for slot in control.slots:
                slot._enabled = False
            control.attachlist = [None]
            control.active = None
            backend._holding = False
            backend._command_holding = False
            backend._gripper_state = 0
        row = {
            'label': label,
            'target_pose': [float(target[0]), float(target[1]),
                            float(target[2]), float(yaw)],
            'command': int(command),
            'step': int(backend._step_count['n']),
            'holding': bool(backend._holding),
            'target_override': False,
        }
        result['actions'].append(row)
        return row

    def fake_terminal(rt, backend, out, result, evidence, case, level, fold,
                      last_target, last_yaw, prediction, obs_row,
                      grasp_count, release_count):
        terminal_calls.append({
            'grasps': int(grasp_count),
            'releases': int(release_count),
            'fold_present': fold is not None,
            'policy_target': np.asarray(prediction['xyz']).tolist(),
        })
        # The real terminal path executes the policy's target unchanged.
        fake_execute(rt, backend, result, prediction['xyz'],
                     prediction['yaw'], int(Cmd.OPEN), 'bc_release_open')
        result['terminal_release'] = {
            'policy_open': True,
            'release_action_label': 'bc_release_open',
            'target_override': False,
        }

    def fake_fold(rt, backend, out, result, level, case, local_points, state,
                  source, slot):
        reference = {
            'source': source,
            'measure_error': None,
            'pick_index': int(slot.pick_index),
            'yaw_rad': 0.0,
        }
        result['fold_reference'] = reference
        return {
            'state': np.asarray(state, dtype=np.float64),
            'pick_index': reference['pick_index'],
            'yaw': 0.0,
            'slot': slot,
            'reference': reference,
        }

    class CmdNamespace:
        OPEN = 0
        CLOSE = 1
        HOLD = 2

    rt = types.SimpleNamespace(
        GripperCommand=CmdNamespace,
        LEVEL_BUDGET={'flat': 7, 'perturbed': 12, 'crumpled': 12})
    backend = types.SimpleNamespace(
        _env=types.SimpleNamespace(
            world=types.SimpleNamespace(current_time=0.0),
            control=control),
        _step_count={'n': 0},
        _holding=False,
        _command_holding=False,
        _gripper_state=0,
        _garment_world_positions=lambda: np.zeros((441, 3)))
    evidence = types.SimpleNamespace(samples={})
    case = {'yaw_rad': 0.0}
    initial = np.zeros((441, 3))
    local_points = np.zeros((441, 3))
    policy = object()

    names = ('_observe', '_predict', '_execute_action', '_terminal_release',
             '_make_fold_reference')
    originals = {name: getattr(runner, name) for name in names}
    runner._observe = fake_observe
    runner._predict = fake_predict
    runner._execute_action = fake_execute
    runner._terminal_release = fake_terminal
    runner._make_fold_reference = fake_fold
    try:
        def run(level, sequence):
            commands[:] = list(sequence)
            terminal_calls.clear()
            result = {'actions': [], 'events': []}
            args = types.SimpleNamespace(max_actions=len(sequence))
            obs_rows, budget = runner._run_policy(
                rt, backend, HERE, result, evidence, case, level, args,
                local_points, policy, initial)
            return result, obs_rows, budget

        result, _, budget = run('flat', [0, 1, 2, 0])
        assert budget == 4
        assert len(terminal_calls) == 1
        assert terminal_calls[0]['grasps'] == 1
        assert result['bc_grasps'] == 1
        assert result['bc_nonterminal_opens'] == 1
        assert result['bc_initial_or_idle_opens'] == 1
        assert result['actions'][-1]['label'] == 'bc_release_open'
        assert result['actions'][-1]['target_pose'][:3] == [0.0, 0.0, 0.1]
        assert result['actions'][-1]['target_override'] is False
        assert not any(e['name'] == 'bc_budget_exhausted_without_terminal_release'
                       for e in result['events'])
        print('POLICY_LOOP_L1_OK actions=%d grasps=%d'
              % (len(result['actions']), result['bc_grasps']))

        # L2/L3: approach OPEN, recovery release OPEN, fold approach OPEN are
        # all non-terminal; the OPEN after the second actual grasp is terminal.
        result, _, budget = run('perturbed', [0, 1, 2, 0, 0, 1, 2, 0])
        assert budget == 8
        assert len(terminal_calls) == 1
        assert terminal_calls[0]['grasps'] == 2
        assert terminal_calls[0]['fold_present'] is True
        assert result['bc_nonterminal_opens'] == 3
        assert result['bc_recovery_releases'] == 1
        assert result['actions'][-1]['label'] == 'bc_release_open'
        assert result['actions'][-1]['target_pose'][:3] == [0.0, 0.0, 0.1]
        labels = [action['label'] for action in result['actions']]
        assert labels.count('bc_recovery_release') == 1
        assert sum(label.startswith('bc_fold_approach_open_')
                   for label in labels) == 1
        assert sum(label.startswith('bc_initial_open_')
                   for label in labels) == 1
        print('POLICY_LOOP_L2L3_OK actions=%d opens=%d releases=%d'
              % (len(result['actions']), result['bc_nonterminal_opens'],
                 result['bc_recovery_releases']))

        # Repeated CLOSE while already holding is not a new grasp.
        result, _, budget = run('flat', [0, 1, 1, 2, 0])
        assert budget == 5
        assert result['bc_grasps'] == 1
        assert result['bc_repeated_closes'] == 1
        assert terminal_calls[0]['grasps'] == 1
        assert any(e['name'] == 'bc_repeated_close' for e in result['events'])
        print('POLICY_LOOP_REPEATED_CLOSE_OK grasps=%d repeated=%d'
              % (result['bc_grasps'], result['bc_repeated_closes']))

        # No second grasp => no terminal release, even after a recovery release.
        result, _, budget = run('perturbed', [0, 1, 2, 0, 0, 2])
        assert budget == 6
        assert not terminal_calls
        assert 'terminal_release' not in result
        assert any(e['name'] == 'bc_budget_exhausted_without_terminal_release'
                   for e in result['events'])
        print('POLICY_LOOP_NO_TERMINAL_OK actions=%d'
              % len(result['actions']))

        # A failing action must still retain the already-built observation rows
        # for failure evidence (first-run gap: obs_rows was lost on exception).
        def failing_execute(rt, backend, result, target, yaw, command, label,
                            **kwargs):
            if int(command) == int(Cmd.CLOSE):
                raise RuntimeError('synthetic CLOSE failure')
            return fake_execute(rt, backend, result, target, yaw, command,
                                label, **kwargs)

        runner._execute_action = failing_execute
        commands[:] = [0, 1]
        result = {'actions': [], 'events': []}
        rows = []
        try:
            runner._run_policy(
                rt, backend, HERE, result, evidence, case, 'flat',
                types.SimpleNamespace(max_actions=2), local_points, policy,
                initial, obs_rows=rows)
        except RuntimeError as exc:
            assert 'synthetic CLOSE failure' in str(exc)
        else:
            raise AssertionError('synthetic CLOSE failure was not raised')
        assert len(rows) == 2, len(rows)
        runner._execute_action = fake_execute
        print('POLICY_LOOP_EXCEPTION_KEEPS_OBS_OK rows=%d' % len(rows))
    finally:
        for name, original in originals.items():
            setattr(runner, name, original)


# ----------------------------------------------------------------------
# terminal OPEN keeps the model target/yaw (no Stage 6 override)
# ----------------------------------------------------------------------
def check_terminal_open_target_preserved():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import a5_bc_single as runner

    class Cmd:
        OPEN = 0
        CLOSE = 1
        HOLD = 2

    class Slot:
        def __init__(self, label):
            self.label = label
            self._enabled = True

        def attachment_enabled(self):
            return bool(self._enabled)

    slot = Slot('left_sleeve')
    control = types.SimpleNamespace(
        fold_slot=slot, slots=[slot, slot, slot], active=slot,
        attachlist=[slot, None])
    calls = []

    def original_goto(pos, ori, flag, max_limit=1000):
        calls.append((np.asarray(pos, dtype=float).tolist(), ori, flag,
                      max_limit))
        return None

    control.robot_goto_position = original_goto

    class Robot:
        def get_cur_ee_pos(self):
            return (np.array([0.01, 0.02, 0.03]),
                    np.array([1.0, 0.0, 0.0, 0.0]))

    backend = types.SimpleNamespace(
        _env=types.SimpleNamespace(
            world=types.SimpleNamespace(current_time=0.0,
                                        current_time_step_index=0),
            control=control, robots=[Robot()]),
        _holding=True, _command_holding=True, _gripper_state=1,
        _step_count={'n': 0},
        _garment_world_positions=lambda: np.zeros((441, 3)))

    class Evidence:
        def __init__(self):
            self.samples = {}

        def sample(self, label):
            state = runner._engaged_state(backend)
            self.samples[label] = {
                'ee_m': backend._env.robots[0].get_cur_ee_pos()[0].tolist(),
                'holding': state['holding'],
                'attached': state['attached'],
            }

    evidence = Evidence()
    result = {'actions': [], 'errors': []}
    prediction = {'xyz': np.array([0.20, 0.30, 0.40]),
                  'yaw': 0.50, 'gripper': int(Cmd.OPEN)}
    captured = {}

    def fake_execute(rt, backend, result, target, yaw, command, label,
                     **kwargs):
        captured['target'] = np.asarray(target, dtype=float).tolist()
        captured['yaw'] = float(yaw)
        captured['command'] = int(command)
        captured['label'] = label
        # Simulate the original Backend OPEN semantics: ungrasp, then move to
        # the policy's requested target.  This is not a Stage 6 override.
        slot._enabled = False
        control.attachlist = [None]
        control.active = None
        backend._holding = False
        backend._gripper_state = 0
        control.robot_goto_position([np.asarray(target, dtype=float)],
                                    [None], [True], 1000)
        row = {
            'label': label,
            'target_pose': [float(target[0]), float(target[1]),
                            float(target[2]), float(yaw)],
            'command': int(command),
            'step': 1,
            'ee': [0.20, 0.30, 0.40],
            'holding': False,
            'target_override': False,
        }
        result['actions'].append(row)
        return row

    original_execute = runner._execute_action
    runner._execute_action = fake_execute
    try:
        rt = types.SimpleNamespace(GripperCommand=Cmd)
        row = runner._execute_terminal_open(
            rt, backend, result, evidence, prediction, {})
    finally:
        runner._execute_action = original_execute

    assert captured['target'] == [0.20, 0.30, 0.40], captured
    assert captured['yaw'] == 0.50
    assert captured['command'] == int(Cmd.OPEN)
    assert captured['label'] == 'bc_release_open'
    assert row['target_override'] is False
    assert row['release_observation']['target'] == [0.20, 0.30, 0.40]
    assert control.robot_goto_position is original_goto
    assert evidence.samples['released']['holding'] is False
    assert evidence.samples['retreated']['holding'] is False
    assert calls and calls[0][0] == [[0.20, 0.30, 0.40]]
    print('TERMINAL_OPEN_TARGET_PRESERVED_OK target=%s yaw=%.3f'
          % (captured['target'], captured['yaw']))


# ----------------------------------------------------------------------
# terminal criteria: expert target identity is not a Stage 6 success gate
# ----------------------------------------------------------------------
def check_terminal_criteria_expert_identity_not_gate():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import a5_bc_single as runner

    class Cmd:
        OPEN = 0
        CLOSE = 1
        HOLD = 2

    class Slot:
        label = 'left_sleeve'
        pick_index = 0

        def attachment_enabled(self):
            return False

    slot = Slot()
    control = types.SimpleNamespace(
        fold_slot=slot, slots=[slot, slot, slot], active=slot,
        attachlist=[None])
    backend = types.SimpleNamespace(
        _env=types.SimpleNamespace(
            world=types.SimpleNamespace(current_time=0.0,
                                        current_time_step_index=0),
            control=control),
        _holding=False, _gripper_state=0, _command_holding=False,
        _step_count={'n': 1},
        _garment_world_positions=lambda: np.zeros((441, 3)))
    evidence = types.SimpleNamespace(samples={
        'released': {'ee_m': [0.0, 0.0, 0.0], 'holding': False,
                     'attached': False},
        'retreated': {'ee_m': [0.0, 0.0, 0.02]},
    })
    result = {'actions': [], 'events': []}
    fold = {
        'state': np.zeros((441, 3)),
        'pick_index': 0,
        'yaw': 0.0,
        'reference': {'measure_error': None},
    }
    prediction = {'xyz': np.array([0.0, 0.0, 0.10]),
                  'yaw': 0.0, 'gripper': 0}
    out = TEMP_ROOT
    final_path = out / 'final.npz'

    def fake_execute_terminal_open(rt, backend, result, evidence, prediction,
                                   obs_row):
        return {'target_pose': [0.0, 0.0, 0.10, 0.0], 'step': 1}

    def fake_held(rt, backend, last_target, last_yaw, tolerance):
        return {'accepted': True, 'position_error_m': 0.0,
                'arm_speed_rad_s': 0.0, 'anchor_gap_max_m': 0.0,
                'orientation_reached': True}

    def fake_window(rt, backend, out, result, evidence, initial, pick_index,
                    yaw, upward_displacement_m):
        result['release_clock'] = {
            'absolute_step': 0, 'sim_time_s': 0.0, 'dt_s': 1.0 / 60.0,
            'pick_index': 0, 'yaw_rad': 0.0,
            'upward_displacement_m': upward_displacement_m,
        }
        return np.zeros((441, 3))

    def fake_partial(*args, **kwargs):
        return None

    rt = types.SimpleNamespace(
        GripperCommand=Cmd,
        pfs1=types.SimpleNamespace(
            record_stage=lambda *a, **k: None,
            record_material_stage=lambda *a, **k: None))
    originals = {
        '_execute_terminal_open': runner._execute_terminal_open,
        '_held_check': runner._held_check,
        '_record_release_window': runner._record_release_window,
        '_save_partial_trace': runner._save_partial_trace,
    }
    runner._execute_terminal_open = fake_execute_terminal_open
    runner._held_check = fake_held
    runner._record_release_window = fake_window
    runner._save_partial_trace = fake_partial
    try:
        runner._terminal_release(
            rt, backend, out, result, evidence, {'yaw_rad': 0.0}, 'flat',
            fold, np.array([0.0, 0.0, 0.0]), 0.0, prediction, {},
            grasp_count=1, release_count=0)
        terminal = result['terminal_release']
        # The policy target (0.10 m) deliberately differs from the expert
        # identity target (released EE + 0.15 m), but physical retreat is 2 cm.
        assert terminal['expert_target_consistency'] is False
        assert terminal['physical_retreat_ok'] is True
        assert terminal['terminal_ok'] is True, terminal
        assert terminal['reasons'] == [], terminal
        assert result['release_clock']['upward_displacement_m'] == .02

        # Physical retreat < 1 cm remains a failure gate.
        evidence.samples['retreated'] = {'ee_m': [0.0, 0.0, 0.005]}
        result2 = {'actions': [], 'events': []}
        runner._terminal_release(
            rt, backend, out, result2, evidence, {'yaw_rad': 0.0}, 'flat',
            fold, np.array([0.0, 0.0, 0.0]), 0.0, prediction, {},
            grasp_count=1, release_count=0)
        terminal2 = result2['terminal_release']
        assert terminal2['expert_target_consistency'] is False
        assert terminal2['physical_retreat_ok'] is False
        assert terminal2['terminal_ok'] is False
        assert any('upward displacement' in r for r in terminal2['reasons'])
        print('TERMINAL_CRITERIA_EXPERT_IDENTITY_NOT_GATE_OK '
              'expert_target=False physical_retreat=True '
              'physical_fail_gate=True')
    finally:
        for name, original in originals.items():
            setattr(runner, name, original)
        try:
            final_path.unlink()
        except FileNotFoundError:
            pass


# ----------------------------------------------------------------------
# runner syntax / no-expert-action static check
# ----------------------------------------------------------------------
def check_runner_syntax():
    runner = HERE / 'a5_bc_single.py'
    hook = HERE / 'step_hook.py'
    source = runner.read_text(encoding='utf-8')
    compile(source, str(runner), 'exec')
    compile(hook.read_text(encoding='utf-8'), str(hook), 'exec')
    for marker in ('_record_release_window', 'physical_verdict', 'StepHook',
                   'LEVEL_BUDGET', 'bc_release_open', 'target_override',
                   'frozen_target_ok', 'bc_repeated_close',
                   'success_trace.npz', 'bc_observations.npz', 'failure.json'):
        assert marker in source, 'runner missing marker: ' + marker
    for forbidden in ("'arc45'", "'rec_approach'", "'fold_arc45'",
                      "'release_retreat'"):
        assert forbidden not in source, 'expert action marker in runner: ' + forbidden
    print('RUNNER_SYNTAX_OK lines=%d' % len(source.splitlines()))


def main():
    check_step_hook()
    check_model_io()
    adapter_ok = check_adapter()
    check_policy_loop()
    check_terminal_open_target_preserved()
    check_terminal_criteria_expert_identity_not_gate()
    check_runner_syntax()
    if adapter_ok:
        print('ALL_CHECKS_OK')
    else:
        print('ALL_CHECKS_OK_EXCEPT_ADAPTER_SKIPPED')


if __name__ == '__main__':
    main()
