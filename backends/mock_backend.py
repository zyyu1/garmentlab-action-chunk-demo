"""MockBackend: pure-Python backend for unit tests.

No Isaac Sim, no GPU. Simulates a trivial garment state that shrinks
slightly toward a target after each execute() call.

Used by:
  - tests/test_chunk_alignment.py
  - scripts/smoke_test.py
  - any CI without GPU
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from backends.base import RobotBackend
from schemas.action import ActionChunk
from schemas.observation import (
    Observation,
    TaskPhase,
    GripperState,
    DEFAULT_NUM_KEYPOINTS,
)


class MockBackend(RobotBackend):
    """Deterministic mock backend.

    State:
        step_count         : int
        phase              : TaskPhase
        gripper_state      : GripperState
        garment_center     : (3,) float32
        keypoints          : (N, 3) float32

    execute() advances step_count, moves garment_center slightly toward
    the last target_pose, and stops when step_count >= max_steps.
    """

    def __init__(
        self,
        num_keypoints: int = DEFAULT_NUM_KEYPOINTS,
        max_steps: int = 20,
        rng_seed: int = 0,
    ) -> None:
        self.num_keypoints = int(num_keypoints)
        self.max_steps = int(max_steps)
        self._rng = np.random.default_rng(rng_seed)
        self._started = False
        self.reset()

    # -----------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------
    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    # -----------------------------------------------------------------
    # Core interface
    # -----------------------------------------------------------------
    def get_observation(self) -> Observation:
        obs = Observation(
            timestamp=float(self.step_count),
            garment_keypoints=self.keypoints.copy(),
            valid_keypoint_count=self.num_keypoints,
            garment_center=self.garment_center.copy(),
            end_effector_pose=self.ee_pose.copy(),
            gripper_state=int(self.gripper_state),
            task_phase=int(self.phase),
            rgb=None,
            depth=None,
        )
        obs.validate()
        return obs

    def execute(self, action_chunk: ActionChunk) -> Dict[str, Any]:
        self._check_action_chunk(action_chunk)
        executed = 0
        for a in action_chunk.actions:
            if self.is_done():
                break
            self._apply_single_action(a)
            executed += 1
        return {
            "executed_steps": executed,
            "done": self.is_done(),
            "info": {
                "step_count": self.step_count,
                "phase": int(self.phase),
                "gripper_state": int(self.gripper_state),
            },
        }

    # -----------------------------------------------------------------
    # Simulation-only hook
    # -----------------------------------------------------------------
    def reset(
        self,
        seed: Optional[int] = None,
        difficulty: Optional[str] = None,
    ) -> Observation:
        if seed is not None:
            self._rng = np.random.default_rng(int(seed))
        self.step_count = 0
        self.phase = TaskPhase.APPROACH
        self.gripper_state = GripperState.OPEN
        # Start slightly off-center so motion is observable.
        self.garment_center = np.array([0.1, 0.0, 0.0], dtype=np.float32)
        self.keypoints = np.zeros(
            (self.num_keypoints, 3), dtype=np.float32
        )
        # Lay keypoints out on a line for easy visual debugging.
        for i in range(self.num_keypoints):
            self.keypoints[i, 0] = 0.1 + 0.02 * i
            self.keypoints[i, 1] = 0.0
            self.keypoints[i, 2] = 0.0
        self.ee_pose = np.zeros(7, dtype=np.float32)
        self.ee_pose[3] = 1.0  # qw = 1
        self.last_target = self.garment_center.copy()
        return self.get_observation()

    def is_done(self) -> bool:
        return self.step_count >= self.max_steps

    # -----------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------
    def _apply_single_action(self, a) -> None:
        target_xyz = np.asarray(a.target_pose[:3], dtype=np.float32)
        # Move garment center 10% toward target each step.
        self.garment_center = (
            0.9 * self.garment_center + 0.1 * target_xyz
        ).astype(np.float32)
        # Shift keypoints by the same delta.
        delta = 0.1 * (target_xyz - self.garment_center)
        self.keypoints = (self.keypoints + delta).astype(np.float32)
        self.last_target = target_xyz.copy()

        # Update gripper state.
        from schemas.action import GripperCommand
        cmd = int(a.gripper_command)
        if cmd == int(GripperCommand.OPEN):
            self.gripper_state = GripperState.OPEN
        elif cmd == int(GripperCommand.CLOSE):
            self.gripper_state = GripperState.CLOSED_HOLDING

        # Advance phase on a fixed schedule.
        self.step_count += 1
        if self.step_count < 4:
            self.phase = TaskPhase.APPROACH
        elif self.step_count < 8:
            self.phase = TaskPhase.GRASP
        elif self.step_count < 12:
            self.phase = TaskPhase.LIFT
        elif self.step_count < 16:
            self.phase = TaskPhase.TRANSFER
        elif self.step_count < 20:
            self.phase = TaskPhase.PLACE
        else:
            self.phase = TaskPhase.DONE

    def metadata(self) -> Dict[str, Any]:
        return {
            "backend": "MockBackend",
            "num_keypoints": self.num_keypoints,
            "max_steps": self.max_steps,
        }
