# Stage 4 最低验收：waypoint 不收敛续跑规则（2026-11-06 登记）

**结论：允许。** 已确认的 waypoint 不收敛（episode 已启动、已结束、有完整结果目录）按原状态保留、计为**一次失败**，并转入 `minimum_slots.json` 的下一预登记 seed；其他执行/证据/观测异常仍按原规则暂停。

## 1. 依据（逐条）

| 条款 | 原文要点 | 含义 |
|---|---|---|
| [STAGE4_FORMAL_BATCH_PLAN.md](../../STAGE4_FORMAL_BATCH_PLAN.md) §3 | “折叠失败不中断批次、不覆盖旧结果，**没有结果目录则视为基础设施错误并停止**（其余数据不可比）” | 有结果目录的折叠失败**不**停止批次；只有“没有结果目录”才停 |
| 同上 §4 | 拒绝率 `= (rejected + error) / 总尝试`；`rejected` = 有完整 `result.json` 但 `passed=false`；`error` = 尝试了却没有结果目录 | 有 `result.json` 的失败计为 rejected；错误保留在分母 |
| [STAGE4_SUCCESS_CRITERIA_V1.md](../../STAGE4_SUCCESS_CRITERIA_V1.md) §5 | `rejected` = 完整证据未过门槛；`incomplete` = 缺失时序证据；`error` = 非法输入/评价器身份错误；“后两类均不得从尝试分母删除，也不得转成成功” | 不完整尝试留在分母，且不能算成功 |
| [MINIMUM_ACCEPTANCE_PLAN.md](MINIMUM_ACCEPTANCE_PLAN.md) §3 | “全部失败/错误保留；拒绝率按 (rejected+error)/attempts”；“执行/证据/观测异常按原规则暂停，不重试” | 失败/错误是批次内的正常记录；“暂停”针对异常，不是针对专家折叠失败 |

**判定：** waypoint 不收敛是一次**已启动并结束的专家折叠尝试**，产生了结果目录、`result.json`、`a5-verdict.json`（`status=incomplete`）和明确的 `RuntimeError`。它不是基础设施/证据/观测异常，因此按 §3 的“折叠失败不中断批次”处理：计为失败并继续。

## 2. 本续跑类的判定条件（同时满足）

1. episode 已实际启动并结束；
2. 结果目录存在且含 `result.json`；
3. `a5-verdict.json` 的 `status == 'incomplete'`；
4. `result.json` 的 `passed == false`，且 `errors` 含 `Square waypoint velocity/position did not converge`。

## 3. 仍然暂停的异常（不属本类）

gate 失败、缺结果目录、entry 无 `DOWNLOAD_DIR`、audit 失败、证据不完整（file_complete / observation_semantics_valid / overall_valid 任一 false）、质量状态非 accepted/rejected、锁占用、未完成 attempt、pair 不一致、观测/hold 语义失败。

## 4. 记录与计数

- **4110–4112 保持原记录**，不重跑、不改写。4112 的 `state=error, error=execution_error` 按 §1 计入分母、计为失败。
- 后续同类失败写 `state=error`、`error=waypoint_non_convergence`、`failure_class=expert_timeout`、`result_dir`、`runner_exit`，`attempts += 1`，继续下一 seed。
- `successes` 只认 `quality_status=accepted` 且审计完整有效的尝试；error 不增加成功数。
- 判据、初态协议、动作、评价器、冻结候选（`40858efc…`）均不变；不改 seed 顺序、不重试同一 seed。

## 5. 部署身份变更

- 驱动：`minimum_driver_v2.py`（新增续跑类），旧 `minimum_driver.py` 保留。
- 新 `minimum_deployment_manifest_v2.json` 固定 v2 驱动与本文档哈希；旧 manifest v1 保留。
- 已知旧问题：v1 的 `check_minimum_deployment.py` 的 `paths` 缺 `adapter_run.py`，而 manifest v1 已含该条目，导致 preflight `KeyError`（发生在本次登记之前，不是本次引入）；v2 检查器补上。

## 6. 执行状态

- 从 **4113 single** 继续，沿 `minimum_slots.json` 固定顺序；每档最多 20 seed、5 个不同 seed 的有效成功即停。
- 不补跑 4100、不重跑 4110–4112、不启动原 120 槽批次。
- 本次结果仍按最低验收口径汇总；不解释为固定样本量成功率或策略性能。
