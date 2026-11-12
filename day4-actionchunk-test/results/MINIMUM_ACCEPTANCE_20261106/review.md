# Stage 4 最低验收：完成报告（2026-11-06）

**结论：通过。** 冻结候选 `a5-rc8b-recovery-hold120-rc7-r2`（manifest `40858efc…`）在 L1/L2/L3 三档各取得 **5 个不同 seed 的有效成功**（共 15 个），达到最低验收门槛。批次按登记规则自动停止，`summary.json.passed = true`。

## 1. 身份与协议

| 项 | 值 |
|---|---|
| 候选 manifest | `40858efc1a5840ab2bf51e025f823382e8586bc037fbe41bf1d1de5b21dee86a` |
| 验证 manifest | `7d328159b72a2bd55be0254fd6844cb94408e1efa67e973148b67e8ffa3dcdae` |
| E_RELEASE | `9042e88ed8b4d082917151023705276230c1a4ba5c8e65b3c602337fa68ab66a` |
| gate | `A5_GATE_OK_SOURCE 7 manifest 40858efc…` |
| 部署 manifest v2 | 20 项，`bad 0`（`minimum_deployment_manifest_v2.json`） |
| 初态 | 既有 30 份预登记初态（`init_dirs.json`），不重生成 |
| 执行 | 仅 single；沿 `minimum_slots.json` 固定顺序；每档 ≤20 seed、5 个有效成功即停 |
| 判据 | 原质量评价 + 修订观测/hold 审计；阈值、初态协议、动作均未改 |

**续跑规则**（2026-11-06 登记，见 [CONTINUATION_RULE_20261106.md](../../minimum_hold120/CONTINUATION_RULE_20261106.md)）：已启动并结束、有结果目录、`a5-verdict.status=incomplete`、`passed=false` 且 errors 含 `Square waypoint velocity/position did not converge` 的尝试，计为失败并继续下一 seed；其他异常仍暂停。本批次中 4312、4314 适用该规则。

## 2. 分档结果

| 档 | 尝试 | 有效成功 | 拒绝 | 错误 | 拒绝率 | 停止原因 |
|---|---:|---:|---:|---:|---:|---|
| L1 flat | 8 | **5** | 0 | 3 | 0.375 | five_valid_successes |
| L2 perturbed | 6 | **5** | 1 | 0 | 0.167 | five_valid_successes |
| L3 crumpled | 7 | **5** | 0 | 2 | 0.286 | five_valid_successes |

- 成功 seed：L1 `4113, 4114, 4115, 4116, 4117`；L2 `4210, 4212, 4213, 4214, 4215`；L3 `4310, 4311, 4313, 4315, 4316`。
- 拒绝率按 `(rejected+error)/attempts`；L1 的 3 个 error 含 4110/4111 的旧 receipt 入口失败与 4112 的 execution_error，均已原样保留、未重跑。
- 三档合计：21 次尝试、15 个有效成功、1 rejected、5 error。

## 3. 逐 seed 记录

| 档 | seed | 状态 | 质量/错误 | 结果目录 |
|---|---:|---|---|---|
| flat | 4110 | error | episode_or_missing_result | — |
| flat | 4111 | error | episode_or_missing_result | — |
| flat | 4112 | error | execution_error（waypoint 不收敛） | `day4-a5-rc2-l1-20261106-033055-623326` |
| flat | 4113 | finished | accepted | `day4-a5-rc2-l1-20261106-074405-520751` |
| flat | 4114 | finished | accepted | `day4-a5-rc2-l1-20261106-075728-021170` |
| flat | 4115 | finished | accepted | `day4-a5-rc2-l1-20261106-081145-421086` |
| flat | 4116 | finished | accepted | `day4-a5-rc2-l1-20261106-082415-314656` |
| flat | 4117 | finished | accepted | `day4-a5-rc2-l1-20261106-083728-323861` |
| perturbed | 4210 | finished | accepted | `day4-a5-rc2-pfs1-observation-v2-20261106-085122-325946` |
| perturbed | 4211 | finished | rejected | `day4-a5-rc2-pfs1-observation-v2-20261106-091015-520319` |
| perturbed | 4212 | finished | accepted | `day4-a5-rc2-pfs1-observation-v2-20261106-092909-420652` |
| perturbed | 4213 | finished | accepted | `day4-a5-rc2-pfs1-observation-v2-20261106-094850-227251` |
| perturbed | 4214 | finished | accepted | `day4-a5-rc2-pfs1-observation-v2-20261106-100815-925057` |
| perturbed | 4215 | finished | accepted | `day4-a5-rc2-pfs1-observation-v2-20261106-102608-715841` |
| crumpled | 4310 | finished | accepted | `day4-a5-rc2-pfs1-observation-v2-20261106-104416-658552` |
| crumpled | 4311 | finished | accepted | `day4-a5-rc2-pfs1-observation-v2-20261106-110346-225816` |
| crumpled | 4312 | error | waypoint_non_convergence | `day4-a5-rc2-pfs1-observation-v2-20261106-112234-124355` |
| crumpled | 4313 | finished | accepted | `day4-a5-rc2-pfs1-observation-v2-20261106-112820-311984` |
| crumpled | 4314 | error | waypoint_non_convergence | `day4-a5-rc2-pfs1-observation-v2-20261106-114811-918419` |
| crumpled | 4315 | finished | accepted | `day4-a5-rc2-pfs1-observation-v2-20261106-115307-436594` |
| crumpled | 4316 | finished | accepted | `day4-a5-rc2-pfs1-observation-v2-20261106-120738-727611` |

## 4. 证据核验

- 15/15 accepted 目录：`a5-verdict.status=accepted`、`result.json.passed=true`、`audit_exit=0`、`file_complete=true`、`observation_semantics_valid=true`、`overall_valid=true`。
- L2/L3 的 `hold_applicable=true`、`recovery_hold=true`（hold120 语义通过）。
- 30/30 初态截图：`stage4-minimum-hold120-state-v1/initial_screenshots/*.png`，哈希见 `screenshots.json`。
- 账本与收尾：`attempts.jsonl`（21 次尝试全量）、`summary.json`、`completed`、`init_dirs.json`。
- 本地证据包：本目录（15 个结果目录 + state + `minimum_20261106_evidence.tgz`）；服务器原件在 `<remote-root>/` 对应目录。

## 5. 接口隔离（按原条款结项：代码审查）

原条款：[README](../../../README.md) Stage 4 验收计划第 6 条“公共接口隔离检查”与第 4 节“禁止 policy 直接依赖 Isaac Sim 关节命令、USD 对象路径或粒子索引”。

| 检查项 | 源码位置（冻结候选 `app/`） | 结论 |
|---|---|---|
| 公共动作只有 5 维笛卡尔 waypoint `[x,y,z,yaw]+gripper`，不含关节角/速度/力矩 | `garmentlab-action-chunk-demo/schemas/action.py:1-6`、`:33-34`（4+1 维）、`:42-62` | 满足 |
| 公共观测禁止 Isaac joint command、USD 路径、粒子索引 | `garmentlab-action-chunk-demo/schemas/observation.py:1-11` | 满足 |
| Backend 仅 `get_observation / execute / stop`，policy 不直接调 Isaac | `garmentlab-action-chunk-demo/backends/base.py:1-14`、`:23` | 满足 |
| expert 的仿真真值使用范围 | `a5_l1.py:106`（cloth view 速度）、`:121-137`（control/attachment）、`:160-166`（EE）、`:237-243`（control/robot/open）、`:329-343`（StableHold/关节速度） | 属登记的 state-oracle expert，仅用于演示生成；动作仍经 `b.execute(chunk)`（`:120`、`:159`） |

**判定：条款满足，结项**；不另写脚本。边界：这是代码级审查，不是运行时审计；若 Stage 5 引入真实 policy，需重新核对。

## 6. reset 兼容（按修订闭合，2026-11-06 批准）

原条款：[README](../../../README.md) Stage 4 验收计划第 2 条“验证 `reset(seed, difficulty)`、episode 内重抓取及连续 10 次 reset/rollout”；[DAY4_MINIMUM_PLAN](../../../DAY4_MINIMUM_PLAN.md) 第 5 条“将连续 10 次 reset/rollout 检查并入批次，检查状态残留、资源和保存错误”。

**批准修订：** [stage4-reset-clause-rev-20261106](../../minimum_hold120/STAGE4_RESET_CLAUSE_REVISION_20261106.md)（用户批准 2026-11-06）——冻结候选及 Stage 5 采用**每个 episode 独立进程**，替代进程内连续 10 次场景 reset/rollout；若以后改为同进程复用场景，恢复原 reset 验证要求。

**进程依据（现有入口）：**

1. `a5_entry.py:130-154`：每个 episode 校验初态、建 attempt/journal、用 `subprocess.run` 启动独立 runner（`:137-141`），评估后写 verdict、打印 `DOWNLOAD_DIR`、进程退出。
2. `minimum_driver_v2.py:45-52`（`:49`）用 `subprocess.run` 调 `adapter_run.py`（`:15-16` 只改 `E_RELEASE` 路径）。
3. 正式批次 21 个 episode 各对应独立 attempt 目录、21 个唯一 seed、无重复；驱动退出后写 `completed`、移锁。

**保留：** 2026-11-01 的 [10 循环审查](../day4-prepared-square-backend-reset-20261101-080713-870146/review.md)（`passed=true`、10 循环）及其“题前 `PreparedSquareBackend`”适用范围；不删除、不改写、不作为冻结候选证据。

**结论：按修订闭合。** 若恢复同进程复用，需实现场景 reset（冻结候选当前 `reset()` 只做 robot home/settle/difficulty）并完成 10 次验证。

## 7. 结论与边界

- **最低验收批次：通过**。三档各 5 个不同 seed 的有效成功，共 15 个正式 accepted episode；成功计数由 0 更新为 **15**。
- **接口隔离：结项**（代码审查满足原条款，见 §5）。
- **reset 兼容：按修订闭合**（逐进程 episode；见 §6）。
- **Stage 4 状态：完成（2026-11-06）**，可正式进入 Stage 5。
- 边界：single-only；每档“5 成功即停”不是固定样本量成功率，拒绝率（L1 0.375 / L2 0.167 / L3 0.286）只描述本次预登记 seed 的尝试结果，不得当作策略性能或难度曲线；expert 为 state-oracle；判据仍是仿真几何代理，不认证真实夹持/平整质量。
- 未启动：原 60 初态/120 槽批次；未重跑 4110–4112；未补跑 4100。
