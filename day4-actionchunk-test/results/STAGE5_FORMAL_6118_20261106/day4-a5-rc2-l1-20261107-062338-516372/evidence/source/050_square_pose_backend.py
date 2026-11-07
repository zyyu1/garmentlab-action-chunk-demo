"""Development Backend candidate: explicit world yaw, fixed downward local Z.
Not installed as the production Backend and not yet dynamically validated.
"""
import numpy as np
from backends.garmentlab_backend import GarmentLabBackend
from schemas.action import CartesianAction,GripperCommand
from schemas.observation import GripperState,TaskPhase
from square_pose_contract import orientation_euler,GRASP_OFFSET_LOCAL

class SquarePoseBackend(GarmentLabBackend):
    def start(self):
        super().start()
        control=self._env.control
        if not hasattr(control,'slots'):raise RuntimeError('Requires prepared square control')
        for slot in control.slots:slot.local_offset=GRASP_OFFSET_LOCAL.copy()

    def _execute_single(self, a: CartesianAction) -> None:
        target = np.asarray(a.target_pose[:3], dtype=np.float64)
        orientation = orientation_euler(float(a.target_pose[3]))
        cmd = int(a.gripper_command)

        control = self._env.control
        robot = self._env.robots[0]

        if cmd == int(GripperCommand.CLOSE):
            control.grasp([target], [orientation], [True])
            self._gripper_state = GripperState.CLOSED_HOLDING
            self._holding = True
            self._phase = TaskPhase.GRASP
        elif cmd == int(GripperCommand.HOLD):
            if self._holding:
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
        else:
            raise ValueError(f"unknown gripper_command: {cmd}")

        if not robot.reach(target, orientation):
            raise RuntimeError(f"robot did not reach target {target.tolist()}")

