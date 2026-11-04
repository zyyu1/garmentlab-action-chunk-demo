# D1-120 步骤 5：离线预检

对象：`a5-rc2-d1-120`（父 `a5-rc2-drift-diag-v1` v1.1）。**仅离线预检；没有导入 Isaac、没有运行仿真、没有生成诊断结果目录、没有 held-out。**

## 结果

**65/65 检查通过**，`D1_PREFLIGHT_OK`。

- 预检脚本：[d1_120_preflight.py](../../d1_120_preflight.py)
- 机器结果：[preflight.json](preflight.json)
- 原始输出：[preflight_stdout.txt](preflight_stdout.txt)
- 运行命令：`cd day4-actionchunk-test && python -I d1_120_preflight.py --force`

当前 runner 已包含 step 6 单次运行/ledger 保护（`D1_ALLOW_RERUN`、`completed`、`run.lock`、`run_ledger.json`、事后证据清单）；D1 manifest 已同步为该 runner 的版本，SHA256 `cd1d7f83…`，`bash -n` 通过。

2026-11-04 步骤 6 的两次 runner 启动均在 Isaac 前失败：第一次 `mode` 未传入，第二次 `$initial` 未赋值（未启动 Isaac、无结果目录；第二次写入一条 started attempt）。已修复为传入 `$mode`、预检前设置 `$initial`，并加入 `D1_PREFLIGHT_ONLY` 无仿真预检出口；失败日志/账本保留在 [D1_120_RUN_PREFLIGHT_FAILURE_20261104](../D1_120_RUN_PREFLIGHT_FAILURE_20261104/review.md)，修复后重新预检 65/65。

## 检查范围

| 类别 | 关键结果 |
|---|---|
| 身份 | 父 v1.1 manifest `13c1f20a…`/config `aa5da98b…` 未变；基础 RC2 candidate `10a6cb45…`、manifest `39dc5055…`（60 项）核验通过；4202 初态哈希 `4472f4df…`/`a6646d66…` 记录一致 |
| D1 manifest | 66 项；全部路径存在且 SHA256 匹配；60 项基础 hash 与 RC2 完全一致；6 项诊断条目精确；manifest/config 与 registration 哈希一致 |
| 配置 | 版本 `a5-rc2-d1-120`；delay=120；公开动作 12；scope 仅 4202/perturbed/single/right；无 4302/revalidation；`diagnostic_only=true`、`public_actions_unchanged=true`、`action_targets_unchanged=true`、`physics_step_count_changed=true` |
| 语法 | 6 个诊断 Python 文件 `compile` 通过；runner `bash -n` 通过 |
| 插入位置 | `hold_open_for_steps` 仅含 120 次 `world.step(render=True)` 循环；无 `control.robot_goto_position`/`robot.open`/`robot.close`/布料位置写入/速度清除；`measure_detachment` 中 `delay_begin → hold → delay_end → retreat_begin → original → retreat_end` 顺序正确 |
| 事件 | `ungrasp_return` 在 `control.ungrasp` 返回后记录；五个事件各只发出一次；`release_diag.json:events` + `release_diag_events.csv`；`release_diag.npz` 保留逐步顶点/EE/关节/attachment 和 `phase` |
| 动作预算 | 等待位于第 12 个公开动作；`len(actions)+1==12`、`sum(call_horizons)==12`；v1.1 与 D1 的 21 条 action/horizon 行逐条相同；退让目标 `start_ee + [0,0,.15]` 未变 |
| recovery 隔离 | `release_window` 在 `a5_recovery_diag.py` 只导入/调用一次，位于最终释放；recovery 文件无 `hold_open_for_steps`/delay 事件；recovery 的 OPEN 不受等待影响 |
| 采集逻辑 | `release_diag` 事件/NPZ/CSV 写出逻辑存在；assessor 检查事件顺序、120 步、phase 行数、公开动作索引和内部延迟字段 |
| 范围 | runner 拒绝非 `4202` seed 和非 `single` mode；config 仅登记 4202；本地无 D1 结果目录 |
| fixture | `test_d1_120_delay.py` 5/5；`test_release_diag.py` 1/1（含事件、`events_complete`、事件 CSV） |

## 预检脚本自身修正

首次预检有 3 个 **检查器** 问题，不是诊断实现失败：

1. `public_actions` 在 config 中位于 `delay.public_actions`，检查器只读顶层；已兼容读取。
2. `unittest` 把结果写到 stderr，检查器只看 stdout；已合并 stdout/stderr。
3. `runner_scope_rejection` 的字符串匹配漏了引号；已改为匹配 `!= "4202"` / `!= "single"`。

修正后 65/65 通过；`preflight.json` 为最终记录。

## 结论与下一步

- 步骤 5 完成标准满足：语法、manifest、插入位置、动作计数、采集逻辑均通过；等待只影响最终释放/退让，不影响 recovery 的 OPEN；运行范围仅 4202 single。
- 该记录完成时尚未运行；2026-11-04 步骤 6 已单次运行并完成 postfix 评估，见 [D1_120_RUN_4202_20261104](../D1_120_RUN_4202_20261104/review.md)。注册文件在运行后追加了 run 结果，因此 registration hash 更新；manifest/config 未变。
- 正式 Stage 4 成功仍为 0；RC2 与 v1.1 目录未修改。
