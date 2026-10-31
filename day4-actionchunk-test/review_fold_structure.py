import json
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
b=Path(__file__).resolve().parent;out=b/'structural_review';out.mkdir(exist_ok=True)
d=b/'results/day4-minimum-half-fold-20261031-065311-595489';p=dict(np.load(d/'fold_definition.npz'));v=p['initial_vertices'];pick=int(p['pick_index']);mask=p['source_mask'];c=np.load(d/'cloth_constructed.npz');e=[];offset=0
for n in c['faceVertexCounts']:
 f=c['faceVertexIndices'][offset:offset+n];offset+=n;e.extend(zip(f,np.roll(f,-1)))
e,count=np.unique(np.sort(np.array(e),axis=1),axis=0,return_counts=True);boundary=e[count==1];g=coo_matrix((np.ones(len(e)*2),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(len(v),len(v))).tocsr();h=dijkstra(g,indices=pick,unweighted=True)
low=np.flatnonzero(mask&(v[:,2]<.02));other=int(low[np.argmin(np.linalg.norm(v[low,:2]-v[pick,:2],axis=1))]);length=np.linalg.norm(v[e[:,1]]-v[e[:,0]],axis=1);assert np.all(length>0)
rows={}
for name in ['00_initial','02_grasp','04_cross_line','06_supported_place','07_released','08_release_stationary','11_retention_4s']:
 x=np.load(d/(name+'.npz'))['vertices'];ratio=np.linalg.norm(x[e[:,1]]-x[e[:,0]],axis=1)/length
 rows[name]={'upper_pick':x[pick].tolist(),'lower_nearest_initial':x[other].tolist(),'paired_distance_mm':float(np.linalg.norm(x[pick]-x[other])*1000),'paired_dy_mm':float((x[pick,1]-x[other,1])*1000),'edge_length_ratio_p50_p95_p99_max_vs_settled':np.percentile(ratio,[50,95,99,100]).tolist(),'edges_over_1_2_fraction':float((ratio>1.2).mean())}
result={'pick':pick,'other':other,'graph_hops':float(h[other]),'mesh_edges':len(e),'boundary_edges':len(boundary),'nonmanifold_edges':int((count>2).sum()),'pick_on_boundary':bool(np.isin(pick,boundary).any()),'nearest_boundary_hops':float(h[np.unique(boundary)].min()) if len(boundary) else None,'rows':rows,'limitations':'Upper/lower are initial height groups. Edge ratios relative to settled shape, not solver rest spring strain. Paired vertices are nearest XY, not certified sewn correspondence.'}
(out/'topology_and_deformation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
