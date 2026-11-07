# Stage 5 最小采集试跑报告（2026-11-06）

**结论：试跑通过。** seed 4100 single 一次，原评价器 `accepted`；每个公开动作前均有只读观测，7/7 对齐；同一条轨迹成功构造 single-step（7 条）与 H=4（1 个完整块 + 尾部 3 动作按 mask 补齐）样本。未启动批量采集或训练。

## 1. 身份与授权

| 项 | 值 |
|---|---|
| seed / 档 | **4100 / flat**（dev seed，不属于验收 seed 集 4110–4129 / 4210–4229 / 4310–4329） |
| 初态 | `/root/autodl-tmp/day4-square-initial-20261105-014501-526555`；协议 `stage4-initial-v2-task-scoped`；`result.json` `df9ed582…`、`initial_geometry.npz` `dd578303…` |
| 授权路径 | `split=dev`（`a5_entry.authorize_initial` 校验 dev 注册与文件哈希） |
| 冻结候选 | manifest `40858efc1a5840ab2bf51e025f823382e8586bc037fbe41bf1d1de5b21dee86a`；gate `A5_GATE_OK_SOURCE 7` |
| 采集入口 | `stage5_collect/collect_demos.py` + `trial_adapter.py`（`adapter_run.py` 的 `STAGE5_APP` 覆盖）+ 只读 pre-action overlay |

## 2. 预检与运行

| 步骤 | 结果 |
|---|---|
| `--preflight` | exit 0；manifest `40858efc…`、gate OK |
| plan-only | 只安排 **1** 个 seed（flat 4100；其余档 0） |
| 运行 | `python collect_demos.py --config trial/stage5_config_trial.json --run` |
| 退出码 | **0** |
| 结果目录 | `/root/autodl-tmp/day4-a5-rc2-l1-20261106-235108-211843` |
| 评价器 | `a5-verdict.status=accepted`、`success=true`、`runner_exit=0`、`criteria=accepted` |
| 重试 | 无 |

**运行前修过一次 overlay 的导入钩子**：`sitecustomize` 曾把 `audit_episode_evidence` 误判为 `episode_evidence` 并尝试 patch，导致 gate 预检失败（未启动 episode、未消耗尝试）；改为精确模块名 + `hasattr(EpisodeEvidence)` 后预检通过。

## 3. 观测采集与配对

采集方式：`EpisodeEvidence.emit('action_begin')` 之后、动作执行之前做一次**只读**快照（读 `vertices`、`ee`、`joints`；不 step、不调控制、不写布料）。未启用全物理帧 overlay。

| 检查 | 结果 |
|---|---|
| 观测数 / 动作数 | **7 / 7** |
| call_id | 1..7 连续 |
| 顶点形状 | 全部 (441, 3) |
| EE 形状 | 全部 (3,) |
| 关节向量 | 长度 9 |
| step / 时间单调 | 是 |
| 观测 target vs `result.actions[i].target_pose` | 最大差 **7.5e-9** |
| 观测 command vs `actions[i].command` | 差 **0** |
| 配对方式 | `call_id = 动作序号 + 1`；同一 `action_begin` 记录 target/command |

动作标签：`approach, close, arc45, arc90, arc135, place, release_retreat` → phase 映射见 [phase_map.json](../../stage5_collect/phase_map.json)。

## 4. 样本构造（同一轨迹，无跨 episode）

| 类型 | 数量 | 字段形状 |
|---|---:|---|
| single-step | **7** | `obs_vertices (7,441,3)`、`obs_ee (7,3)`、`obs_joints (7,9)`、`action (7,5)`、`phase (7,)`、`seed/level/success (7,)` |
| H=4 完整块 | **1** | `obs_vertices (1,4,441,3)`、`action (1,4,5)`、`mask (1,4)` |
| H=4 尾部 | 3 动作 | 补齐为 4 并给 `mask=[1,1,1,0]`；`h4_tail_padded.npz` |

- 切块：非重叠、同一 episode 内连续 4 个动作；本轨迹只有 1 个完整块，剩余 3 个动作为尾部。
- 无跨 episode 拼接；文件内 `episodes_in_file=1`。
- 产物：[export_summary.json](export/export_summary.json)、[single_step.npz](export/single_step.npz)、[h4.npz](export/h4.npz)、[h4_tail_padded.npz](export/h4_tail_padded.npz)。

## 5. 证据路径

- 本地：`day4-actionchunk-test/results/STAGE5_TRIAL_20261106/`（`obs/`、`state/`、结果目录、`export/`）
- 服务器：`/root/autodl-tmp/stage5-trial/`（obs、state、app overlay）、结果目录同上
- 采集账本：`state/attempts.jsonl`（started + accepted）、`state/demonstrations.jsonl`（1 条 accepted）

## 6. 结论与边界

- 试跑达到目标：accepted + 动作前观测完整 + 可配对 + single/H4 样本可构造。
- 仍只覆盖 1 个 flat seed；L2/L3 的 recovery 动作、更长动作序列与尾部比例未验证。
- 逐动作前的观测满足 BC 所需的最低字段（状态输入）；若后续要求逐物理帧或 RGB-D，需另行登记。
- 批量采集未启动；正式演示 seed 池、每档 50 条目标、并发度等待确认后再开。
