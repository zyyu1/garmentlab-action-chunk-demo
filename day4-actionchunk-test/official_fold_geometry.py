"""Parameterize the downloaded official FoldDemo's three position transfers.

Oracle landmark processing is internal to the development expert. No pitch action.
"""
import numpy as np

NOMINAL_PICKS=np.array([[.35282,-.26231],[-.377,-.26231],[0.,-.65]])
NOMINAL_MOVES=[[[.1,-.26231,.22],[-.12,-.26231,.10]],
               [[0.,-.26231,.22],[.07,-.26231,.03]],
               [[0.,-.515,.22],[0.,-.25,.05]]]

def official_plan(initial,pick_indices):
    v=np.asarray(initial,dtype=float);ids=np.asarray(pick_indices,dtype=int)
    if v.ndim!=2 or v.shape[1]!=3 or ids.shape!=(3,) or len(set(ids.tolist()))!=3:
        raise ValueError('Expected three distinct material landmarks')
    if not np.isfinite(v).all() or np.any(ids<0) or np.any(ids>=len(v)):raise ValueError('Invalid geometry')
    design=np.column_stack([NOMINAL_PICKS,np.ones(3)])
    transform=np.linalg.solve(design,v[ids,:2])
    if np.linalg.cond(transform[:2])>5:raise ValueError('Degenerate landmark mapping')
    singular=np.linalg.svd(transform[:2],compute_uv=False)
    if singular.min()<.5 or singular.max()>2:raise ValueError('Outside nominal-flat development scale')
    stages=[]
    for label,pick,moves in zip(['right_sleeve','left_sleeve','hem'],ids,NOMINAL_MOVES):
        moves=np.asarray(moves,dtype=float)
        xy=np.column_stack([moves[:,:2],np.ones(2)])@transform
        waypoints=np.column_stack([xy,moves[:,2]])
        stages.append({'slot':label,'pick_index':int(pick),'reference_pick_xyz':v[pick].tolist(),
                       'waypoints_xyz':waypoints.tolist()})
    hem_pick=v[ids[2]]
    hem_place=np.asarray(stages[2]['waypoints_xyz'][-1])
    line=float((hem_pick[1]+hem_place[1])/2)
    mask=v[:,1]<line
    if min(mask.sum(),(~mask).sum())<100:raise ValueError('Invalid hem split')
    return {'version':'official-three-position-stage-v1','xy_affine_transform':transform.tolist(),
            'nominal_picks_xy':NOMINAL_PICKS.tolist(),'initial_picks_xyz':v[ids].tolist(),
            'stages':stages,'fold_line_y':line,'source_mask':mask,
            'metric_scope':'Provisional hem half-plane proxies; not frozen formal surface overlap',
            'pitch_override':False}

def live_stage_waypoints(stage,live_pick):
    delta=np.asarray(live_pick,dtype=float)-stage['reference_pick_xyz']
    waypoints=np.asarray(stage['waypoints_xyz'],dtype=float).copy()
    waypoints[:,:2]+=delta[:2]
    if not np.isfinite(waypoints).all() or np.any(abs(waypoints[:,0])>.55) or np.any(waypoints[:,1]<-.9) or np.any(waypoints[:,1]>-.08):
        raise ValueError('Stage targets outside declared development workspace')
    return waypoints
