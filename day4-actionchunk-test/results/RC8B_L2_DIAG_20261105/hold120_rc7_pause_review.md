# hold120 rc7 七例 RC：slot 1 后暂停（审计 L1 语义缺陷，非仿真失败）

**状态：** 候选 `a5-rc8b-recovery-hold120-rc7` 预检通过，按顺序启动七槽。**slot 1（4100 single）已执行并 accepted**，但 runner 在 audit 阶段暂停：L1 的 `hold_applicable=false` 被错误计入 `observation_semantics_valid`，导致 audit exit 5。**slot 2–7 未运行**；队列无 `completed`，账本保留 1 started + 1 paused。未自动重试或补跑。

## 1. 候选与预检

| 项目 | 值 |
|---|---|
| 候选 / manifest | `a5-rc8b-recovery-hold120-rc7` / **`41db790f…`**（63 项；61 项与 r2 相同，仅 config/runner；`a5_recovery.py` 哈希相同） |
| 物理 | L1 pfs=0、无 hold；L2/L3 pfs=1；初态生成/reset/rollout 同协议 |
| 初态 | rc8b 原生 4100/4202/4302/4201，完整哈希 |
| 保持 | L2/L3 在原 240 步 settle 后 120 步/2.0 s；single/arc4 同一位置与时长 |
| 账本/锁 | `a5-rc8b-recovery-hold120-rc7-runs`；一次性锁 |
| 预检 | `HOLD120RC7_PREFLIGHT_OK 63 41db790f… cases 7`；`bash -n`、py_compile、audit contract 测试通过 |

## 2. slot 1 结果（4100 single）

- 运行：`day4-a5-rc2-l1-20261105-081311-735952`；**accepted 0.1435 / 0.2072 mm**；无 hold（L1 不适用）。
- 证据：110 个结果文件 + 账本/日志，下载 **118/118** 哈希一致。
- 初次 audit：`observation_semantics_valid=false`，唯一失败项 `hold_applicable=false`；质量 accepted、证据完整，原因是 audit 把“L1 不适用”当成必须为真的语义项。
- 修复：audit 将 `hold_applicable` 移出 `semantics` 必须项，仅保留为输出字段；L1 仍要求**无** `recovery_hold`/trace（`hold_ok=True` as N/A）。
- 对**同一 slot1 结果**重跑完整 audit → **exit 0**、`observation_semantics_valid=true`、`overall_valid=true`；未重跑仿真。

## 3. 队列状态

| 槽 | 状态 |
|---:|---|
| 1 4100 single | 已运行，accepted；初次 audit exit 5（L1 语义缺陷），同结果复审计 exit 0 |
| 2 4100 arc4 | 未运行 |
| 3–4 4202 s/a | 未运行 |
| 5–6 4302 s/a | 未运行 |
| 7 4201 single | 未运行 |

`batch.log` 最后一行 `HOLD120RC7_QUEUE_PAUSED slot=1 reason=audit_failed`；`attempts.jsonl` 1 started + 1 paused；无 `completed`。

## 4. 判读与恢复

- **不是物理/证据失败**：slot1 质量 accepted、证据完整；暂停来自 audit 的 L1 N/A 处理缺陷。
- 按停止规则，队列已暂停且未自动补跑。**恢复需要明确指令**：可保留 slot1 结果，从 slot 2 继续；或按新要求重跑 slot1。不得覆盖已保留记录。
- 未运行剩余六槽；未 freeze、未写回执、未跑 held-out/正式批次；正式成功仍为 0。
- 不延长保持、不扫摩擦、不扩大 patch。

## 5. 产物

- [slot1 运行](hold120_rc7/day4-a5-rc2-l1-20261105-081311-735952)
- [复审计](hold120_rc7/a5-rc8b-recovery-hold120-rc7-runs/slot1-postaudit.json) · [日志](hold120_rc7/a5-rc8b-recovery-hold120-rc7-runs/slot1-postaudit.log)
- [账本 batch.log](hold120_rc7/a5-rc8b-recovery-hold120-rc7-runs/batch.log) · [attempts.jsonl](hold120_rc7/a5-rc8b-recovery-hold120-rc7-runs/attempts.jsonl)
- [候选登记](../../a5-rc8b-recovery-hold120-rc7/registration.json)
