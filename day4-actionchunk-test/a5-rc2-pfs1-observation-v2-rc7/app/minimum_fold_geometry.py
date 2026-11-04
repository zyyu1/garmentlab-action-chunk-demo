"""Minimum Day4: inspect and correct only the terminal placement of a hem fold."""
import numpy as np
from scipy.spatial import cKDTree

def edge_length_summary(initial,current,faces,anchor_ids):
    rest=np.asarray(initial);v=np.asarray(current);faces=np.asarray(faces).reshape(-1,3)
    edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
    lengths=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1)
    if np.any(lengths<=1e-8):raise ValueError('Degenerate initial mesh edge')
    ratios=np.linalg.norm(v[edges[:,0]]-v[edges[:,1]],axis=1)/lengths
    incident=np.isin(edges,anchor_ids).any(axis=1)
    return {'ratio_to_initial_p50_p95_p99_max':np.percentile(ratios,[50,95,99,100]).tolist(),
            'fraction_over_1p1':float((ratios>1.1).mean()),
            'anchor_incident_max':float(ratios[incident].max()) if incident.any() else None,
            'scope':'Geometric edge lengths relative to settled initial mesh; not measured tension or stress'}

def support_summary(vertices,source_mask,pick_index):
    v=np.asarray(vertices,dtype=float);mask=np.asarray(source_mask,dtype=bool)
    if v.ndim!=2 or v.shape[1]!=3 or mask.shape!=(len(v),) or not np.isfinite(v).all():
        raise ValueError('Invalid mesh for support measurement')
    fixed=v[~mask];moving=v[mask]
    if len(fixed)<10 or len(moving)<10:raise ValueError('Insufficient material halves')
    tree=cKDTree(fixed[:,:2]);distance,index=tree.query(moving[:,:2])
    gap=moving[:,2]-fixed[index,2]
    pd,pi=tree.query(v[pick_index,:2])
    return {'source_z_p10_p50_p90_m':np.percentile(moving[:,2],[10,50,90]).tolist(),
            'source_to_fixed_nearest_xy_p10_p50_p90_m':np.percentile(distance,[10,50,90]).tolist(),
            'source_to_fixed_vertical_gap_p10_p50_p90_m':np.percentile(gap,[10,50,90]).tolist(),
            'source_near_fixed_xy_10mm_fraction':float((distance<.01).mean()),
            'source_near_layer_xy10mm_z0to30mm_fraction':float(((distance<.01)&(gap>=0)&(gap<.03)).mean()),
            'pick_nearest_fixed_xy_m':float(pd),'pick_nearest_fixed_z_m':float(fixed[pi,2]),
            'pick_vertical_gap_to_nearest_fixed_m':float(v[pick_index,2]-fixed[pi,2]),
            'evidence_scope':'Geometric layer proximity only; no direct normal force/contact measurement'}

def supported_material_target(vertices,source_mask,pick_index,nominal_target,fold_line_y,
                              clearance=.02,max_xy_shift=.06):
    """Choose a nearby low, locally populated fixed-half support patch.

    Keep nominal x. Only the terminal target changes; no curve/material tuning.
    Clearance is a declared geometric center-spacing proxy, not a solidRestOffset readback.
    """
    v=np.asarray(vertices,dtype=float);mask=np.asarray(source_mask,dtype=bool)
    goal=np.asarray(nominal_target,dtype=float);fixed=v[~mask]
    if goal.shape!=(3,) or not np.isfinite(v).all() or not np.isfinite(goal).all():raise ValueError('Invalid support selection inputs')
    if not .01<=clearance<=.03:raise ValueError('Unexpected geometric layer clearance')
    tree=cKDTree(fixed[:,:2]);x=float(goal[0])
    pool=fixed[(abs(fixed[:,0]-x)<.015)&(abs(fixed[:,1]-goal[1])<=max_xy_shift)&(fixed[:,1]>fold_line_y+.04)]
    candidates=[]
    for y in np.unique(pool[:,1]):
        xy=np.array([x,y]);ids=tree.query_ball_point(xy,.015)
        if len(ids)<6:continue
        near=fixed[ids];distance=float(tree.query(xy)[0])
        if distance>.006 or np.percentile(near[:,2],90)>.05 or np.ptp(near[:,2])>.02:continue
        z=float(np.percentile(near[:,2],75))
        candidates.append((float(np.linalg.norm(xy-goal[:2])),xy,z,len(ids),distance))
    if not candidates:raise RuntimeError('No nearby fixed-half support patch; do not invent a release target')
    candidates.sort(key=lambda x:x[0]);distance,xy,z,count,nearest=candidates[0]
    target=np.r_[xy,z+clearance]
    if distance>max_xy_shift or target[1]<=fold_line_y+.04:raise RuntimeError('Support target outside correction bound')
    return {'material_target_xyz':target.tolist(),'nominal_material_target_xyz':goal.tolist(),
            'selected_support_z_p75_m':z,'support_neighborhood_count':count,
            'support_nearest_xy_m':nearest,'xy_target_correction_m':distance,
            'geometric_center_clearance_m':clearance,'max_xy_correction_m':max_xy_shift,
            'pick_before_xyz':v[pick_index].tolist(),
            'scope':'Terminal supported placement hypothesis; not confirmed contact force or material calibration'}

def material_to_ee_target(ee_position,current_material_point,material_target):
    ee=np.asarray(ee_position,dtype=float);pick=np.asarray(current_material_point,dtype=float);goal=np.asarray(material_target,dtype=float)
    if any(x.shape!=(3,) or not np.isfinite(x).all() for x in (ee,pick,goal)):raise ValueError('Expected finite xyz')
    target=ee+(goal-pick)
    if not -.55<target[0]<.55 or not -.9<target[1]<-.1 or not .005<target[2]<.3:
        raise RuntimeError('Corrected EE target outside development workspace')
    return target
