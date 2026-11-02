"""Frozen action schema.

A policy emits a high-level Cartesian waypoint action. It does NOT emit
joint angles, velocities, or torques. Backends convert waypoint actions
to joint trajectories via IK and low-level control.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import List

import numpy as np


# ---------------------------------------------------------------------------
# Enums (order is frozen; only append at the end)
# ---------------------------------------------------------------------------

class GripperCommand(IntEnum):
    OPEN = 0
    CLOSE = 1
    HOLD = 2


NUM_GRIPPER_COMMANDS = len(GripperCommand)

TARGET_POSE_DIM = 4  # x, y, z, yaw
ACTION_VECTOR_DIM = TARGET_POSE_DIM + 1  # + gripper command


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

@dataclass
class CartesianAction:
    """One high-level action.

    target_pose: [x, y, z, yaw] in world/table frame.
    gripper_command: GripperCommand value.
    """
    target_pose: np.ndarray    # (4,) float32
    gripper_command: int       # GripperCommand value

    def to_vector(self) -> np.ndarray:
        """Flatten to float32 vector of length ACTION_VECTOR_DIM."""
        return np.concatenate(
            [
                np.asarray(self.target_pose, dtype=np.float32).reshape(-1),
                np.array([float(self.gripper_command)], dtype=np.float32),
            ],
            axis=0,
        )

    def validate(self) -> None:
        if self.target_pose.shape != (TARGET_POSE_DIM,):
            raise ValueError(
                f"target_pose must be ({TARGET_POSE_DIM},), got {self.target_pose.shape}"
            )
        if int(self.gripper_command) not in [int(c) for c in GripperCommand]:
            raise ValueError(f"unknown gripper_command: {self.gripper_command}")


def action_vector_to_parts(vec: np.ndarray):
    """Split an ACTION_VECTOR_DIM vector into (target_pose, gripper_command)."""
    vec = np.asarray(vec, dtype=np.float32).reshape(-1)
    if vec.shape[0] != ACTION_VECTOR_DIM:
        raise ValueError(
            f"expected {ACTION_VECTOR_DIM}-dim vector, got {vec.shape[0]}"
        )
    return vec[:TARGET_POSE_DIM], int(round(float(vec[TARGET_POSE_DIM])))


@dataclass
class ActionChunk:
    """A sequence of high-level actions of length H."""
    actions: List[CartesianAction]

    @property
    def horizon(self) -> int:
        return len(self.actions)

    def to_matrix(self) -> np.ndarray:
        """(H, ACTION_VECTOR_DIM) float32."""
        return np.stack([a.to_vector() for a in self.actions], axis=0)

    @staticmethod
    def from_matrix(mat: np.ndarray) -> "ActionChunk":
        mat = np.asarray(mat, dtype=np.float32)
        if mat.ndim != 2 or mat.shape[1] != ACTION_VECTOR_DIM:
            raise ValueError(
                f"expected (H, {ACTION_VECTOR_DIM}) matrix, got {mat.shape}"
            )
        actions = []
        for row in mat:
            pose, cmd = action_vector_to_parts(row)
            actions.append(CartesianAction(target_pose=pose, gripper_command=cmd))
        return ActionChunk(actions=actions)
