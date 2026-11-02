# Garment Folding with Action Chunking

研究 single-step behavior cloning 与 H=4 action-chunk BC 在三档衣物初态下的折叠成功率、恢复能力和推理开销。当前工作集中在 GarmentLab / Isaac Sim 中建立可靠的 expert 和动作接口，尚未进入策略训练或正式对比实验。

> **当前状态：Stage 4 开发中，正式成功轨迹 0 条。** 流程正常结束、视频可解码或 `passed=True`，不等于折叠成功或 Stage 4 验收通过。

## 当前进度（2026-10-31）

| 工作项 | 状态与证据 |
| --- | --- |
| 仿真与动作接口 | 已有 `GarmentLabBackend`、动作/观测 schema、状态导出和视频记录；仍有待整合项。 |
| 物理配置与诊断 | 已完成配置读取、质量/迭代数对照及抓取、释放、控制诊断；历史结果和失败记录已保留。 |
| 原服装折叠 | 多次动作流程完成，但未得到已验收的释放后保持折叠；旧服装与被动载体探索分支已冻结。 |
| 单层方巾 L1 | 转向原计划范围内的 40 cm 单层方巾、单 Franka；441 顶点、800 三角形。先打通一个符合公共接口的 L1，再扩展三档。 |
| 最新短程验证 | v5 保持/释放与接触正控通过；双指触地证据及接触明细全零仍需审查。不是 L1 折叠成功。 |
| 初态与离线工具 | L1 开发初态 10/10，L2/L3 各 0/10；接口预算、评价及尝试记录工具已有离线版本，尚未完成正式整合。 |
| 正式验收与学习 | 三档正式成功轨迹、Stage 5 demonstrations、BC 训练及正式评估均未完成。 |

当前进度以 [Stage 4 下一步](DAY4_NEXT_STEPS.md) 和 [验收记录](DAY4_ACCEPTANCE_TRACKER.md) 为准。历史日报和旧脚本用于追溯，不应作为当前运行入口。

## 当前阻塞与修正候选

此前方巾试跑先后在抓取距离检查和下降运动中失败，均未证明 L1 折叠成功。源码审查确认：共享 Backend 尚未使用动作中的 `yaw`，位置运动也未固定末端姿态；使用下降前姿态一次性换算抓取偏移，不能保证到达时对齐。

独立开发候选 [square_pose_backend.py](day4-actionchunk-test/square_pose_backend.py) 采用统一定义：

- 公共动作保持 `XYZ + yaw + gripper_command`。
- `XYZ` 表示世界系 `right_gripper` 位置，单位为米；`yaw` 为世界 Z 轴角，单位为弧度。
- Backend 统一使用 `Rz(yaw) Rx(pi)`，固定局部 Z 轴向下，不由 expert 额外传入俯仰指令。
- 抓取代理参考点采用 URDF 命名指尖中点，相对 `right_gripper` 的局部偏移为 `+3.4 mm`；这不是经过真实夹持校准的接触模型。

该候选尚未替换共享 Backend。离线运动学解不代表动态执行成功：完整折叠末段仍出现关节解跳变；抓取段的 URDF 手指网格对地余量约 1 mm，不能据此认证实际 USD 碰撞或稳定性。v5 接触正控已验证，但发现双指触地 356 条事件；接触明细位置、法向和冲量均为零，不能解释为零接触力。机器人与附件组已有过滤，robot_block=0 不能证明无碰撞。

详见 [末端接口审查](DAY4_SQUARE_FRAME_AUDIT.md)、[离线运动学结果](day4-actionchunk-test/frame_audit/pose_audit.json) 和 [网格间隙检查](day4-actionchunk-test/frame_audit/clearance_audit.json)。

## 最新交接与下一步

最新 v5 运行 `day4-square-grasp-hold-v5-20261031-113930-047613` 的短程保持/释放通过：位置误差 0.4733 mm、末臂速 0.00860 rad/s、锚点间隙 1.361 mm；事件和辅助块净力正控有效。首次 v5 因 `KeyError('attachment_bodies')` 失败，两个结果均保留。

目前停工，不自动启动实验。下次先核对抓取坐标偏移、手指碰撞几何、地面间隙及辅助块实际/目标高度，再决定修正与短程复验；随后解决完整 L1 末段路径连续性。旧服装、翻腕和参数扫描分支冻结。

详见 [最新交接日报](2026-10-31-GarmentLab日报%20Day4%20v5保持与接触审查交接.md) 和 [v5 预登记](day4-actionchunk-test/SQUARE_GRASP_HOLD_V5.md)。后续下载由用户手动执行。

仓库是代码与精简证据归档，不是完整环境镜像。实验依赖 Isaac Sim 4.0、现有 GarmentLab/Backend 环境及对应文件清单；历史入口不代表当前应运行的实验。

## Stage 4 剩余验收

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

更多背景：[环境记录](environment_log.md)、[Stage 2 报告](docs/2026-10-13_day2_report.md)、[真机迁移假设](docs/sim2real_assumptions.md)。早期环境与硬件记录属于对应实验日期，不代表当前实例配置。
