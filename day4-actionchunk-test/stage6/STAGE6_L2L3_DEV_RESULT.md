# Stage 6 L1/L2/L3 最低开发验收

日期：2026-11-08。**状态：Stage 6 最低开发验收完成**（最低开发评估已执行；这不是 Stage 6 成功验收通过）。
本轮只运行 L2/L3 learned 各 5 例；未重训、未追加采集、未重跑 L1、未增加 random、未运行其他 seed、未自动 rollout。
**开发评估，不是独立 test 泛化结果；L2/L3 基于缩减数据，属探索性结果。**

## 1. 固定身份与初态清单

| 项 | 值 |
|---|---|
| checkpoint | `best_val.pt` epoch 498，`ade6013141cfa3b114fe6583602da4b14486b96d736ffe5bbfd104cc3e517208` |
| stats | `cbc4d711b2341b7ab786ca345ccb490bb32de1ebf93fb1eacc59de22d61a9ae9` |
| holding | 原始 0/1，identity normalization |
| L2/L3 runner | `562386ee…`（与 learned L1 相同） |
| L2/L3 budget | 12 / 12；未加专家动作、等待或补救控制 |

L2/L3 初态清单（运行前冻结，见
`<remote-root>/stage6_runs/evals/l2l3_dev_budget500_20261108/manifest.json`）：

- **L2 perturbed**：4210, 4211, 4212, 4213, 4214。最终清单**没有 perturbed val**，
  因此从 `passed=true`、`B_nominal`、有 strip records 的初态中按 seed 升序取。
- **L3 crumpled**：6504, 6507 为已有 final val 初态；再取 4310, 4311, 4312。
- **初态来源修正**：4210–4214、4310–4312 曾用于 Stage 4；本次**未用于 Stage 5 模型训练**，
  也不称“全新 held-out”。6504/6507 是已有 final val 初态。完整证据见
  `manifest.json` 的 `initial_source_note`。
- 未选 train；test seeds `6300, 6301, 6516, 6517` 保留；未选此前 L1/策略调试 seed。
- 全量 initial `result.json` / `initial_geometry.npz` 哈希、task、strips、strip_records
  均记录在 manifest；`initial passed=true` 仅表示初态生成有效，不是专家 rollout accepted。
- 无 seed 替换；无附件槽不兼容报告。

## 2. 接口与 settle/hold 差异

预检 `precheck.json` 通过：

- `grasp_events` 只在 not-engaged→engaged 增加；重复 CLOSE 只记 repeated，不增加 grasp；
- recovery 中间释放由实际 engaged→not-engaged 转换识别；终端要求实际 engaged 且
  L2/L3 `grasp_events >= 2`；不按专家标签计抓取；
- fold reference、terminal clock、331 帧评价、`physical_retreat_ok` 为实际判据；
  expert target equality 只单列，不作为成功门槛；
- 第一个 L2 4210 的初始化、观测、动作、结果和视频接口均正常，因此继续其余 9 例。

**已知差异**：专家 `a5_recovery.py` 在 recovery release 后执行 `_settle(240)` +
120-step recovery hold；当前 BC runner 只有初始 `_settle(30)`，未加入专家等待/补救。
本轮没有临时改变这一点。

## 3. L1/L2/L3 成功数

| 档 | learned accepted | random accepted |
|---|---:|---:|
| L1 flat | **2/5** | **0/5** |
| L2 perturbed | **0/5** | 未运行（本轮不增加 random） |
| L3 crumpled | **0/5** | 未运行 |
| **learned 合计** | **2/15** | — |
| **random 合计** | — | **0/5** |

## 4. 逐例结果

### L1 learned / random

| seed | learned status/class | learned actions | learned first failure | random status/class | random actions | random first failure |
|---:|---|---:|---|---|---:|---|
| 6120 | execution_error / prepared_region | 1 | bc_grasp_01 pred1 | execution_error / prepared_region | 1 | bc_grasp_01 pred1 |
| 6121 | execution_error / waypoint_timeout | 1 | bc_grasp_01 pred1 | execution_error / prepared_region | 2 | bc_grasp_01 pred2 |
| 6122 | **accepted** | 7 | — | execution_error / prepared_region | 1 | bc_grasp_01 pred1 |
| 6148 | rejected / physical (geometry) | 7 | —（7 动作完成） | execution_error / prepared_region | 5 | bc_grasp_01 pred5 |
| 6151 | **accepted** | 7 | — | execution_error / prepared_region | 1 | bc_grasp_01 pred1 |

L1 6121 的 CLOSE target 在 0.03 m 内（0.02732），但 grasp 执行超时，归为 waypoint timeout。

### L2 learned

| seed | status | class | actions | first failure |
|---:|---|---|---:|---|
| 4210 | execution_error | grasp_region_reject | 1 | bc_grasp_01 pred1 |
| 4211 | incomplete | terminal_held_check_failed | 12 | —（terminal held check，arm speed/position 不通过） |
| 4212 | execution_error | prepared_region_reject | 6 | bc_grasp_02 pred6 |
| 4213 | execution_error | prepared_region_reject | 1 | bc_grasp_01 pred1 |
| 4214 | execution_error | prepared_region_reject | 6 | bc_grasp_02 pred6 |

### L3 learned

| seed | status | class | actions | first failure |
|---:|---|---|---:|---|
| 6504 | execution_error | grasp_region_reject | 1 | bc_grasp_01 pred1 |
| 6507 | execution_error | grasp_region_reject | 1 | bc_grasp_01 pred1 |
| 4310 | execution_error | prepared_region_reject | 1 | bc_grasp_01 pred1 |
| 4311 | execution_error | prepared_region_reject | 1 | bc_grasp_01 pred1 |
| 4312 | execution_error | prepared_region_reject | 1 | bc_grasp_01 pred1 |

L2 4211 是唯一到达第 12 个动作并尝试 terminal OPEN 的 L2：2 次实际抓取、1 次 recovery
中间释放；terminal `held_check_ok=false`（arm speed `0.17365 rad/s`、position error
`0.01468 m`，tolerance `0.03 m`），因此没有启动 331 帧。

## 5. 完整窗口物理指标

- L1：6122/6151 accepted、6148 rejected 有完整 331 帧；指标见
  [STAGE6_L1_DEV_RESULT.md](STAGE6_L1_DEV_RESULT.md)。
- **L2/L3：10/10 都没有完整 331 帧窗口**，几何/稳定性指标记为**不可用**，不是 0。
  - 9 例在 recovery/fold CLOSE 前后被 prepared/selected-region 拒绝或 grasp 拒绝；
  - 4211 完成 12 个动作和 terminal OPEN，但 terminal held check 失败，未进入 331 帧。

## 6. 证据与视频

汇总：

- [L1 summary](stage6_l1_dev_20261108/summary.json)
- [L2/L3 summary](stage6_l2l3_dev_20261108/summary_l2l3.json)
- [combined summary](stage6_l2l3_dev_20261108/summary_all.json)
- [L2/L3 manifest](stage6_l2l3_dev_20261108/manifest.json)
- [L2/L3 precheck](stage6_l2l3_dev_20261108/precheck.json)

L1 视频（成功/失败）：

- [6122 accepted](stage6_l1_dev_20261108/videos/l1dev-learned-6122.mp4)、
  [6151 accepted](stage6_l1_dev_20261108/videos/l1dev-learned-6151.mp4)、
  [6148 completed/rejected](stage6_l1_dev_20261108/videos/l1dev-learned-6148.mp4)、
  [6120 failure](stage6_l1_dev_20261108/videos/l1dev-learned-6120.mp4)、
  [6121 timeout](stage6_l1_dev_20261108/videos/l1dev-learned-6121.mp4)

L2/L3 代表视频（全部无 accepted）：

- L2 [4211 terminal held check](stage6_l2l3_dev_20261108/videos/l2l3-perturbed-4211.mp4)、
  [4212 fold CLOSE prepared reject](stage6_l2l3_dev_20261108/videos/l2l3-perturbed-4212.mp4)、
  [4210 grasp region reject](stage6_l2l3_dev_20261108/videos/l2l3-perturbed-4210.mp4)
- L3 [6504 grasp region reject](stage6_l2l3_dev_20261108/videos/l2l3-crumpled-6504.mp4)、
  [4310 prepared-region reject](stage6_l2l3_dev_20261108/videos/l2l3-crumpled-4310.mp4)、
  [4312 prepared-region reject](stage6_l2l3_dev_20261108/videos/l2l3-crumpled-4312.mp4)

完整 10 个 L2/L3 结果与视频路径见 `summary_l2l3.json`；每个 result 下均有
`result.json`、`bc-verdict.json`、`failure.json`、`partial_trace.npz`、
`bc_observations.npz` 和 `evidence/episode.mp4`。

## 7. 原 Stage 6 最低条款逐条对照

| 原条款 | 状态 | 说明/剩余项 |
|---|---|---|
| 15 个 learned（L1/L2/L3 各 5）+ 5 个 L1 random | **已执行** | 15/15 learned、5/5 random，均一次；无重试 |
| 同初态、同预算、同 Backend/评价器/阈值 | **满足** | 7/12 预算；无 target/yaw/gripper 覆盖；无物理/阈值修改 |
| learned/random 使用相同规则 | **L1 满足** | random 仅 L1；L2/L3 未跑 random，本轮按要求不增加 |
| 成功 = geometry + hold，不用专家标签 | **已实现** | 仅 L1 2/5 accepted；L2/L3 0/5，且无完整窗口 |
| 保存逐例结果/视频/失败原因 | **满足** | 结果、partial trace、视频、manifest/预检均保存 |
| 区分入口跑通与 Stage 6 验收 | **满足** | 入口正常不等于通过；L2/L3 0/5，Stage 6 未通过 |
| L2/L3 缩减数据、探索性 | **已标注** | 不作为独立 test，不作统计显著性声明 |
| 专家 settle(240)+hold(120) 对齐 | **未满足/已知差异** | runner 仅 initial settle(30)；本轮未临时加入等待或补救控制 |

**状态**：**Stage 6 最低开发验收完成**（最低开发评估已执行；成功验收未达成）。
Stage 6 的入口/证据/固定评估链路已经跑通并完成 15 learned + 5 random；
但 learned 总计 2/15、random 0/5，L2/L3 均 0/5 且没有完整 331 帧物理指标。
L2/L3 失败不能单独归因于数据量：prepared/grasp region 拒绝、4211 terminal held
check 失败，以及 runner 与专家 settle/hold 的差异都是并列的具体剩余项。
本轮不自行追加采集、训练或仿真任务。
