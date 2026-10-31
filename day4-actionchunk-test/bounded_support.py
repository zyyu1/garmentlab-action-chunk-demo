"""Development-only terminal correction; geometric gates are not fold acceptance."""
import numpy as np
from minimum_fold_geometry import support_summary, material_to_ee_target

CONFIG = dict(max_corrections=3, max_step_m=.02, total_travel_m=.06,
              material_error_m=.005, nearest_xy_m=.01, layer_fraction=.5,
              speed_p95_m_s=.02, patch_drift_m=.005, edge_growth_factor=1.05)

def assess(history, dt, mask, pick, patch, goal, edge_max, reference_edge_max):
    v=np.asarray(history)
    if len(v)<31 or dt<=0 or not np.isfinite(v).all():
        raise ValueError('Need finite 31-frame history and positive dt')
    last=v[-31:];speed=np.linalg.norm(np.diff(last[:,mask],axis=0),axis=2)/dt
    summary=support_summary(v[-1],mask,pick)
    values=dict(material_error_m=float(np.linalg.norm(v[-1,pick]-goal)),
                nearest_xy_m=summary['pick_nearest_fixed_xy_m'],
                layer_fraction=summary['source_near_layer_xy10mm_z0to30mm_fraction'],
                speed_p95_m_s=float(np.percentile(speed,95)),
                patch_drift_m=float(np.linalg.norm(last[-1,patch].mean(0)-last[0,patch].mean(0))),
                edge_max=float(edge_max))
    checks={k:values[k]<=CONFIG[k] for k in ('material_error_m','nearest_xy_m','speed_p95_m_s','patch_drift_m')}
    checks['layer_fraction']=values['layer_fraction']>=CONFIG['layer_fraction']
    checks['edge_growth']=values['edge_max']<=reference_edge_max*CONFIG['edge_growth_factor']
    return dict(values=values,checks=checks,ready=all(checks.values()),support=summary)

def correction(current, ee, pick, patch, patch_reference, initial_goal, spent):
    """Track the same material patch, never search for a new farther patch."""
    current=np.asarray(current)
    drift=(current[patch]-patch_reference).mean(0)
    if np.linalg.norm(drift[:2])>.06:
        raise ValueError('Selected patch moved beyond 60 mm; stop correction')
    goal=np.asarray(initial_goal)+drift
    if np.ptp(current[patch,2])>.02 or np.percentile(current[patch,2],90)>.05:
        raise ValueError('Selected support patch is no longer low/flat')
    remaining=CONFIG['total_travel_m']-spent
    if remaining<.001:raise ValueError('Correction travel budget exhausted')
    delta=goal-current[pick];length=float(np.linalg.norm(delta))
    if length<.001:raise ValueError('No useful geometric correction; do not chase noise')
    step=delta*min(1.,CONFIG['max_step_m']/length,remaining/length)
    command_material=current[pick]+step
    target=material_to_ee_target(ee,current[pick],command_material)
    return target,goal,float(np.linalg.norm(step))
