"""Experimental single-grasp adapter. Import only after SimulationApp starts."""
import numpy as np
import torch
from pxr import UsdGeom, Gf, PhysxSchema
from scipy.spatial.transform import Rotation
import omni.timeline
from Env.env.Control import AttachmentBlock


class SeparateBlock(AttachmentBlock):
    def create(self):
        view = super().create()
        self.stage.DefinePrim('/World/AttachmentConstraints', 'Scope')
        self.attachment_path = '/World/AttachmentConstraints/prepared_grasp'
        if self.stage.GetPrimAtPath(self.attachment_path).IsValid():
            raise RuntimeError('Prepared constraint path already exists')
        return view


class PreparedGraspControl:
    """One robot, one garment, one grasp at the preselected cloth region.

    Target positions retain the right_gripper frame used by MyFranka.
    This adapter does not claim arbitrary-point or repeated grasp support.
    """
    def __init__(self, env):
        if len(env.robots) != 1 or len(env.garment) != 1:
            raise ValueError('Prepared grasp supports one robot and one garment')
        self.original = env.control
        self.env = env
        self.world = env.world
        self.robot = env.robots[0]
        self.garment = env.garment[0]
        self.holding = False
        self.used = False
        self.attachlist = [None]
        self.local_offset = self.original.grasp_offset.detach().cpu().numpy().astype(float)
        mesh = UsdGeom.Mesh(self.world.stage.GetPrimAtPath(self.garment.garment_mesh_prim_path))
        transform = UsdGeom.XformCache().GetLocalToWorldTransform(mesh.GetPrim())
        vertices = np.array([tuple(transform.Transform(Gf.Vec3d(*map(float, p))))
                             for p in mesh.GetPointsAttr().Get()], dtype=np.float32)
        if not np.isfinite(vertices).all() or not len(vertices):
            raise RuntimeError('Invalid initial cloth geometry')
        anchor = vertices[np.argmin(vertices[:, 0])].copy()
        self.tracked = np.flatnonzero(np.linalg.norm(vertices - anchor, axis=1) < 0.02)
        self.block = SeparateBlock(self.world, self.robot, anchor,
                                   collision_group=self.original.collectionAPI_attach)
        self.block.attach(self.garment)
        import os
        overlap = float(os.environ.get("GARMENTLAB_ATTACHMENT_OVERLAP", "0.02"))
        if not np.isfinite(overlap) or not 0 <= overlap <= 0.02:
            raise ValueError("Attachment overlap must be between 0 and 0.02 m")
        prim = self.world.stage.GetPrimAtPath(self.block.attachment_path)
        attr = prim.GetAttribute("physxAutoAttachment:deformableVertexOverlapOffset")
        if not attr.IsValid() or not attr.Set(overlap):
            raise RuntimeError("Could not set attachment overlap")
        print("ATTACHMENT_OVERLAP_METERS", attr.Get(), flush=True)
        attachment = PhysxSchema.PhysxPhysicsAttachment.Get(self.world.stage, self.block.attachment_path)
        self.enabled = attachment.CreateAttachmentEnabledAttr()
        if not self.enabled.Set(False):
            raise RuntimeError('Could not disable precreated constraint')
        print('PREPARED_GRASP_CREATED', self.block.block_path, self.block.attachment_path, flush=True)

    def __getattr__(self, name):
        return getattr(self.original, name)

    def initialize(self):
        self.block.initialize_physics()
        self.block.set_velocities(np.zeros(6))

    def vertices(self):
        raw = self.garment.garment_mesh._cloth_prim_view.get_world_positions(clone=True)
        value = raw.detach().cpu().numpy()[0].copy()
        if value.ndim != 2 or value.shape[1] != 3 or not np.isfinite(value).all():
            raise RuntimeError('Invalid live cloth geometry')
        return value

    def block_target(self):
        pos, quat = self.robot.get_cur_ee_pos()
        quat = np.asarray(quat, dtype=float)
        offset = Rotation.from_quat(quat[[1, 2, 3, 0]]).apply(self.local_offset)
        return np.asarray(pos, dtype=float) + offset

    @staticmethod
    def _args(pos, ori, flag):
        if len(pos) != 1 or len(ori) != 1 or list(flag) != [True]:
            raise ValueError('Expected one active robot')
        target = np.asarray(pos[0], dtype=float)
        if target.shape != (3,) or not np.isfinite(target).all():
            raise ValueError('Invalid target position')
        return target, ori[0]

    def _tick(self, target, ori, follow=False):
        if not omni.timeline.get_timeline_interface().is_playing():
            raise RuntimeError('Timeline is not playing')
        self.robot.move(target, ori)
        if follow:
            delta = self.block_target() - self.block.get_position().numpy()
            velocity = delta / self.world.get_physics_dt()
            speed = np.linalg.norm(velocity)
            if speed > 0.3:
                velocity *= 0.3 / speed
            self.block.set_velocities(np.r_[velocity, np.zeros(3)])
        self.world.step()
        if not omni.timeline.get_timeline_interface().is_playing():
            raise RuntimeError('Timeline stopped during motion')

    def _drive(self, target, ori, follow=False, limit=1000):
        consecutive = 0
        try:
            for _ in range(int(limit)):
                self._tick(target, ori, follow)
                ee, _ = self.robot.get_cur_ee_pos()
                reached = np.linalg.norm(np.asarray(ee) - target) < 0.01
                reached = reached and bool(self.robot.reach(target, ori))
                if follow:
                    reached = reached and np.linalg.norm(
                        self.block_target() - self.block.get_position().numpy()) < 0.005
                consecutive = consecutive + 1 if reached else 0
                if consecutive >= 6:
                    return
            raise RuntimeError('Robot/block target timed out')
        finally:
            if follow:
                self.block.set_velocities(np.zeros(6))

    def robot_goto_position(self, pos, ori, flag, max_limit=1000):
        target, orientation = self._args(pos, ori, flag)
        self._drive(target, orientation, self.holding, max_limit)

    def move(self, pos, ori, flag, max_limit=1000):
        self.robot_goto_position(pos, ori, flag, max_limit)

    def grasp(self, pos, ori, flag, assign_garment=None):
        if assign_garment not in (None, 0):
            raise ValueError('Only garment zero is supported')
        if self.used or self.holding:
            raise RuntimeError('This experimental adapter permits only one grasp per process')
        target, orientation = self._args(pos, ori, flag)
        self._drive(target, orientation)
        # close() advances physics; keep the constraint disabled until it returns.
        self.robot.close()
        self._drive(target, orientation, follow=True)
        anchor = self.block.get_position().numpy()
        vertices = self.vertices()
        distance = float(np.linalg.norm(vertices[self.tracked] - anchor, axis=1).min())
        print('PREPARED_GRASP_REGION_DISTANCE', distance, flush=True)
        if distance >= 0.02:
            raise RuntimeError('Grasp is outside the preselected cloth region')
        before = vertices.copy()
        self.used = True
        import os
        disabled_probe = os.environ.get("GARMENTLAB_DISABLED_ATTACHMENT_PROBE") == "1"
        if not disabled_probe:
            if not self.enabled.Set(True):
                raise RuntimeError('Could not enable constraint')
        elif self.enabled.Get() is not False:
            raise RuntimeError('Disabled probe requires an inactive attachment')
        print("ATTACHMENT_ACTUALLY_ENABLED", self.enabled.Get(), flush=True)
        self.holding = True
        self.attachlist[0] = self.block
        try:
            self._tick(target, orientation, follow=True)
            after = self.vertices()
            displacement = np.linalg.norm(after - before, axis=1)
            worst = int(np.argmax(displacement))
            jump = float(displacement[worst])
            block_after = self.block.get_position().numpy()
            from pathlib import Path
            from datetime import datetime
            diagnostic = Path("/root/autodl-tmp") / (
                "attachment-enable-jump-" +
                datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".npz"
            )
            np.savez(
                diagnostic,
                before=before, after=after,
                tracked_indices=self.tracked,
                block_before=anchor, block_after=block_after,
                attachment_target=self.block_target(),
            )
            print("ENABLE_DIAGNOSTIC_FILE", diagnostic, flush=True)
            print("ENABLE_WORST_VERTEX", worst,
                  "IN_TRACKED", bool(worst in self.tracked), flush=True)
            print("ENABLE_WORST_BEFORE_AFTER",
                  before[worst], after[worst], flush=True)
            print("ENABLE_DISPLACEMENT_P50_P95_P99_MAX",
                  np.percentile(displacement, [50, 95, 99, 100]), flush=True)
            print("ENABLE_TRACKED_MEAN_MAX",
                  float(displacement[self.tracked].mean()),
                  float(displacement[self.tracked].max()), flush=True)
            print("ENABLE_BLOCK_BEFORE_AFTER",
                  anchor, block_after, flush=True)
            print('PREPARED_ENABLE_MAX_VERTEX_DISPLACEMENT', jump, flush=True)
            if disabled_probe:
                print("DISABLED_ATTACHMENT_PROBE_CAPTURED", flush=True)
                raise RuntimeError("Diagnostic stop: disabled attachment comparison captured")
            if jump >= 0.03:
                raise RuntimeError('Attachment caused a one-step displacement >= 3 cm')
            self._drive(target, orientation, follow=True)
        except BaseException:
            self.block.set_velocities(np.zeros(6))
            self.enabled.Set(False)
            self.holding = False
            self.attachlist[0] = None
            raise

    def ungrasp(self, flag, keep=None):
        if list(flag) != [False] or (keep is not None and any(keep)):
            raise ValueError('Only release of the single grasp is supported')
        self.block.set_velocities(np.zeros(6))
        if not self.enabled.Set(False):
            raise RuntimeError('Could not disable constraint')
        self.holding = False
        self.attachlist[0] = None
        # open() advances physics after the constraint has been disabled.
        self.robot.open()

    def robot_reset(self):
        if self.holding:
            raise RuntimeError('Release before reset; episode restoration is not implemented')
        self.robot.open()
