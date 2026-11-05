"""RobotBackend: the only interface between policy and device.

Hard constraints from the demo plan:
  - Policy never calls Isaac Sim API directly.
  - Policy never emits joint angles, velocities, or torques.
  - Policy emits high-level Cartesian waypoint actions only.

Subclasses:
  - MockBackend              (no GPU, unit tests)
  - GarmentLabBackend        (Isaac Sim / GarmentLab)
  - RealRobotBackendStub     (future real robot, interface only)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import numpy as np

from schemas.action import ActionChunk
from schemas.observation import Observation


class RobotBackend(ABC):
    """Abstract device backend.

    Lifecycle:
        backend = SomeBackend(config)
        backend.start()
        try:
            obs = backend.get_observation()
            result = backend.execute(action_chunk)
        finally:
            backend.stop()

    reset() is a simulation-only concept. Real-robot reset is manual at
    the start of the project; a future RealRobotBackend may implement
    reset() as a no-op or raise NotImplementedError.
    """

    # -----------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------
    @abstractmethod
    def start(self) -> None:
        """Bring up the device. Must be idempotent-safe."""

    @abstractmethod
    def stop(self) -> None:
        """Shut down the device and release resources."""

    # -----------------------------------------------------------------
    # Core interface
    # -----------------------------------------------------------------
    @abstractmethod
    def get_observation(self) -> Observation:
        """Return one Observation (see schemas.observation)."""

    @abstractmethod
    def execute(self, action_chunk: ActionChunk) -> Dict[str, Any]:
        """Execute an ActionChunk of length >= 1.

        Returns a dict with at least:
            executed_steps : int
            done : bool
            info : dict

        Backends are responsible for converting Cartesian waypoints
        into joint trajectories via IK and low-level control. The
        policy is not allowed to know about IK, joint limits, or
        trajectory planning.
        """

    # -----------------------------------------------------------------
    # Optional simulation-only hooks (default: not implemented)
    # -----------------------------------------------------------------
    def reset(self, seed: Optional[int] = None, difficulty: Optional[str] = None) -> Observation:
        """Simulation-only. Real backends may raise NotImplementedError."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support reset()."
        )

    def is_done(self) -> bool:
        """Optional. Default: backend keeps running until stop()."""
        return False

    # -----------------------------------------------------------------
    # Metadata
    # -----------------------------------------------------------------
    def metadata(self) -> Dict[str, Any]:
        """Optional. Override to record device config, commit hash, etc."""
        return {"backend": type(self).__name__}

    # -----------------------------------------------------------------
    # Safety helpers
    # -----------------------------------------------------------------
    def _check_action_chunk(self, action_chunk: ActionChunk) -> None:
        if not isinstance(action_chunk, ActionChunk):
            raise TypeError(
                f"expected ActionChunk, got {type(action_chunk).__name__}"
            )
        if action_chunk.horizon < 1:
            raise ValueError("ActionChunk must have horizon >= 1")
        for a in action_chunk.actions:
            a.validate()
