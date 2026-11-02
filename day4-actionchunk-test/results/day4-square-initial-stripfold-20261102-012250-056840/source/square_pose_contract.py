"""Candidate public action contract; SI units, world XYZ and yaw radians."""
import numpy as np
from scipy.spatial.transform import Rotation
# URDF fingertip-frame midpoint relative to right_gripper, not a calibrated contact patch.
GRASP_OFFSET_LOCAL=np.array([0.,0.,.0034])
def orientation_euler(yaw):
    if not np.isfinite(yaw):raise ValueError('Nonfinite yaw')
    return np.array([np.pi,0.,float(yaw)])
def orientation_matrix(yaw):
    return Rotation.from_euler('xyz',orientation_euler(yaw)).as_matrix()
def grasp_to_ee(point,yaw):
    p=np.asarray(point,dtype=float)
    if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('Invalid point')
    return p-orientation_matrix(yaw)@GRASP_OFFSET_LOCAL
