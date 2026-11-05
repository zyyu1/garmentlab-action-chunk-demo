"""Hold applicability contract for hold120 audits (pure, testable)."""
import numpy as np

STEPS = 120
FRAMES = 121
DT = 1.0 / 60.0


def evaluate(level, result, trace_exists, trace=None):
    """Return (ok, applicable, error). L1 must not have a hold; L2/L3 must."""
    applicable = level != 'flat'
    hold = result.get('recovery_hold')
    if not applicable:
        if hold is not None or trace_exists:
            return False, False, 'L1 must not have recovery_hold or hold trace'
        return True, False, None
    if not isinstance(hold, dict):
        return False, True, 'L2/L3 missing recovery_hold metadata'
    if hold.get('schema') != 'recovery-hold-v1':
        return False, True, 'bad hold schema'
    if int(hold.get('steps_requested', 0)) != STEPS:
        return False, True, 'bad steps_requested'
    if int(hold.get('completed_steps', 0)) != STEPS:
        return False, True, 'bad completed_steps'
    if int(hold.get('frames', 0)) != FRAMES:
        return False, True, 'bad frames'
    if abs(float(hold.get('dt_s', 0)) - DT) > 1e-12:
        return False, True, 'bad dt'
    if abs(float(hold.get('duration_s', 0)) - 2.0) > 1e-6:
        return False, True, 'bad duration'
    if hold.get('error') is not None:
        return False, True, 'hold recorded an error'
    checks = hold.get('checks') or {}
    if not (bool(checks.get('all_frames_ok')) and bool(checks.get('all_time_ok'))):
        return False, True, 'hold checks failed'
    if not trace_exists:
        return False, True, 'hold trace missing'
    if trace is not None:
        V = np.asarray(trace['vertices'], float)
        fd = np.asarray(trace['fd_velocities'], float)
        dt = np.asarray(trace['fd_interval_s'], float)
        steps = np.asarray(trace['absolute_step'], int)
        times = np.asarray(trace['sim_time_s'], float)
        target = np.asarray(trace['control_target'], float)
        if V.shape != (FRAMES, 441, 3) or fd.shape != (STEPS, 441, 3) or dt.shape != (STEPS,):
            return False, True, 'bad trace shapes'
        if not (np.all(np.isfinite(V)) and np.all(np.isfinite(fd)) and np.all(dt > 0)):
            return False, True, 'non-finite trace'
        if not np.allclose(dt, DT, atol=1e-6, rtol=0):
            return False, True, 'bad trace dt'
        if not np.all(np.diff(steps) == 1):
            return False, True, 'bad trace step increments'
        if not np.allclose(np.diff(times), DT, atol=1e-6, rtol=0):
            return False, True, 'bad trace time increments'
        for key in ('holding', 'logical_attached', 'command_holding',
                    'attachment_enabled_any', 'enabled_slots'):
            if np.asarray(trace[key], bool).any():
                return False, True, 'attachments/holding not false during hold'
        if not np.array_equal(target, np.repeat(target[:1], FRAMES, axis=0)):
            return False, True, 'control target changed during hold'
    return True, True, None
