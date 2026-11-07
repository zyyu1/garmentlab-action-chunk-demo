import numpy as np

def square_targets(pick, fold_line_y):
    """Four expert targets; backend interpolation only follows straight segments."""
    p = np.asarray(pick, dtype=float)
    radius = float(fold_line_y-p[1])
    if p.shape != (3,) or not np.isfinite(p).all() or not .15 < radius < .25:
        raise ValueError('Unexpected settled square geometry')
    angles = np.arange(1,5)*np.pi/4
    targets = np.column_stack([np.full(4,p[0]), fold_line_y-radius*np.cos(angles),
                              p[2]+.02*angles/np.pi+radius*np.sin(angles)])
    return targets


def material_grasp_to_ee(pick, quaternion_wxyz, local_offset):
    """Invert the existing Backend grasp-point transform; public XYZ remains EE."""
    from scipy.spatial.transform import Rotation
    pick=np.asarray(pick,dtype=float)
    q=np.asarray(quaternion_wxyz,dtype=float)
    offset=np.asarray(local_offset,dtype=float)
    if pick.shape!=(3,) or q.shape!=(4,) or offset.shape!=(3,) or not all(np.isfinite(x).all() for x in (pick,q,offset)):
        raise ValueError('Invalid grasp frame input')
    world_offset=Rotation.from_quat(q[[1,2,3,0]]).apply(offset)
    return pick-world_offset,world_offset
