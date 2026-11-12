# GarmentLab 交接日报｜2026-10-24｜Stage 4：ActionChunk、锚点对齐与抬升保持

## 1. 交接结论：恢复时先读这里

用户要求此处暂停，晚上继续。本日报写入时，最后一次实验及本地离线分析均已完成；没有继续发起新实验，没有执行远程关机、Git 提交或推送。实例当前开关、计费及 GPU 占用状态没有重新查询。

今天在新 RTX 3090 实例恢复了数据盘，完成以下推进：

1. 公开 `ActionChunk/execute()` 接口通过：H=4 未抓取分层下降，随后 H=1 CLOSE、持物 HOLD、OPEN。不是包含抓取和释放的混合 H=4 动作块验证。
2. 实际 USD-visible 锚点为 28 对。补存首次 reset 前的原始 mesh，确认 28 个 `points0` 各自精确对应一个不同的原始顶点；23 个跟踪点是这 28 个点的子集。
3. 匹配状态的独立基线/对齐实验通过：只在约束关闭、方块到位后重算 `points1`，开启单帧最大位移从 **24.202 mm 降至 4.295 mm（降低 82.25%）**，抬升和释放保持通过。
4. 逐步采样发现抬升时明显伸长集中于抓取区边界及邻近区域。最坏边为 **8958—9025**，其中 9025 是锚点、8958 不是。
5. 保持原抬升目标再运行 3 秒后，最坏边由抬升结束的 **1.645 倍初始长度**进一步到约 **1.76 倍**，末段低刚体运动下没有明显回落。但保持早期末端额外上移约 **6.69 mm**，因此不能把新增伸长归因于纯等待时间，也没有证明全衣物静态平衡。

**下一步尚未执行：以抬升结束时的实测末端位姿为保持目标做独立对照，减少继续靠近更高目标带来的混淆。对应新脚本尚未生成。现有 `day4-aligned-lift-hold-test.py` 仍保持原更高目标，不能误当作这一新对照。**

锚点对齐仍是独立测试进程中的运行时 USD 修改，尚未正式整合进 backend。默认抓取路径、独立 reset、重复/换点抓取、yaw、完整折叠与训练均未通过验收。

## 2. 当前实例、环境与操作边界

| 项目 | 今天确认的信息 |
|---|---|
| 实例 | 内蒙 B 区 / 430 机 |
| 容器 | `autodl-container-ac0a41b2f7-bc28942d` |
| VS Code SSH 别名 | `autodl-garmentlab-430` |
| SSH 命令 | `ssh -p <port> <server>` |
| GPU | NVIDIA GeForce RTX 3090，24576 MiB |
| 驱动 | 580.105.08 |
| nvidia-smi CUDA 显示 | 13.0，指驱动支持信息；没有因此重装 CUDA |
| Python | `<remote-root>/envs/isaac40/bin/python`，3.10.8 |
| 仿真 | 沿用迁移的 Isaac Sim 4.0 环境，今天多次测试通过，没有重装 |
| 数据盘 | 今天开始时 50G，总使用约 34G、可用约 17G；之后新增结果，需按需复查 |

旧实例 264 机为 RTX 4090：`7dde4b87a0-ea1fac3d`，旧地址 `<server>`，不是今天的连接地址。用户通过 AutoDL 的跨实例拷贝数据盘功能把 `<remote-root>/` 内容迁到新实例，随后确认关键环境、源码和成功备份均存在。

本助手未成功 SSH 登录：对新地址的非交互认证失败。远程命令均由用户在 VS Code 远程 Bash 执行，随后提供日志/截图；上传下载由用户在本地 PowerShell 执行。本助手创建本地脚本、读取已下载文件并做离线审计与绘图。不要把本地脚本语法/适配器检查称为新的 GPU 物理验证。

目录时间戳、Kit 日志时间和用户时区可能不同；今天按 2026-10-24 归档，以运行目录和文件对应关系为准，不凭日志小时数判断数据错配。

## 3. 代码、备份与未提交状态

远程两个仓库：

- `<remote-root>/garmentlab-action-chunk-demo`
- `<remote-root>/garmentlab_workspace/GarmentLab`

今天恢复时，正式项目的 `backends/garmentlab_backend.py` 有未提交修改，`prepared_grasp_control.py` 及若干备份文件为未跟踪；GarmentLab 仓库中的 `MyFranka.py`、`BaseEnv.py`、`Control.py` 有未提交修改。没有确认今天产生新的 commit/push，当前 HEAD 未重新核实。

昨天成功备份的完整名称今天已确认：
`<remote-root>/day4-passed-grasp-20261024-000433`。

今天没有持久修改这两个仓库的控制源码。实验在 `<remote-root>/` 的独立脚本中使用实例方法包装和运行时 `points1` 写入；新测试每次按已通过运行的 manifest 核对相关源码，另外保存本次脚本及依赖。

正式方案的基础仍为：Torch/CUDA、reset 前预创建刚体与约束、独立约束路径、分层下降、`prepared_grasp=True`、5 mm overlap、每进程一次抓取。原有 30 mm 开启跳变检查没有放宽；它是诊断阈值，不是物理质量标准。

`E:\learning\project\thesis\day4-prepared-grasp-patch\` 是早期补丁包，不是服务器最终版本，不要用它覆盖当前源码。

本地已下载的结果中保存了带哈希的 backend、PreparedGraspControl、三份 GarmentLab 适配文件和观察器。首次 reset 前采集结果还含 `source/FoldEnv.py`。这些副本比旧补丁更新，但不是完整仓库、安装环境或衣物资产备份；衣物 USD 等资产仍需保留远程数据盘。

## 4. 本地与远程结果索引

以下运行目录均在远程 `<remote-root>/`，且已完整下载到：
`E:\learning\project\thesis\day4-actionchunk-test\results\`。

| 目录 | 内容与结论 |
|---|---|
| `day4-prepared-actionchunk-20261024-204755-573715` | 公开 ActionChunk 验证通过，6 个 chunk、9 个高层动作、48 项结束状态检查 |
| `day4-anchor-diagnostic-20261024-210929-786774` | 10 阶段 USD/物理锚点诊断，每阶段 28 对锚点，数组未变 |
| `day4-pre-reset-mesh-20261024-212943-485691` | 首次 reset 前的原始网格、面拓扑、精确锚点映射 |
| `day4-anchor-pair-baseline-20261024-215325-587860` | 独立对照基线，不写 points1 |
| `day4-anchor-pair-aligned-20261024-215858-281289` | 独立对齐组，只重算 points1，改善开启跳变 |
| `day4-anchor-pair-run-fhFIzk2Z` | 两组运行日志、结果路径和 comparison.json |
| `day4-aligned-lift-step-20261024-223712-756159` | 已对齐方案的逐步抬升采样：50 帧、49 次 World.step |
| `day4-aligned-lift-hold-20261024-230123-728994` | 逐步抬升 + 保持原目标 3 秒：230 帧、229 次 World.step |

另外已下载：`attachment-enable-jump-20261024-205242-730012.npz`，位于本地 results 根目录，是第一轮 ActionChunk 测试的单帧开启诊断。

所有运行的 `result.json` 已在本地读取。不要只依赖 shell 退出码：SimulationApp 关闭曾使异常过程也返回 0；成功必须结合最终标记、JSON 和检查字段。

## 5. 今天的验证与关键数值

### 5.1 公开动作接口

源码确认：`CartesianAction.target_pose` 为 `[x,y,z,yaw]`，形状 `(4,)`；`ActionChunk` 含 actions，序列化矩阵为 `(H,5)`；`execute()` 调用 `_check_action_chunk()` 后逐个分发。

6 个 chunk 的 horizon：`1,1,4,1,1,1`，共 9 个高层动作。H=4 对应下降的 0.08、0.05、0.03、0.02 m；0.12 m 作为前一个 H=1。CLOSE、持物抬升 HOLD、OPEN 分别为 H=1。yaw=0，backend 仍忽略 yaw，传给底层的 ori=None。

测试检查执行动作数、步数增长、phase、gripper state、backend/control holding、attachment enabled 和引用一致性，共 48 项动作块结束检查。不等于逐物理帧全状态验收。

### 5.2 真实锚点及坐标处理

- `points0/points1` 各为 28×3，从 after_start 到 release 的 10 个阶段逐元素不变，只有 attachmentEnabled 等状态切换。
- actor0 为 `/World/Garment/garment/mesh`，actor1 为 `/World/Attachment/attach/block`，约束路径 `/World/AttachmentConstraints/prepared_grasp`。
- points0 是衣物侧局部坐标，points1 是方块侧局部坐标，不能直接相减或当世界坐标。
- 原始衣物缩放约 0.005，方块缩放约 0.03；初始 USD 世界坐标中的两侧配对误差最大约 0.00002146 mm。
- GPU 下方块 USD 平移滞后，方块对齐阶段与物理位置相差约 258 mm。分析必须使用实时刚体位置、四元数和 authored scale 重建 points1 世界目标。
- 不能用静态衣物 USD 变换表示当前形变后的衣物材料点。

### 5.3 首次 reset 前网格与准确映射

首次 World.reset 在入口被截获而未执行；采集前后 timeline 均未播放，仿真时间和步索引为 0。创建 PreparedGraspControl 前、创建后、reset 入口三个阶段的几何与拓扑完全相同。

- 顶点数：9945。
- 三角面数：19756；faceVertexIndices 长度 59268。
- 去重网格边：29703；无 hole faces。
- 28 个 points0 分别与不同的原始顶点坐标精确相等，最大匹配距离 0。
- 第二近点至少相距约 0.884448 局部单位，即约 4.42 mm，没有重复位置导致的映射歧义。
- 23 个 tracked_indices 全部包含在这 28 个映射顶点内。
- 原始映射与开启后、抓取稳定及抬升快照中的最近目标顶点索引均吻合。未直接读取内部求解器成员 API，不能把 collisionFilterIndices 单凭名称或数量等同于锚点成员。

映射索引按锚点配对顺序为：
`8629,8630,8631,8632,8633,8634,8661,8703,8748,8749,8754,8755,8779,8819,8820,8822,8823,8861,8862,9004,9025,9059,9074,9119,9120,9154,9155,9156`。

早期的 8.03 mm 是目标到任意最近衣物顶点的平均距离。精确配对后，开启前真实对应索引的平均几何间距为 15.58 mm；这两个指标不同，不是数值矛盾，也都不等于内部求解器残差。

### 5.4 匹配状态的 points1 对照

两组 11 份源码、5 份参考文件、干预前全部顶点/方块位姿/缩放/索引/原始锚点数组一致；6 个动作矩阵及每次 execute 的步数一致。

baseline 不写 USD；aligned 在方块对齐、约束关闭时，以当前对应衣物顶点和实时方块位姿反算 points1，只写该属性。points0、overlap、原控制轨迹及诊断阈值不变。写入操作没有推进物理或直接改衣物位置，回读与后续各阶段数组保留检查通过。

| 指标 | baseline | aligned |
|---|---:|---:|
| 开启前逐对平均间距 | 15.583 mm | 写入后约 0 mm |
| 开启单帧最大顶点位移 | 24.202 mm | 4.295 mm |
| 开启单帧跟踪区域平均位移 | 16.671 mm | 1.353 mm |
| 单帧位移超过 5 mm 的顶点数 | 173 | 0 |
| 同一帧方块位移 | 0.004895 mm | 0.004895 mm |
| 开启后逐对平均间距 | 1.368 mm | 1.369 mm |
| 开启后锚点邻接边最大长度比 | 1.659 | 1.242 |
| 抬升时锚点邻接边最大长度比 | 1.682 | 1.645 |
| 从稳定抓取状态计的衣物抬升 | 92.803 mm | 92.832 mm |
| 抬升终点跟随误差 | 0.53145 mm | 0.53145 mm |
| 释放回落 | 106.940 mm | 92.360 mm |
| 释放后方块漂移 | 0 | 0 |

最大开启位移降低 82.25%，跟踪区域平均位移降低 91.88%。本次干预证据支持“原锚点布局与衣物落地形变不匹配是开启跳变的重要可干预因素”。不能据此推断全部内部自动生成机制或一般场景已解决。

aligned 绝对抬升高度更低，主要对应开启时额外抬高衣物的现象被减少；两组从稳定抓取状态算的抬升仍约 92.8 mm。

### 5.5 抬升逐步采样

记录 50 帧，步号 508～557，共 49 次显式 World.step、约 0.816667 s。与原 aligned 运行的 6 个阶段快照、动作矩阵及执行步数完全一致。

边类按锚点端点数量定义：内部边 63 条（两端为锚点）、边界边 30 条（一端为锚点）、区域外边 29610 条（零锚点端点）。不是按衣物外轮廓划分。

- 全段最大边长比为 1.64535，发生在最后一帧、边 8958—9025。
- 该边初始 7.080 mm，抬升开始 7.175 mm，抬升结束 11.650 mm。
- 末帧超过 1.5 倍的 4 条边中，3 条是边界边，另 1 条距锚点仅 1～2 个拓扑跳；较低程度伸长也存在于更远处。
- 内部边全段最大约 1.184，区域外边全段最大约 1.581。
- 末端速度峰值约 0.19494 m/s（step 513）；方块峰值约 0.19536 m/s（step 514），均远早于最大伸长。
- 全段逐对锚点最大几何间距约 1.561 mm，没有随边长增长出现同量级发散。

仅覆盖 World.step 结束点，不含内部 PhysX 子步；当时最后一帧最大不能当作后续全过程最大。

### 5.6 最新：保持同一原目标 3 秒

记录 230 帧、步号 508～737。原 50 帧抬升轨迹完全相同，新增 180 步目标保持。保持前的阶段快照和前五次 execute 的矩阵/步数一致；保持与释放后的状态不要求与旧的立即释放实验相同。

原请求抬升目标 z≈0.120137918 m，抬升动作结束实测 z≈0.113548058 m；保持同一原目标后，实测末端继续靠近目标，结束 z≈0.120235279 m。

| 指标 | 结果 |
|---|---:|
| 保持阶段末端额外上移 | 6.687 mm |
| 方块额外上移 | 7.242 mm |
| 跟踪区域平均额外上移 | 7.531 mm |
| 保持开始最大边长比 | 1.64535 |
| 保持 0.5 s 时最大边长比 | 1.71156 |
| 保持 1.0 s 时最大边长比 | 1.73913 |
| 保持全段峰值 | 1.76258，step 732，保持后 2.91667 s |
| 保持结束最大边长比 | 1.75750 |
| 峰值边长度 | 12.480 mm，仍为 8958—9025 |
| 末 30 帧最大边长比范围 | 1.75454～1.76258 |
| 末 30 帧末端最大速度 | 0.13296 mm/s |
| 末 30 帧方块速度 | 保存位置有限差分为 0 |
| 保持阶段逐对锚点最大间距 | 1.485 mm |
| 保持后释放回落 | 99.043 mm，以保持结束状态为基准 |
| 保持后释放方块漂移 | 0 |

新增保持的 180 帧中，全局最大边长比始终位于边界类。方块保存位置在保持约 1.333 s 后不再变化，持续到 3 s；这不排除低于存储精度的运动。

末段约 0.5 秒没有明显回落，但衣物仍有粒子运动：全衣物单步位移最大约 2.945 mm，平均约 0.0668 mm，P95 约 0.1664 mm。因此不能宣称整件衣物达到静态平衡。

## 6. 本地分析与图表：恢复时优先打开

所有分析已离线完成，无需再次启动 GPU 来重复核对这些结果。

- [两组完整对照报告](E:/learning/project/thesis/day4-actionchunk-test/results/day4-anchor-pair-run-fhFIzk2Z/analysis/pair_review.md)
- [抬升逐步采样报告](E:/learning/project/thesis/day4-actionchunk-test/results/day4-aligned-lift-step-20261024-223712-756159/analysis/lift_step_review.md)
- [最新保持阶段报告](E:/learning/project/thesis/day4-actionchunk-test/results/day4-aligned-lift-hold-20261024-230123-728994/analysis/lift_hold_review.md)
- [最新运动与伸长曲线](E:/learning/project/thesis/day4-actionchunk-test/results/day4-aligned-lift-hold-20261024-230123-728994/analysis/lift_hold_motion_and_extension.png)
- [最新局部边界图](E:/learning/project/thesis/day4-actionchunk-test/results/day4-aligned-lift-hold-20261024-230123-728994/analysis/hold_boundary_geometry.png)

其他运行对应的 analysis/ 内有 raw audit JSON、CSV 和图像。原始快照保留，分析不覆盖采集数据。

本地脚本根目录：`E:\learning\project\thesis\day4-actionchunk-test\`。

| 脚本 | 用途 |
|---|---|
| `day4-prepared-actionchunk-test.py` | 公开 ActionChunk 接口测试 |
| `day4-anchor-diagnostic-test.py` + `anchor_observer.py` | 开启前后锚点观察 |
| `day4-pre-reset-mesh-capture.py` | 首次 reset 前捕获原始 mesh/topology 后停止 |
| `day4-anchor-alignment-test.py` + `anchor_alignment_observer.py` | baseline/aligned 单变量 points1 对照 |
| `run-anchor-alignment-pair.sh` | 串行独立进程跑两组，检查标记/JSON/干预前匹配 |
| `day4-aligned-lift-step-test.py` + `lift_step_observer.py` | 仅抬升段逐 World.step 采样 |
| `day4-aligned-lift-hold-test.py` + `lift_hold_step_observer.py` | 最新：抬升后保持原目标 180 步 |
| `analyze_local_results.py` | 首轮 ActionChunk 结果与开启快照离线分析 |
| `analyze_anchors.py` | 10 阶段锚点数组与刚体侧目标分析 |
| `analyze_paired_anchors.py` | 原始网格精确配对和拓扑边长分析 |
| `analyze_alignment_pair.py` | 基线/对齐两组完整核对与图表 |
| `analyze_lift_step_trace.py` | 50 帧抬升轨迹与边界峰值定位 |
| `analyze_lift_hold_trace.py` | 230 帧目标保持轨迹与末段放大图 |

说明文件：ANCHOR_ALIGNMENT_CONTROL.md、LIFT_STEP_TRACE.md、LIFT_HOLD_TRACE.md。

运行分析脚本使用本地已有 Python/NumPy/Matplotlib/SciPy，不导入 Isaac Sim；直接 `python` 执行相应本地文件即可。PowerShell Python 默认文本编码可能为 GBK，读取中文源码/日报时明确使用 UTF-8。

## 7. 晚上恢复的具体顺序

1. 先读本日报第 1、5.6、6 节，不从昨天的 GPU/夹爪适配或已完成下载重新开始。
2. 如果实例仍是原实例且用户已连入，按需只读检查 `hostname`、`nvidia-smi`、`df -h <remote-root>`；若 SSH 地址变更，以用户提供的新命令为准，不混用旧 264 机配置。不重装现有可用环境。
3. 下一项实验是 **实测末端位姿目标保持**：保持原 50 帧抬升前缀不变，在 step 557 后以该时刻的实测 EE xyz 为新的保持目标，仍用相同控制器、姿态策略和 180 步保持，继续逐步保存。新目标会产生制动/微调，必须记录实测运动，不假定立即静止。
4. 与本次“原更高目标保持”的 230 帧运行比较。重点看额外上移是否减少、近停稳后的边界边长是否仍高、逐对间距是否稳定，以及抬升和释放是否保留。保留源码/参考哈希、原 50 帧一致性及状态检查；所有新干预使用新文件、新输出目录和新进程。
5. 取得这一对照后再决定是否有必要做速度、时间步或材料/求解参数单变量实验，不同时改多个参数，不直接提高阈值。
6. 独立 reset 和重复抓取仍是后续工作；不要删除当前单次抓取限制来宣称支持通用抓取。正式 backend 整合 points1 对齐也尚未进行。

## 8. 已知边界与容易误判之处

- 当前证明的是固定衣物、固定区域、单次抓取的若干接口与几何对照；没有完整折叠质量、难度协议、BC、VLA 或真实机器人结果。
- 5 mm overlap 仍必须显式设置；默认 20 mm 不是本次通过配置。
- `prepared_grasp=False` 仍是旧动态创建/删除路径，不能认为已通过本次 GPU 抓取。
- backend reset 不恢复完整独立 episode；robot_reset 主要开夹爪，不等于机械臂回 home。
- max_action_steps 仍是自 start 起累计预算，不是每次 execute 单独预算。
- 约束属性写入回读和后续保留不直接暴露内部 solver；本次强证据来自匹配状态下的实际几何响应改善。
- 边长比不是应力、材料真实性或自穿透检测。1.3/1.5 倍等是描述性切点，不是验收阈值；4.295 mm 也不是新的通用跳变阈值。
- 固定目标不等于固定实测位姿；近静止的刚体也不等于全部衣物静止。
- 所有轨迹为显式 World.step 结束时采样，不覆盖内部 PhysX 子步。单一运行窗口不能证明更晚时刻的最终状态。
- 地面 Wireframe 纹理缺失、退出 GLFW 和 UsdStage 引用警告仍出现于通过运行；本次没有修复，不把它们当作当前物理失败根因。
- 默认地面资产查询可能在 `get_assets_root_path -> check_server -> omni.client.stat` 等待，曾出现堆栈后仍继续成功；仅凭启动停顿或截图堆栈片段不能宣布新实验失败。
- PowerShell 上传应使用绝对路径，或先确认当前目录；今天曾因先 scp 后 cd 而找不到本地文件。远程执行必须在 Bash，不能把 Linux heredoc 命令直接当 PowerShell 命令。
- 后续若 shell 退出码为 0，仍须核对最终成功标记、result.json passed=true、采集 complete 和参考一致性检查；这些比退出码更可靠。

## 9. 给接手 agent 的简短提示

用户习惯由助手准备本地脚本，自己用 PowerShell 上传，再在 VS Code 远程 Bash 执行并回传截图/日志。下载后助手可直接读取本地 results/，无需反复要求粘贴已有源码或已分析的图。

今天最重要的推进是：**points1 对齐明显减少开启跳变，且因果对照前态完全一致；剩余主要几何问题转为抓取区边界在抬升/保持时的持续伸长。最新保持实验还存在末端继续上移约 6.7 mm 的混淆。下一步做实测末端目标保持对照，不要把当前结果写成整体物理质量、reset 或完整折叠已通过。**
