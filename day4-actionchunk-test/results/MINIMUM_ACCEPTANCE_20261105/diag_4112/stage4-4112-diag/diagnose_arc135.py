"""Read-only arc135 probe: patches the control loop at import time.

No frozen file is edited.  The patch is installed when square_probe_control is
imported (after Isaac starts), so it never imports pxr before SimulationApp.
"""
import builtins
import json
import os
import runpy
import sys
from pathlib import Path

APP = Path('/root/autodl-tmp/stage4-4112-diag/app')
LOG = Path(os.environ.get('ARC135_DIAG_LOG', '/root/autodl-tmp/stage4-4112-diag/arc135_ticks.jsonl'))
sys.path.insert(0, str(APP))
LOG.parent.mkdir(parents=True, exist_ok=True)
ARC_TARGET = [0.154372245, -0.431117028, 0.170363352]
_counter = {'calls': 0, 'records': 0}
_orig = None
_np = None


def emit(rec):
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, default=float) + '\n')
        f.flush()
        os.fsync(f.fileno())
    _counter['records'] += 1


def robot_goto_position(self, pos, ori, flag, max_limit=1000):
    _counter['calls'] += 1
    call = _counter['calls']
    target0, orientation0 = self.active._args(pos, ori, flag)
    if _np.linalg.norm(_np.asarray(target0)[:3] - _np.array(ARC_TARGET)) > 1e-4:
        return _orig(self, pos, ori, flag, max_limit)
    from hem_fold_geometry import short_segments
    target, orientation = target0, orientation0
    start, _ = self.robot.get_cur_ee_pos()
    segments = short_segments(start, target, max_step=.025)
    record = {'call_index': call, 'stage': 'arc135', 'segment_count': len(segments),
              'action_target': list(map(float, target)), 'start_ee': list(map(float, start))}
    emit(dict(record, event='begin'))
    for i, point in enumerate(segments):
        self.probe_subtarget = {'segment': i, 'xyz': point.tolist(), 'orientation': orientation}
        self.active.robot_goto_position([point], [orientation], flag, min(max_limit, 240))
        consecutive = 0
        for tick in range(120):
            self.active._tick(target, orientation, follow=self.holding)
            ee, _ = self.robot.get_cur_ee_pos()
            raw = self.robot._robot.get_joint_velocities()
            vel = raw.detach().cpu().numpy() if hasattr(raw, 'detach') else _np.asarray(raw)
            err = float(_np.linalg.norm(_np.asarray(ee) - target))
            pos_ok = err < .01
            vel_max = float(_np.max(_np.abs(vel[:7])))
            vel_ok = vel_max < .1
            block_err = None
            if self.holding:
                block_err = float(_np.linalg.norm(
                    self.active.block_target() - self.active.block.get_position().numpy()))
            block_ok = None if not self.holding else block_err < .005
            ok = pos_ok and vel_ok and (True if block_ok is None else block_ok)
            consecutive = consecutive + 1 if ok else 0
            emit({'event': 'tick', 'call_index': call, 'stage': 'arc135',
                  'segment': i, 'segment_target': list(map(float, point)),
                  'action_target': list(map(float, target)),
                  'sim_step': int(self.world.current_time_step_index),
                  'sim_time_s': float(self.world.current_time),
                  'ee': list(map(float, ee)), 'error_m': err,
                  'joint_vel_7': [float(x) for x in vel[:7]],
                  'joint_vel_max': vel_max,
                  'holding': bool(self.holding), 'block_error_m': block_err,
                  'pos_ok': bool(pos_ok), 'vel_ok': bool(vel_ok),
                  'block_ok': None if block_ok is None else bool(block_ok),
                  'all_ok': bool(ok), 'consecutive': consecutive})
            if consecutive >= 6:
                emit(dict(record, event='converged', segment=i, consecutive=consecutive))
                return
    emit(dict(record, event='timeout', branch='120_ticks_exhausted', consecutive=consecutive))
    raise RuntimeError('Square waypoint velocity/position did not converge')


def _patch(mod):
    global _orig, _np
    if getattr(mod, '_diag_patched', False):
        return
    import numpy as np
    _np = np
    _orig = mod.SquareProbeControl.robot_goto_position
    mod.SquareProbeControl.robot_goto_position = robot_goto_position
    mod._diag_patched = True


_orig_import = builtins.__import__


def _import(name, globals=None, locals=None, fromlist=(), level=0):
    mod = _orig_import(name, globals, locals, fromlist, level)
    if name == 'square_probe_control' or (fromlist and 'square_probe_control' in fromlist):
        target = sys.modules.get('square_probe_control')
        if target is not None:
            _patch(target)
    return mod


builtins.__import__ = _import

os.environ['GARMENTLAB_ATTACHMENT_OVERLAP'] = '0.005'
os.environ['GARMENTLAB_DISABLED_ATTACHMENT_PROBE'] = '0'

sys.argv = ['a5_l1.py', '--initial-dir', '/root/autodl-tmp/day4-square-initial-20261105-232137-703257',
            '--allow-root', '--execution', 'single', '--split', 'formal', '--overhang', '.02']
os.chdir(APP)
runpy.run_path(str(APP / 'a5_l1.py'), run_name='__main__')
