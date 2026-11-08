# 6120 CLOSE 误差离线定位（2026-11-08）

本轮只做离线定位：不启动仿真、不重训、不重跑 6120、不运行其余 19 例。

## 1. 身份与结论保持

| 项 | 值 |
|---|---|
| 首例 run | `6120-single-20261108-175431` |
| 实际运行 runner | `ae024ea41963837b98c5c73a0db120fb67731330d1584f7e9eb2d0057f3f7448` |
| 首例后证据/日志修订 | `22b8dc503b1c023215c427d039125ee713237faba4131de92695a424efd73882` |
| 终端判据修订 | `562386eec41826c818febbf930c7107f39b9d2ebafcc92de4b45be76c5205a7d` |
| 原始 verdict | `execution_error` / `close_target_outside_prepared_region`，未改写 |
| accepted/rejected | 不适用；无完整 331 帧评价窗口，折叠指标不可用 |
| 自动重试 | 无 |

首例 `result.json` / `bc-verdict.json` / `failure.json` 的哈希保持不变：
`4dec448a…` / `4eae016f…` / `163d8116…`。完整登记见
`STAGE6_RUN_IDENTITY.json`。

## 2. 专家观测 vs 闭环观测（真实 torch）

同一 checkpoint `5bff9e67…`、stats `8f1788d1…`、BCPolicy、torch 2.2.2+cu121。

### A. 专家 action_002 执行前观测 → BCPolicy

输入：6120 `action_002_obs.npz` / `.json`，1340 维，finite，holding=false。

输出：`xyz=[-0.1316609413, -0.4452133263, 0.0388517239]`，
`yaw=0.1131916113`，`command=1`。

专家 action_002 标签：`[-0.1900197715, -0.4488316178, 0.0133000202]`，
`yaw=0.0859541968`，command 1。

误差：XYZ L2 **0.063810 m**；yaw 0.027237 rad；gripper 正确。
到实际 prepared region（left_210）距离 **0.065246 m**，大于 Backend 阈值 0.03。

### B. 本次 rollout 第二次预测（闭环观测）→ 已有真实输出

B 的完整 1340 维输入**未保存**：`bc_observations.npz` 缺失；StepHook 只有
vertices/EE/quat/holding，**没有 9 维 joints**；因此没有重算 B，也不拿专家
joints 补。B 的 prediction 直接取首例 `runner.log` 的真实 BCPolicy 输出：

`xyz=[-0.1320276446, -0.4420829843, 0.0376174162]`，
`yaw=0.1135668123`，`command=1`。

误差：XYZ L2 **0.063245 m**；yaw 0.027613 rad；gripper 正确。
到实际 prepared region 距离 **0.064629 m**。

### C. 对照表

| 项 | 专家观测 A | 闭环观测 B（实际 rollout 输出） |
|---|---|---|
| xyz | `[-0.131661, -0.445213, 0.038852]` | `[-0.132028, -0.442083, 0.037617]` |
| yaw | 0.113192 | 0.113567 |
| command | 1 | 1 |
| vs 专家 XYZ L2 | **0.063810 m** | **0.063245 m** |
| vs 专家 yaw | 0.027237 rad | 0.027613 rad |
| nearest region | left_210，0.065246 m | left_210，0.064629 m |
| within 0.03 m | 否 | 否 |

两者预测几乎相同（差约 3.1 mm / 0.0004 rad），说明 **CLOSE 误差不是闭环执行后
观测漂移造成的**；模型在专家观测上就已经错。

### D. 输入差异 A2 vs B（B 为 StepHook 事后部分重建）

StepHook 在 `absolute_step=360`、`sim_time_s=6.0000003129` 的帧与
`BC_OBS 1` 完全对应；标记 `posthoc_reconstructed=true`。比较：

| 字段 | 差异 |
|---|---|
| vertices | mean L2 `7.5e-11 m`；max `1.5e-8 m` |
| EE | L2 `0.014435 m`；Δ=`[+0.008239, +0.011725, +0.001740] m` |
| quat（wxyz） | sign-invariant L2 `0.007982`；angle `0.015964 rad` |
| joints | **不可比**：StepHook 无 joint_positions，且 `bc_observations.npz` 缺失 |
| holding | A=false，B=false，相同 |
| full 1340 | **不可恢复** |

所以 B 的完整 1340 维输入无法重建；只能确认 vertices 几乎不变、EE 差 1.44 cm、
quat 差 0.016 rad。没有用专家 joints 补、没有追加仿真数据。

### E. action_001 一致性

用真实 torch 再算 6120 保存的专家 action_001 观测，输出
`[-0.1801185907, -0.4375714555, 0.1616588295]`，yaw `0.0746104539`，
gripper 0；与首例 action 0 的 `target_pose`/policy target 逐值一致
（`target_match=true, yaw_match=true, gripper_match=true`）。

## 3. 误差定位：拟合 / 字段顺序 / 归一化 / 标签对齐

### 3.1 holding 通道是常量零（具体数据缺陷）

- 数据集 `dataset_single.npz` 全部 590 条 `obs_holding == 0.0`；
  command 0/1/2 分别 180/90/320 条，holding true 均为 0。
- 6120 的 7 个 `action_00k_obs.json` 全部 `"holding": false`。
- stats：holding mean=0，std=`1e-6`。

源码定位：

- `stage5_collect/trial/sitecustomize.py` 第 107-110 行：
  `'holding': bool(row.get('holding'))`；
- `episode_evidence.py` 第 113-120 行：`execute()` 的 `action_begin`
  只传 `targets`、`commands`、`horizon`，**没有 holding**；
  `emit` 也不补 holding；因此 `row.get('holding')` 为 None → false。

后果：训练集 holding 始终 0；推理时真实的 holding=1 经 stats 归一化为
`(1-0)/1e-6 = 1e6`，是灾难性 OOD 输入。首例在 CLOSE 前 holding=false，
CLOSE 本身已因模型拟合差失败；即使 CLOSE 成功，后续 post-grasp 输入也不可用。
这是 Stage 5 观测管线的具体缺陷，**不是 Stage 6 runner 引入的**。

### 3.2 标签对齐：正常

6120 的 7 条 dataset action 与保存的 `action_00k_obs.json` targets/commands
**全部一致**；dataset obs 与保存 obs 的 vertices/EE/quat/joints 最大绝对差
均为 **0.0**。action #2（GRASP）标签就是
`[-0.19001977, -0.44883162, 0.01330002, 0.0859542]`，command 1。
没有标签错位、没有动作/观测错配。

### 3.3 字段顺序：正常（仅 float32/float64 cast）

`BCPolicy.build_obs` 与 `train_bc.obs_matrix` 对 6120 全部 7 行：
- 各段 vertices/ee/quat/joints/holding 均 `allclose(1e-6)=true`；
- 最大绝对差 `2.95e-8`；
- exact array equal=false 仅因为 `build_obs` 输出 float32、`obs_matrix` 为
  float64；不是字段顺序错。

### 3.4 归一化：无 gross 异常

6120 action_002 观测的 z-score：
vertices max |z| 1.00；EE 1.35；quat 0.37；joints 1.50；holding 0。
没有极端值；归一化不是这次 CLOSE 误差的主因（holding 的 std=1e-6 是上述
常量零缺陷的后果）。

### 3.5 拟合：CLOSE 在训练集上就明显欠拟合

对 dataset 全部 command=1（CLOSE）样本运行同一 BCPolicy：

| split | n | mean XYZ L2 | median | p95 | max |
|---|---:|---:|---:|---:|---:|
| train | 59 | **0.100732 m** | 0.085605 | 0.224614 | 0.238022 |
| val | 14 | **0.134008 m** | 0.128050 | 0.264899 | 0.307592 |
| test | 17 | **0.112092 m** | 0.083527 | 0.257937 | 0.338421 |

6120 的 CLOSE 误差 0.063810 m，甚至小于 train CLOSE 均值；不是 6120 单例异常，
而是模型对 CLOSE 的普遍拟合失败。top-level test 3 cm 指标掩盖了按 command
分组的 10–13 cm CLOSE 误差。

### 3.6 结论

- **专家观测上也有明显 CLOSE 误差**（6.38 cm），不是闭环观测漂移；
  B 的预测只比 A 差/好约 0.5 mm。
- 标签对齐、字段顺序、数值归一化均未发现错误；**holding 恒零**是确定的数据
  管线缺陷，且模型在训练集 CLOSE 上就欠拟合（均值 10.1 cm）。
- 因此优先方向是 **Stage 5 观测 holding 修复 + CLOSE 拟合/训练目标复查**，
  不是 Stage 6 闭环执行或 prepared-region 阈值。
- 不能唯一归因到单一机制；可以说“数据缺陷 + CLOSE 欠拟合”均有直接证据，
  但具体因果链（holding 常量零导致多少 CLOSE 误差）不能由本轮单独量化。

## 4. 仍缺字段/证据

- 首例 `bc_observations.npz` 缺失：B 的完整 1340 维观测无法复原；
- StepHook 无 `joint_positions`：9 维 joints 无法比较；
- 首例 `partial_trace.npz` 缺失（已在当前代码修复，未重跑）；
- 首例 `finished.json` 已重建，原文件保留；
- 无 331 帧评价窗口，折叠指标不可用。

## 5. 下一步最小动作

1. 先修 Stage 5 观测管线：`sitecustomize._snap` 改为从
   `evidence.state()`/`b._holding` 读取真实 holding（或让 `action_begin`
   携带 holding），只重导出观测，不改物理/动作。
2. 用同一 70 条演示重新生成 stats 与 CLOSE 标签检查；确认训练集
   `obs_holding` 不再恒零、holding std 不再 1e-6。
3. 在不重训的前提下先离线评估现有 checkpoint 对修正后观测的 CLOSE 误差；
   若仍 10 cm 级，再决定是否重训（本轮不重训）。
4. 修好观测/模型前，不重跑 6120、不跑其余 19 例；不要用调阈值或 target 裁剪
   掩盖策略误差。
