# a5-rc8b-recovery-hold120-rc7-r2：审计修订与 slots 2–7 受控续跑（已登记；未运行）

**父版本：** rc7 `41db790f…`。**修订 manifest：** `40858efc…`（63 项；62 项与 rc7 相同，仅 config 变化；`a5_recovery.py` 哈希相同）。审计入口在 app manifest 之外修订，因此 app 文件仅 config 变化。

## 1. 审计契约

- `hold_applicable` 是适用性字段，**不要求恒为 true**。
- **L1：** `hold_applicable=false`；必须无 `recovery_hold`、无 hold trace，且无新增 hold 执行。
- **L2/L3：** `hold_applicable=true`；必须有 120 步、121 帧、2.0 s、附件全关、事件与 FD 证据；缺失/类型错误拒绝。
- 离线测试：合法 L1 N/A 通过；L1 意外 hold 拒绝；合法 L2/L3 hold 通过；缺失/错误 hold 拒绝；输出契约缺字段/类型错误拒绝。

## 2. slot1 继承

- slot1 原结果、verdict、初次 audit exit 5、暂停日志、账本全部保留；**不重跑、不覆盖**。
- 同结果复审计 exit 0 另存；审计代码哈希记录在 `inheritance.json`。
- 原 manifest `41db790f…` 未改写为修订 manifest；继承范围仅 slot1。

## 3. 续跑

- 仅 slots 2–7，固定顺序：4100 arc4、4202 s、4202 a、4302 s、4302 a、4201 single。
- 新账本/锁 `a5-rc8b-recovery-hold120-rc7-r2-resume`；原 attempts 不变；不调用完整批次入口。
- 同 seed 共享 rc8b 原生初态；L1 pfs=0 无 hold，L2/L3 pfs=1 且 240 settle + 120 hold。
- 停止规则：身份/结果/审计/配对/保持时序异常立即暂停；质量 rejected 且证据完整可继续；4201 允许有效接受/拒绝。
- 不 freeze、不写回执、不跑 held-out/正式批次；正式成功保持 0。
