import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components,dijkstra
base=Path(__file__).resolve().parent
out=base/'results/day4-minimum-half-fold-20261031-060323-618705'
p=dict(np.load(out/'fold_definition.npz'));v=p['initial_vertices'];m=p['source_mask'];line=float(p['fold_line_y']);pick=int(p['pick_index'])
groups={'all':m,'left':m&(v[:,0]<-.06),'middle':m&(abs(v[:,0])<=.06),'right':m&(v[:,0]>.06),'initial_upper_z_gt_20mm':m&(v[:,2]>.02),'initial_lower_z_le_20mm':m&(v[:,2]<=.02)}
names=['04_cross_line','04b_arrived_before_hold','06_supported_place','07_released','08_release_stationary'];rows={}
fig,axs=plt.subplots(1,3,figsize=(13,4))
for name in names:
 q=np.load(out/(name+'.npz'))['vertices'];rows[name]={}
 for group,g in groups.items():
  rows[name][group]={'count':int(g.sum()),'crossed_fraction':float(np.mean(q[g,1]>line)),'dy_mean_mm':float(np.mean(q[g,1]-v[g,1])*1000),'z_median_mm':float(np.median(q[g,2])*1000),'reflected_xy_error_mean_mm':float(np.mean(np.linalg.norm(q[g,:2]-np.c_[v[g,0],2*line-v[g,1]],axis=1))*1000)}
for ax,name in zip(axs,['00_initial','06_supported_place','08_release_stationary']):
 q=np.load(out/(name+'.npz'))['vertices']
 for group,color in [('initial_upper_z_gt_20mm','orange'),('initial_lower_z_le_20mm','steelblue')]:
  g=groups[group];ax.scatter(q[g,1],q[g,2],s=2,c=color,label=group)
 ax.axvline(line,c='gray',ls='--');ax.scatter(q[pick,1],q[pick,2],c='red',s=25);ax.set(title=name,xlabel='world y (m)',ylabel='z (m)',ylim=(0,.15),xlim=(-.8,-.1))
axs[0].legend(fontsize=6);fig.tight_layout();fig.savefig(out/'material_layer_coverage.png',dpi=150);plt.close(fig)
c=np.load(out/'cloth_constructed.npz');edges=[];i=0
for n in c['faceVertexCounts']:
 f=c['faceVertexIndices'][i:i+n];i+=n;edges.extend(zip(f,np.roll(f,-1)))
e=np.array(edges);g=coo_matrix((np.ones(len(e)*2),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(len(v),len(v))).tocsr();n,labels=connected_components(g)
low=np.flatnonzero(groups['initial_lower_z_le_20mm']);other=int(low[np.argmin(np.linalg.norm(v[low,:2]-v[pick,:2],axis=1))])
a={'stages':rows,'mesh_connected_components':int(n),'pick_id':pick,'nearby_lower_id':other,'nearby_lower_xy_gap_mm':float(np.linalg.norm(v[other,:2]-v[pick,:2])*1000),'nearby_lower_z_gap_mm':float((v[pick,2]-v[other,2])*1000),'mesh_edge_hops_between_points':float(dijkstra(g,indices=pick,unweighted=True)[other]),'limits':'Initial-height material groups, not verified garment front/back labels or contact-force evidence; topology connectivity does not imply a local hem seam.'}
(out/'material_coverage_audit.json').write_text(json.dumps(a,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in a.items() if k!='stages'},indent=2))
