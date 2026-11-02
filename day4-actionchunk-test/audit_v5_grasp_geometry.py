"""Read saved v5 data only. No Isaac imports, robot commands or simulation."""
import argparse, collections, hashlib, json, struct, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--results',type=Path,required=True)
    ap.add_argument('--assets',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); p=a.results
    joints={j.find('child').get('link'):j for j in ET.parse(a.assets/'lula_franka_gen.urdf').getroot().findall('joint')}
    def transform(link,opening):
        if link=='panda_link8':return np.eye(4)
        j=joints[link];o=j.find('origin');t=np.eye(4)
        if o is not None:
            t[:3,3]=np.fromstring(o.get('xyz','0 0 0'),sep=' ')
            t[:3,:3]=R.from_euler('xyz',np.fromstring(o.get('rpy','0 0 0'),sep=' ')).as_matrix()
        if j.get('type')=='prismatic':
            m=np.eye(4);m[:3,3]=np.fromstring(j.find('axis').get('xyz'),sep=' ')*opening;t=t@m
        return transform(j.find('parent').get('link'),opening)@t
    data=(a.assets/'finger.stl').read_bytes();n=struct.unpack_from('<I',data,80)[0]
    assert len(data)==84+50*n
    dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attr','<u2')])
    mesh=np.frombuffer(data,offset=84,count=n,dtype=dtype)['vertices'].reshape(-1,3).astype(float)
    rows=[]
    for name in ['00_initial','01_before_close','02_grasp','03_held','04_released']:
        z=np.load(p/(name+'.npz'));ee=z['ee_position'];rot=R.from_quat(z['ee_quaternion'][[1,2,3,0]])
        target=ee+rot.apply([0,0,.0034]);bp=z['block_position_2'].reshape(3);bq=z['block_quaternion_2'].reshape(4)
        br=R.from_quat(bq[[1,2,3,0]]).as_matrix();bottom=bp[2]-.015*np.abs(br[2]).sum()
        clear={}
        for opening in [0.,.04]:
            for side in ['left','right']:
                rel=np.linalg.inv(transform('right_gripper',opening))@transform('panda_'+side+'finger',opening)
                link=joints['panda_'+side+'finger'].find('child').get('link')
                el=ET.parse(a.assets/'lula_franka_gen.urdf').getroot().find("link[@name='%s']/collision/origin"%link)
                mt=np.eye(4)
                if el is not None:
                    mt[:3,3]=np.fromstring(el.get('xyz','0 0 0'),sep=' ')
                    mt[:3,:3]=R.from_euler('xyz',np.fromstring(el.get('rpy','0 0 0'),sep=' ')).as_matrix()
                rel=rel@mt
                world=rot.apply(mesh@rel[:3,:3].T+rel[:3,3])+ee
                clear[side+'_'+str(opening)]=float(world[:,2].min())
        rows.append({'snapshot':name,'ee_world_m':ee.tolist(),'material_reference_world_m':target.tolist(),
          'cloth_pick_world_m':z['vertices'][10].tolist(),'block_center_world_m':bp.tolist(),
          'block_bottom_z_m':float(bottom),'block_center_minus_target_m':(bp-target).tolist(),
          'urdf_mesh_min_z_open_closed_m':clear})
    events=[json.loads(l) for l in (p/'block_contacts.jsonl').read_text().splitlines()]
    counts=collections.Counter((e['category'],e['phase']) for e in events)
    h=[json.loads(l) for l in (p/'hold_trace.jsonl').read_text().splitlines()]
    dt=json.loads((p/'result.json').read_text())['physics_dt']
    vel=[]
    for x in h:
        delta=np.array(x['block_target'])-x['block_position'];v=delta/dt
        if np.linalg.norm(v)>.3:v*=.3/np.linalg.norm(v)
        vel.append(v)
    out={'scope':'Offline saved-state audit. URDF triangle mesh is not cooked USD collision geometry; ground z=0 from default-ground construction.',
      'source_result':str(p),'snapshots':rows,'hold_reconstructed_follow_velocity_first_m_s':vel[0].tolist(),
      'hold_reconstructed_follow_speed_range_m_s':[float(np.linalg.norm(vel,axis=1).min()),float(np.linalg.norm(vel,axis=1).max())],
      'contact_counts':[{'category':k[0],'phase':k[1],'count':v} for k,v in counts.items()],
      'input_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [a.assets/'lula_franka_gen.urdf',a.assets/'finger.stl',p/'result.json',p/'hold_trace.jsonl',p/'block_contacts.jsonl']}}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps({'snapshots':rows,'hold_follow_speed_range':out['hold_reconstructed_follow_speed_range_m_s']},indent=2))

if __name__=='__main__':main()
