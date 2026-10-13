"""GarmentLabBackend: wraps GarmentLab FoldEnv as a RobotBackend.

Rules:
  - Policy never sees GarmentLab or Isaac Sim directly.
  - This file is the only place that imports Env.env.FoldEnv.
  - Lazy import: constructing the backend does NOT start Isaac Sim.
    Only start() triggers SimulationApp.
  - stop() closes SimulationApp.

Known simplifications (Day 3):
  - `yaw` in CartesianAction is not wired to GarmentLab orientation.
    We pass ori=[None] and use GarmentLab's default controller behavior.
  - End-effector pose: read from env.robots[0] if a compatible method
    exists, else zero-padded with a warning.
  - Garment keypoints: subsampled from garment vertices.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backends.base import RobotBackend
from schemas.action import ActionChunk, CartesianAction, GripperCommand
from schemas.observation import (
    Observation,
    TaskPhase,
    GripperState,
    DEFAULT_NUM_KEYPOINTS,
)


# ---------------------------------------------------------------------------
# Lazy GarmentLab import
# ---------------------------------------------------------------------------

_GARMENTLAB_ROOT = Path(
    "/root/autodl-tmp/garmentlab_workspace/GarmentLab"
)

_env_module_cache: Optional[Tuple[Any, Any]] = None


def _import_garmentlab():
    """Import GarmentLab FoldEnv exactly once.

    Returns (FoldEnv_class, simulation_app).
    """
    global _env_module_cache
    if _env_module_cache is not None:
        return _env_module_cache

    root = _GARMENTLAB_ROOT
    if not root.is_dir():
        raise RuntimeError(f"GarmentLab root not found: {root}")

    os.chdir(root)
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "Env"))

    from Env.env.FoldEnv import FoldEnv, simulation_app  # noqa: E402

    _env_module_cache = (FoldEnv, simulation_app)
    return _env_module_cache


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

DEFAULT_GARMENT_USD = (
    _GARMENTLAB_ROOT
    / "Assets/Garments/Tops/NoCollar_LSleeve_FrontClose"
    / "TNLC_Dress057/TNLC_Dress057_obj.usd"
)


class GarmentLabBackend(RobotBackend):
    """Wraps FoldEnv. One instance per process (Isaac Sim limitation)."""

    def __init__(
        self,
        garment_usd: Optional[str] = None,
        num_keypoints: int = DEFAULT_NUM_KEYPOINTS,
        settle_steps: int = 120,
        snapshot_steps: int = 10,
        max_action_steps: int = 15000,
    ) -> None:
        self.garment_usd = str(garment_usd or DEFAULT_GARMENT_USD)
        self.num_keypoints = int(num_keypoints)
        self.settle_steps = int(settle_steps)
        self.snapshot_steps = int(snapshot_steps)
        self.max_action_steps = int(max_action_steps)

        self._started = False
        self._env = None
        self._simulation_app = None

        # Internal task state.
        self._step_count = 0
        self._phase = TaskPhase.APPROACH
        self._gripper_state = GripperState.OPEN
        self._holding = False

    # -----------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------
    def start(self) -> None:
        if self._started:
            return

        FoldEnv, simulation_app = _import_garmentlab()
        self._simulation_app = simulation_app

        from Env.Config.GarmentConfig import GarmentConfig  # noqa: E402
        from Env.Config.FrankaConfig import FrankaConfig  # noqa: E402

        if not Path(self.garment_usd).is_file():
            raise FileNotFoundError(f"garment usd not found: {self.garment_usd}")

        config = GarmentConfig(
            usd_path=self.garment_usd,
            visual_material_usd=None,
            pos=np.array([0, -0.95, 0.3]),
            ori=np.array([0, 0, 0]),
            particle_contact_offset=0.01,
        )
        env = FoldEnv(
            garment_config=[config],
            franka_config=FrankaConfig(ori=[np.array([0, 0, -np.pi / 2])]),
        )
        env.reset()

        # Bound the total number of physics steps inside execute().
        original_step = env.world.step
        counter = {"n": 0}

        def bounded_step(*args, **kwargs):
            counter["n"] += 1
            if counter["n"] > self.max_action_steps:
                raise RuntimeError(
                    f"execute() exceeded max_action_steps={self.max_action_steps}"
                )
            return original_step(*args, **kwargs)

        env.world.step = bounded_step
        self._env = env
        self._step_count = counter
        self._started = True

    def stop(self) -> None:
        if self._simulation_app is not None:
            try:
                self._simulation_app.close()
            finally:
                self._simulation_app = None
        self._env = None
        self._started = False

    # -----------------------------------------------------------------
    # reset (simulation only)
    # -----------------------------------------------------------------
    def reset(
        self,
        seed: Optional[int] = None,
        difficulty: Optional[str] = None,
    ) -> Observation:
        if not self._started:
            raise RuntimeError("call start() before reset()")
        if seed is not None:
            np.random.seed(int(seed))
        # Difficulty protocol is implemented on Day 4.
        if difficulty is not None and difficulty != "flat":
            raise NotImplementedError(
                f"difficulty={difficulty!r} not implemented yet (Day 4)"
            )

        self._env.control.robot_reset()
        for _ in range(self.settle_steps):
            self._env.step()

        self._phase = TaskPhase.APPROACH
        self._gripper_state = GripperState.OPEN
        self._holding = False
        return self.get_observation()

    # -----------------------------------------------------------------
    # Core interface
    # -----------------------------------------------------------------
    def get_observation(self) -> Observation:
        if not self._started:
            raise RuntimeError("call start() before get_observation()")

        keypoints, center = self._read_garment_geometry()
        ee_pose = self._read_end_effector_pose()

        obs = Observation(
            timestamp=float(self._step_count["n"]),
            garment_keypoints=keypoints,
            valid_keypoint_count=int(getattr(self, "_last_valid_keypoints", keypoints.shape[0])),
            garment_center=center,
            end_effector_pose=ee_pose,
            gripper_state=int(self._gripper_state),
            task_phase=int(self._phase),
            rgb=None,
            depth=None,
        )
        obs.validate()
        return obs

    def execute(self, action_chunk: ActionChunk) -> Dict[str, Any]:
        if not self._started:
            raise RuntimeError("call start() before execute()")
        self._check_action_chunk(action_chunk)

        executed = 0
        for a in action_chunk.actions:
            self._execute_single(a)
            executed += 1

        return {
            "executed_steps": executed,
            "done": self._phase == TaskPhase.DONE,
            "info": {
                "step_count": self._step_count["n"],
                "phase": int(self._phase),
                "gripper_state": int(self._gripper_state),
                "holding": self._holding,
            },
        }

    def is_done(self) -> bool:
        return self._phase == TaskPhase.DONE

    # -----------------------------------------------------------------
    # Internal: action mapping
    # -----------------------------------------------------------------
    def _execute_single(self, a: CartesianAction) -> None:
        target = np.asarray(a.target_pose[:3], dtype=np.float64)
        cmd = int(a.gripper_command)

        control = self._env.control
        robot = self._env.robots[0]

        if cmd == int(GripperCommand.CLOSE):
            control.grasp([target], [None], [True])
            self._gripper_state = GripperState.CLOSED_HOLDING
            self._holding = True
            self._phase = TaskPhase.GRASP
        elif cmd == int(GripperCommand.HOLD):
            control.move([target], [None], [True])
            if self._holding:
                self._gripper_state = GripperState.CLOSED_HOLDING
            self._phase = TaskPhase.TRANSFER
        elif cmd == int(GripperCommand.OPEN):
            if self._holding:
                control.ungrasp([False])
                self._holding = False
            self._gripper_state = GripperState.OPEN
            control.robot_goto_position([target], [None], [True], max_limit=1000)
            self._phase = TaskPhase.RELEASE
        else:
            raise ValueError(f"unknown gripper_command: {cmd}")

        # Reach check when supported by the robot wrapper.
        if hasattr(robot, "reach"):
            try:
                if not robot.reach(target, None):
                    raise RuntimeError(
                        f"robot did not reach target {target.tolist()}"
                    )
            except RuntimeError:
                raise
            except Exception:
                pass  # reach() signature may differ; don't block

    # -----------------------------------------------------------------
    # Internal: geometry
    # -----------------------------------------------------------------
    def _read_garment_geometry(self) -> Tuple[np.ndarray, np.ndarray]:
        raw = np.asarray(
            self._env.garment[0].get_vertices_positions()
        ).reshape(-1, 3).astype(np.float32)
        if raw.shape[0] == 0:
            raise RuntimeError("empty garment vertices")

        center = raw.mean(axis=0).astype(np.float32)
        n = self.num_keypoints
        if raw.shape[0] <= n:
            kp = np.zeros((n, 3), dtype=np.float32)
            kp[: raw.shape[0]] = raw
            valid = raw.shape[0]
        else:
            idx = np.linspace(0, raw.shape[0] - 1, n).astype(np.int64)
            kp = raw[idx]
            valid = n

        kp = kp.copy()
        # Store valid count implicitly; Observation carries it separately.
        self._last_valid_keypoints = valid
        return kp, center

    def _read_end_effector_pose(self) -> np.ndarray:
        robot = self._env.robots[0]
        for attr in ("get_end_effector_pose", "get_ee_pose"):
            if hasattr(robot, attr):
                try:
                    pose = np.asarray(getattr(robot, attr)(), dtype=np.float32).reshape(-1)
                    out = np.zeros(7, dtype=np.float32)
                    out[: min(7, pose.shape[0])] = pose[:7]
                    if pose.shape[0] < 7:
                        out[3] = 1.0  # qw default
                    return out
                except Exception:
                    break
        # Fallback: zero-padded identity orientation.
        out = np.zeros(7, dtype=np.float32)
        out[3] = 1.0
        return out

    # -----------------------------------------------------------------
    # Metadata
    # -----------------------------------------------------------------
    def metadata(self) -> Dict[str, Any]:
        return {
            "backend": "GarmentLabBackend",
            "garment_usd": self.garment_usd,
            "num_keypoints": self.num_keypoints,
            "settle_steps": self.settle_steps,
            "max_action_steps": self.max_action_steps,
            "started": self._started,
        }
