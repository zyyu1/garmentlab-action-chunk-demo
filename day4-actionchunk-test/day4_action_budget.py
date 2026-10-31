"""Offline waypoint plan construction. No simulator imports or execution."""
import math

LIMIT = 12
FOLD = (('approach', 0), ('pick', 1), ('lift', 2), ('transfer', 2),
        ('place', 2), ('release', 0), ('retreat', 0))
RECOVERY = (('approach', 0), ('pick', 1), ('lift', 2),
            ('spread_place', 2), ('release', 0))

class BudgetExceeded(ValueError):
    pass

def remaining_recoveries(used_actions, fold_reserve=7, completed_recoveries=0):
    for value in (used_actions, fold_reserve, completed_recoveries):
        if type(value) is not int or value < 0:raise ValueError('Invalid count')
    if used_actions > LIMIT or completed_recoveries > 2:raise ValueError('Invalid history')
    return max(0, min(2-completed_recoveries, (LIMIT-used_actions-fold_reserve)//5))

def build_stage(poses, recovery=False):
    """Accept explicit world-frame [x,y,z,yaw] targets, never invent paths.

    Stage labels are audit metadata, not additional policy inputs.
    """
    template = RECOVERY if recovery else FOLD
    if set(poses) != {name for name, _ in template}:raise ValueError('Missing/extra pose')
    rows=[]
    for label, command in template:
        pose=[float(x) for x in poses[label]]
        if len(pose)!=4 or not all(math.isfinite(x) for x in pose):
            raise ValueError('Expected finite XYZ+yaw')
        rows.append({'stage':label, 'action':pose+[command]})
    return rows

def admit_stage(rows, used_actions, reserve_after=0):
    """Reject the whole stage before dispatch; never truncate a trajectory.

    The executor must count every submitted action, including failed attempts.
    H-step chunks consume H actions, not one. This module is not yet integrated.
    """
    if any(type(v) is not int or v<0 for v in (used_actions,reserve_after)):
        raise ValueError('Invalid count')
    if used_actions+len(rows)+reserve_after>LIMIT:
        raise BudgetExceeded('Stage exceeds total 12-waypoint budget')
    return rows
