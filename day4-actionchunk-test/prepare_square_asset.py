from pathlib import Path
import numpy as np,json,hashlib
b=Path('day4-actionchunk-test/square_l1_candidate');b.mkdir(exist_ok=True)
n=21;v=np.array([[i*.02-.2,j*.02-.2,0.] for j in range(n) for i in range(n)]);f=[]
for j in range(n-1):
 for i in range(n-1):
  a=j*n+i;f.extend([[a,a+1,a+n],[a+1,a+n+1,a+n]])
f=np.array(f);edges=np.sort(np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);u,c=np.unique(edges,axis=0,return_counts=True)
assert len(v)==441 and len(f)==800 and (c<=2).all() and (c==1).sum()==80
assert (np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])[:,2]>0).all()
points=', '.join('('+', '.join(format(x,'.8g') for x in p)+')' for p in v)
text='#usda 1.0\n(\n    defaultPrim = "SquareCloth"\n    metersPerUnit = 1\n    upAxis = "Z"\n)\ndef Xform "SquareCloth"\n{\n    def Mesh "mesh"\n    {\n        uniform token subdivisionScheme = "none"\n        bool doubleSided = true\n        point3f[] points = ['+points+']\n        int[] faceVertexCounts = ['+', '.join(['3']*len(f))+']\n        int[] faceVertexIndices = ['+', '.join(map(str,f.ravel()))+']\n        color3f[] primvars:displayColor = [(0.25, 0.55, 0.8)]\n    }\n}\n'
p=b/'square_cloth_40cm.usda';p.write_text(text,encoding='utf8')
np.savez_compressed(b/'square_cloth_geometry.npz',vertices=v,triangles=f)
audit={'vertices':len(v),'triangles':len(f),'boundary_edges':int((c==1).sum()),'single_plane':bool(np.all(v[:,2]==0)),'consistent_positive_z_winding':True,'size_m':.4,'spacing_m':.02,'usd_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'usd_runtime_loaded':False,'simulation_run':False}
(b/'geometry_audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit))
