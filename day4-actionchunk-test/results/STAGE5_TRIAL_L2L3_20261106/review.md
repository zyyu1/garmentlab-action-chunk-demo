# Stage 5 L2/L3 最小采集试跑报告（2026-11-06）

**结论：两档试跑均通过。** L2 4202 与 L3 4302 各 single 一次、原评价器 accepted；每条轨迹 12 个公开动作均有执行前只读观测，call_id/target/command/phase 全部对齐；每条轨迹导出 single-step 12 条、H=4 3 个完整块（12/4，无尾部）。未启动批量采集或训练。

## 1. 试跑 seed 与初态

| 档 | seed | 初态目录 | 协议 | 关键校验 |
|---|---|---|---|---|
| L2 perturbed | **4202** | `day4-square-initial-stripfold-20261105-015817-115841` | `stage4-initial-v2-task-scoped`，`B_nominal`/perturbed，pfs 1.0/1.0 | `result.json` `1eef6c83…`、`initial_geometry.npz` `13b56808…`；dev 注册一致 |
| L3 crumpled | **4302** | `day4-square-initial-stripfold-20261105-020706-026048` | 同上，`B_nominal`/crumpled，pfs 1.0/1.0 | `result.json` `6a06021d…`、`initial_geometry.npz` `bc085359…`；dev 注册一致 |

两者均为 dev seed，**不属于 Stage 4 验收 seed 集**（4210–4229 / 4310–4329）。

**运行中的一个登记错误（已定位，未消耗 episode）：** 首次 L2/L3 合并配置里 4302 初态路径误写为 `20261106-020706-026048`（实际是 `20261105-…`），collector 记 `missing_initial`、未启动 L3；修正后用独立配置重跑 L3 一次。L2 未受影响。

## 2. 预检与运行

| 步骤 | 结果 |
|---|---|
| preflight（合并配置） | exit 0；gate `A5_GATE_OK_SOURCE 7`、manifest `40858efc…` |
| plan-only（合并配置） | flat 0、perturbed 1、crumpled 1（共 2 个 single） |
| L2 运行 | `--config trial/stage5_config_l2l3.json --run`；4202 accepted；结果目录 `day4-a5-rc2-pfs1-observation-v2-20261107-003043-007245`；entry_exit 0 |
| L3 运行 | 修正后 `--config trial/stage5_config_4302.json --run`；4302 accepted；结果目录 `day4-a5-rc2-pfs1-observation-v2-20261107-004441-518050`；entry_exit 0 |
| 重试 | 无（L3 首次是登记路径错误，未起 episode） |

## 3. 观测与配对

| 检查 | L2 4202 | L3 4302 |
|---|---|---|
| 观测数 / 动作数 | 12 / 12 | 12 / 12 |
| call_id | 1..12 连续 | 1..12 连续 |
| vertices | (441,3) 全部 | (441,3) 全部 |
| EE | (3,) 全部 | (3,) 全部 |
| joints | 9 | 9 |
| target 最大差 | 1.44e-8 | 1.37e-8 |
| command 最大差 | 0 | 0 |
| phase 未识别标签 | 无 | 无 |

动作序列：`rec_approach, rec_pick, rec_lift, rec_spread, rec_release, fold_approach, fold_close, fold_arc45, fold_arc90, fold_arc135, fold_place, release_retreat`；前 5 个为 recovery（phase=RECOVERY），后 7 个为 fold + release。

## 4. 字段口径（模型输入 vs 元数据）

| 字段 | 来源 | 用途 |
|---|---|---|
| `vertices` (441×3, 世界坐标) | 动作前快照 | **模型输入**（状态真值；计划允许 oracle_keypoints） |
| `ee` (3) | 动作前快照 | **模型输入**（末端位置；**不含显式 yaw/四元数**） |
| `joints` (9) | 动作前快照 | **模型输入**（含两指，可推夹爪开合） |
| `holding` | 动作前快照 | **模型输入**（抓取状态 bool） |
| `action` `[x,y,z,yaw,cmd]` | `action_begin` targets/commands | **监督标签**（yaw 在动作里必需） |
| `phase` | phase_map 映射 | **元数据**（计划暂作元数据，不入训练目标） |
| timestamp / call_id / seed / level / success | 快照与评价器 | **元数据/审计** |

**yaw 口径：** 动作标签必须含 yaw（目标位姿第 4 维）；**观测当前只有 EE 位置，没有 EE 姿态**——若策略需要显式末端朝向，应在快照中补四元数（属后续登记项，本轮未加）。

## 5. 样本导出（同一 episode 内，无跨 episode）

| 轨迹 | single-step | H=4 完整块 | 尾部 | 备注 |
|---|---:|---:|---|---|
| 4202 | **12** | **3**（12/4） | 0 | 每块仅用起始动作前观测；动作 2–4 的观测仅存审计 |
| 4302 | **12** | **3**（12/4） | 0 | 同上 |

形状：single `vertices (12,441,3)`、`ee (12,3)`、`joints (12,9)`、`action (12,5)`、`phase (12,)`；H=4 `obs_vertices_start (3,441,3)`、`action (3,4,5)`、`mask (3,4)`；审计 `h4_audit.npz` 保留每块 4 个观测，不作为输入。

## 6. 证据路径

- 本地：`day4-actionchunk-test/results/STAGE5_TRIAL_L2L3_20261106/`
  - [L2 导出](export_4202/export_summary.json)、[L3 导出](export_4302/export_summary.json)
  - 结果目录（各含 result.json、success_trace.npz、evidence/）、obs 目录、state（attempts/demonstrations）
- 服务器：`/root/autodl-tmp/stage5-trial/`（`obs-l2l3/`、`obs-4302/`、`state-l2l3/`、`state-4302/`）
- 试跑账本：`state-l2l3/attempts.jsonl`（4202 started+accepted；4302 首次 missing_initial）、`state-4302/attempts.jsonl`（4302 started+accepted）

## 7. 结论与边界

- L2/L3 均 accepted，采集证据完整，12/12 对齐，样本可构造；试跑轨迹与正式演示集分开计数（本报告不计入正式演示集）。
- 未验证：尾部 H=4 补齐（本轮 12/4 无尾部）；EE 姿态字段；RGB-D；更长 episode。
- 批量采集未启动；正式 seed 池、每档 50 条目标、并发度待登记后再开。
