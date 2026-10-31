"""Development adapter: existing point grasp plus ordinary linear interpolation."""
import numpy as np
from single_anchor_hem_control import SingleAnchorHemControl
from hem_fold_geometry import short_segments

class SquareControl(SingleAnchorHemControl):
    def initialize(self):
        super().initialize()
        if self.rest_world.shape != (441,3):
            raise RuntimeError('Expected 441 square vertices')
        s=self.slots[2]
        if not np.isclose(self.rest_world[s.pick_index,1],self.rest_world[:,1].min(),atol=1e-6):
            raise RuntimeError('Square grasp must be on lower boundary')
        self.motion_records=[]

    def robot_goto_position(self,pos,ori,flag,max_limit=1000):
        target,orientation=self.active._args(pos,ori,flag)
        start,_=self.robot.get_cur_ee_pos()
        segments=short_segments(start,target,max_step=.025)
        record={'start':np.asarray(start).tolist(),'target':target.tolist(),
                'linear_subtargets':[p.tolist() for p in segments], 'holding':self.holding}
        self.motion_records.append(record)
        for point in segments:
            self.active.robot_goto_position([point],[orientation],flag,max_limit)
        consecutive=0
        for _ in range(120):
            self.active._tick(target,orientation,follow=self.holding)
            ee,_=self.robot.get_cur_ee_pos()
            raw=self.robot._robot.get_joint_velocities()
            vel=raw.detach().cpu().numpy() if hasattr(raw,'detach') else np.asarray(raw)
            ok=(np.linalg.norm(np.asarray(ee)-target)<.01 and np.max(abs(vel[:7]))<.1)
            if self.holding:
                ok=ok and np.linalg.norm(self.active.block_target()-self.active.block.get_position().numpy())<.005
            consecutive=consecutive+1 if ok else 0
            if consecutive>=6:
                record['converged']=True
                return
        raise RuntimeError('Square waypoint velocity/position did not converge')

    def move(self,pos,ori,flag,max_limit=1000):
        return self.robot_goto_position(pos,ori,flag,max_limit)

    def set_fold_angle(self,*args,**kwargs):
        raise RuntimeError('Pitch side channel prohibited for square candidate')
