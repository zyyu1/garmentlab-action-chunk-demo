import copy
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
import stage4_success_v1 as ev


def fixture(task='B_nominal', edge='left', yaw=0.):
    x,y = np.meshgrid(np.linspace(-.2,.2,21), np.linspace(-.2,.2,21))
    lp=np.c_[x.ravel(), y.ravel(), np.zeros(441)]
    a=lp.copy(); a[:,2]=.0099
    b=a.copy(); sign=1 if edge=='left' else -1
    mask=sign*lp[:,0]<-1e-6
    b[mask,0]=-b[mask,0]+sign*(.04 if task=='A_l1_overfold' else 0.)
    b[mask,2]=.02
    b[np.isclose(sign*lp[:,0],-.2),2]=.0099
    c,s=np.cos(yaw),np.sin(yaw); R=np.array([[c,-s,0],[s,c,0],[0,0,1]])
    a=a@R.T+[.1,-.5,0]; b=b@R.T+[.1,-.5,0]
    pick=210 if edge=='left' else 230
    meta={'task':task,'level':'flat' if task=='A_l1_overfold' else 'perturbed','edge':edge,'pick_index':pick,'yaw_rad':yaw,'floor_z_m':0.,'width_m':.2,'overhang_m':.02 if task=='A_l1_overfold' else 0.,'action_count':7 if task=='A_l1_overfold' else 12,'recovery_count':0 if task=='A_l1_overfold' else 1,'dt_s':1/60,'errors':[],'held_check':{'position_error_m':.001,'arm_speed_rad_s':.001,'anchor_gap_max_m':.001,'orientation_reached':True}}
    data={'initial':a,'local_points':lp,'vertices':np.repeat(b[None],331,axis=0),'steps':np.arange(331),'holding':np.zeros(331,dtype=bool),'attachment_enabled':np.zeros((331,3),dtype=bool),'gripper_open':np.ones(331,dtype=bool)}
    return meta,data


class CriteriaTests(unittest.TestCase):
    def test_identity_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'x.py').write_text('changed')
            (root/'stage4-success-v1-files.json').write_text(json.dumps({'x.py':'0'*64}))
            with patch.object(ev,'HERE',root):
                with self.assertRaises(ValueError):ev.identity()

    def test_two_tasks(self):
        for task in ['A_l1_overfold','B_nominal']:
            m,d=fixture(task); self.assertTrue(ev.evaluate(m,d)['success'])

    def test_yaw_and_mirror(self):
        for edge in ['left','right']:
            m,d=fixture(edge=edge,yaw=.37); self.assertTrue(ev.evaluate(m,d)['success'])

    def test_unfolded(self):
        m,d=fixture();d['vertices'][:]=d['initial'];self.assertFalse(ev.evaluate(m,d)['success'])

    def test_whole_cloth_moved(self):
        m,d=fixture();d['vertices'][:,:,0]+=.06;self.assertFalse(ev.evaluate(m,d)['checks']['geometry_entire_window'])

    def test_transient_rebound_cannot_hide_in_final(self):
        m,d=fixture();d['vertices'][250]=d['initial'];r=ev.evaluate(m,d)
        self.assertTrue(r['final_geometry']['geometry_pass']);self.assertFalse(r['success'])

    def test_particle_motion_not_just_centroid(self):
        m,d=fixture();d['vertices'][211::2,:220,1]+=.0005;d['vertices'][211::2,220:440,1]-=.0005
        r=ev.evaluate(m,d);self.assertLess(r['stability']['centroid_drift_max_m'],1e-10);self.assertFalse(r['checks']['stable'])

    def test_release_for_entire_window(self):
        m,d=fixture();d['attachment_enabled'][1,2]=True;self.assertFalse(ev.evaluate(m,d)['success'])

    def test_missing_and_short_are_incomplete(self):
        m,d=fixture();del d['gripper_open'];self.assertIsNone(ev.evaluate(m,d)['success'])
        m,d=fixture();d['steps']=np.arange(211);self.assertEqual(ev.evaluate(m,d)['status'],'incomplete')

    def test_nonfinite_and_bad_state_rejected(self):
        m,d=fixture();d['vertices'][0,0,0]=np.nan
        with self.assertRaises(ValueError):ev.evaluate(m,d)
        m,d=fixture();d['holding']=np.zeros(331)
        with self.assertRaises(ValueError):ev.evaluate(m,d)

    def test_budget_held_and_wrong_target(self):
        for key,value in [('action_count',13),('overhang_m',.02),('recovery_count',2)]:
            m,d=fixture();m[key]=value;self.assertFalse(ev.evaluate(m,d)['success'])
        m,d=fixture();m['held_check']['position_error_m']=.03;self.assertFalse(ev.evaluate(m,d)['success'])

    def test_task_specific_shape(self):
        m,d=fixture('A_l1_overfold');m['task']='B_nominal';m['level']='perturbed';m['overhang_m']=0;m['action_count']=12;m['recovery_count']=1
        self.assertFalse(ev.evaluate(m,d)['success'])

    def test_nominal_fold_not_l1_overfold(self):
        m,d=fixture();m.update(task='A_l1_overfold',level='flat',overhang_m=.02,action_count=7,recovery_count=0)
        self.assertFalse(ev.evaluate(m,d)['success'])

if __name__=='__main__':unittest.main()
