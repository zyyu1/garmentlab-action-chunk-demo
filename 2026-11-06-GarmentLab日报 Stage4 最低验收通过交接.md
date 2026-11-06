# 2026-11-06 GarmentLab 日报 · Stage 4 最低验收通过交接

> 时间说明：批次在远端（UTC+8）2026-11-06 04:00–12:20 运行；本地 Europe/Berlin 为 2026-11-05 21:00–2026-11-06 05:20。按远端运行日命名。

**暂停位置**　Stage 4 **最低验收已通过**：冻结候选 `a5-rc8b-recovery-hold120-rc7-r2`（manifest `40858efc…`）在 L1/L2/L3 各取得 5 个不同 seed 的有效成功，共 **15 个正式 accepted episode**，`summary.json.passed = true`，批次按登记规则自动停止。收尾状态：**接口隔离结项；reset 兼容待闭合**（冻结候选无 in-process 场景 reset），因此 Stage 4 **暂不标记完成**。原 60 初态/120 槽批次未启动；正式成功计数由 0 更新为 **15**。

## 1. 本轮做了什么

1. **规则核对与续跑登记**：确认 `waypoint 不收敛` 属于“有结果目录的专家折叠失败”，按 [STAGE4_FORMAL_BATCH_PLAN](STAGE4_FORMAL_BATCH_PLAN.md) §3（折叠失败不中断批次、只有缺结果目录才停）、§4（`rejected+error` 进分母）与 [STAGE4_SUCCESS_CRITERIA_V1](STAGE4_SUCCESS_CRITERIA_V1.md) §5（incomplete/error 不得移出分母、不得转成功）处理；登记 [CONTINUATION_RULE_20261106.md](day4-actionchunk-test/minimum_hold120/CONTINUATION_RULE_20261106.md)。
2. **驱动与部署身份**：新增 `minimum_driver_v2.py`（唯一改动：该类失败写 `error=waypoint_non_convergence`、`attempts+1`、`continue`），其余分支不变；`minimum_deployment_manifest_v2.json` 20 项、`bad 0`；gate `A5_GATE_OK_SOURCE 7 manifest 40858efc…`；preflight 通过。离线谓词测试：4112 → True，缺目录/错状态 → False。
3. **从 4113 续跑**：沿 `minimum_slots.json` 固定顺序，每档 5 成功即停；21 个 seed 各只尝试一次（无重复、无重试），所有 verdict 的 `manifest_sha256` 均为 `40858efc…`。
4. **证据下载与核验**：15 个 accepted 目录 + state + 30 张初态截图打包下载（`minimum_20261106_evidence.tgz`，5.9 MB），逐项核验。
5. **前序 4112 零速度目标诊断（2026-11-05/06）**：在 arc135 最终 120 tick 内把 DOF 0–6 速度目标置零，drive 读回确认位置目标逐位相同、速度目标全 0；最大关节速度 0.352→0.221 rad/s，但 120 tick 仍全部不过（末 tick EE 92 mm），失败由位置发散主导。见 [零速度诊断](day4-actionchunk-test/results/DIAG_4112_ZEROVEL_20261105/review.md)。

## 2. 分档结果

| 档 | 尝试 | 有效成功 | 拒绝 | 错误 | 拒绝率 | 停止原因 |
|---|---:|---:|---:|---:|---:|---|
| L1 flat | 8 | **5** | 0 | 3 | 0.375 | five_valid_successes |
| L2 perturbed | 6 | **5** | 1 | 0 | 0.167 | five_valid_successes |
| L3 crumpled | 7 | **5** | 0 | 2 | 0.286 | five_valid_successes |

- 成功 seed：L1 `4113, 4114, 4115, 4116, 4117`；L2 `4210, 4212, 4213, 4214, 4215`；L3 `4310, 4311, 4313, 4315, 4316`。
- 合计 21 次尝试、15 个有效成功、1 rejected、5 error；拒绝率 `(rejected+error)/attempts`。

## 3. 失败与异常（全量保留，未重跑）

| 档 | seed | 状态 | 质量/错误 | 说明 |
|---|---:|---|---|---|
| flat | 4110 | error | episode_or_missing_result | 旧 receipt 入口失败，无 episode |
| flat | 4111 | error | episode_or_missing_result | 同上 |
| flat | 4112 | error | execution_error | arc135 waypoint 不收敛；result 目录保留 |
| perturbed | 4211 | finished | rejected | 完整评价未过门槛 |
| crumpled | 4312 | error | waypoint_non_convergence | 续跑规则适用，计失败并继续 |
| crumpled | 4314 | error | waypoint_non_convergence | 同上 |

## 4. 证据与身份核验

- 15/15 accepted：`a5-verdict.status=accepted`、`result.json.passed=true`、`audit_exit=0`、`file_complete / observation_semantics_valid / overall_valid` 全 true；L2/L3 `hold_applicable=true`、`recovery_hold=true`。
- 30/30 初态截图与哈希（`screenshots.json`）；`init_dirs.json` 复用既有 30 份初态，未重新生成。
- 账本 21 条尝试全量、`summary.json`、`completed` 齐全；无重复 seed（started=21、unique=21）。
- 候选/回执/部署身份：`40858efc…` / `9042e88e…` / 部署 v2（20 项）。

## 5. 验收收尾结论（2026-11-06 更新）

1. **接口隔离：结项**。按原条款做代码审查（公共 5 维 `[x,y,z,yaw]+gripper` 动作 schema；观测 schema 禁止 joint command/USD 路径/粒子索引；`RobotBackend` 仅 `get_observation/execute/stop`；expert 的 `b._env` 属登记的 state-oracle，动作仍经 `b.execute(chunk)`）。路径与行号见 [完成报告](day4-actionchunk-test/results/MINIMUM_ACCEPTANCE_20261106/review.md) §5。
2. **reset 兼容：待闭合**。2026-11-01 的 10 次 reset/rollout 证据无 `code_files`/manifest（无代码身份），且用 `PreparedSquareBackend`；冻结候选用 `SquarePoseBackend/FoldPoseBackend`（`app/square_pose_backend.py`、`app/a5_l1.py:40`），其 `reset()` 只做 robot home/settle/difficulty（`garmentlab_backend.py:190-218`），**不调用**场景 reset 钩子（`app/multi_prepared_grasp_control.py:132/142/268/273` 无调用点）；reset 控制文件最后修改 2026-11-02（commit `bd61389`），晚于 11-01 证据。继承不成立，冻结候选当前无法执行 10 次场景 reset。
3. **Stage 4 状态：暂不标记完成**（最低验收通过 + 接口结项，reset 缺口未闭合）。

## 6. 下一步（需明确指令）

- reset 二选一：在冻结候选实现并验证 in-process reset 后补跑 10 次；或正式登记该条款由 2026-11-01 的题前 Backend 满足、被逐进程 episode 协议取代（口径变更）。
- 若接受上述口径变更，Stage 4 可标记完成并进入 Stage 5（demonstrations 批量生成）。
- `DAY4_ACCEPTANCE_TRACKER.md` 已同步本轮状态（2026-11-06 段）。

## 7. 产物

- [最低验收完成报告](day4-actionchunk-test/results/MINIMUM_ACCEPTANCE_20261106/review.md)（分档表、逐 seed、证据核验、接口/reset 状态）
- 本地证据包：`day4-actionchunk-test/results/MINIMUM_ACCEPTANCE_20261106/`（15 个结果目录 + `stage4-minimum-hold120-state-v1/` + tgz）
- 登记：[CONTINUATION_RULE_20261106.md](day4-actionchunk-test/minimum_hold120/CONTINUATION_RULE_20261106.md)、`minimum_driver_v2.py`、`minimum_deployment_manifest_v2.json`
- 前序诊断：[零速度目标诊断](day4-actionchunk-test/results/DIAG_4112_ZEROVEL_20261105/review.md)
- 服务器原件：`/root/autodl-tmp/day4-a5-rc2-*`、`/root/autodl-tmp/stage4-minimum-hold120-state-v1/`

## 8. 边界

- single-only；每档“5 成功即停”不是固定样本量成功率，拒绝率只描述本次预登记 seed，不得当作策略性能或难度曲线。
- expert 为 state-oracle；判据为仿真几何代理，不认证真实夹持/平整质量/自交。
- 未启动 120 槽批次；未重跑 4110–4112；未补跑 4100。
- **本日暂停**：批次驱动与诊断进程均已退出，无在途仿真；未启动新实验，等待 reset 条款决定。
