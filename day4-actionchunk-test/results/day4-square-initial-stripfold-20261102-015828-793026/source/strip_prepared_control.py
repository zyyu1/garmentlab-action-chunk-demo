"""Prepared single-anchor edge slots for partial edge-strip folds (L2/L3).

L2 folds one strip inward from the left edge; L3 folds two strips (left edge
and bottom hem).  Only the used edge slots are converted to single manual
anchors.  The strips are the small-strip version of the validated x-axis
half-fold: the moving strip is carried over the fold line by the same
semicircular arc, so the folded strip lands on the sheet and stays there.
"""
import numpy as np
from pxr import PhysxSchema
from scipy.spatial.transform import Rotation

from hem_fold_geometry import short_segments
from single_anchor_hem_control import author_single_anchor
from square_proxy_ground_control import SquareProxyGroundControl

SLOT_BY_EDGE = {'right': 0, 'left': 1, 'bottom': 2}


class StripPreparedControl(SquareProxyGroundControl):
    def __init__(self, env, edges):
        super().__init__(env)
        self.strip_slots = []
        seen = set()
        for edge in edges:
            if edge not in SLOT_BY_EDGE or edge in seen:
                raise ValueError('Invalid or duplicate strip edge: ' + str(edge))
            seen.add(edge)
            slot = self.slots[SLOT_BY_EDGE[edge]]
            prim = self.world.stage.GetPrimAtPath(slot.block.attachment_path)
            author_single_anchor(prim, slot.rest_local[slot.pick_index])
            slot.max_single_anchor_gap_m = 0.
            self.strip_slots.append((edge, slot))
        for slot in self.slots:
            slot.output_directory = getattr(type(self), 'output_directory', None)

    def initialize(self):
        super().initialize()
        for edge, slot in self.strip_slots:
            prim = self.world.stage.GetPrimAtPath(slot.block.attachment_path)
            if prim.HasAPI(PhysxSchema.PhysxAutoAttachmentAPI) or \
                    slot.anchor_ids.tolist() != [slot.pick_index]:
                raise RuntimeError('Strip single anchor not preserved: ' + slot.label)
            x, y = self.rest_world[slot.pick_index, :2]
            xs = self.rest_world[:, 0]
            ys = self.rest_world[:, 1]
            on_boundary = (np.isclose(x, xs.min(), atol=1e-6) or
                           np.isclose(x, xs.max(), atol=1e-6) or
                           np.isclose(y, ys.min(), atol=1e-6))
            if not on_boundary:
                raise RuntimeError('Strip pick is not on a cloth boundary: ' + slot.label)
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
                        raise RuntimeError('Strip single anchor did not follow within 10 mm')
                return value

            slot._tick = checked_tick
            self._install_relaxed_drive(slot)

    @staticmethod
    def _install_relaxed_drive(slot):
        """Holding-phase convergence: public 3 cm EE contract, strict block/anchor.

        The pre-grasp drive keeps the original 10 mm gate so the gripper reaches
        the strip midpoint.  Once holding, the cloth load pulls the EE off the
        target; the prepared fold adapter's 10 mm / 0.1 rad/s gate would time
        out even though the block (and the anchored strip) follows correctly.
        """
        original_drive = slot._drive

        def relaxed_drive(target, ori, follow=False, limit=1000):
            if not follow:
                return original_drive(target, ori, follow, limit)
            consecutive = 0
            try:
                for _ in range(int(limit)):
                    slot._tick(target, ori, follow)
                    ee, _ = slot.robot.get_cur_ee_pos()
                    reached = np.linalg.norm(np.asarray(ee) - target) < .03
                    reached = reached and bool(slot.robot.reach(
                        target, slot.fold_orientation(ori)))
                    reached = reached and np.linalg.norm(
                        slot.block_target() - slot.block.get_position().numpy()) < .005
                    reached = reached and np.linalg.norm(slot.block_rotation_error()) < .03
                    consecutive = consecutive + 1 if reached else 0
                    if consecutive >= 6:
                        break
                else:
                    raise RuntimeError('Perturbation drive timed out')
            finally:
                slot.block.set_velocities(np.zeros(6))
            if not slot.holding and not slot.attachment_enabled():
                slot.align_disabled()

        slot._drive = relaxed_drive

    def robot_goto_position(self, pos, ori, flag, max_limit=1000):
        relaxed = self.holding or bool(getattr(self.active, 'used', False))
        if not relaxed:
            return super().robot_goto_position(pos, ori, flag, max_limit)
        target, orientation = self.active._args(pos, ori, flag)
        start, _ = self.robot.get_cur_ee_pos()
        segments = short_segments(start, target, max_step=.025)
        record = {'start': np.asarray(start).tolist(), 'target': target.tolist(),
                  'linear_subtargets': [p.tolist() for p in segments],
                  'holding': self.holding, 'used': bool(self.active.used),
                  'perturbation_ee_tolerance_m': .03,
                  'post_check': 'relaxed; no joint-velocity gate'}
        self.motion_records.append(record)
        for i, point in enumerate(segments):
            self.probe_subtarget = {'segment': i, 'xyz': point.tolist(),
                                    'orientation': orientation}
            self.active.robot_goto_position([point], [orientation], flag, min(max_limit, 240))
        consecutive = 0
        for _ in range(60):
            self.active._tick(target, orientation, follow=self.holding)
            ee, _ = self.robot.get_cur_ee_pos()
            ok = np.linalg.norm(np.asarray(ee) - target) < .03
            if self.holding:
                ok = ok and np.linalg.norm(
                    self.active.block_target() - self.active.block.get_position().numpy()) < .005
            consecutive = consecutive + 1 if ok else 0
            if consecutive >= 6:
                record['converged'] = True
                return
        record['converged'] = False
