# recovery-hold120 七例 RC：准备稿（已启动；slot 1 后暂停）

> 实际执行状态：候选 `a5-rc8b-recovery-hold120-rc7` 已预检并启动；slot1 4100 single accepted 0.1435/0.2072，但 L1 审计契约误判导致队列暂停；slot 2–7 未运行。详见 [七例暂停审查](hold120_rc7_pause_review.md)。恢复需明确指令。

**前置：** 4202 r2 干净复验（0.2374/0.3484，runner/entry/audit 均 0）与 4302 扩展（0.2386/0.3468，均 0）已通过。本稿只准备七例，不运行。

## 1. 候选

- 以 `a5-rc8b-recovery-hold120-r2` 的 app 为基线（`a5_recovery.py` 含 120 步 hold；物理/控制/采样不变）。
- 新登记 `a5-rc8b-recovery-hold120-rc7`：新 manifest、config、runner、账本与锁；不改 r2/4302 的已用账本。
- 七例矩阵与 rc8b 相同；**hold 只作用于 L2/L3**（a5_recovery 路径），4100 L1 不经过 hold。

## 2. 矩阵（顺序执行，每槽一次）

| 槽 | seed | 任务 | 模式 | 动作 |
|---:|---:|---|---|---:|
| 1–2 | 4100 | L1 过折 | single / arc4 | 7 |
| 3–4 | 4202 | L2 nominal right | single / arc4 | 12 |
| 5–6 | 4302 | L3 nominal right | single / arc4 | 12 |
| 7 | 4201 | L2 历史失败对照 | single | 12 |

- L2/L3 的 recovery 结束后：原 240 步 settle → 120 步 hold → 重新观测 → fold；总 360 步，不能写成仅 120。
- L1 无 recovery/hold；保持原 rc8b 行为。
- release_retreat 完成仍为 step 0；原窗口/评价器/阈值。

## 3. 通过门

- 六阳性全部 accepted；4201 允许有效接受或有效拒绝。
- 三组配对 target 差 0（atol 1e-6）；7/7 证据完整；`hold120`/`initial_protocol` 审计通过。
- 下载哈希全一致；本地 evaluator 复算一致；原版 verify-dev 退出 0。
- 任一 runner/entry/audit 非零、质量拒绝或证据异常：保留现场并暂停，不自动重试/扩批。

## 4. 必做预检（不启动仿真）

1. 新候选 manifest 63/63；相对 r2 仅 config/runner 变化，`a5_recovery.py` 哈希相同。
2. 七例 initial 路径/哈希、task-scoped protocol 1.0、policy modes 匹配。
3. config 矩阵、hold 定义、账本为空、锁未占用。
4. runner `bash -n`、app `py_compile`、audit contract 离线测试。
5. 远端上传后逐项核对 manifest，再 preflight-only。

## 5. 解释边界

- 两例诊断通过不等于七例会通过；L2/L3 其他 seed、L1 与配对仍需独立验证。
- hold120 仅是候选衔接改进；不能解释为运动衰减，也不计正式 Stage 4 成功。
- 本稿不运行七例、不冻结、不跑 held-out、不扫摩擦、不扩大 patch。
