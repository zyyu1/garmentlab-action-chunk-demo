"""Prepared single-anchor corner slots for L2/L3 fold-over and recovery.

Adds four corner regions to the existing prepared square control.  Each corner
uses a single manual anchor (5 mm attachment setup).

The perturbation generator needs a grasp that actually reaches the corner
(the original Control stops at its 3 cm reach tolerance and closes above the
cloth).  The prepared grasp reaches with a 10 mm gate before closing, then the
cloth load pulls the EE ~14 mm off the lift target.  For these L2/L3
generation runs only, holding-phase convergence is relaxed to the public 3 cm
contract while block follow (<5 mm) and the single-anchor gap (<10 mm) stay
strict.  The production fold control is not changed.
"""
import numpy as np
from pxr import Gf, PhysxSchema, UsdGeom, UsdPhysics
from scipy.spatial.transform import Rotation

from hem_fold_geometry import short_segments
from multi_prepared_grasp_control import PreparedRegion
from single_anchor_hem_control import author_single_anchor
from square_proxy_ground_control import GROUND, SquareProxyGroundControl

CORNER_LOCAL = np.array([[-.2, -.2, 0.], [.2, -.2, 0.], [.2, .2, 0.], [-.2, .2, 0.]])


class CornerPreparedControl(SquareProxyGroundControl):
    def __init__(self, env):
        super().__init__(env)
        mesh = UsdGeom.Mesh(self.world.stage.GetPrimAtPath(self.garment.garment_mesh_prim_path))
        local = np.asarray(mesh.GetPointsAttr().Get(), dtype=float)
        transform = UsdGeom.XformCache().GetLocalToWorldTransform(mesh.GetPrim())
        world = np.asarray([tuple(transform.Transform(Gf.Vec3d(*map(float, row)))) for row in local])
        if local.shape != (441, 3) or world.shape != (441, 3):
            raise RuntimeError('Unexpected constructed vertex arrays')
        self.corner_picks = []
        self.corner_labels = []
        for index, corner in enumerate(CORNER_LOCAL):
            distance = ((local - corner) ** 2).sum(axis=1)
            pick = int(np.argmin(distance))
            if distance[pick] > 1e-8:
                raise RuntimeError(f'Corner {index} not found in constructed mesh')
            label = 'corner_%d' % index
            slot = PreparedRegion(env, label, pick, local, world)
            slot.max_single_anchor_gap_m = 0.
            prim = self.world.stage.GetPrimAtPath(slot.block.attachment_path)
            author_single_anchor(prim, slot.rest_local[pick])
            ground = self.world.stage.GetPrimAtPath(GROUND)
            if not ground.IsValid() or not ground.HasAPI(UsdPhysics.CollisionAPI):
                raise RuntimeError('Expected default ground collider')
            block_prim = self.world.stage.GetPrimAtPath(slot.block.block_path)
            api = UsdPhysics.FilteredPairsAPI.Apply(block_prim)
            relation = api.CreateFilteredPairsRel()
            self.proxy_ground_before[slot.block.block_path] = [str(p) for p in relation.GetTargets()]
            if not relation.AddTarget(ground.GetPath()):
                raise RuntimeError('Could not filter corner proxy from ground')
            self.slots.append(slot)
            self.regions.append((label, pick))
            self.corner_picks.append(pick)
            self.corner_labels.append(label)
        for slot in self.slots:
            slot.output_directory = getattr(type(self), 'output_directory', None)
        self.proxy_ground_authored = self.verify_proxy_ground()

    def initialize(self):
        super().initialize()
        for slot in self.slots[3:]:
            prim = self.world.stage.GetPrimAtPath(slot.block.attachment_path)
            if prim.HasAPI(PhysxSchema.PhysxAutoAttachmentAPI) or \
                    slot.anchor_ids.tolist() != [slot.pick_index]:
                raise RuntimeError('Corner single anchor not preserved: ' + slot.label)
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
                        raise RuntimeError('Corner single anchor did not follow within 10 mm')
                return value

            slot._tick = checked_tick
            self._install_relaxed_drive(slot)

    @staticmethod
    def _install_relaxed_drive(slot):
        original_drive = slot._drive

        def relaxed_drive(target, ori, follow=False, limit=1000):
            if not follow:
                # Pre-grasp approach/descend keeps the strict 10 mm gate.
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
        if not self.holding:
            return super().robot_goto_position(pos, ori, flag, max_limit)
        target, orientation = self.active._args(pos, ori, flag)
        start, _ = self.robot.get_cur_ee_pos()
        segments = short_segments(start, target, max_step=.025)
        record = {'start': np.asarray(start).tolist(), 'target': target.tolist(),
                  'linear_subtargets': [p.tolist() for p in segments],
                  'holding': self.holding,
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
            ok = ok and np.linalg.norm(
                self.active.block_target() - self.active.block.get_position().numpy()) < .005
            consecutive = consecutive + 1 if ok else 0
            if consecutive >= 6:
                record['converged'] = True
                return
        record['converged'] = False
