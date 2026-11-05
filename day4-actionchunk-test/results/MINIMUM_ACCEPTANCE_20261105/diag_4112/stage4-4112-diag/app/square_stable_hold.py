"""Joint-space stationary hold for the square grasp diagnostic.

Replaces repeated RMP calls at a fixed target (v3 trace: controller output
diverges from step 690) with explicit joint position targets captured at the
converged configuration. Block follow velocities are kept identical to
HemPreparedGraspControl._tick(follow=True). Development diagnostic only.
"""
import json
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from omni.isaac.core.utils.types import ArticulationAction

ARM_NAMES=['panda_joint'+str(i) for i in range(1,8)]

class StableHold:
    def __init__(self,robot,world,slot,out):
        self.robot=robot;self.world=world;self.slot=slot;self.out=Path(out)
        dofs=list(robot._robot.dof_names)
        self.indices=[dofs.index(name) for name in ARM_NAMES]
        self.target=None;self.dt=float(world.get_physics_dt())
        self.rows=[];self.steps=0
    def begin(self):
        reference=self.robot._robot.get_joint_positions()
        if not isinstance(reference,torch.Tensor):raise TypeError('Expected torch joint state')
        self.target=reference[self.indices].clone()
        if self.target.shape!=(7,) or not bool(torch.isfinite(self.target).all().item()):
            raise RuntimeError('Invalid hold target')
        return self.target.detach().cpu().numpy().tolist()
    def _apply(self):
        reference=self.robot._robot.get_joint_positions()
        target=torch.as_tensor(self.target,dtype=reference.dtype,device=reference.device)
        indices=torch.as_tensor(self.indices,dtype=torch.long,device=reference.device)
        self.robot._articulation_controller.apply_action(ArticulationAction(
            joint_positions=target,joint_velocities=torch.zeros_like(target),joint_indices=indices))
    def _follow_block(self):
        delta=self.slot.block_target()-self.slot.block.get_position().numpy()
        velocity=delta/self.dt
        speed=float(np.linalg.norm(velocity))
        if speed>.3:velocity*=.3/speed
        angular=self.slot.block_rotation_error()/self.dt
        angular_speed=float(np.linalg.norm(angular))
        if angular_speed>1.:angular*=1./angular_speed
        self.slot.block.set_velocities(np.r_[velocity,angular])
    def _check_anchor(self):
        if not (self.slot.holding and self.slot.attachment_enabled()):return
        prim=self.world.stage.GetPrimAtPath(self.slot.block.attachment_path)
        p1=np.asarray(prim.GetAttribute('points1').Get(),dtype=float)
        pos,q=self.slot.block.move_block_controller.get_world_poses()
        pos=pos.detach().cpu().numpy().reshape(3);q=q.detach().cpu().numpy().reshape(4)
        scale=np.asarray(self.world.stage.GetPrimAtPath(self.slot.block.block_path).GetAttribute('xformOp:scale').Get(),dtype=float)
        desired=Rotation.from_quat(q[[1,2,3,0]]).apply(p1*scale)+pos
        gap=float(np.linalg.norm(self.slot.vertices()[self.slot.anchor_ids]-desired,axis=1).max())
        self.slot.max_single_anchor_gap_m=max(self.slot.max_single_anchor_gap_m,gap)
        if not np.isfinite(gap) or gap>.01:
            raise RuntimeError('Manual single anchor did not follow within 10mm diagnostic bound')
    def _record(self):
        ee,q=self.robot.get_cur_ee_pos()
        jp=self.robot._robot.get_joint_positions();jv=self.robot._robot.get_joint_velocities()
        def arr(value):
            return value.detach().cpu().numpy().tolist() if hasattr(value,'detach') else np.asarray(value).tolist()
        self.rows.append({'hold_step':self.steps,'physics_step':int(self.world.current_time_step_index),
            'ee_position':np.asarray(ee).tolist(),'ee_quaternion_wxyz':np.asarray(q).tolist(),
            'joint_positions':arr(jp),'joint_velocities':arr(jv),
            'block_position':self.slot.block.get_position().numpy().tolist(),
            'block_target':self.slot.block_target().tolist(),
            'holding':bool(self.slot.holding),'attachment_enabled':bool(self.slot.attachment_enabled()),
            'anchor_gap_max_m':float(self.slot.max_single_anchor_gap_m)})
    def tick(self):
        self._apply()
        self._follow_block()
        self.world.step()
        self._check_anchor()
        self.steps+=1
        self._record()
    def run(self,steps):
        for _ in range(int(steps)):self.tick()
        self.slot.block.set_velocities(np.zeros(6))
    def save(self):
        (self.out/'hold_trace.jsonl').write_text(
            '\n'.join(json.dumps(row) for row in self.rows)+'\n',encoding='utf-8')
        return {'steps':self.steps,'control':'joint_position_hold; RMP not called at fixed target',
                'target_joint_positions':self.target.detach().cpu().numpy().tolist(),
                'arm_joint_indices':self.indices}
