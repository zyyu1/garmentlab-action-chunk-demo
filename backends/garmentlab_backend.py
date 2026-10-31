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
  - End-effector pose: strict read from env.robots[0]; invalid data raises.
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
        prepared_grasp: bool = False,
    ) -> None:
        self.garment_usd = str(garment_usd or DEFAULT_GARMENT_USD)
        self.num_keypoints = int(num_keypoints)
        self.settle_steps = int(settle_steps)
        self.snapshot_steps = int(snapshot_steps)
        self.max_action_steps = int(max_action_steps)
        self.prepared_grasp = bool(prepared_grasp)

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
        if self.prepared_grasp:
            from backends.prepared_grasp_control import PreparedGraspControl
            env.control = PreparedGraspControl(env)
        env.reset()

        # Initialize the cloth view after the world has created physics.
        import carb
        import omni.timeline
        if omni.timeline.get_timeline_interface().is_stopped():
            raise RuntimeError("Timeline stopped after reset")
        if not carb.settings.get_settings().get_as_bool("/physics/suppressReadback"):
            raise RuntimeError("Cloth backend requires GPU pipeline")
        cv = env.garment[0].garment_mesh._cloth_prim_view
        cv.initialize()
        if cv._physics_view is None or int(cv.count) != 1:
            raise RuntimeError("Expected one initialized cloth physics view")

        if self.prepared_grasp:
            env.control.initialize()

        # Existing counter still limits all steps since start, not each execute.
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

        # 1. Robot home, then settle.
        self._env.control.robot_reset()
        for _ in range(self.settle_steps):
            self._env.step()

        # 2. Apply difficulty protocol.
        from envs.difficulty import (
            DifficultyLevel,
            load_configs,
            apply as apply_difficulty,
        )
        rng = np.random.default_rng(0 if seed is None else int(seed))
        lvl = DifficultyLevel.parse(difficulty)
        cfg = load_configs()[lvl]
        apply_difficulty(self, cfg, rng)

        # 3. Reset internal task state.
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
            if self._holding:
                control.move([target], [None], [True])
            else:
                control.robot_goto_position([target], [None], [True], max_limit=1000)
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

        if not robot.reach(target, None):
            raise RuntimeError(f"robot did not reach target {target.tolist()}")

    # -----------------------------------------------------------------
    # Internal: geometry
    # -----------------------------------------------------------------

    @staticmethod
    def _to_numpy(value) -> np.ndarray:
        if hasattr(value, "detach"):
            value = value.detach().cpu().numpy()
        return np.asarray(value, dtype=np.float32).copy()

    def _checked_cloth_view(self):
        import omni.timeline
        if self._env is None:
            raise RuntimeError("Backend environment is unavailable")
        if omni.timeline.get_timeline_interface().is_stopped():
            raise RuntimeError("Cannot read live cloth while timeline is stopped")
        cv = self._env.garment[0].garment_mesh._cloth_prim_view
        if cv._physics_view is None or int(cv.count) != 1:
            raise RuntimeError("Cloth physics view is unavailable; initialize after reset")
        return cv

    def _read_garment_geometry(self) -> Tuple[np.ndarray, np.ndarray]:
        raw = self._garment_world_positions()

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
        self._last_valid_keypoints = valid
        return kp, center

    def _read_end_effector_pose(self) -> np.ndarray:
        pos, quat = self._env.robots[0].get_cur_ee_pos()
        pos = self._to_numpy(pos).reshape(-1)
        quat = self._to_numpy(quat).reshape(-1)
        if pos.shape != (3,) or quat.shape != (4,):
            raise RuntimeError("Invalid end-effector pose shape")
        if not np.isfinite(pos).all() or not np.isfinite(quat).all():
            raise RuntimeError("Non-finite end-effector pose")
        norm = float(np.linalg.norm(quat))
        if norm < 1e-8:
            raise RuntimeError("Invalid zero quaternion")
        return np.concatenate((pos, quat / norm)).astype(np.float32)

    # -----------------------------------------------------------------
    # Internal: helpers for difficulty protocol (Day 4)
    # Called from envs.difficulty.apply(). Not part of the policy API.
    # -----------------------------------------------------------------
    def _garment_world_positions(self) -> np.ndarray:
        cv = self._checked_cloth_view()
        raw = self._to_numpy(cv.get_world_positions(clone=True))
        if raw.ndim != 3 or raw.shape[0] != 1 or raw.shape[2] != 3:
            raise RuntimeError(f"Invalid cloth position shape: {raw.shape}")
        if raw.shape[1] == 0 or not np.isfinite(raw).all():
            raise RuntimeError("Empty or non-finite cloth positions")
        return raw[0].copy()

    def _set_garment_world_positions(self, positions: np.ndarray) -> None:
        import torch
        cv = self._checked_cloth_view()
        reference = cv.get_world_positions(clone=True)
        raw = self._to_numpy(positions)
        expected = (reference.shape[1], 3)
        if raw.shape != expected or not np.isfinite(raw).all():
            raise ValueError(f"Expected finite cloth positions with shape {expected}")
        if not isinstance(reference, torch.Tensor):
            raise RuntimeError("Expected Torch cloth positions")
        value = torch.as_tensor(
            raw, dtype=reference.dtype, device=reference.device
        ).unsqueeze(0)
        cv.set_world_positions(value)

    def _clear_garment_velocities(self) -> None:
        import torch
        cv = self._checked_cloth_view()
        reference = cv.get_world_positions(clone=True)
        if not isinstance(reference, torch.Tensor):
            raise RuntimeError("Expected Torch cloth positions")
        cv.set_velocities(torch.zeros_like(reference))

    def _settle(self, steps: int) -> None:
        for _ in range(int(steps)):
            self._env.step()

    def _apply_flat_perturbation(self, rng, config) -> None:
        positions = self._garment_world_positions()
        if positions.shape[0] == 0:
            return
        center = positions.mean(axis=0)
        tx_lo, tx_hi = config.translate_xy_range
        dx = float(rng.uniform(tx_lo, tx_hi))
        dy = float(rng.uniform(tx_lo, tx_hi))
        y_lo, y_hi = config.yaw_range
        yaw = float(rng.uniform(y_lo, y_hi))
        c, s = float(np.cos(yaw)), float(np.sin(yaw))
        R = np.array(
            [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]],
            dtype=np.float32,
        )
        rel = positions - center
        moved = rel @ R.T + center + np.array(
            [dx, dy, 0.0], dtype=np.float32
        )
        self._set_garment_world_positions(moved.astype(np.float32))
        self._clear_garment_velocities()
        print(
            f"[difficulty] flat dx={dx:.4f} dy={dy:.4f} yaw={yaw:.4f} "
            f"center={center.tolist()} extent="
            f"{(positions.max(0) - positions.min(0)).tolist()}",
            flush=True,
        )

    def _lift_drop_once(self, rng, config) -> None:
        positions = self._garment_world_positions()
        if positions.shape[0] == 0:
            return
        center = positions.mean(axis=0)
        extent = positions.max(0) - positions.min(0)
        jitter = float(config.drop_xy_jitter)
        if jitter <= 0.0:
            jitter = 0.03
        pick = center.copy()
        pick[0] += float(rng.uniform(-jitter, jitter))
        pick[1] += float(rng.uniform(-jitter, jitter))
        pick[2] = float(positions[:, 2].max()) + 0.01
        lift_h = float(rng.uniform(*config.lift_height_range))
        lift = pick.copy()
        lift[2] += lift_h
        print(
            f"[difficulty] lift_drop pick={pick.tolist()} "
            f"lift={lift.tolist()} center={center.tolist()} "
            f"extent={extent.tolist()}",
            flush=True,
        )
        control = self._env.control
        control.robot_goto_position([pick], [None], [True], max_limit=1000)
        control.grasp([pick], [None], [True])
        control.move([lift], [None], [True])
        self._settle(int(config.lift_hold_steps))
        control.ungrasp([False])
        self._settle(int(config.settle_steps))

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
