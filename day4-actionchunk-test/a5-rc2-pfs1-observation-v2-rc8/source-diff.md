# 源码差异：rc7 → rc8（task-scoped 修正）

文件集合与 v2 相同（63 项）。相对 v2 **59 项逐字节不变**；相对 rc7 有 4 项变化，其中只有 `a5_l1.py` 含物理改动。

| 文件 | 相对 rc7 的变化 | 角色 |
|---|---|---|
| `a5_l1.py` | `particle_friction_scale` **1.0 → 0.0**；4 处材料读回传 `expected_scale=0.0` | L1 任务物理 + 观测 |
| `pfs1_observation_v2.py` | `capture_material_object` / `record_material_stage` 增加 `expected_scale` 参数；`_load_material` 按任务写 `expected`；默认仍 1.0 | 观测 |
| `a5-rc2-pfs1-observation-v2.json` | task-scoped 协议、路由、矩阵、报告口径 | 登记（不被仿真代码读取） |
| `run-a5-rc2-pfs1-observation-v2.sh` | rc8 编排、预检、账本、audit_rc8 | 编排 |

## 物理协议

- 路由键：任务身份（flat=0.0，perturbed/crumpled=1.0）；不读取 seed、模式或运行结果。
- 设置时机：`fixed_material` 在材料构造时写入 `particle_friction_scale`，早于 backend reset 与任何物理步。
- L1 与 L2/L3 的 `a5_recovery.py` 均未改；`a5_capture.py`、`a5_entry.py`、`stage4_success_v1.py`、资产与 evaluator 配置未改。

## 观测

- 材料五阶段读回仍逐阶段检查；`expected` 块现在记录任务的期望值（L1 0.0，L2/L3 1.0）。
- 不匹配仍在 `after_reset` / `after_initial_settle` / `after_recovery` / `pre_release` 停止。
- 速度、contact 能力、证据 manifest 语义与 rc7/v2 相同。

## 未改

- 7/12 公开动作、命令、horizon、目标构造、held gate、release_window、阈值、evaluator；
- 初态登记与哈希（不重生）；
- 4201 仅 single；同 seed single/arc4 共用初态。
