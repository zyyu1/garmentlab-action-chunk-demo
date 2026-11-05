"""Development-only early descent; public Cartesian waypoints, no physics overrides."""
import numpy as np

def early_descent(arc):
    original=np.asarray(arc,dtype=float)
    if original.ndim!=2 or original.shape[1]!=3 or len(original)%2 or len(original)<6 or not np.isfinite(original).all():
        raise ValueError('Expected even finite XYZ arc')
    changed=original.copy();middle=len(original)//2
    peak=original[middle-1,2];end=original[-1,2]
    if peak<=end:raise ValueError('Expected descending second half')
    u=np.arange(1,middle+1,dtype=float)/middle
    changed[middle:,2]=end+(peak-end)*np.cos(np.pi*u/2)**2
    changed[-1]=original[-1]
    if np.any(changed[middle:,2]>original[middle:,2]+1e-9):
        raise ValueError('Candidate would raise the original descent')
    if np.max(np.linalg.norm(np.diff(changed,axis=0),axis=1))>.025+1e-9:
        raise ValueError('Candidate exceeds 25mm waypoint spacing')
    return changed
