# Garment Folding with Action Chunking

研究 single-step behavior cloning 与 H=4 action-chunk BC 在三档衣物初态下的折叠成功率、恢复能力和推理开销。当前工作集中在 GarmentLab / Isaac Sim 中建立可靠的 expert 和动作接口，尚未进入策略训练或正式对比实验。

## 当前状态（2026-11-04）

**Stage 4 暂停在 D2 释放顺序对照之后。** D1-120 的延迟退让没有降低漂移；D2-A/B 完成实际场景与接触通道核查；D2-C 预登记“附着保持期间完成夹爪张开、随后解除附件”的单变量干预；D2-D 仅运行一次 4202 single：episode `passed=True`、诊断 `complete=True`、质量 `rejected`（质心 **1.9823 mm**、P95 **4.3426 mm**，仍超 1 mm / 3 mm）。释放一步粒子速度 **17.4197 vs 17.4223 mm/s**，free 0–30 基本不变 → **释放顺序不是该例漂移的主要因素**；formal 窗口小幅下降（2.0409→1.9823 mm、4.4134→4.3426 mm）不能归因于释放冲量减少。正式 Stage 4 成功仍为 **0**；RC2 未冻结；held-out 与正式批次暂停。[D2-D 对照](day4-actionchunk-test/results/D2_D_COMPARE_20261104/review.md) · [交接日报](2026-11-04-GarmentLab日报%20Stage4%20D2释放顺序对照交接.md) · [D2-C 版本](day4-actionchunk-test/a5-rc2-d2c-release-order/README.md)

## 历史进度（截至 2026-11-04）

| 工作项 | 状态与证据 |
| --- | --- |
| 仿真与动作接口 | 已有 `GarmentLabBackend`、动作/观测 schema、状态导出和视频记录；仍有待整合项。 |
| 物理配置与诊断 | 已完成配置读取、质量/迭代数对照及抓取、释放、控制诊断；历史结果和失败记录已保留。 |
| 原服装折叠 | 多次动作流程完成，但未得到已验收的释放后保持折叠；旧服装与被动载体探索分支已冻结。 |
| 单层方巾 L1 | 转向原计划范围内的 40 cm 单层方巾、单 Franka；441 顶点、800 三角形。先打通一个符合公共接口的 L1，再扩展三档。 |
| L1 折叠（开发） | yaw-aware 7 动作 + 独立“过折”折形（place 多伸 2 cm）：seeds 4100–4109 共 10/10 通过 runner 断言，释放后稳定（crossed 1.000、IoU 0.37–0.42、z_p95≈67.5 mm）。只算开发复验，不是验收。 |
| L2/L3 组合（开发） | 12 动作（5 recovery + 7 fold）在 L2/L3 的 right 槽位各有一个通过例；left（默认折向）在 4200/4300 释放后回弹。 |
| 任务定义冻结 | L1（过折）与 L2/L3（nominal 20/20）是两个折形任务，L2/L3 是同一任务下的两种初态族；三档汇总只能称多任务平均。见 [冻结文档](STAGE4_TASK_DEFINITION_FREEZE.md)。 |
| 表示层（single vs H=4） | 两个折叠脚本支持 `--execution single` / `arc4`，只把四个 arc 目标合成一个 H=4 chunk。L1/4100 与 L2/4200 各跑 single+arc4 配对：审计 `PAIRS_COMPARABLE`，同一对内快照**逐字节相同**、指标差全为 0 → 只证明专家轨迹在两种表示下等价，**不构成 H=4 收益证据**。 |
| 分任务报告 | 按 L1（过折）与 L2/L3（nominal 20/20）分别汇总：冻结版 seed 级 L1 1/1、L2/L3 0/2（L2/4200、L3/4300 left，共 4 次尝试全失败），多任务平均 0.50（A n=1、B n=2 个 seed）**不是难度曲线**；失败均为释放后回弹摊平，且补充的两例与既有同条件运行逐字节相同。见 [分任务报告](day4-actionchunk-test/results/STAGE4_PER_TASK_20261102/review.md)。 |
| 正式批次准备 | 每档 20 个 held-out seeds（L1 4110–4129、L2 4210–4229、L3 4310–4329）已登记并写入初态 plan；两个初态 runner 的 seed 断言已放宽，批次驱动与拒绝率汇总工具已就位，两份初态 manifest 已在远端无排除项核对通过。**未运行**（按 `b-right-dev-v1` 暂停），且正式成功判据阈值未冻结。见 [正式批次准备](STAGE4_FORMAL_BATCH_PLAN.md)。 |
| D2 释放顺序对照（2026-11-04） | D2-A/B 场景/接触核查；D2-C 单变量版本；D2-D 4202 single 一次：诊断 complete、quality rejected。释放瞬态/前 0.5 s 基本不变，正式窗口 2.0409→1.9823 mm、4.4134→4.3426 mm，仍拒绝。见 [D2-D 对照](day4-actionchunk-test/results/D2_D_COMPARE_20261104/review.md)。 |
| 正式验收与学习 | 三档正式成功轨迹、Stage 5 demonstrations、BC 训练及正式评估均未完成。正式 Stage 4 成功仍为 0。 |

截至 11 月 4 日的进度以 [Stage 4 下一步](DAY4_NEXT_STEPS.md) 和 [验收记录](DAY4_ACCEPTANCE_TRACKER.md) 为准。历史日报和旧脚本用于追溯，不应作为当前运行入口。

## 历史抓取诊断与修正候选

此前方巾试跑先后在抓取距离检查和下降运动中失败，均未证明 L1 折叠成功。源码审查确认：共享 Backend 尚未使用动作中的 `yaw`，位置运动也未固定末端姿态；使用下降前姿态一次性换算抓取偏移，不能保证到达时对齐。

独立开发候选 [square_pose_backend.py](day4-actionchunk-test/square_pose_backend.py) 采用统一定义：

- 公共动作保持 `XYZ + yaw + gripper_command`。
- `XYZ` 表示世界系 `right_gripper` 位置，单位为米；`yaw` 为世界 Z 轴角，单位为弧度。
- Backend 统一使用 `Rz(yaw) Rx(pi)`，固定局部 Z 轴向下，不由 expert 额外传入俯仰指令。
- 抓取代理参考点采用 URDF 命名指尖中点，相对 `right_gripper` 的局部偏移为 `+3.4 mm`；这不是经过真实夹持校准的接触模型。

该候选尚未替换共享 Backend。离线运动学解不代表动态执行成功：完整折叠末段仍出现关节解跳变；抓取段的 URDF 手指网格对地余量约 1 mm，不能据此认证实际 USD 碰撞或稳定性。v5 接触正控已验证，但发现双指触地 356 条事件；接触明细位置、法向和冲量均为零，不能解释为零接触力。机器人与附件组已有过滤，robot_block=0 不能证明无碰撞。

详见 [末端接口审查](DAY4_SQUARE_FRAME_AUDIT.md)、[离线运动学结果](day4-actionchunk-test/frame_audit/pose_audit.json) 和 [网格间隙检查](day4-actionchunk-test/frame_audit/clearance_audit.json)。

## 2026-11-02 交接记录

当时状态以 [2026-11-02 日报](2026-11-02-GarmentLab日报%20Stage4%20L2L3初态与6b交接.md) 为准：任务定义与表示层已冻结，表示层配对、分任务报告与任务 B 的冻结版 single 证据均已完成。第 7 步正式批次已**登记但未运行**：每档 20 个 held-out seeds（L1 4110–4129、L2 4210–4229、L3 4310–4329）与初态 plan/批次工具已就位，详见 [正式批次准备](STAGE4_FORMAL_BATCH_PLAN.md)。开跑前还差两件事：冻结正式成功判据阈值；决定是先跑 left 基线还是先解决 B 的释放后回弹。当前按 `b-right-dev-v1` 先做 right 的开发验证，批次保持暂停。

此前的 v5 短程保持/释放结论（位置误差 0.4733 mm、末臂速 0.00860 rad/s、锚点间隙 1.361 mm；双指触地 356 条事件、接触明细全零）仍是有效证据，但已被折叠开发例取代为“最新运行”。历史日报与旧脚本仅用于追溯，不作为当前运行入口。

详见 [11 月 2 日交接日报](2026-11-02-GarmentLab日报%20Stage4%20L2L3初态与6b交接.md)、[Stage 4 下一步](DAY4_NEXT_STEPS.md) 与 [v5 预登记](day4-actionchunk-test/SQUARE_GRASP_HOLD_V5.md)。后续下载由用户手动执行。

仓库是代码与精简证据归档，不是完整环境镜像。实验依赖 Isaac Sim 4.0、现有 GarmentLab/Backend 环境及对应文件清单；历史入口不代表当前应运行的实验。

## Stage 4 原验收计划（历史）

1. 得到完整释放、退让和静置后仍保持重叠的 L1 候选，并独立重复确认。
2. 将有效控制整合到正式 Backend，验证 `reset(seed, difficulty)`、episode 内重抓取及连续 10 次 reset/rollout；折叠与 recovery 合计不超过 12 个高层动作。
3. 固定 L1/L2/L3 初态协议和 seeds，每档保存 10 张可复现、肉眼可区分的初态截图，共 30 张。
4. 实现有明确触发与停止条件的 recovery：全局最多两次，但当前 7+5 动作模板在 12 步预算内仅能执行一次；在开发回合上冻结指标、测量时刻和阈值。
5. 正式批次每档至少取得 5 条成功 expert episodes，共至少 15 条。保留全部尝试、失败原因、动作/状态/视频，并报告 `rejection rate = 被拒绝的尝试数 / 总尝试数`。
6. 完成公共接口隔离检查及验收材料后，再进入 Stage 5 demonstrations 批量生成。

详细要求见 [最低完成计划](DAY4_MINIMUM_PLAN.md) 和 [十阶段执行计划](Marian_Frei_GarmentLab_2024_10_stage_execution_plan.md)。

## 仓库导航与数据范围

| 路径 | 内容 |
| --- | --- |
| `backends/`、`schemas/` | 共享 Backend 与动作/观测定义；实验候选不等于正式整合版本。 |
| `configs/`、`envs/` | 难度配置与接口；存在配置不代表三档已验收。 |
| `day4-actionchunk-test/` | Stage 4 实验脚本、依赖清单、离线审查及精简结果。 |
| `day4/upstream/` | 当前 GarmentLab 适配 patch 与部分源码快照。 |
| `runs/2026-10-13-third-grasp/` | Stage 2 历史图像、数组与日志证据。 |
| `docs/`、根目录日报 | 早期报告、假设与交接记录。 |

[2026-10-31 检查点说明](CHECKPOINT_20261031.md) 记录归档范围。Stage 4 原始视频、完整粒子数组、大型日志、环境和外部资产仍在本地及服务器，未随本次检查点全部上传。精简结果不能替代原始实验数据备份。离线审查使用的 SDK URDF/STL 网格也未打包；重跑审查需从对应安装版本取得。

## 后续研究安排

Stage 4 验收完成后，依次进行 demonstrations 与 dataset 构建、single-step BC、H=4 action-chunk BC、三档正式评估、结果分析与复现整理。当前不报告策略性能或折叠成功率结论。

## 上游与环境记录

本项目复用 [GarmentLab](https://github.com/GarmentLab/GarmentLab) 的场景、机器人、布料和控制组件，新增动作分块接口、实验控制与审查流程。当前适配快照的基线与覆盖范围见 [检查点说明](CHECKPOINT_20261031.md)；早期改动见 [AutoDL 适配 patch](third_party/autodl_adaptations.patch)。

更多背景：[环境记录](environment_log.md)、[Stage 2 报告](docs/2026-10-13_stage2_report.md)、[真机迁移假设](docs/sim2real_assumptions.md)。早期环境与硬件记录属于对应实验日期，不代表当前实例配置。


## 2026-11-02 b-right-dev-v1 开发复验与移交后审计完成

汇总器缺失结果分母修复与8项离线测试已通过；原项目代码与已测试副本SHA256一致（9a757d34…）。一次通过+一次无结果error的合成回归输出2次尝试、50%拒绝率；空批次保持null。

L2 4200的right single/arc4由本聊天在移交前完成；L3 4300采用另一聊天产出的最早外部single/arc4，按目录启动时间选择而非passed。两对均通过原版PAIRS_COMPARABLE，四份选定结果held gate通过、crossed=1.0，L2 IoU=0.559091、L3 IoU=0.562997；各对目标差及五项指标差值精确为0。底层21项代码不变，四份结果的独立23项变体manifest、配置和初态文件哈希均核对一致。

共下载核验66个远端文件，包含6份完整开发结果：选定4份配对结果与2份额外L3 single重复尝试。额外尝试原样保留，不增加独立seed覆盖，不计算正式成功率。用户移交后本聊天仅下载审计，未再提交GPU仿真，未终止已在途远端进程。

结论仅为每档一个开发seed在OPEN后30 release ticks+settle(180)终态保持；没有独立退让、第二retention样本或长期稳定性验证，不能外推整个开发集/held-out，更不能解释为BC策略或H=4性能提升。right为独立变体，不替换left失败或默认定义。held-out与正式批次保持暂停，正式Stage 4成功仍为0。

完整报告：[right开发复验与移交后审计](../thesis/day4-actionchunk-test/results/TASK_B_RIGHT_DEV_V1_20261102-183740/review.md)。

补充交叉核对（2026-11-02）：把主审计未采用的 4200 arc4 尝试 `025355-106410` 与 4300 single 重复尝试 `031535-711404` 一并核对，5 个目录 77 项检查全部通过；同 seed 全部 7 次已下载尝试（4200 三例、4300 四例）的 `final.npz` 441 个顶点逐位相同（max|Δ|=0），包括并发在途的 4200 arc4 两例。该核对不新增 seed、不改任何阈值、不改变上述结论。[补充审计](../thesis/day4-actionchunk-test/results/B_RIGHT_DEV_AUDIT_SUPPLEMENT_20261102/review.md)。

right 开发覆盖扩展 `b-right-dev-v2` 已登记、未运行：L2 4201–4209、L3 4301–4309 共 18 个剩余开发 seed，先登记初态哈希再跑 right single；不跑 arc4、不冻结阈值、held-out 不动。见 [扩展计划](STAGE4_B_RIGHT_DEV_V2_PLAN.md)。

## 2026-11-04 D2 释放顺序对照（暂停点）

D1-120 的 120 步延迟退让没有降低漂移（等待 2.0783/4.5603 mm、退让 2.4590/5.3214 mm、正式窗口 2.0409/4.4134 mm；与基线在相同 elapsed 时间点逐位相同），说明问题不在等待时长。D2-A/B 完成实际支撑、材质、释放时序和 contact-report 核查：支撑面只有 PhysX 默认材质；particle material 已绑定（friction 0.3、particleFrictionScale 0）；附件在 1944 断开而夹爪到 1954 才报告 open，释放一步速度跳至 17.42/11.04 mm/s；cloth-ground contact report 不支持，0 事件不是无接触。

D2-C 因此只改释放顺序：夹爪在附件仍启用时完成 10 步张开，再解除附件；抑制原 `ungrasp` 内第二次 `open()`。120 步等待、12 个公开动作/目标/命令/horizon 和退让目标保留；总物理步数与 D1 相同。preopen 10/10 步每步检查 holding/attachment 一致并调用 `control.assert_exclusive()`；全程 evidence 检查未关闭。D2-C 的 `released` sample 与最后 preopen state 同 step/time（delta=0），首个全关 state 为 +1 步。

D2-D 仅运行一次 4202 single `day4-a5-rc2-d2c-release-order-20261104-090032-412133`：退出码 0、episode `passed=True`、`DIAG_ASSESS complete=True`、`quality=rejected`、`absolute_step=2219`、等待 1955–2075、trace 331 步，与 D1 完全一致；无重试，下载证据与 ledger SHA256 一致。

| 对照项 | D1 | D2-C |
|---|---:|---:|
| 干预前 action target / EE / anchor 最大差 | — | **0.0** |
| release t=0 质心 / P95 / 最大差 | — | **0.0113 / 0.0293 / 0.0375 mm** |
| 释放一步粒子平均速度 | 17.4197 mm/s | 17.4223 mm/s |
| free 0–30 质心 / P95 | 1.9092 / 12.2286 mm | 1.9119 / 12.2044 mm |
| free 30–120 质心 / P95 | 1.4730 / 3.2355 mm | 1.4284 / 3.1499 mm |
| 正式窗口 210–330 质心 / P95 | 2.0409 / 4.4134 mm | 1.9823 / 4.3426 mm |
| quality | rejected | rejected |

**结论：** 正式窗口质心/P95 小幅下降 2.87%/1.60%，可以表述为“释放顺序改变降低了本例正式窗口漂移”；但释放一步速度、release transition 和 free 0–30 基本不变，**不能说是降低了释放冲量**，也不能把下降归因于释放冲量。释放顺序不是该例漂移的主要因素；仍超 1 mm / 3 mm，质量 rejected。正式 Stage 4 成功仍为 0；held-out 与正式批次暂停；恢复工作时优先核查附件约束释放能量/接触状态、支撑面材质和布料—地面接触观测，不继续微调开爪顺序，不直接提高摩擦或清零速度。

详见 [D2-D 对照](day4-actionchunk-test/results/D2_D_COMPARE_20261104/review.md)、[交接日报](2026-11-04-GarmentLab日报%20Stage4%20D2释放顺序对照交接.md) 与 [D2-C 版本](day4-actionchunk-test/a5-rc2-d2c-release-order/README.md)。
