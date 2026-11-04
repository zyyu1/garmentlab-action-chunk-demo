
from typing import Tuple
import numpy as np
from omni.isaac.core.utils.types import ArticulationAction
from omni.isaac.franka import Franka
from omni.isaac.core.utils.prims import is_prim_path_valid
from omni.isaac.core.utils.string import find_unique_string_name
from omni.isaac.core import World
from omni.isaac.core.utils.nucleus import get_assets_root_path
from omni.isaac.core.utils.stage import add_reference_to_stage, get_stage_units
from omni.isaac.franka.controllers.pick_place_controller import PickPlaceController
from omni.isaac.franka.controllers.rmpflow_controller import RMPFlowController
from omni.isaac.franka import KinematicsSolver
from omni.isaac.core.utils.types import ArticulationAction
from Env.Utils.transforms import euler_angles_to_quat
import torch
from Env.Utils.transforms import quat_diff_rad



def _cpu_numpy(value):
    """Convert controller inputs to CPU NumPy; preserve optional None."""
    if value is None:
        return None
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().numpy().copy()
    return np.asarray(value).copy()


class CpuPoseFranka(Franka):
    """Expose base poses as NumPy for the existing Lula controllers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        original_initialize = self._gripper.initialize

        def initialize_gripper_cpu(
            articulation_apply_action_func,
            get_joint_positions_func,
            set_joint_positions_func,
            dof_names,
            physics_sim_view=None,
        ):
            def get_joint_positions_cpu(joint_indices=None):
                positions = _cpu_numpy(get_joint_positions_func())
                if positions is None:
                    raise RuntimeError("Robot joint positions are unavailable")
                if joint_indices is None:
                    return positions
                indices = _cpu_numpy(joint_indices).astype(np.int64).reshape(-1)
                return positions[indices].copy()

            def set_joint_positions_backend(positions, joint_indices=None):
                reference = get_joint_positions_func()
                if not isinstance(reference, torch.Tensor):
                    raise TypeError("预期机器人关节状态为 Torch Tensor")
                positions = torch.as_tensor(
                    positions,
                    dtype=reference.dtype,
                    device=reference.device,
                )
                if joint_indices is not None:
                    joint_indices = torch.as_tensor(
                        joint_indices,
                        dtype=torch.long,
                        device=reference.device,
                    )
                return set_joint_positions_func(
                    positions=positions,
                    joint_indices=joint_indices,
                )

            def apply_gripper_action_backend(control_actions):
                # This adapter handles the position commands used by open/close.
                if (control_actions.joint_velocities is not None
                        or control_actions.joint_efforts is not None):
                    raise NotImplementedError(
                        "Gripper adapter currently supports position commands only"
                    )
                if control_actions.joint_positions is None:
                    return

                values = _cpu_numpy(
                    control_actions.joint_positions
                ).reshape(-1)
                if control_actions.joint_indices is None:
                    indices = np.arange(len(values), dtype=np.int64)
                else:
                    indices = _cpu_numpy(
                        control_actions.joint_indices
                    ).astype(np.int64).reshape(-1)
                if len(indices) != len(values):
                    raise ValueError("Gripper indices and positions differ in length")

                keep = [i for i, value in enumerate(values) if value is not None]
                if not keep:
                    return
                positions = np.asarray(
                    [values[i] for i in keep], dtype=np.float32
                )
                indices = indices[keep]
                if not np.isfinite(positions).all():
                    raise ValueError("Non-finite gripper position target")

                allowed = set(int(i) for i in self._gripper.joint_dof_indicies)
                if not set(indices.tolist()).issubset(allowed):
                    raise ValueError("Gripper command includes non-gripper joints")

                reference = get_joint_positions_func()
                if not isinstance(reference, torch.Tensor):
                    raise TypeError("Expected Torch joint state")
                action = ArticulationAction(
                    joint_positions=torch.as_tensor(
                        positions, dtype=reference.dtype, device=reference.device
                    ),
                    joint_indices=torch.as_tensor(
                        indices, dtype=torch.long, device=reference.device
                    ),
                )
                return articulation_apply_action_func(action)

            return original_initialize(
                articulation_apply_action_func=apply_gripper_action_backend,
                get_joint_positions_func=get_joint_positions_cpu,
                set_joint_positions_func=set_joint_positions_backend,
                dof_names=dof_names,
                physics_sim_view=physics_sim_view,
            )

        # Only adapt this gripper instance's joint-reading callback.
        self._gripper.initialize = initialize_gripper_cpu

    def get_world_pose(self, *args, **kwargs):
        position, orientation = super().get_world_pose(*args, **kwargs)
        return _cpu_numpy(position), _cpu_numpy(orientation)


class MyFranka:
    def __init__(self,world:World,pos=None,ori=None,prim_path:str=None,robot_name:str=None,):
        self.world=world
        if prim_path is None:
            self._franka_prim_path = find_unique_string_name(
                initial_name="/World/Franka", is_unique_fn=lambda x: not is_prim_path_valid(x)
            )
        else:
            self._franka_prim_path=prim_path

        if robot_name is None:
            self._franka_robot_name = find_unique_string_name(
                initial_name="my_franka", is_unique_fn=lambda x: not self.world.scene.object_exists(x)
            )
        else:
            self._franka_robot_name=robot_name

        self.init_position=pos
        self.init_ori=ori
        self.default_ee_ori=torch.from_numpy(np.array([0,np.pi,0]))+ori
        self.world.scene.add(CpuPoseFranka(prim_path=self._franka_prim_path,name=self._franka_robot_name,position=pos,orientation=euler_angles_to_quat(ori)))
        self._robot:Franka=self.world.scene.get_object(self._franka_robot_name)
        self._articulation_controller=self._robot.get_articulation_controller()
        self._controller=RMPFlowController(name="rmpflow_controller",robot_articulation=self._robot)
        self._kinematic_solover=KinematicsSolver(self._robot)
        self._pick_place_controller=PickPlaceController(name="pick_place_controller",robot_articulation=self._robot,gripper=self._robot.gripper)
        self._controller.reset()
        self._pick_place_controller.reset()
        
    def get_prim_path(self):
        return self._franka_prim_path
    def get_cur_ee_pos(self):
        """Read the live right_gripper pose from measured joint positions."""
        from scipy.spatial.transform import Rotation

        wrapper = self._kinematic_solover
        solver = wrapper.get_kinematics_solver()
        frame = wrapper.get_end_effector_frame()
        expected = self._controller.rmp_flow_config["end_effector_frame_name"]
        if frame != expected:
            raise RuntimeError(f"FK/RMP frame mismatch: {frame} != {expected}")

        positions = _cpu_numpy(self._robot.get_joint_positions())
        if positions is None:
            raise RuntimeError("Robot joint positions are unavailable")
        positions = positions.reshape(-1)
        dof_names = list(self._robot.dof_names)
        indices = [dof_names.index(name) for name in solver.get_joint_names()]
        joints = positions[indices]
        if not np.isfinite(joints).all():
            raise RuntimeError("Non-finite robot joint positions")

        base_pos, base_quat = self._robot.get_world_pose()
        solver.set_robot_base_pose(
            _cpu_numpy(base_pos), _cpu_numpy(base_quat)
        )
        pos, matrix = solver.compute_forward_kinematics(
            frame, joints, position_only=False
        )
        pos = _cpu_numpy(pos).reshape(3)
        matrix = _cpu_numpy(matrix).reshape(3, 3)
        if not np.isfinite(pos).all() or not np.isfinite(matrix).all():
            raise RuntimeError("Non-finite forward kinematics result")

        # SciPy returns xyzw; Isaac/GarmentLab uses wxyz.
        xyzw = Rotation.from_matrix(matrix).as_quat()
        quat = xyzw[[3, 0, 1, 2]]
        return pos, quat


    def pick_and_place(self,pick,place):
        self._pick_place_controller.reset()
        self._robot.gripper.open()
        while 1:
            self.world.step(render=True)
            actions=self._pick_place_controller.forward(
                picking_position=pick,
                placing_position=place,
                current_joint_positions=_cpu_numpy(self._robot.get_joint_positions()),
                end_effector_offset=np.array([0,0.005,0]),
            )
            if self._pick_place_controller.is_done():
                break
            self._articulation_controller.apply_action(actions)
    
    def open(self):
        for _ in range(10):
            self._robot.gripper.open()
            self.world.step(render=True)
    
    def close(self):
        for _ in range(10):
            self._robot.gripper.close()
            self.world.step(render=True)
        

    @staticmethod
    def interpolate(start_loc, end_loc, speed):
        start_loc = np.array(start_loc)
        end_loc = np.array(end_loc)
        dist = np.linalg.norm(end_loc - start_loc)
        chunks = dist // speed
        if chunks==0:
            chunks=1
        return start_loc + np.outer(np.arange(chunks+1,dtype=float), (end_loc - start_loc) / chunks)
    
    def position_reached(self, target, thres=0.03):
        if target is None:
            return True
        position, _ = self.get_cur_ee_pos()
        return bool(np.linalg.norm(position - _cpu_numpy(target)) < thres)
    def rotation_reached(self, target):
        if target is None:
            return True
        _, actual = self.get_cur_ee_pos()
        target = _cpu_numpy(target).reshape(4)
        target_norm = float(np.linalg.norm(target))
        if not np.isfinite(target).all() or target_norm < 1e-8:
            raise ValueError("Invalid target quaternion")
        actual = actual / np.linalg.norm(actual)
        target = target / target_norm
        angle = 2.0 * np.arccos(np.clip(abs(np.dot(actual, target)), 0.0, 1.0))
        return bool(angle < 0.1)
        
    def move(self,end_loc,env_ori=None):
        start_loc=self.get_cur_ee_pos()[0]
        # if env_ori is None:
        #     env_ori=self.default_ee_ori
        if env_ori is not None:
            end_effector_orientation = euler_angles_to_quat(env_ori)
        else:
            end_effector_orientation = None
        target_joint_positions = self._controller.forward(
            target_end_effector_position=_cpu_numpy(end_loc), target_end_effector_orientation=_cpu_numpy(end_effector_orientation)
        )
        self._articulation_controller.apply_action(target_joint_positions)
    
    def reach(self,end_loc,env_ori=None):
        # if env_ori is not None:
        # #     env_ori=self.default_ee_ori
        #     end_effector_orientation = euler_angles_to_quat(env_ori)
        #     if self.position_reached(end_loc) and self.rotation_reached(end_effector_orientation):
        #         return True
        # else:
        if env_ori is None:
            if self.position_reached(end_loc):
                return True
        else:
            if self.position_reached(end_loc) and self.rotation_reached(euler_angles_to_quat(env_ori)):
                return True

        
    
        
    def movep(self,end_loc):
        self.world.step(render=True)
        start_loc=self.get_cur_ee_pos()[0]
        cur_step=0
        for i in range(200):
            self.world.step(render=True)
            end_effector_orientation = euler_angles_to_quat(self.default_ee_ori)
            target_joint_positions = self._controller.forward(
                target_end_effector_position=_cpu_numpy(end_loc), target_end_effector_orientation=_cpu_numpy(end_effector_orientation)
            )
            self._articulation_controller.apply_action(target_joint_positions)
            cur_step+=1
            if self.position_reached(end_loc):
                break
    
    def movel(self,end_loc:Tuple[np.ndarray,torch.Tensor],env_ori:Tuple[np.ndarray,torch.Tensor]=None):
        self.world.step(render=True)
        start_loc=self.get_cur_ee_pos()[0]
        cur_step=0
        while 1:
            self.world.step(render=True)
            if env_ori is None:
                env_ori=self.default_ee_ori
            end_effector_orientation = euler_angles_to_quat(env_ori)
            target_joint_positions = self._controller.forward(
                target_end_effector_position=_cpu_numpy(end_loc), target_end_effector_orientation=_cpu_numpy(end_effector_orientation)
            )
            self._articulation_controller.apply_action(target_joint_positions)
            cur_step+=1
            if self.position_reached(end_loc) and self.rotation_reached(end_effector_orientation):
                break
            if cur_step>300:
                print("Failed to reach target")
                break
            
            

            



