# a5-rc8b-recovery-hold120-rc7：hold120 七例开发 RC（已登记；未运行）

**统一候选：** L1 `pfs=0`、无 hold；L2/L3 `pfs=1`，recovery 原 240 步 settle 后增加 **120 步 / 2.0 s**，再重新观测并计算 fold pick/yaw。single/arc4 使用同一保持位置与时长；动作预算 L1=7、L2/L3=12；原评价器/阈值/窗口不变。

- 父版本：r2 `60733a6b…`；manifest **`41db790f…`**（63 项；61 项与 r2 相同，仅 config/runner；`a5_recovery.py` 哈希相同）。
- 初态：rc8b 原生 4100/4202/4302/4201，完整文件与哈希；不重新生成、不使用 pfs=0 或诊断派生初态。
- 七槽固定顺序：4100 s/a、4202 s/a、4302 s/a、4201 single；每槽一次、顺序、无重试。
- 新账本/锁 `a5-rc8b-recovery-hold120-rc7-runs`；不允许 formal/held-out。
- 审计：L1 标记 hold 不适用、不要求 hold 轨迹；L2/L3 要求 121 帧/120 区间/2.0 s 与事件。
- 停止规则：身份/结果/证据/配对/保持时序异常立即暂停；质量 rejected 但证据完整可继续；4201 允许有效接受或拒绝。
- 本轮不 freeze、不写回执、不跑 held-out/正式批次；不计正式成功。
