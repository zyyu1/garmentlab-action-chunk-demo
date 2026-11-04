"""Development adapter: x-axis centre fold with the precreated left-edge slot.

Only the selected edge slot is converted to a single manual anchor.  The other
slots keep their original prepared configuration; proxy-ground filtering and
public action semantics are inherited unchanged.
"""
import numpy as np
from pxr import PhysxSchema
from scipy.spatial.transform import Rotation
from single_anchor_hem_control import author_single_anchor
from square_proxy_ground_control import SquareProxyGroundControl

FOLD_SLOT_INDEX = 1


class SquareEdgeProxyGroundControl(SquareProxyGroundControl):
    def __init__(self, env):
        super().__init__(env)
        slot = self.slots[FOLD_SLOT_INDEX]
        if slot.label != 'left_sleeve':
            raise RuntimeError('Expected precreated left_sleeve slot')
        prim = self.world.stage.GetPrimAtPath(slot.block.attachment_path)
        author_single_anchor(prim, slot.rest_local[slot.pick_index])
        slot.max_single_anchor_gap_m = 0.
        self.fold_slot = slot

    def initialize(self):
        super().initialize()
        slot = self.fold_slot
        prim = self.world.stage.GetPrimAtPath(slot.block.attachment_path)
        if prim.HasAPI(PhysxSchema.PhysxAutoAttachmentAPI) or slot.anchor_ids.tolist() != [slot.pick_index]:
            raise RuntimeError('Left-edge single anchor not preserved through reset')
        if not np.isclose(self.rest_world[slot.pick_index, 0], self.rest_world[:, 0].min(), atol=1e-6):
            raise RuntimeError('Fold pick must lie on the left boundary')
        mid_y = (self.rest_world[:, 1].min() + self.rest_world[:, 1].max()) / 2
        if abs(self.rest_world[slot.pick_index, 1] - mid_y) > .02:
            raise RuntimeError('Fold pick must lie near the edge midpoint')

        original_tick = slot._tick

        def checked_tick(target, ori, follow=False, slot=slot, original_tick=original_tick):
            value = original_tick(target, ori, follow)
            if slot.holding and slot.attachment_enabled():
                prim = self.world.stage.GetPrimAtPath(slot.block.attachment_path)
                p1 = np.asarray(prim.GetAttribute('points1').Get(), dtype=float)
                pos, q = slot.block.move_block_controller.get_world_poses()
                pos = pos.detach().cpu().numpy().reshape(3)
                q = q.detach().cpu().numpy().reshape(4)
                scale = np.asarray(self.world.stage.GetPrimAtPath(
                    slot.block.block_path).GetAttribute('xformOp:scale').Get(), dtype=float)
                desired = Rotation.from_quat(q[[1, 2, 3, 0]]).apply(p1 * scale) + pos
                gap = float(np.linalg.norm(slot.vertices()[slot.anchor_ids] - desired, axis=1).max())
                slot.max_single_anchor_gap_m = max(slot.max_single_anchor_gap_m, gap)
                if not np.isfinite(gap) or gap > .01:
                    raise RuntimeError('Manual single anchor did not follow within 10mm diagnostic bound')
            return value

        slot._tick = checked_tick
