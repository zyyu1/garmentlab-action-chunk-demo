"""Development oracle regions; identifiers stay inside the simulator adapter."""
import numpy as np

def select_regions(vertices):
    v=np.asarray(vertices,dtype=float)
    if v.ndim!=2 or v.shape[1]!=3 or len(v)<3 or not np.isfinite(v).all():
        raise ValueError('Expected finite garment vertices')
    mid_y=(v[:,1].min()+v[:,1].max())/2
    regions=[]
    for label,edge in [('right_sleeve',v[:,0].max()),('left_sleeve',v[:,0].min())]:
        band=np.flatnonzero(abs(v[:,0]-edge)<=.005)
        pick=int(band[np.argmin(abs(v[band,1]-mid_y))])
        regions.append((label,pick))
    hem=np.flatnonzero(v[:,1]<=v[:,1].min()+.015)
    mid_x=(v[:,0].min()+v[:,0].max())/2
    regions.append(('hem',int(hem[np.argmin(abs(v[hem,0]-mid_x))])))
    if len({i for _,i in regions})!=3:raise ValueError('Regions must be distinct')
    if any(np.linalg.norm(v[i]-v[j])<.05 for n,(_,i) in enumerate(regions) for _,j in regions[n+1:]):
        raise ValueError('Prepared regions too close for unambiguous selection')
    return regions

def choose_unused_region(vertices, regions, used, target, max_distance=.03):
    v=np.asarray(vertices,dtype=float);target=np.asarray(target,dtype=float)
    if target.shape!=(3,) or not np.isfinite(target).all():raise ValueError('Invalid target')
    options=[(float(np.linalg.norm(v[pick]-target)),n) for n,(_,pick) in enumerate(regions) if not used[n]]
    if not options:raise RuntimeError('All precreated regions have been used')
    options.sort()
    if options[0][0]>=max_distance:raise RuntimeError('CLOSE target is outside unused prepared regions')
    if len(options)>1 and options[1][0]-options[0][0]<.005:raise RuntimeError('Ambiguous prepared region')
    return options[0][1]
