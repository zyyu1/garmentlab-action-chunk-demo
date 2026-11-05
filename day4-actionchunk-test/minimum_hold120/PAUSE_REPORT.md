# 最低验收方案：执行异常暂停报告

**状态：** 未通过；执行异常暂停；正式 Stage 4 成功 **0**。未自动重试、未换 seed、未调阈值。

## 1. 进度

| 项目 | 结果 |
|---|---|
| 初态截图 | **30/30**（L1 10、L2 10、L3 10） |
| 折叠尝试 | 3 个 seed（4110、4111、4112），均 flat/single |
| 有效成功 | **0** |
| 每档 5 成功 | 未达到；尚未完成 flat 档 |
| 原 60/120 计划 | 未启动，保留并标记为被取代 |

## 2. 逐次记录

| seed | slot | entry_exit | 结果 |
|---:|---:|---:|---|
| 4110 | 1 | 1 | 冻结 `a5_entry.py` 在 app/ 内找不到 E_RELEASE，gate 失败；无 episode |
| 4111 | 2 | 1 | 同上（子进程 `a5_l1.py` 仍使用 app 内 receipt）；无 episode |
| 4112 | 3 | 3 | 实际开始；9.3 min 后 `RuntimeError('Square waypoint velocity/position did not converge')`；`status=incomplete`，无完整 success_trace |

- 4112 结果目录：`day4-a5-rc2-l1-20261106-033055-623326`，已保留。
- `a5-verdict.json` 记录 `runner_exit=0`、`status=incomplete`、`development_pass=false`。
- 4110/4111 的 attempts 与错误保留；未重跑。
- 4112 后驱动按执行异常规则暂停；无 `summary.json`/`completed`。

## 3. 停止原因

**执行异常：L1 waypoint 速度/位置未收敛。** 按预先登记规则暂停；未继续下一个 seed，未重试。最低验收未通过。

## 4. 冻结与计划

- 候选 `40858efc…`、验证 manifest `7d328159…`、回执未改。
- 原 60/120 计划未启动；本最低方案独立 plan/部署/账本。
- 截图 30 份已保存；折叠只试了 3 个 seed。

## 5. 下一步（需明确指令）

- 不自动重跑 4112 或跳过到 4113；不换 seed、不改阈值。
- 若要继续，需决定：调查 waypoint 非收敛（离线/诊断）并重新登记；或终止最低验收。
- 正式成功仍为 0；held-out/正式 120 槽未运行。
