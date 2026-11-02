"""Read initialized USD audit and saved v5 states; never start simulation."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

ap=argparse.ArgumentParser();ap.add_argument('readout',type=Path);ap.add_argument('v5',type=Path)
a=ap.parse_args();r=json.loads(a.readout.read_text())
out={'readout':str(a.readout),'initialization_steps':[r.get('step_after_start'),r.get('step_after_read')],
     'effective_offsets':r.get('effective_offsets'),'errors':r.get('errors'),'rows':[],
     'scope':'USD authored collision mesh at saved measured wrist pose; +/-40mm hand-Y opening envelope; not cooked hull vertices or a dynamic replay'}
for name in ['01_before_close','02_grasp','03_held','04_released']:
    z=np.load(a.v5/(name+'.npz'));rot=Rotation.from_quat(z['ee_quaternion'][[1,2,3,0]])
    for c in r.get('colliders',[]):
        if 'mesh_points_hand_frame_m' not in c:continue
        v=np.array(c['mesh_points_hand_frame_m']);lows=[]
        for shift in [-.04,0,.04]:
            hand=v+np.array([0,shift,0])
            # URDF fixed transforms: hand Rz(-pi/4), right_gripper Rz(3pi/4), z=.1.
            ee=hand*np.array([-1,-1,1])+np.array([0,0,-.1])
            w=rot.apply(ee)+z['ee_position'];lows.append(float(w[:,2].min()))
        out['rows'].append({'snapshot':name,'collider':c['path'],'usd_attributes':c['attributes'],
                            'minimum_z_m_opening_envelope':[min(lows),max(lows)],'mesh_vertices':len(v)})
(a.readout.parent/'geometry_summary.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
