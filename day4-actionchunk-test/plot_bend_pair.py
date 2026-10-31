from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
b=Path('day4-actionchunk-test/results');fig,ax=plt.subplots(2,3,figsize=(12,8))
for row,(label,name) in enumerate([('bend100','day4-minimum-half-fold-20261031-065311-595489'),('bend10','day4-minimum-half-fold-20261031-070836-491946')]):
 d=b/name;p=dict(np.load(d/'fold_definition.npz'));mask=p['source_mask']
 for col,stage in enumerate(['00_initial','06_supported_place','11_retention_4s']):
  v=np.load(d/(stage+'.npz'))['vertices'];a=ax[row,col];a.scatter(v[~mask,0],v[~mask,1],s=.3,c='steelblue');a.scatter(v[mask,0],v[mask,1],s=.3,c='orange');a.axhline(float(p['fold_line_y']),color='gray',ls='--');a.set(title=label+' '+stage,xlim=(-.35,.35),ylim=(-.85,.05),aspect='equal')
fig.tight_layout();fig.savefig(b/'day4-minimum-half-fold-20261031-070836-491946/bend_pair_geometry.png',dpi=140)
