"""Hem-centre selection and horizontal half-fold candidate for this garment."""
import numpy as np
from l1_fold_geometry import fold_metrics


def hem_vertex(vertices):
    v=np.asarray(vertices,dtype=float)
    if v.ndim!=2 or v.shape[1]!=3 or not np.isfinite(v).all():
        raise ValueError('Invalid vertices')
    band=np.flatnonzero(v[:,1]<=v[:,1].min()+.015)
    mid_x=(v[:,0].min()+v[:,0].max())/2
    return int(band[np.argmin(np.abs(v[band,0]-mid_x))])


def hem_plan(vertices,index):
    v=np.asarray(vertices,dtype=float)
    line=float((v[:,1].min()+v[:,1].max())/2)
    mask=v[:,1]<line
    pick=v[index].copy();target=pick.copy();target[1]=2*line-pick[1]
    if not mask[index] or min(mask.sum(),(~mask).sum())<100:
        raise ValueError('Invalid lower-half split')
    if abs(target[0])>.45 or not -.85<target[1]<-.10:
        raise ValueError('Target outside pilot workspace')
    return {'fold_axis':'world_x','fold_line_y':line,'source_mask':mask,
            'pick_reference':pick,'target_reference':target,'pick_index':index}


def hem_metrics(initial,final,plan):
    # Reuse identical proxy definitions after swapping world x and y.
    return fold_metrics(np.asarray(initial)[:,[1,0,2]],np.asarray(final)[:,[1,0,2]],
                        {'fold_line_x':plan['fold_line_y'],'source_mask':plan['source_mask']})


def short_segments(start,target,max_step=.025):
    start=np.asarray(start,dtype=float);target=np.asarray(target,dtype=float)
    count=max(1,int(np.ceil(np.linalg.norm(target-start)/max_step)))
    return [start+(target-start)*i/count for i in range(1,count+1)]


def hem_arc(start, fold_line_y, final_z=.03, max_step=.025, lift_height=None):
    """Semicircular gripper path about a fixed initial fold line.

    This is a trajectory candidate, not a guarantee of cloth isometry.
    Count is divisible by six so named phase snapshots land on exact angles.
    """
    start=np.asarray(start,dtype=float)
    radius=float(fold_line_y-start[1])
    if start.shape!=(3,) or not np.isfinite(start).all() or not .05<radius<.40:
        raise ValueError('Invalid hem arc start/radius')
    height=radius if lift_height is None else float(lift_height)
    if not np.isfinite(height) or not 0<height<=radius:
        raise ValueError('Arc lift height must be positive and no greater than radius')
    count=max(6,int(np.ceil((np.pi*radius+abs(final_z-start[2]))/max_step/6))*6)
    angles=np.linspace(0,np.pi,count+1)
    points=np.column_stack([np.full(count+1,start[0]),
        fold_line_y-radius*np.cos(angles),
        start[2]+(final_z-start[2])*angles/np.pi+height*np.sin(angles)])
    return points[1:]
