"""Deep read-only diagnostic for 4112 arc135: RMP command + actual response.

Patches MyFranka.move's RMP forward and SquareProbeControl's convergence loop at
runtime only.  No app file is edited; all control/target/step/threshold logic is
the frozen code path.
"""
import builtins
import json
import os
import runpy
import sys
from pathlib import Path

APP = Path('/root/autodl-tmp/stage4-4112-deep/app')
LOG = Path('/root/autodl-tmp/stage4-4112-deep/deep.jsonl')
ARC_TARGET = [0.154372245, -0.431117028, 0.170363352]
sys.path.insert(0, str(APP))
LOG.parent.mkdir(parents=True, exist_ok=True)
_np = None
_ctx = {'phase': 'idle', 'segment': None, 'tick': None}
_orig_move = None
_orig_probe = None
_seen = {'move': False, 'probe': False}


def emit(rec):
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, default=float) + '\n')
        f.flush()
        os.fsync(f.fileno())


def to_np(v):
    if v is None:
        return None
    if hasattr(v, 'detach'):
        v = v.detach().cpu().numpy()
    return _np.asarray(v).reshape(-1).tolist()


def action_fields(a):
    out = {}
    for k in ('joint_positions', 'joint_velocities', 'joint_efforts', 'joint_indices'):
        out[k] = to_np(getattr(a, k, None)) if hasattr(a, k) else None
    out['type'] = type(a).__name__
    return out


def snap(self):
    try:
        pos = self.robot._robot.get_joint_positions()
        vel = self.robot._robot.get_joint_velocities()
        ee = self.robot.get_cur_ee_pos()[0]
        return {'sim_step': int(self.world.current_time_step_index),
                'sim_time_s': float(self.world.current_time),
                'joint_positions': to_np(pos), 'joint_velocities': to_np(vel),
                'ee': to_np(ee), 'holding': bool(self.holding)}
    except Exception as exc:
        return {'error': repr(exc)}


def make_move(orig):
    def move(self, end_loc, env_ori=None):
        ctrl = self._controller
        original_forward = ctrl.forward

        def forward(*args, **kwargs):
            out = original_forward(*args, **kwargs)
            if _ctx['phase'] != 'idle' and not (
                    _ctx['phase'] == 'segment' and _ctx['segment'] != _ctx.get('last_segment')):
                emit({'kind': 'rmp_output', 'context': dict(_ctx),
                      'target_end_effector_position': to_np(kwargs.get('target_end_effector_position', end_loc)),
                      'target_end_effector_orientation': to_np(kwargs.get('target_end_effector_orientation')),
                      'rmp_action': action_fields(out),
                      'applied': True,
                      'timing': 'before_world_step',
                      'sim_step': int(self.world.current_time_step_index),
                      'sim_time_s': float(self.world.current_time)})
            return out

        ctrl.forward = forward
        try:
            return orig(self, end_loc, env_ori)
        finally:
            ctrl.forward = original_forward
    return move


def probe(self, pos, ori, flag, max_limit=1000):
    target0, orientation0 = self.active._args(pos, ori, flag)
    if _np.linalg.norm(_np.asarray(target0)[:3] - _np.array(ARC_TARGET)) > 1e-4:
        return _orig_probe(self, pos, ori, flag, max_limit)
    from hem_fold_geometry import short_segments
    target, orientation = target0, orientation0
    start, _ = self.robot.get_cur_ee_pos()
    segments = short_segments(start, target, max_step=.025)
    _ctx['last_segment'] = len(segments) - 1
    for i, point in enumerate(segments):
        _ctx.update(phase='segment', segment=i, tick=None)
        before = snap(self)
        self.active.robot_goto_position([point], [orientation], flag, min(max_limit, 240))
        after = snap(self)
        if i == len(segments) - 1:
            emit({'kind': 'segment', 'segment': i, 'segment_target': to_np(point),
                  'action_target': to_np(target), 'before': before, 'after': after,
                  'timing': 'command_then_step; samples before/after'})
    consecutive = 0
    last = len(segments) - 1
    for tick in range(120):
        _ctx.update(phase='window', segment=last, tick=tick)
        before = snap(self)
        self.active._tick(target, orientation, follow=self.holding)
        after = snap(self)
        err = (_np.linalg.norm(_np.asarray(after['ee']) - target)
               if after.get('ee') is not None else None)
        vel = after.get('joint_velocities')
        vel_ok = None if vel is None else max(abs(x) for x in vel[:7]) < .1
        pos_ok = None if err is None else err < .01
        if self.holding:
            block_err = float(_np.linalg.norm(
                self.active.block_target() - self.active.block.get_position().numpy()))
            block_ok = block_err < .005
        else:
            block_err, block_ok = None, None
        ok = bool(pos_ok and vel_ok and (True if block_ok is None else block_ok))
        consecutive = consecutive + 1 if ok else 0
        emit({'kind': 'window_tick', 'tick': tick, 'segment': last,
              'target': to_np(target), 'before': before, 'after': after,
              'error_m': err, 'block_error_m': block_err,
              'pos_ok': pos_ok, 'vel_ok': vel_ok, 'block_ok': block_ok,
              'all_ok': ok, 'consecutive': consecutive,
              'timing': 'before=pre-command/pre-step; after=post-step'})
        if consecutive >= 6:
            emit({'kind': 'converged', 'segment': last, 'consecutive': consecutive})
            return
    emit({'kind': 'timeout', 'segment': last, 'branch': '120_ticks_exhausted',
          'consecutive': consecutive})
    raise RuntimeError('Square waypoint velocity/position did not converge')


def patch(mod):
    global _orig_probe, _orig_move, _np
    if mod.__name__.endswith('square_probe_control') and not _seen['probe']:
        import numpy as np
        _np = np
        _orig_probe = mod.SquareProbeControl.robot_goto_position
        mod.SquareProbeControl.robot_goto_position = probe
        _seen['probe'] = True
    if mod.__name__.endswith('MyFranka') and not _seen['move']:
        if hasattr(mod, 'MyFranka'):
            _orig_move = mod.MyFranka.move
            mod.MyFranka.move = make_move(_orig_move)
            _seen['move'] = True


_orig_import = builtins.__import__


def hook(name, globals=None, locals=None, fromlist=(), level=0):
    mod = _orig_import(name, globals, locals, fromlist, level)
    if name.endswith('square_probe_control') or name.endswith('MyFranka'):
        tgt = sys.modules.get(name)
        if tgt is not None:
            patch(tgt)
    return mod


builtins.__import__ = hook
os.environ['GARMENTLAB_ATTACHMENT_OVERLAP'] = '0.005'
os.environ['GARMENTLAB_DISABLED_ATTACHMENT_PROBE'] = '0'
sys.argv = ['a5_l1.py', '--initial-dir', '/root/autodl-tmp/day4-square-initial-20261105-232137-703257',
            '--allow-root', '--execution', 'single', '--split', 'formal', '--overhang', '.02']
os.chdir(APP)
runpy.run_path(str(APP / 'a5_l1.py'), run_name='__main__')
