# GarmentLab 交接日报｜2026-10-23｜Day4：机器人抓取、抬升、释放首次通过

## 1. 交接结论（先读这里）

今天已打通 Torch/CUDA 下的衣物物理世界坐标读写、夹爪开合、实时末端位姿、附着方块运动，以及机器人驱动的一次抓取—抬升—释放。

最终成功标记：`PREPARED_ROBOT_GRASP_LIFT_RELEASE_OK`。

通过条件组合：

- 单机器人、单件衣物、预选左边缘区域、每进程一次抓取。
- `World(backend="torch", device="cuda:0")`。
- backend 显式开启 `prepared_grasp=True`。
- 方块和 attachment 在首次 reset 前预创建，attachment 位于独立 USD 路径。
- 分层下降到末端目标高度 0.02 m。
- `GARMENTLAB_ATTACHMENT_OVERLAP=0.005`。
- `GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0`。

用户已确认执行了最后的成功版本保存命令。实际保存目录名为 `/root/autodl-tmp/day4-passed-grasp-<时间戳>`，未回传完整名称，下次需要列目录核对。

**这不是完整折叠成功，也不是通用或重复抓取通过。** 尚未验证换点抓取、完整 ActionChunk 接口、独立 episode reset、难度协议和折叠效果。附着开启时仍有约 24.20 mm 的最大单步顶点位移，只是低于当前 30 mm 诊断阈值，不能据此认定物理效果足够平滑。

用户要求今天到此暂停。本次只生成交接文件，没有执行远程关机、提交 Git 或推送。最后测试已返回 shell 提示符；当前 GPU 和实例开关状态没有重新查询。

## 2. 当前实例与环境

| 项目 | 当前值 |
|---|---|
| SSH 别名 | `autodl-garmentlab-264` |
| SSH 命令 | `ssh -p 22895 root@connect.nmb1.seetacloud.com` |
| 容器 | `autodl-container-7dde4b87a0-ea1fac3d` |
| GPU | NVIDIA GeForce RTX 4090，24564 MiB |
| 驱动 | 580.76.05 |
| nvidia-smi CUDA 显示 | 13.0（驱动支持信息，不代表需要重装工具链） |
| Python | 3.10.8 |
| Isaac Sim | 4.0.0.0 |
| NumPy | 1.26.4 |
| Python 路径 | `/root/autodl-tmp/envs/isaac40/bin/python` |
| 数据盘最近检查 | 50G，已用 34G，可用约 17G；后续产生了更多日志，需复查 |

过期实例：17195 / connect.nmb2.seetacloud.com 是前一天的 RTX 3090；16629、18117 也都是更早实例。恢复时不要混用。

时间注意：这次工作按 10 月 23 日日报归档，但 AutoDL 终端本地时间跨入了 10 月 24 日。最后结果目录仍带 `20261023-235941`，对应的附着快照带 `20261024-000327`。Kit 日志时间与目录时间也存在时区差异，不代表数据错配。

## 3. 目录、版本和备份边界

### 3.1 两个代码目录都需要保留

1. GarmentLab 上游适配仓库：
   `/root/autodl-tmp/garmentlab_workspace/GarmentLab`
2. 正式 backend 仓库：
   `/root/autodl-tmp/garmentlab-action-chunk-demo`

今天开始时正式项目 HEAD 为 `233771e`（main，Day4 WIP）；origin/main 为 `2307770`，更早为 `de104ba`。今天没有确认新 commit 或 push，不能只靠 Git 提交恢复所有改动。

衣物资源：
`/root/autodl-tmp/garmentlab_workspace/GarmentLab/Assets/Garments/Tops/NoCollar_LSleeve_FrontClose/TNLC_Dress057/TNLC_Dress057_obj.usd`

### 3.2 本地交付材料

`E:\learning\project\thesis\day4-prepared-grasp-patch\`

含安装脚本、初始接入模块、初始机器人验证脚本及 README。安装脚本已在本地基于用户提供源码做临时目录演练，验证 Python 3.10 语法、备份完整性和重复安装保护。

**本地补丁包不是最终服务器版本。** 之后的分层下降测试、跳变诊断、关闭附着对照和 overlap 环境变量支持，都是用户在服务器执行命令后追加的。下次优先读取服务器当前源码及成功备份，不要用本地旧模块覆盖服务器。

### 3.3 成功保存命令的覆盖范围

用户确认的 `day4-passed-grasp-*` 保存目录包含：

- `garmentlab_backend.py`
- `prepared_grasp_control.py`
- `day4-prepared-robot-staged-test.py`
- 最终成功输出目录的副本
- 最终附着跳变 NPZ
- `run-settings.txt`

**该目录不包含全部环境适配。** 特别是 GarmentLab 仓库中的 `MyFranka.py`、`BaseEnv.py`、`Control.py`，以及安装环境，仍需另外保留。若要克隆，应核对数据盘内容实际是否已迁移；不要把保存镜像等同于完整数据盘备份。

## 4. 今天修改的代码及原因

### 4.1 BaseEnv.py：启用 Torch/CUDA

路径：`/root/autodl-tmp/garmentlab_workspace/GarmentLab/Env/env/BaseEnv.py`

World 初始化为 `World(backend="torch", device="cuda:0")`。已验证 GPU pipeline 开启。此前 NumPy frontend + GPU pipeline 会直接报错，因此不要退回 NumPy 来绕过夹爪兼容问题。

### 4.2 MyFranka.py：CPU 控制接口与 CUDA 物理状态适配

路径：`/root/autodl-tmp/garmentlab_workspace/GarmentLab/Env/Robot/Franka/MyFranka.py`

主要改动：

- `CpuPoseFranka.get_world_pose()` 将基座位姿转换为 CPU NumPy，供 Lula/SciPy 使用。
- 对当前夹爪实例的 initialize 回调做适配：关节读取返回 CPU NumPy；设置关节位置时转换为匹配设备、dtype 的 Tensor。
- 关节索引避免直接把 Python list 传给 Torch `unsqueeze`。
- 夹爪动作过滤 `None`，构造只包含夹爪关节的有效位置和索引；避免 Torch 对 `NoneType` 推断失败。
- 控制器输入按需转换为 CPU NumPy，物理后端仍保持 Torch/CUDA。
- `get_cur_ee_pos()` 改用实测关节位置做实时 FK，且核对 KinematicsSolver 和 RMPFlow 都使用 `right_gripper`。
- FK 输出旋转矩阵经 SciPy 转四元数，再由 xyzw 排序为 wxyz。
- 到位检查使用实时 FK。

关键纠正：RMPFlow 的 debug end-effector prim 不是可靠的实测末端位置，首次 forward 前曾返回错误高度 0.826 m。Franka 默认 end_effector 又可能是 `panda_rightfinger`，不能直接当作 `right_gripper` 替换。

### 4.3 Control.py：方块的 GPU 读写基础适配

路径：`/root/autodl-tmp/garmentlab_workspace/GarmentLab/Env/env/Control.py`

- 创建时通过 PhysxRigidBodyAPI 显式设置禁用重力。
- `initialize_physics()` 要求 playing timeline，初始化 rigid view 并检查 count。
- 位置读取返回 CPU Tensor，速度写入转换为 CUDA 上的 `(1, 6)` Tensor。
- 已发现运行时新增刚体可能触发 CUDA error 700，原控制器暂停后创建/删除对象的路径尚未整体修复。
- 原 `detach()` 仍会删除节点；正式实验不调用这个释放路径。

### 4.4 garmentlab_backend.py：严格世界坐标与可选接入

路径：`/root/autodl-tmp/garmentlab-action-chunk-demo/backends/garmentlab_backend.py`

- 首次 env.reset 后初始化 ClothPrimView，检查 GPU pipeline、timeline 和衣物数量。
- `_garment_world_positions()` 严格从物理 view 读 `(1,N,3)`，转换为 NumPy `(N,3)`；不再静默回退到局部 USD 顶点。
- 世界坐标写入匹配 CUDA dtype/device；可以清零衣物粒子速度。
- 观测读取实时末端位姿，检查有限值、形状及四元数。
- 新构造参数 `prepared_grasp: bool = False`。
- 当设为 True 时，在 reset 前用 PreparedGraspControl 替换 env.control，reset 后初始化方块物理视图。
- 没有 holding 时，HOLD 只移动机器人；holding 时调用附着跟随。
- 到位检查不再吞掉非 RuntimeError 异常。

注意：默认 False 仍走旧抓取路径，不能认为默认路径已通过 GPU 抓取验证。

### 4.5 prepared_grasp_control.py：本次成功的实验控制器

路径：`/root/autodl-tmp/garmentlab-action-chunk-demo/backends/prepared_grasp_control.py`

- 独立约束路径 `/World/AttachmentConstraints/prepared_grasp`；方块留在 `/World/Attachment/attach/block`。
- reset 前预创建方块及关闭的约束。
- 当前预选衣物初始最左侧顶点周围 2 cm 内的 23 个跟踪顶点。
- 跟踪顶点用于诊断，不等于 PhysX 实际附着顶点集合。
- 方块目标为实时末端位置加旋转后的 `grasp_offset`，抓取和移动共用这一公式。
- 方块速度上限 0.3 m/s。
- 机器人位置误差 < 1 cm；跟随时方块误差 < 5 mm；连续 6 步满足才返回。
- `robot.close()` 内部推进 10 步仿真，因此先关闭夹爪，再对齐方块和开启约束。
- 开启前检查与预选衣物区域的距离 < 2 cm。
- 开启后一帧检查全衣物最大顶点位移 < 3 cm；该值是诊断阈值。
- 释放停方块速度、关闭约束，再开夹爪；不删除方块。
- 每进程只允许一次抓取，重复抓取明确报错。
- 超时停止；开启后失败会关闭约束并清理 holding 状态。

后续追加环境变量：

| 变量 | 默认 | 本次成功值 |
|---|---|---|
| `GARMENTLAB_ATTACHMENT_OVERLAP` | `0.02` | `0.005` |
| `GARMENTLAB_DISABLED_ATTACHMENT_PROBE` | 未设置时正常开启 | `0` |

关闭附着对照仅在第二个变量为 `1` 时启用：保存一帧后主动报 `Diagnostic stop`。这是诊断结束，不是抓取通过。

## 5. 已完成验证与证据

### 5.1 衣物世界坐标读写

- `CLOTH_VIEW_PROBE_OK`：Torch/cuda:0，GPU pipeline=True，count=1，形状 `(1,9945,3)`。
- 位置平移 1 mm 后回读误差 0，恢复原位置成功。
- `BACKEND_WORLD_IO_OK`：速度清零通过；120 步中衣物中心高度从约 0.295 m 落到 0.01984 m；最大顶点位移约 0.33027 m。
- 观测 keypoints 为 `(8,3)`。

### 5.2 机器人与夹爪

- `GRIPPER_CYCLE_OK`：打开 `[0.04,0.04]`，关闭接近零，再打开恢复。
- 修正实时 FK 后 `ROBOT_MOTION_OK`：末端从约 z=0.38832 m 向下移动 5 cm，最终误差约 9.54 mm；初始一步误差合理，不再出现 debug 位姿导致的 0.536 m 假误差。

### 5.3 预创建方块

- 动态创建测试出现 CUDA 700，timeline 停止；此路径不继续使用。
- `PRECREATED_BLOCK_OK`：静止漂移 0，z 速度 0.1 m/s 跑 12 步，上升 0.01999998 m，停止后漂移 0。

### 5.4 独立路径解决本次释放视图失效

原结构把 PhysxPhysicsAttachment 定义在方块父节点 `/World/Attachment/attach` 上。关闭附着时触发 tensor simulationView invalidated；重新 initialize 后仍报 unresolved rigid dynamic index，方块读取为 `[0,0,0]`。不能把该值当成真实漂移。

对照改为独立约束路径后：

- `INDEPENDENT_ATTACHMENT_RELEASE_OK`
- 衣物上升约 0.1 m，释放回落约 0.3725 m。
- 原 view 继续可读，方块释放漂移 0。

结论限定：独立路径解决了本测试中观察到的释放视图失效；不推断所有运行时拓扑修改都安全。

### 5.5 开启与落地抓取（方块驱动）

- `RUNTIME_ATTACHMENT_ENABLE_RELEASE_OK`：预创建但关闭，运行时开启后可抬升及释放。
- `SETTLED_ATTACHMENT_GRASP_RELEASE_OK`：先让衣物落地，再把既有方块移到当前衣物区域，开启附着。
- 后者开启最大单步位移 25.46 mm，衣物上升约 99.85 mm，释放回落约 101.59 mm，方块漂移 0。

### 5.6 机器人下降诊断

首次机器人测试用当前姿态反算抓取目标，得到 z=-0.0000815 m，下降超时，尚未开启附着。

随后 `DESCENT_PROBE_OK_NO_GRASP`：按 0.12、0.08、0.05、0.03、0.02 m 分层下降全部可达。

- 目标 0.02 m 时实际末端约 0.02683 m。
- 此姿态下局部 -z 偏移被旋转到世界向上约 1 cm，附着目标高度约 0.03648 m。
- 与跟踪衣物区域最近距离约 6.00 mm。
- 到位误差约 6–7 mm。

最终 staged 测试沿用该路径。固定 2 cm 是当前场景实验设置，不是通用抓取策略。

### 5.7 开启跳变：ON/OFF 对照

20 mm overlap 下：

- 关闭夹爪并对齐后，方块距跟踪区域最近约 3.6459 mm。
- 开启后一帧最大位移 41.7466 mm，触发 30 mm 检查。
- 最大位移顶点 8640，不在预先记录的 23 个跟踪点中。
- 跟踪点平均位移约 16.69 mm，最大约 20.20 mm。
- 方块只移动约 0.02 mm。

关闭附着但执行同样一帧控制：

- 最大顶点位移约 3.092 mm。
- 跟踪点平均约 0.135 mm，最大约 0.235 mm。

NPZ 离线比较确认开启前所有顶点位置差异为 0、方块位置差异为 0。ON/OFF 后差异超过 5 mm 的有 290 点，超过 30 mm 的有 67 点，最大约 41.7503 mm。

结论：在该对照条件下，明显跳变来自开启附着。尚未确认是具体哪些锚点或选点机制导致；受影响顶点不能直接视为约束成员。

安装 schema 已确认：`deformableVertexOverlapOffset` 是到刚体体积的距离，不是到方块中心的距离。`points0/points1` 为一一对应的局部空间附着锚点；schema 未说明运行时重新生成的时机。不要把“沿用旧锚点”写成已证实原因。

### 5.8 最终通过：5 mm overlap + 机器人分层下降

| 指标 | 结果 |
|---|---:|
| 开启瞬间最大顶点位移 | 0.0242022965 m |
| 衣物随机器人抬升 | 0.0927918330 m |
| 方块跟随误差 | 0.0005314489 m |
| 释放后衣物回落 | 0.1073487494 m |
| 释放后方块漂移 | 0.0 m |
| 最终标记 | `PREPARED_ROBOT_GRASP_LIFT_RELEASE_OK` |

减少 overlap 缩小了本次最大跳变，同时仍能有效带起衣物。但跟踪区域平均开启位移仍约 16.67 mm，与原先相近；不能宣称所有附着突变已消除。

## 6. 关键脚本、输出和复现命令

### 6.1 最终通过脚本与结果

- 脚本：`/root/autodl-tmp/day4-prepared-robot-staged-test.py`
- 输出：`/root/autodl-tmp/day4-prepared-robot-staged-20261023-235941-421084/`
- 结果：上述目录内 `result.json`
- 快照：`00_settled.npz`、`01_approach.npz`、`01b_before_close.npz`、`02_grasp.npz`、`03_lift.npz`、`04_release.npz`
- 最终附着快照：`/root/autodl-tmp/attachment-enable-jump-20261024-000327-135229.npz`
- 最终日志：`/root/autodl-tmp/day4-overlap5mm-*.log`，完整时间戳需查目录。

快照包含顶点、tracked_indices、方块位置、末端位置与四元数。当前测试没有输出新的 RGB 图或视频。用户所确认保存的成功目录名称待下次核对。

ON/OFF 对照：

- ON：`/root/autodl-tmp/attachment-enable-jump-20261023-235053-159190.npz`
- OFF：`/root/autodl-tmp/attachment-enable-jump-20261023-235602-926792.npz`

### 6.2 主要辅助测试脚本

均位于 `/root/autodl-tmp/`：

- `day4-cloth-view-probe.py`
- `day4-backend-world-io-test.py`
- `day4-robot-motion-test.py`
- `day4-attachment-block-test.py`（失败的运行时创建实验，不建议重跑）
- `day4-precreated-block-test.py`
- `day4-cloth-attachment-test.py`
- `day4-cloth-attachment-rebind-test.py`（重新初始化视图不能修复原路径问题）
- `day4-cloth-attachment-independent-test.py`
- `day4-cloth-attachment-enable-test.py`
- `day4-cloth-attachment-settled-test.py`
- `day4-prepared-robot-test.py`（最初近零高度超时版本）
- `day4-grasp-approach-probe.py`
- `day4-prepared-robot-staged-test.py`（最终通过版本）

### 6.3 需要复现时使用的远程命令

今天已通过，不需为了日报再次运行。下次在核对文件和 GPU 后按需使用：

```bash
run_log="/root/autodl-tmp/day4-overlap5mm-$(date +%Y%m%d-%H%M%S).log"
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 \
GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
/root/autodl-tmp/envs/isaac40/bin/python \
  -X faulthandler -u \
  /root/autodl-tmp/day4-prepared-robot-staged-test.py \
  --allow-root 2>&1 | tee "$run_log"
run_status=("${PIPESTATUS[@]}")
printf 'PYTHON_EXIT=%s TEE_EXIT=%s\n' \
  "${run_status[0]}" "${run_status[1]}" | tee -a "$run_log"
```

必须看最终成功标记和 `result.json`，不能只看退出码：多次出现 Python 异常后 SimulationApp.close 结束进程、shell 仍报告退出码 0。

## 7. 已知风险与待办

1. **附着物理质量**：开启跳变仍达 24.20 mm。需检查快照/可视化，后续检查实际约束点和锚点；不要直接调大阈值。
2. **重复与换点抓取**：当前 adapter 显式限制单次抓取，不能删除限制就视为支持。
3. **完整动作接口**：当前测试通过 `_execute_single(SimpleNamespace(...))` 验证分发；没有覆盖 ActionChunk/schema 校验链。
4. **reset 独立性**：backend reset 尚未恢复衣物、机械臂、附着对象的完整初始状态；`robot_reset()` 主要开夹爪，不等于回到 home。
5. **步数上限**：现有计数从 start 起累计，不是每次 execute 独立预算。
6. **默认抓取路径**：`prepared_grasp=False` 仍是原动态创建/删除路径，不能用于宣称已通过的 GPU 抓取实验。
7. **姿态/yaw**：backend 仍传 `ori=None`；动作 yaw 未接入。2 cm 高度和当前偏移只对已测场景成立。
8. **难度协议**：flat/lift-drop 的可靠性、独立初始状态、随机种子复现性还未验收。
9. **整体折叠**：历史动作序列运行完成并不代表折叠质量通过；今天只验证单次抬升释放。
10. **提交与复现**：两个仓库改动未确认提交；本地初始补丁包与服务器最终代码不同步。
11. **应用生命周期**：缓存 SimulationApp 后关闭再 start 的生命周期未验证，继续按每个测试独立进程运行。

## 8. 日志中容易误判的现象

- 地面缺失 `omniverse://localhost/...Wireframe*.png` 材质：今天多个通过测试仍出现，不能据此判断仿真失败。
- `GLFW initialization failed`、退出时 UsdStage reference count 警告也出现在通过测试中；不把它们当作已解决，也不作为当前失败根因。
- `Simulation App Startup Complete` 仅表示应用启动；之后创建默认地面会进入 `get_assets_root_path -> check_server -> omni.client.stat`，可能等待资产服务器。
- 用户曾在启动后 Ctrl+C，日志只到 startup，不是新的抓取失败证据。
- 多数测试约 150–250 秒，个别曾更久；约 3–6 分钟无新输出时应新开终端查询进程和日志，避免并行重复启动。
- 容器内 `dmesg` 无读取权限，`free -h` 可能显示宿主机资源；不能据此排除容器限制。

## 9. 下次恢复顺序（建议）

### 第一步：确认实例、文件和当前改动

若没有空闲 GPU，先取得新实例 SSH 地址并更新别名；核对两个仓库、Python 环境、资源和成功备份都存在，再继续。不重装已经可用的 Isaac Sim 环境。

```bash
hostname
nvidia-smi
df -h /root/autodl-tmp
git -C /root/autodl-tmp/garmentlab-action-chunk-demo status --short
git -C /root/autodl-tmp/garmentlab_workspace/GarmentLab status --short
ls -dt /root/autodl-tmp/day4-passed-grasp-*
cat /root/autodl-tmp/day4-prepared-robot-staged-20261023-235941-421084/result.json
```

确认成功备份存在并补存 GarmentLab 的三个适配文件；如克隆了实例，不要只核对 commit，因为关键内容可能尚未提交。

### 第二步：离线检查成功快照

优先读取 02_grasp、03_lift、04_release 的 NPZ，绘制衣物顶点、跟踪区域、方块和末端位置对比。检查是否局部拉伸异常、是否抓取了预期区域。可先离线完成，无需再次消耗 GPU 启动时间。

### 第三步：整理配置并验证完整 ActionChunk

先读实际 schemas/action.py、backends/base.py 和调用方接口，再构造真实 ActionChunk，保持本次通过配置不变。不要凭记忆猜字段。首次重点覆盖未抓取 HOLD、CLOSE、已抓取 HOLD、OPEN 与状态一致性。

### 第四步：阶段性保存与后续扩展

完成快照检查和接口测试后，整理两个仓库 diff、实验参数、结果和备份。随后再设计 reset 恢复和重复抓取。完整折叠、难度随机化放在这些基础通过之后。

## 10. 给接手 agent 的简短提示

用户习惯在本地 PowerShell 上传文件，在 VS Code 远程 Bash 执行命令，再贴日志或截图。助手今天未直接 SSH 登录服务器；本地操作仅用于准备补丁、读取附件和写日报。不要声称已在远程修改或执行未获日志确认的操作。

请先读本日报及服务器最终源码，不要从 10 月 22 日的夹爪初始化错误重新开始。当前最重要事实是：**5 mm overlap、独立约束路径、预创建刚体、分层下降，已完成一次机器人驱动的抓取抬升释放；仍有开启跳变与通用化工作待完成。**
