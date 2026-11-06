# Stage 5 观测字段核对（采集入口准备，2026-11-06）

**状态：准备阶段；未启动批量采集。** 依据：`Marian_Frei_GarmentLab_2024_10_stage_execution_plan.md` Stage 5 字段清单（timestamp、rgb、depth、garment_keypoints、end_effector_pose、gripper_state、task_phase、action、success）。

## 1. 字段对照（冻结候选单 episode 产物）

| Stage 5 字段 | 现有产物 / 位置 | 状态 |
|---|---|---|
| timestamp | `evidence/timeline.jsonl` 每条含 `sim_time_s`、`backend_step`；`success_trace.npz.steps`（0..330，dt=1/60） | **有**，可导出 |
| rgb | `evidence/episode.mp4`（编码视频）；无逐帧 RGB 数组 | **部分**（需抽帧；计划允许可选） |
| depth | 无 | **缺失**（计划为可选） |
| garment_keypoints | 动作边界 `00_initial.npz`、`01_approach.npz`、…；`pfs1_stages/`（initial_loaded / after_recovery / pre_release / release_boundary）；`success_trace.npz.vertices`（331 帧，释放后窗口） | **稀疏**：只有动作边界与释放后 331 帧，**无全 episode 逐帧布料状态** |
| end_effector_pose | `timeline.jsonl` 每条 `ee_m`；`result.json.actions[].ee` | **有** |
| gripper_state | `timeline.jsonl` 的 `holding / attached / enabled_slots / command_holding`；`success_trace.npz.gripper_open` | **有**（布尔；张开量需从关节位置推） |
| task_phase | `result.json.action_labels`、`timeline.jsonl` 的 `action_begin/end`；需映射到计划 phase 枚举 | **可推导**（需登记映射表） |
| action | `result.json.actions[].target_pose/command`；`timeline.jsonl.action_begin.targets/commands` | **有** |
| success | `a5-verdict.json.status`、`result.json.passed` | **有** |

## 2. 关键缺口

1. **无全 episode 逐帧布料观测**：现有记录是为评价设计的（动作边界快照 + 释放后 331 帧）。BC/ACT 数据集需要每一步的 observation（关键点/EE/夹爪/phase）。两个选项：
   - **(a) 被动逐帧 overlay（推荐）**：复用 `pfs1_observation_v2.snapshot()`（记录 vertices、速度、EE、关节、夹爪开合、attachment；不 step、不控制），在 Stage 5 runner 上按步调用；先用 1 个 accepted seed 验证“overlay 不改变物理/动作/评价”，再批量。该 overlay 属观测代码，不改冻结候选的控制/物理；需另行登记。
   - (b) 接受稀疏数据（每 episode 约 12 个动作边界点）——不足以训练 BC，不推荐。
2. **无 depth**；RGB 只有 mp4，需要抽帧或改为直接保存低分辨率帧。按计划属可选，需明确取舍。
3. **seed 池不足**：每档预登记 held-out seed 只有 20 个（4110–4129 / 4210–4229 / 4310–4319），而 Stage 5 目标为每档 50 条成功。需要新增“演示 seed 池”（不进入 Stage 4 验收统计），或降低目标并说明。
4. **phase 映射未登记**：`action_labels`（approach/close/arc45/arc90/arc135/place/release/recovery_*）到 `TaskPhase` 枚举的映射需要固定成表。

## 3. 采集入口（最小）

`collect_demos.py`：复用 `adapter_run.py → a5_entry.py run`，每个 episode 独立进程、单卡串行；只把 `a5-verdict.status == accepted` 的 episode 写入 `demonstrations.jsonl`；全部尝试写入 `attempts.jsonl`；按 seed 记录切分。**本轮只准备入口，不启动。**

## 4. 启动前需要确认的决定

| # | 决定 | 选项 |
|---|---|---|
| 1 | 逐帧观测 overlay | 启用（推荐） / 不启用（数据稀疏） |
| 2 | 演示 seed 池 | 新增演示 seed（推荐） / 仅用现有 20/档（成功数可能不足 50） |
| 3 | RGB-D | 仅 mp4 抽帧 / 加低分辨率帧保存 / 不要 |
| 4 | phase 映射 | 采用建议映射表（需登记） |
| 5 | 单卡并发 | 串行（推荐） |

以上确认后才启动批量采集。
