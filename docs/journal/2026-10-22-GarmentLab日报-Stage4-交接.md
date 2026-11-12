# GarmentLab 交接日报｜2026-10-22｜Stage 4 调试暂停

## 1. 当前结论

今天完成新实例连接检查，继续排查 ClothPrimView 世界坐标读写。尚未通过 CLOTH_VIEW_PROBE_OK，也未运行新的折叠动作或难度评估。

当前阻塞：Torch/CUDA 后端下，ParallelGripper.initialize 将 CUDA 关节位置直接交给 np.array，导致异常。已给出项目内夹爪读取回调适配补丁，但用户尚未反馈是否执行，必须先检查实际文件，不能视为已安装或验证通过。

用户要求在此暂停、关机；下次无空闲 GPU 时可能克隆到新实例。本日报写入时，助手没有执行或确认 AutoDL 关机，也没有直接登录服务器。

## 2. 本次实例和连接

- SSH：ssh -p 17195 <server>
- 建议本地 SSH 别名：autodl-garmentlab-new（是否已采用需核对本机 config）。
- 容器：autodl-container-c62840940c-f610839c
- GPU：RTX 3090，24576 MiB。
- 驱动：580.105.08；nvidia-smi 的 CUDA 13.0 是驱动支持信息。
- 系统盘：30G，使用 4.1G，可用 26G。
- 数据盘 <remote-root>：50G，使用 34G，可用约 17G。
- Python 3.10.8，Isaac Sim 4.0.0.0，NumPy 1.26.4。

旧实例连接仅供辨认，不要误操作：
- 16629 / <server>：上一台 vGPU 克隆实例。
- 18117 / <server>：更早的 4090 实例。

## 3. 目录和代码基线

远程：
- GarmentLab：<remote-root>/garmentlab_workspace/GarmentLab
- 正式项目：<remote-root>/garmentlab-action-chunk-demo
- Python：<remote-root>/envs/isaac40/bin/python
- 验证脚本：<remote-root>/day4-cloth-view-probe.py

新实例首次检查时正式项目工作区干净：
- HEAD main：233771e — Day4 WIP: backend world-frame reading + difficulty protocol; ClothPrimView init bug to fix
- origin/main：2307770
- 更早提交：de104ba

今天改动位于另一个 GarmentLab 仓库，不能只备份正式项目。未进行新提交或推送；下次应分别检查两个仓库的 git status 和 git diff。

## 4. 今天的排查结果

### 4.1 原始配置

BaseEnv 中 self.world=World()，后续 enable_gpu_dynamics(True)。场景能启动，但验证脚本打印：

```text
TIMELINE_STOPPED False
GPU_PIPELINE False
RuntimeError: GPU pipeline 尚未启用；先调整 World 初始化，再验证 ClothPrimView
```

这是验证脚本主动拦截，尚未执行 cv.initialize()。不能据此断言 ClothPrimView 已经初始化失败。

### 4.2 已从安装源码确认的限制

- PhysicsContext 在 device 包含 cuda 时启用 GPU 管线；默认配置分支设置 /physics/suppressReadback=True。
- NumPy frontend 明确不支持 GPU pipelines。
- ArticulationMotionPolicy.get_next_articulation_action 已经将关节位置、速度从 Torch 转为 CPU NumPy，无需重复修改。
- RMPFlowController 初始化把机器人 get_world_pose() 直接传入 Lula，缺少 CUDA 转换。
- ParallelGripper 初始化、关节读取和增量开合共用 get_joint_positions_func。

### 4.3 尝试和当前状态

1. World(backend="torch", device="cuda:0")：在 RMPFlow 基座位姿传入 SciPy 时失败。
2. World(backend="numpy", device="cuda:0")：在 world.reset 创建物理视图时失败，错误为 The Numpy frontend cannot be used with GPU pipelines。此方案已否定，不要再次尝试。
3. 恢复 Torch/CUDA，并修改 MyFranka.py：通过原 RMPFlow 初始化错误，进入 world.reset；最新失败转移到夹爪初始化。

最新异常：
```text
Franka.initialize
  -> ParallelGripper.initialize，约第 116 行
  -> self._default_state = np.array(...)
TypeError: can't convert cuda:0 device type tensor to numpy.
```

贴图缺失、GLFW、关闭时 USD 引用计数警告不是这次 Python 异常的直接位置；没有据此宣称全部警告无害。

## 5. 已下发并由后续运行支持的项目修改

### BaseEnv.py

路径：<remote-root>/garmentlab_workspace/GarmentLab/Env/env/BaseEnv.py

当前预期：
```python
self.world=World(backend="torch", device="cuda:0")
```

### MyFranka.py

路径：<remote-root>/garmentlab_workspace/GarmentLab/Env/Robot/Franka/MyFranka.py

已下发的修改：
- 新增 _cpu_numpy(value)：None 保持 None，Torch 经 detach().cpu().numpy().copy() 转换，其余 np.asarray(...).copy()。
- 新增 CpuPoseFranka(Franka)，重写 get_world_pose，将返回的位置和四元数转成 CPU NumPy。
- MyFranka 创建 CpuPoseFranka 实例。
- 三处末端位姿读取后转换为 CPU NumPy。
- 三处 RMPFlow.forward 的目标位置、方向参数转换为 CPU NumPy。
- pick_and_place 的 current_joint_positions 转成 CPU NumPy。

这些修改只验证到夹爪初始化之前，尚未验证完整机械臂运动、抓取或难度 reset。

## 6. 待确认执行的最后一个补丁

在 CpuPoseFranka 类里增加 __init__，仅包装该夹爪实例的 initialize；传入的关节读取回调先转换 CPU NumPy，写入和动作回调保持原样。

```python
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
        def get_joint_positions_cpu(*args, **kwargs):
            return _cpu_numpy(get_joint_positions_func(*args, **kwargs))

        return original_initialize(
            articulation_apply_action_func=articulation_apply_action_func,
            get_joint_positions_func=get_joint_positions_cpu,
            set_joint_positions_func=set_joint_positions_func,
            dof_names=dof_names,
            physics_sim_view=physics_sim_view,
        )

    self._gripper.initialize = initialize_gripper_cpu
```

上段应作为类方法缩进写入，不是独立模块函数。下一位接手者应先检查：

```bash
grep -n -A 55 'class CpuPoseFranka' <remote-root>/garmentlab_workspace/GarmentLab/Env/Robot/Franka/MyFranka.py
```

若已有 initialize_gripper_cpu，不要重复添加；若没有，先备份，再应用补丁。不要修改 Isaac Sim 的 site-packages。

## 7. 验证脚本和日志

脚本流程：backend.start → 检查 timeline 和 GPU_PIPELINE → cv.initialize() → 读取布料世界位置 → 不推进仿真地平移 1 mm → 回读比较 → 恢复 → 输出末端位姿。

成功要求包括：
- GPU_PIPELINE True。
- cloth count 为 1；位置 shape 为 (1, N, 3)，N > 0，数值有限。
- WRITE_READ_MAX_ERROR < 1e-5，恢复后坐标误差也小于 1e-5。
- CLOTH_VIEW_PROBE_OK。

退出码 0 单独不足以证明通过。即使通过，这仍只是静态读写测试，不能证明动态仿真、抓取或折叠质量正确。

今天的远程日志：
- <remote-root>/day4-cloth-view-probe-new-instance.log
- <remote-root>/day4-cloth-view-probe-gpu.log
- <remote-root>/day4-cloth-view-probe-numpy-cuda.log
- <remote-root>/day4-cloth-view-probe-cuda-compat.log
- <remote-root>/day4-cloth-view-probe-gripper-compat.log：仅建议了此路径，是否存在未知。

补丁脚本生成的备份位于被改文件旁，后缀可能包括：
- .before-gpu-pipeline-时间戳
- .before-numpy-cuda-时间戳
- .before-cuda-compat-时间戳
- .before-gripper-compat-时间戳（执行状态未知）

## 8. 关机前保全

在远程终端检查是否仍有本次验证进程：
```bash
pgrep -af '[d]ay4-cloth-view-probe.py'
```
若仍在运行，回原终端 Ctrl+C，等进程结束；不要直接杀全部 Python 进程。

建议保存当前两个仓库的差异：
```bash
git -C <remote-root>/garmentlab_workspace/GarmentLab diff > <remote-root>/day4-garmentlab-20261022.patch
git -C <remote-root>/garmentlab-action-chunk-demo diff > <remote-root>/day4-backend-20261022.patch
```
注意 git diff 不包含未跟踪文件，也不包含已提交但未推送的 233771e；完整备份还应保留两个仓库目录及其 .git、验证脚本、日志。将重要文件下载到本机后，在 AutoDL 控制台选择关机，不要释放或删除实例。

## 9. 下次无空闲 GPU 时的克隆与恢复

1. 保留现有实例作为源，使用平台克隆/迁移功能，并核对是否同时复制系统盘和数据盘。不要假定仅保存镜像就包含 <remote-root>。
2. 当前数据盘使用约 34G，目标容量需容纳实际数据，并满足平台对源盘容量的要求；不能只依据显存大小判断。
3. 之前曾在 RTX4090/560.35.03、vGPU32G/580.105.08 运行成功。本次 RTX3090/580.105.08 已能创建场景，尚未通过新的布料验证。驱动版本相同不等于完整兼容保证。
4. 取得新 SSH 命令；在本机 C:\Users\yexun\.ssh\config 新增别名，保留旧入口。不要沿用本日报端口猜测新实例。
5. 连接后执行检查：

```bash
hostname
nvidia-smi
df -h / <remote-root>
<remote-root>/envs/isaac40/bin/python -c 'import sys; from importlib.metadata import version; print(sys.version); print(version("isaacsim")); print(version("numpy"))'
git -C <remote-root>/garmentlab-action-chunk-demo status --short
git -C <remote-root>/garmentlab-action-chunk-demo log -3 --oneline
git -C <remote-root>/garmentlab_workspace/GarmentLab status --short
grep -n 'self.world=World' <remote-root>/garmentlab_workspace/GarmentLab/Env/env/BaseEnv.py
grep -n -A 55 'class CpuPoseFranka' <remote-root>/garmentlab_workspace/GarmentLab/Env/Robot/Franka/MyFranka.py
ls -lh <remote-root>/day4-cloth-view-probe.py
```

6. 确认文件和未提交补丁都已复制后，继续夹爪兼容验证。不要重新安装环境或重做已完成实验。

## 10. 恢复工作后的执行顺序

1. 核对当前实际代码，确定夹爪回调补丁是否已应用。
2. 应用缺失补丁，运行：

```bash
<remote-root>/envs/isaac40/bin/python -u <remote-root>/day4-cloth-view-probe.py --allow-root 2>&1 | tee <remote-root>/day4-cloth-view-probe-resume.log
echo "Python exit code: ${PIPESTATUS[0]}"
```

3. 若失败，保留完整 traceback，定位新的数据接口；不要再尝试 NumPy + GPU pipeline。
4. 读写测试通过后，将布料初始化正确接入 backend，并验证物理步进后的坐标读取。
5. backend 的世界坐标读取失败时不能静默退回局部坐标；Torch 数据输出给 NumPy 的位置统一显式转换。
6. 验证夹爪开合和单次机械臂运动，再验证抓取。
7. 处理 reset 独立性：当前 robot_reset 只打开夹爪；难度 reset 不能继承上一轮布料形态。检查附件清理、粒子位置/速度恢复、机械臂状态和步数计数。
8. 先测单个 flat seed，再扩展 flat/perturbed/crumpled × 5 seeds。不要把脚本跑完视为折叠质量通过。
9. 保存测试证据、更新日报，之后再整理提交。

## 11. 交接边界

- 本日报依据用户粘贴的远程源码、日志和命令输出；助手只在本机写日报，没有远程修改权限或已验证的 SSH 会话。
- 夹爪补丁执行状态、关机状态、是否下载备份均待用户确认。
- 今天没有新增通过的布料读写结果，没有新的折叠成功结论。
