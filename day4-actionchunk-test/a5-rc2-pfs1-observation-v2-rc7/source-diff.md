# 源码差异：a5-rc2-pfs1-observation-v2 → rc7 最终候选

本候选的文件集合与 v2 完全相同（63 项），其中 **60 项逐字节不变**，3 项变化：`a5_l1.py`（唯一物理改动 + 观测接入）、登记 JSON、编排 runner。

## 1. manifest 差异

| 类别 | 数量 | 文件 |
|---|---:|---|
| 相同 | 60 | `a5_recovery.py`、`a5_capture.py`、`pfs1_observation_v2.py`、`stage4_success_v1.py`、`a5_entry.py`、`a5_l1.py` 以外的全部源/资产 |
| 变化 | 3 | `a5_l1.py`；`a5-rc2-pfs1-observation-v2.json`；`run-a5-rc2-pfs1-observation-v2.sh` |
| 新增/删除 | 0 | 文件集合与 v2 相同 |

父 manifest `d97bf349…`；新 manifest `bcba8c11…`。

## 2. `a5_l1.py`（唯一物理改动 + 观测接入）

| 变化 | 内容 |
|---|---|
| 物理（已登记） | `fixed_material` 的 `particle_friction_scale` **0.0 → 1.0**；统一应用于 L1/L2/L3，4100 single/arc4 是 L1 回归检查 |
| 观测（只读） | `capture_material_object(..., 'after_construction')`；`record_material_stage` at `after_reset` / `after_initial_settle` / `pre_release`；`record_stage` at `initial_loaded` / `pre_release` |
| 未改 | 7 个公开动作、目标构造、`overhang=0.02`、held gate、release_window 调用、阈值、evaluator |

`bend_stiffness=100`、slot 选择、初始态加载与 settle 均未改。观测钩子只读状态并写 `material_readbacks.json` / `pfs1_stages` / `pfs1_stage_index.json`，不额外推进物理步、不改变控制。

## 3. `a5-rc2-pfs1-observation-v2.json`（登记）

- `revision=final-candidate-rc7-seven-case`、`final_candidate=true`；
- `physics_scope`：uniform 1.0、applies_to 三档、无 task-scoped override、L1 回归说明；
- 七例 `matrix`（槽位、seed、level、task、mode、actions、positive）；
- 四个 seed 的初态目录与哈希（不重生）；
- 停止规则、配对容差 1e-6、release gates；
- 该 JSON 不被仿真代码读取。

## 4. `run-a5-rc2-pfs1-observation-v2.sh`（编排）

- 七槽顺序执行；每槽 `a5_entry.py run` 一次；新批次账本 `a5-rc2-pfs1-observation-v2-rc7-runs`；
- 逐例 `audit_rc7_case.py`（原 RC evidence checks + v2 观测语义 + 可选配对）；
- 暂停/继续规则按登记：incomplete/执行错误/语义失败 → exit 3；质量拒绝但证据完整 → 记录并继续；配对超差 → exit 3；预检不符 → exit 4；
- 无自动重试；失败现场保留。

## 5. 未改动的运行语义

- `a5_recovery.py` 仍为 `particle_friction_scale=1.0`，12 动作、recovery/fold/release 逻辑与 v2/pfs1 相同；
- `a5_capture.py` 与 `pfs1_observation_v2.py` 未改；
- `a5_entry.py` 未改：`assess()` 的原 RC 采集检查与 `verify-dev` 逻辑/阈值保留，仅以新 manifest 身份运行；
- 4201 仍只登记 single；同 seed single/arc4 共用初态。
