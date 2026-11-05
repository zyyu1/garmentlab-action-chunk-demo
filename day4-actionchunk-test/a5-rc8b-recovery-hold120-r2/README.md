# a5-rc8b-recovery-hold120-r2：审计修复后的干净复验候选（已登记；未运行）

**目的：** 保持物理、控制、120 步与采样完全不变，只修审计入口；用新账本/锁做一次 4202 single 干净复验，通过后再扩展 4302 single。

**父版本：** `a5-rc8b-recovery-hold120`（manifest `b61fd56e…`）。**新 manifest：** `60733a6b…`（63 项；61 项与父版本相同，仅 config/runner 变化；`a5_recovery.py` 哈希完全相同）。

## 1. 审计修复

- 原 runner exit 3：audit 打印投影缺 `recovery_hold`，触发 `KeyError`；结果 JSON 已完整写出。
- 修复：audit 增加 `check_output_contract()`，打印前校验必需字段；离线测试 `test_audit_output.py` 覆盖 complete / missing / non-bool 三种情况。
- 对同一 r1 保存结果重跑完整审计 → exit 0；未重跑仿真。原始 exit 3、异常日志、复审计记录全部保留。

## 2. 保持定义（与 r1 相同）

- 位置：`rec_release` 返回 → 原 240 步 settle → **120 步 hold** → 重新观测 → 原 expert fold。
- 总时序：从 `rec_release` 返回起 **360 个物理步**（240 + 120），不能写成仅 120 步。
- 只调用 `b._env.step()` 120 次；保持当前控制目标；不移动/开闭爪、不重置布料、不清零速度、不改材料。
- 121 帧 trace / 120 FD 区间 / 2.0 s；事件 `recovery_retreat_end`、`recovery_hold_begin`、`recovery_hold_end`、`fold_observation`。
- release_retreat 完成仍为 step 0；原评价窗口/评价器/阈值。

## 3. 运行计划

1. 4202 single 一次（同一 rc8b 新初态 `…015817-115841`）；要求 runner/entry/audit 均 exit 0、质量 accepted、证据完整；与 r1 逐阶段比较，有差异先调查，不自动重试。
2. 4202 通过后，用同一任务规则/保持长度跑一次 4302 single（新账本/锁）；质量拒绝或证据异常则保留并暂停。

## 4. 边界

- 本轮不扩批、不扫摩擦、不延长保持、不重跑七例、不冻结、不跑 held-out。
- 两例通过后再准备七例 RC；诊断不计入正式 Stage 4 成功。
