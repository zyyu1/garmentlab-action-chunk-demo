"""Frozen observation schema.

Shared by:
  - GarmentLabBackend  (simulation)
  - RealRobotBackend   (future)

Hard constraints from the demo plan:
  - No Isaac Sim joint commands.
  - No USD object paths.
  - No particle indices.
  - Fixed input dimension for policies.

The policy only ever sees Observation. It never touches simulator state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Enums (order is frozen; only append at the end)
# ---------------------------------------------------------------------------

class TaskPhase(IntEnum):
    APPROACH = 0
    GRASP = 1
    LIFT = 2
    TRANSFER = 3
    PLACE = 4
    RELEASE = 5
    RECOVERY = 6
    DONE = 7


NUM_PHASES = len(TaskPhase)


class GripperState(IntEnum):
    OPEN = 0
    CLOSED_EMPTY = 1
    CLOSED_HOLDING = 2
    UNKNOWN = 3


NUM_GRIPPER_STATES = len(GripperState)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_NUM_KEYPOINTS = 8
EE_POSE_DIM = 7  # x, y, z, qw, qx, qy, qz


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

@dataclass
class Observation:
    """One observation.

    All geometry is in world/table frame unless stated otherwise.
    Unused keypoints must be zero-padded; `valid_keypoint_count` tells
    the consumer how many are real. Policies may ignore this field and
    rely on zero-padding, but backends must set it correctly.
    """

    timestamp: float

    # Garment geometry.
    garment_keypoints: np.ndarray    # (N, 3) float32
    valid_keypoint_count: int        # 0 <= count <= N
    garment_center: np.ndarray       # (3,) float32

    # Robot state.
    end_effector_pose: np.ndarray    # (7,) float32
    gripper_state: int               # GripperState value

    # Task phase.
    task_phase: int                  # TaskPhase value

    # Optional visual input. Both None or both present.
    rgb: Optional[np.ndarray] = None      # (H, W, 3) uint8
    depth: Optional[np.ndarray] = None    # (H, W) float32 meters

    # -----------------------------------------------------------------
    def gripper_one_hot(self) -> np.ndarray:
        v = np.zeros(NUM_GRIPPER_STATES, dtype=np.float32)
        v[int(self.gripper_state)] = 1.0
        return v

    def phase_one_hot(self) -> np.ndarray:
        v = np.zeros(NUM_PHASES, dtype=np.float32)
        v[int(self.task_phase)] = 1.0
        return v

    def to_policy_vector(self) -> np.ndarray:
        """Flatten to a float32 vector.

        Frozen order:
            garment_keypoints (N * 3)
            garment_center (3)
            end_effector_pose (7)
            gripper_one_hot (NUM_GRIPPER_STATES)
            phase_one_hot (NUM_PHASES)

        Timestamp is NOT part of the policy vector.
        """
        parts = [
            np.asarray(self.garment_keypoints, dtype=np.float32).reshape(-1),
            np.asarray(self.garment_center, dtype=np.float32).reshape(-1),
            np.asarray(self.end_effector_pose, dtype=np.float32).reshape(-1),
            self.gripper_one_hot(),
            self.phase_one_hot(),
        ]
        return np.concatenate(parts, axis=0)

    @staticmethod
    def policy_vector_dim(num_keypoints: int) -> int:
        return (
            num_keypoints * 3
            + 3
            + EE_POSE_DIM
            + NUM_GRIPPER_STATES
            + NUM_PHASES
        )

    def validate(self) -> None:
        if not isinstance(self.garment_keypoints, np.ndarray):
            raise ValueError("garment_keypoints must be np.ndarray")
        if self.garment_keypoints.ndim != 2 or self.garment_keypoints.shape[1] != 3:
            raise ValueError(
                f"garment_keypoints must be (N, 3), got {self.garment_keypoints.shape}"
            )
        n = self.garment_keypoints.shape[0]
        if not (0 <= self.valid_keypoint_count <= n):
            raise ValueError(
                f"valid_keypoint_count={self.valid_keypoint_count} out of [0, {n}]"
            )
        if self.garment_center.shape != (3,):
            raise ValueError(
                f"garment_center must be (3,), got {self.garment_center.shape}"
            )
        if self.end_effector_pose.shape != (EE_POSE_DIM,):
            raise ValueError(
                f"end_effector_pose must be ({EE_POSE_DIM},), got {self.end_effector_pose.shape}"
            )
        if int(self.gripper_state) not in [int(g) for g in GripperState]:
            raise ValueError(f"unknown gripper_state: {self.gripper_state}")
        if int(self.task_phase) not in [int(p) for p in TaskPhase]:
            raise ValueError(f"unknown task_phase: {self.task_phase}")
        if (self.rgb is None) != (self.depth is None):
            raise ValueError("rgb and depth must be both None or both present")
