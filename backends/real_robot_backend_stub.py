"""RealRobotBackendStub: interface placeholder for future real robot.

Does not connect to hardware. Raises NotImplementedError on every
method that would touch a device. Exists so that:

  - The shared observation/action schema is exercised by a second
    implementation, proving the schema is device-independent.
  - A future RealRobotBackend can subclass and fill in the methods.
  - tests/test_backend_interface.py can assert interface compliance.

Plan: see docs/sim2real_plan.md (to be written on Day 3 or later).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backends.base import RobotBackend
from schemas.action import ActionChunk
from schemas.observation import Observation


class RealRobotBackendStub(RobotBackend):
    """Interface-only real robot backend.

    Intentionally non-functional. Subclass to implement.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    def start(self) -> None:
        raise NotImplementedError(
            "RealRobotBackendStub.start(): connect to arm, gripper, camera."
        )

    def stop(self) -> None:
        raise NotImplementedError(
            "RealRobotBackendStub.stop(): release arm, gripper, camera."
        )

    def get_observation(self) -> Observation:
        raise NotImplementedError(
            "RealRobotBackendStub.get_observation(): "
            "top RGB-D -> keypoints + EE pose + gripper state."
        )

    def execute(self, action_chunk: ActionChunk) -> Dict[str, Any]:
        raise NotImplementedError(
            "RealRobotBackendStub.execute(): "
            "Cartesian waypoints -> IK -> trajectory -> controller."
        )

    def metadata(self) -> Dict[str, Any]:
        return {
            "backend": "RealRobotBackendStub",
            "implemented": False,
            "config_keys": sorted(self.config.keys()),
        }
