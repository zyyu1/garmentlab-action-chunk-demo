from pathlib import Path
import sys,json,hashlib,xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root.parent))
from square_pose_contract import orientation_matrix,grasp_to_ee,GRASP_OFFSET_LOCAL
from square_geometry import square_targets
u=root/'lula_franka_gen.urdf';tree=ET.parse(u).getroot()
joints={j.find('child').get('link'):j for j in tree.findall('joint')}
names=['panda_joint'+str(i) for i in range(1,8)]
js={j.get('name'):j for j in joints.values()}
bounds=np.array([[float(js[n].find('limit').get(k)) for k in ('lower','upper')] for n in names])
def vec(el,tag,default):return np.fromstring(el.get(tag,default),sep=' ')
def fk(q,link='right_gripper',finger=.04):
    cache={}
    base=np.eye(4);base[:3,:3]=R.from_euler('z',-np.pi/2).as_matrix()
    def walk(l):
        if l not in joints:return base
        if l in cache:return cache[l]
        j=joints[l];o=j.find('origin');T=np.eye(4)
        if o is not None:T[:3,:3]=R.from_euler('xyz',vec(o,'rpy','0 0 0')).as_matrix();T[:3,3]=vec(o,'xyz','0 0 0')
        M=np.eye(4);n=j.get('name');typ=j.get('type')
        if typ in ('revolute','continuous'):M[:3,:3]=R.from_rotvec(vec(j.find('axis'),'xyz','1 0 0')*q[names.index(n)]).as_matrix()
        elif typ=='prismatic':M[:3,3]=vec(j.find('axis'),'xyz','1 0 0')*finger
        out=walk(j.find('parent').get('link'))@T@M;cache[l]=out;return out
    return walk(link)
nominal=np.array([0,-.785,0,-2.356,0,1.571,.785])
# Independently verify named frame midpoint against complete URDF chain, for three openings.
midpoints=[]
for opening in (0.,.02,.04):
    ee=fk(nominal);left=fk(nominal,'panda_leftfingertip',opening);right=fk(nominal,'panda_rightfingertip',opening)
    mid=ee[:3,:3].T@((left[:3,3]+right[:3,3])/2-ee[:3,3]);assert np.allclose(mid,GRASP_OFFSET_LOCAL,atol=1e-10);midpoints.append(mid.tolist())
for yaw in (-1.,0.,1.):
    A=orientation_matrix(yaw);assert np.allclose(A[:,2],[0,0,-1]);assert np.allclose(A[:,0],[np.cos(yaw),np.sin(yaw),0])
    point=np.array([0.,-.65,.0099]);assert np.allclose(grasp_to_ee(point,yaw)+A@GRASP_OFFSET_LOCAL,point)
# Compare manual FK with saved Isaac FK/command records if available.
checks=[]
for path in sorted((root.parent/'results').glob('day4-wrist-reach-*/result.json')):
    data=json.loads(path.read_text());rows=data.get('targets',[])
    for row in rows[-1:]:
        if 'joint_positions' not in row or 'actual_position' not in row:continue
        T=fk(np.array(row['joint_positions'])[:7]);err=float(np.linalg.norm(T[:3,3]-row['actual_position']))
        checks.append({'source':str(path),'position_error_m':err})
if checks:assert max(x['position_error_m'] for x in checks)<1e-5,checks
# One declared downward-yaw-zero path, no height search and no physics simulation.
pick=np.array([0.,-.65,.0099]);material=square_targets(pick,-.45)
public=[('approach',pick+[0,0,.15]),('descend',grasp_to_ee(pick,0.))]+[(label,grasp_to_ee(v,0.)) for label,v in zip(('arc45','arc90','arc135','place'),material)]
rot=orientation_matrix(0);rows=[];previous=nominal;prev_point=None
for label,goal in public:
    sub=[goal] if prev_point is None else [prev_point+(goal-prev_point)*i/max(1,int(np.ceil(np.linalg.norm(goal-prev_point)/.025))) for i in range(1,max(1,int(np.ceil(np.linalg.norm(goal-prev_point)/.025)))+1)]
    for i,tgt in enumerate(sub):
        def residual(q):
            T=fk(q);return np.r_[T[:3,3]-tgt,.2*R.from_matrix(rot@T[:3,:3].T).as_rotvec()]
        candidates=[]
        for seed in (previous,nominal):
            opt=least_squares(residual,np.clip(seed,bounds[:,0]+1e-7,bounds[:,1]-1e-7),bounds=(bounds[:,0],bounds[:,1]),max_nfev=300,ftol=1e-10,xtol=1e-10,gtol=1e-10)
            q=opt.x;T=fk(q);pe=float(np.linalg.norm(T[:3,3]-tgt));re=float(R.from_matrix(rot@T[:3,:3].T).magnitude())
            candidates.append((pe+re*.2,q,pe,re))
            if pe<.002 and re<.02:break
        _,q,pe,re=min(candidates,key=lambda a:a[0]);valid=pe<.002 and re<.02
        link_points={l:fk(q,l)[:3,3].tolist() for l in ('panda_hand','panda_leftfingertip','panda_rightfingertip')}
        rows.append({'label':label,'subtarget':i,'target':tgt.tolist(),'q':q.tolist(),'position_error_m':pe,'orientation_error_rad':re,'within_limits':bool(np.all(q>=bounds[:,0]) and np.all(q<=bounds[:,1])),'max_joint_delta_rad':float(abs(q-previous).max()),'valid':valid,'named_link_origins':link_points})
        if not valid:break
        previous=q
    if not valid:break
    prev_point=goal
report={'urdf_sha256':hashlib.sha256(u.read_bytes()).hexdigest(),'base_yaw_rad':-np.pi/2,'fingertip_midpoint_local':midpoints,'saved_fk_crosschecks':checks,'targets':rows,'all_ik_verified':all(x['valid'] for x in rows),'scope':'URDF numerical IK/FK only; no robot commands, no GPU simulation; link origins do not certify mesh clearance or dynamic stability','collision_meshes_available':False}
(root/'pose_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({'all_ik_verified':report['all_ik_verified'],'targets':len(rows),'fk_crosschecks':checks,'last':rows[-1]},indent=2))
