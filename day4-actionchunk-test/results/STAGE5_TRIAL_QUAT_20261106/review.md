# Stage 5 EE 姿态字段验证（4201，2026-11-06）

**用途：仅验证新增 `ee_quat_wxyz` 字段与对齐；不进入演示集。** 4201 是已登记 dev seed（perturbed），原评价器为 **rejected**（已知案例），因此该轨迹只作字段验证。

## 1. 运行

| 项 | 值 |
|---|---|
| seed / 档 | 4201 / perturbed |
| 初态 | `<remote-root>/day4-square-initial-stripfold-20261105-014825-318974`（`stage4-initial-v2-task-scoped`，pfs 1.0） |
| 结果目录 | `day4-a5-rc2-pfs1-observation-v2-20261107-010753-512313` |
| 评价器 | `a5-verdict.status=rejected`、`runner_exit=0`、`result.json.passed=true`（runner 门槛通过，质量拒绝） |
| 重试 | 无 |

## 2. 字段与对齐

| 检查 | 结果 |
|---|---|
| 观测 / 动作 | 12 / 12 |
| `vertices` | (441,3) |
| `ee_position` | (3,) |
| `ee_quat_wxyz` | (4,)，单位范数 |
| `joints` | 9 |
| target 最大差 | 1.04e-8 |
| command 差 | 0 |
| phase 未识别 | 无 |

## 3. 样本

- single-step：12 条；`obs_quat (12,4)`、`obs_vertices (12,441,3)`、`obs_ee (12,3)`、`action (12,5)`。
- H=4：3 个完整块（12/4，无尾部）；每块仅用起始观测；`split=val`（按 seed 哈希）。

## 4. 结论

动作前快照的 EE 完整位姿（位置 + wxyz 四元数）可用，与动作逐条对齐；后续演示采集沿用该字段，命名 `ee_position` / `ee_quat_wxyz`。动作标签中的 yaw 仅作监督信号，不替代观测朝向。

## 5. 产物

- 本地：`day4-actionchunk-test/results/STAGE5_TRIAL_QUAT_20261106/`（`obs-4201/`、结果目录、`export/export_summary.json`、`single_step.npz`、`h4.npz`、`h4_audit.npz`）
- 服务器：`<remote-root>/stage5-trial/obs-4201/`、`state-4201/`
