# Garment Folding with Action Chunking

研究 single-step behavior cloning 与 H=4 action-chunk BC 在三档衣物初态下的折叠成功率、恢复能力和推理开销。当前工作集中在 GarmentLab / Isaac Sim 中建立可靠的 expert 和动作接口，尚未进入策略训练或正式对比实验。

> **当前状态：Day4 开发中，正式成功轨迹 0 条。** 流程正常结束、视频可解码或 `passed=True`，不等于折叠成功或 Day4 验收通过。

## 当前进度（2026-10-31）

| 工作项 | 状态与证据 |
| --- | --- |
| 仿真与动作接口 | 已有 `GarmentLabBackend`、动作/观测 schema、状态导出和视频记录；仍有待整合项。 |
| 物理配置与诊断 | 已完成配置读取、质量/迭代数对照及抓取、释放、控制诊断；历史结果和失败记录已保留。 |
| 原服装折叠 | 多次动作流程完成，但未得到已验收的释放后保持折叠；旧服装与被动载体探索分支已冻结。 |
| 单层方巾 L1 | 转向原计划范围内的 40 cm 单层方巾、单 Franka；441 顶点、800 三角形。先打通一个符合公共接口的 L1，再扩展三档。 |
| 最新姿态候选 | `SquarePoseBackend` 已准备并通过静态检查；抓取段离线 IK/FK 已检查，**尚未运行该候选的仿真**。 |
| 正式验收与学习 | 三档正式成功轨迹、Day5 demonstrations、BC 训练及正式评估均未完成。 |

当前进度以 [Day4 下一步](DAY4_NEXT_STEPS.md) 和 [验收记录](DAY4_ACCEPTANCE_TRACKER.md) 为准。历史日报和旧脚本用于追溯，不应作为当前运行入口。

## 当前阻塞与修正候选

此前方巾试跑先后在抓取距离检查和下降运动中失败，均未证明 L1 折叠成功。源码审查确认：共享 Backend 尚未使用动作中的 `yaw`，位置运动也未固定末端姿态；使用下降前姿态一次性换算抓取偏移，不能保证到达时对齐。

独立开发候选 [square_pose_backend.py](day4-actionchunk-test/square_pose_backend.py) 采用统一定义：

- 公共动作保持 `XYZ + yaw + gripper_command`。
- `XYZ` 表示世界系 `right_gripper` 位置，单位为米；`yaw` 为世界 Z 轴角，单位为弧度。
- Backend 统一使用 `Rz(yaw) Rx(pi)`，固定局部 Z 轴向下，不由 expert 额外传入俯仰指令。
- 抓取代理参考点采用 URDF 命名指尖中点，相对 `right_gripper` 的局部偏移为 `+3.4 mm`；这不是经过真实夹持校准的接触模型。

该候选尚未替换共享 Backend。离线运动学解不代表动态执行成功：完整折叠末段仍出现关节解跳变；抓取段的 URDF 手指网格对地余量约 1 mm，不能据此认证实际 USD 碰撞或稳定性。接触诊断的零事件记录尚无独立正控验证，不能解释为无碰撞。

详见 [末端接口审查](DAY4_SQUARE_FRAME_AUDIT.md)、[离线运动学结果](day4-actionchunk-test/frame_audit/pose_audit.json) 和 [网格间隙检查](day4-actionchunk-test/frame_audit/clearance_audit.json)。

## 下一次运行：短程抓取与释放

只验证 **approach → descend → CLOSE → OPEN**，包含抓住后的静止检查和释放检查；不执行完整折叠，不计入正式成功批次。

在已配置好的 AutoDL 实例中，确认 [文件清单](day4-actionchunk-test/square-grasp-pose-files.json) 列出的文件及该清单本身均放在 `/root/autodl-tmp/` 后运行：

```bash
bash /root/autodl-tmp/run-square-grasp-pose.sh
```

入口：[run-square-grasp-pose.sh](day4-actionchunk-test/run-square-grasp-pose.sh)。脚本先核验文件哈希，再启动仿真。依赖现有环境：

- Isaac Sim 4.0 与 `/root/autodl-tmp/envs/isaac40/bin/python`；
- 项目 Backend 位于 `/root/autodl-tmp/garmentlab-action-chunk-demo`；
- 已适配的 GarmentLab 位于 `/root/autodl-tmp/garmentlab_workspace/GarmentLab`。

仓库是代码与证据归档，**不是克隆后即可直接运行的完整环境镜像**。下载源码时须保持文件字节与清单一致，避免换行转换导致哈希失败。查看输出中的 `RESULT_FILE` 和 `DOWNLOAD_DIR`，保留完整结果目录，包括失败结果；审查实际位置、姿态、关节速度、附件及释放状态后，再决定是否接回 L1。

## Day4 剩余验收

1. 得到完整释放、退让和静置后仍保持重叠的 L1 候选，并独立重复确认。
2. 将有效控制整合到正式 Backend，验证 `reset(seed, difficulty)`、episode 内重抓取及连续 10 次 reset/rollout；折叠与 recovery 合计不超过 12 个高层动作。
3. 固定 L1/L2/L3 初态协议和 seeds，每档保存 10 张可复现、肉眼可区分的初态截图，共 30 张。
4. 实现每回合最多两次、有明确触发与停止条件的 recovery；在开发回合上冻结指标、测量时刻和阈值。
5. 正式批次每档至少取得 5 条成功 expert episodes，共至少 15 条。保留全部尝试、失败原因、动作/状态/视频，并报告 `rejection rate = 被拒绝的尝试数 / 总尝试数`。
6. 完成公共接口隔离检查及验收材料后，再进入 Day5 demonstrations 批量生成。

详细要求见 [最低完成计划](DAY4_MINIMUM_PLAN.md) 和 [十天执行计划](Marian_Frei_GarmentLab_2024_10_day_execution_plan.md)。

## 仓库导航与数据范围

| 路径 | 内容 |
| --- | --- |
| `backends/`、`schemas/` | 共享 Backend 与动作/观测定义；实验候选不等于正式整合版本。 |
| `configs/`、`envs/` | 难度配置与接口；存在配置不代表三档已验收。 |
| `day4-actionchunk-test/` | Day4 实验脚本、依赖清单、离线审查及精简结果。 |
| `day4/upstream/` | 当前 GarmentLab 适配 patch 与部分源码快照。 |
| `runs/2026-10-13-third-grasp/` | Day2 历史图像、数组与日志证据。 |
| `docs/`、根目录日报 | 早期报告、假设与交接记录。 |

[2026-10-31 检查点说明](CHECKPOINT_20261031.md) 记录归档范围。Day4 原始视频、完整粒子数组、大型日志、环境和外部资产仍在本地及服务器，未随本次检查点全部上传。精简结果不能替代原始实验数据备份。离线审查使用的 SDK URDF/STL 网格也未打包；重跑审查需从对应安装版本取得。

## 后续研究安排

Day4 验收完成后，依次进行 demonstrations 与 dataset 构建、single-step BC、H=4 action-chunk BC、三档正式评估、结果分析与复现整理。当前不报告策略性能或折叠成功率结论。

## 上游与环境记录

本项目复用 [GarmentLab](https://github.com/GarmentLab/GarmentLab) 的场景、机器人、布料和控制组件，新增动作分块接口、实验控制与审查流程。当前适配快照的基线与覆盖范围见 [检查点说明](CHECKPOINT_20261031.md)；早期改动见 [AutoDL 适配 patch](third_party/autodl_adaptations.patch)。

更多背景：[环境记录](environment_log.md)、[Day2 报告](docs/2026-10-13_day2_report.md)、[真机迁移假设](docs/sim2real_assumptions.md)。早期环境与硬件记录属于对应实验日期，不代表当前实例配置。
