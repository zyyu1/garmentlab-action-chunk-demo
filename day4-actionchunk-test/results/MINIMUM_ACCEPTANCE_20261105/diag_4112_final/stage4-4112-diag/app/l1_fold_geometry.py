"""State-oracle expert geometry and explicitly provisional fold metrics."""
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import binary_dilation


def fold_plan(vertices, tracked_indices):
    v=np.asarray(vertices,dtype=float)
    if v.shape != (9945,3) or not np.isfinite(v).all():
        raise ValueError('Expected finite garment vertices')
    line=float((v[:,0].min()+v[:,0].max())/2)
    source=v[:,0]<line
    if source.sum()<100 or (~source).sum()<100:
        raise ValueError('Degenerate fold split')
    pick=v[int(tracked_indices[0])].copy()
    if pick[0]>=line:
        raise ValueError('Prepared grasp must lie in the moving left half')
    target=pick.copy();target[0]=2*line-pick[0]
    if abs(target[0])>.55 or not -.85<target[1]<.10:
        raise ValueError('Fold target outside conservative pilot workspace')
    return {'fold_axis':'world_y','fold_line_x':line,'source_mask':source,
            'pick_reference':pick,'target_reference':target}


def fold_metrics(initial, final, plan):
    initial=np.asarray(initial);final=np.asarray(final)
    if final.shape!=initial.shape or not np.isfinite(final).all():
        raise ValueError('Invalid final geometry')
    mask=plan['source_mask'];line=plan['fold_line_x']
    moving=final[mask,:2];stationary=final[~mask,:2]
    distances=np.r_[cKDTree(stationary).query(moving)[0],cKDTree(moving).query(stationary)[0]]
    # Fixed-resolution particle occupancy proxy, NOT triangle area overlap.
    cell=.01
    lo=np.minimum(initial[:,:2].min(axis=0),final[:,:2].min(axis=0))-.02
    hi=np.maximum(initial[:,:2].max(axis=0),final[:,:2].max(axis=0))+.02
    shape=np.ceil((hi-lo)/cell).astype(int)+1
    if np.any(shape>1000):
        raise ValueError('Geometry escaped occupancy grid workspace')
    grids=[]
    for points in (moving,stationary):
        ij=np.floor((points-lo)/cell).astype(int)
        grid=np.zeros(tuple(shape),dtype=bool);grid[ij[:,0],ij[:,1]]=True
        grids.append(binary_dilation(grid,iterations=1))
    overlap=float(np.logical_and(*grids).sum()/max(1,np.logical_or(*grids).sum()))
    desired=initial[mask,:2].copy();desired[:,0]=2*line-desired[:,0]
    return {'symmetric_xy_alignment_mean_m':float(distances.mean()),
      'particle_occupancy_iou':overlap,'occupancy_cell_m':cell,'occupancy_dilation_cells':1,
      'moving_half_crossed_fraction':float((final[mask,0]>line).mean()),
      'moving_material_reflected_target_mean_error_m':float(np.linalg.norm(moving-desired,axis=1).mean()),
      'cloth_z_p95_m':float(np.percentile(final[:,2],95)),
      'metric_scope':'Particle projection proxies; not certified triangle overlap, self-intersection or material quality.'}
