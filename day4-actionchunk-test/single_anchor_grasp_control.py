"""Diagnostic point-grasp proxy: remove rigid patch orientation coupling.

This changes the grasp model, not the robot action schema. Not a calibrated pinch.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from pxr import Gf, Vt, PhysxSchema
from multi_prepared_grasp_control import MultiPreparedGraspControl

def author_single_anchor(prim,point_local):
    if prim.HasAPI(PhysxSchema.PhysxAutoAttachmentAPI):
        if not prim.RemoveAPI(PhysxSchema.PhysxAutoAttachmentAPI):raise RuntimeError('Could not remove auto attachment API')
    if prim.HasAPI(PhysxSchema.PhysxAutoAttachmentAPI):raise RuntimeError('Auto attachment API still applied')
    for name,value in [('points0',np.asarray(point_local,dtype=float).reshape(1,3)),('points1',np.zeros((1,3)))]:
        attr=prim.GetAttribute(name)
        if not attr.Set(Vt.Vec3fArray([Gf.Vec3f(*map(float,row)) for row in value])):
            raise RuntimeError('Manual anchor write failed: '+name)
        if not np.array_equal(np.asarray(attr.Get()),value.astype(np.float32).astype(float)):
            raise RuntimeError('Manual anchor readback mismatch')

class SingleAnchorMultiControl(MultiPreparedGraspControl):
    def __init__(self,env):
        super().__init__(env)
        for slot in self.slots:
            prim=self.world.stage.GetPrimAtPath(slot.block.attachment_path)
            if slot.attachment_enabled():raise RuntimeError('Manual anchors must be authored disabled')
            author_single_anchor(prim,slot.rest_local[slot.pick_index])
            slot.max_single_anchor_gap_m=0.

    def initialize(self):
        super().initialize()
        for slot in self.slots:
            prim=self.world.stage.GetPrimAtPath(slot.block.attachment_path)
            if prim.HasAPI(PhysxSchema.PhysxAutoAttachmentAPI) or slot.anchor_ids.tolist()!=[slot.pick_index]:
                raise RuntimeError('Single anchor configuration not preserved through reset')
            original_tick=slot._tick
            def checked_tick(target,ori,follow=False,slot=slot,original_tick=original_tick):
                value=original_tick(target,ori,follow)
                if slot.holding and slot.attachment_enabled():
                    prim=self.world.stage.GetPrimAtPath(slot.block.attachment_path)
                    p1=np.asarray(prim.GetAttribute('points1').Get(),dtype=float)
                    pos,q=slot.block.move_block_controller.get_world_poses()
                    pos=pos.detach().cpu().numpy().reshape(3);q=q.detach().cpu().numpy().reshape(4)
                    scale=np.asarray(self.world.stage.GetPrimAtPath(slot.block.block_path).GetAttribute('xformOp:scale').Get(),dtype=float)
                    desired=Rotation.from_quat(q[[1,2,3,0]]).apply(p1*scale)+pos
                    gap=float(np.linalg.norm(slot.vertices()[slot.anchor_ids]-desired,axis=1).max())
                    slot.max_single_anchor_gap_m=max(slot.max_single_anchor_gap_m,gap)
                    if not np.isfinite(gap) or gap>.01:
                        raise RuntimeError('Manual single anchor did not follow within 10mm diagnostic bound')
                return value
            slot._tick=checked_tick
        print('SINGLE_ANCHOR_SLOTS_VERIFIED_AFTER_RESET',flush=True)
