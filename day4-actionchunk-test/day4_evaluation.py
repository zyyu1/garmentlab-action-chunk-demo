"""Development metrics only. No frozen success classifier or simulator access."""
import numpy as np
from scipy.spatial import cKDTree

def metrics(initial, final, source_mask, line_origin_xy, line_normal_xy):
    a=np.asarray(initial,dtype=float);b=np.asarray(final,dtype=float)
    mask=np.asarray(source_mask)
    o=np.asarray(line_origin_xy,dtype=float);n=np.asarray(line_normal_xy,dtype=float)
    if a.ndim!=2 or a.shape[1]!=3 or b.shape!=a.shape or not np.isfinite([a,b]).all():
        raise ValueError('Expected matching finite Nx3 geometry with stable material indexing')
    if mask.dtype!=bool or mask.shape!=(len(a),) or not mask.any() or mask.all():
        raise ValueError('Expected nonempty material halves')
    if o.shape!=(2,) or n.shape!=(2,) or not np.isfinite([o,n]).all() or np.linalg.norm(n)<1e-9:
        raise ValueError('Invalid fold line')
    n=n/np.linalg.norm(n)
    signed=(a[:,:2]-o)@n
    if np.any(signed[mask]>=0) or np.any(signed[~mask]<-1e-6):
        raise ValueError('Normal must point from moving half toward stationary half')
    desired=a[mask,:2]-2*signed[mask,None]*n
    moving=b[mask,:2];fixed=b[~mask,:2]
    alignment=np.r_[cKDTree(fixed).query(moving)[0],cKDTree(moving).query(fixed)[0]]
    # Fixed world-grid particle occupancy, no adaptive origin or dilation.
    def cells(x):return {tuple(v) for v in np.floor(x/.01).astype(np.int64)}
    u,v=cells(moving),cells(fixed)
    return {'symmetric_alignment_m':float(alignment.mean()),
            'particle_grid_iou':len(u&v)/len(u|v), 'grid_cell_m':.01,
            'reflected_material_error_m':float(np.linalg.norm(moving-desired,axis=1).mean()),
            'stationary_material_drift_m':float(np.linalg.norm(b[~mask,:2]-a[~mask,:2],axis=1).mean()),
            'crossed_fraction':float((((moving-o)@n)>0).mean()),
            'height_p95_m':float(np.percentile(b[:,2],95)),
            'scope':'Particle projection proxies, not triangle-area overlap or self-intersection certification',
            'success':None, 'threshold_status':'unfrozen'}

def retention(initial, release, settled, source_mask, origin, normal):
    """Require separate release and settled measurements; do not accept release alone."""
    first=metrics(initial,release,source_mask,origin,normal)
    last=metrics(initial,settled,source_mask,origin,normal)
    return {'release':first,'settled':last,
            'post_release_displacement_mean_m':float(np.linalg.norm(np.asarray(settled)-np.asarray(release),axis=1).mean()),
            'success':None}
