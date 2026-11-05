# a5-rc8b-recovery-hold120-r2-4302：4302 single 扩展（已登记；未运行）

**目的：** 在 4202 r2 干净复验通过后，用同一候选代码、同一任务规则、同一 120 步保持长度，跑一次 4302 single。不为不同 seed 调整保持长度。

- 父版本：r2 `60733a6b…`；新 manifest `3bc1351b…`（63 项；61 项与 r2 相同，仅 config/runner 变化；`a5_recovery.py` 哈希相同）。
- 初态：rc8b 新 4302 `day4-square-initial-stripfold-20261105-020706-026048`（pfs=1）。
- 保持：`rec_release` → 原 240 步 settle → 120 步 hold；总 360 步；121 帧 trace；事件四段；release_retreat 完成仍为 step 0。
- 只跑 4302 single 一次；新账本/锁；质量拒绝或证据异常则保留并暂停。
- 不扩批、不扫摩擦、不延长保持、不重跑七例、不冻结、不跑 held-out。
