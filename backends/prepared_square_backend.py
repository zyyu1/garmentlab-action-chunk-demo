"""Prepared square-cloth Backend: yaw, stable hold, reset and re-grasp.

This is the Day4 integration candidate.  Public actions stay
``[x, y, z, yaw, gripper_command]``; the validated multi-slot control and
URDF fingertip-midpoint contract are imported from the Day4 package, which the
run harness places on ``sys.path``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from backends.garmentlab_backend import GarmentLabBackend
from schemas.action import CartesianAction, GripperCommand
from schemas.observation import GripperState, TaskPhase


class PreparedSquareBackend(GarmentLabBackend):
    def __init__(
        self,
        *,
        output_dir: Optional[str] = None,
        hold_steps: int = 60,
        hold_tolerance: float = 0.005,
        auto_regrasp: bool = True,
        enable_contact_reporting: bool = False,
        **kwargs: Any,
    ) -> None:
        kwargs["prepared_grasp"] = True
        super().__init__(**kwargs)
        self.output_dir = Path(output_dir) if output_dir is not None else None
        self.hold_steps = int(hold_steps)
        self.hold_tolerance = float(hold_tolerance)
        self.auto_regrasp = bool(auto_regrasp)
        self.enable_contact_reporting = bool(enable_contact_reporting)
        self.last_hold_summary: Optional[Dict[str, Any]] = None
        self.reset_count = 0

    # -----------------------------------------------------------------
    # Lifecycle / control factory
    # -----------------------------------------------------------------
    def _make_prepared_control(self, env):
        from square_edge_control import SquareEdgeProxyGroundControl
        SquareEdgeProxyGroundControl.enable_early_contact_reporting = self.enable_contact_reporting
        SquareEdgeProxyGroundControl.output_directory = self.output_dir
        return SquareEdgeProxyGroundControl(env)

    def set_output_dir(self, path) -> None:
        self.output_dir = Path(path)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            from square_edge_control import SquareEdgeProxyGroundControl
            SquareEdgeProxyGroundControl.output_directory = self.output_dir
        except ImportError:
            pass
        control = getattr(self._env, "control", None)
        if control is not None:
            for slot in control.slots:
                slot.output_directory = self.output_dir

    def start(self) -> None:
        super().start()
        from square_pose_contract import GRASP_OFFSET_LOCAL
        control = self._env.control
        if not hasattr(control, "fold_slot"):
            raise RuntimeError("Expected prepared square control")
        if control.fold_slot.label != "left_sleeve":
            raise RuntimeError("Expected left_sleeve fold slot")
        for slot in control.slots:
            slot.local_offset = GRASP_OFFSET_LOCAL.copy()
        self.reset_count = 0

    # -----------------------------------------------------------------
    # Action mapping
    # -----------------------------------------------------------------
    def _execute_single(self, a: CartesianAction) -> None:
        from square_pose_contract import orientation_euler

        target = np.asarray(a.target_pose[:3], dtype=np.float64)
        yaw = float(a.target_pose[3])
        if target.shape != (3,) or not np.isfinite(target).all() or not np.isfinite(yaw):
            raise ValueError("Invalid target pose")
        orientation = orientation_euler(yaw)
        cmd = int(a.gripper_command)
        control = self._env.control
        robot = self._env.robots[0]
        was_holding = self._holding

        if cmd == int(GripperCommand.CLOSE):
            control.grasp([target], [orientation], [True])
            self._gripper_state = GripperState.CLOSED_HOLDING
            self._holding = True
            self._phase = TaskPhase.GRASP
        elif cmd == int(GripperCommand.HOLD):
            if self._holding:
                ee, _ = robot.get_cur_ee_pos()
                if np.linalg.norm(np.asarray(ee, dtype=float) - target) <= self.hold_tolerance:
                    self._run_stable_hold(target, orientation)
                else:
                    control.move([target], [orientation], [True])
            else:
                control.robot_goto_position([target], [orientation], [True], max_limit=1000)
            if self._holding:
                self._gripper_state = GripperState.CLOSED_HOLDING
            self._phase = TaskPhase.TRANSFER
        elif cmd == int(GripperCommand.OPEN):
            if self._holding:
                control.ungrasp([False])
                self._holding = False
            self._gripper_state = GripperState.OPEN
            control.robot_goto_position([target], [orientation], [True], max_limit=1000)
            self._phase = TaskPhase.RELEASE
            if was_holding and self.auto_regrasp:
                control.enable_regrasp()
        else:
            raise ValueError(f"unknown gripper_command: {cmd}")

        if not robot.reach(target, orientation):
            raise RuntimeError(f"robot did not reach target {target.tolist()} yaw={yaw}")

    def _run_stable_hold(self, target: np.ndarray, orientation: np.ndarray) -> None:
        from square_stable_hold import StableHold

        control = self._env.control
        slot = control.active
        out = self.output_dir
        if out is None:
            import tempfile
            out = Path(tempfile.mkdtemp(prefix="prepared-square-hold-"))
        out.mkdir(parents=True, exist_ok=True)
        hold = StableHold(self._env.robots[0], self._env.world, slot, out)
        hold.begin()
        try:
            hold.run(self.hold_steps)
        finally:
            self.last_hold_summary = hold.save()
        control.assert_exclusive()
        if not self._env.robots[0].reach(target, orientation):
            raise RuntimeError("Stable hold ended away from the commanded pose")

    # -----------------------------------------------------------------
    # Reset
    # -----------------------------------------------------------------
    def reset(self, seed: Optional[int] = None, difficulty: Optional[str] = None,
              apply_difficulty: bool = True):
        if not self._started:
            raise RuntimeError("call start() before reset()")
        import omni.timeline
        control = self._env.control

        # 1. Force all attachments into a clean released state, then reset the
        #    world (cloth, robot, rigid blocks) in one step.
        control.prepare_episode_reset()
        self._env.reset()
        if omni.timeline.get_timeline_interface().is_stopped():
            raise RuntimeError("Timeline stopped after reset")
        cv = self._env.garment[0].garment_mesh._cloth_prim_view
        cv.initialize()
        if cv._physics_view is None or int(cv.count) != 1:
            raise RuntimeError("Expected one initialized cloth physics view after reset")

        # 2. Re-validate precreated slots/blocks; no scene topology rebuild.
        control.after_scene_reset()
        if hasattr(control, "verify_proxy_ground"):
            control.proxy_ground_after_reset = control.verify_proxy_ground()
        control.robot_reset()

        # 3. The bounded step counter is per episode.
        self._step_count["n"] = 0
        for _ in range(self.settle_steps):
            self._env.step()

        # 4. Optional difficulty protocol (step 6/7); state-isolation tests use
        #    apply_difficulty=False so the world-axis candidate stays valid.
        if apply_difficulty:
            from envs.difficulty import DifficultyLevel, load_configs, apply as apply_difficulty_fn
            rng = np.random.default_rng(0 if seed is None else int(seed))
            level = DifficultyLevel.parse(difficulty)
            apply_difficulty_fn(self, load_configs()[level], rng)

        self._phase = TaskPhase.APPROACH
        self._gripper_state = GripperState.OPEN
        self._holding = False
        self.reset_count += 1
        return self.get_observation()
