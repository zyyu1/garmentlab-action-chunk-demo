# Stage 4 最低完成验收方案（已登记，未运行）

**状态：** 已登记；正式结果尚未产生。原 60 初态/120 槽计划保留但被本方案取代；不删除历史。

## 1. 原计划处置

- 原 `formal_hold120`（60 初态/120 槽）**未启动**：无 `stage4-formal-hold120-formal-v1`、无正式 attempts/completed、无 episode。
- 标记为 **被最低验收方案取代**；原 plan、slots、deployment manifest 和历史文档全部保留。
- 不沿用原 120 槽账本；本方案使用独立 plan、deployment identity、state/ledger。

## 2. 固定矩阵（single expert）

| 档 | seeds（固定顺序） | 最大尝试 |
|---|---|---:|
| L1 flat | 4110–4129 | 20 |
| L2 perturbed | 4210–4229 | 20 |
| L3 crumpled | 4310–4329 | 20 |

- 每档仅运行 **single**，不使用 arc4。
- 不换 seed、不自动重试、不调阈值。
- 与 dev seeds 无重叠；不生成 held-out 之外的新 seed。

## 3. 停止规则（预先登记）

- 每档取得 **5 个不同 seed 的有效成功**后立即停止该档。
- 有效成功：原质量评价 accepted + 修订观测/hold 审计完整有效。
- 全部失败/错误保留；拒绝率按 `(rejected+error)/attempts`。
- 最多尝试该档 20 个 seed；不足 5 成功 → 该档验收未通过。
- 执行/证据/观测异常按原规则暂停，不重试。
- 不把“5 成功即停”解释为固定样本量成功率或策略性能。

## 4. 初态与截图

- 每档先固定生成前 10 个 seed 的最终协议初态（共 30 份）。
- 每档保存至少 10 份 `initial.png` 截图及 `initial_geometry.npz` 哈希。
- 折叠 episode 只为达到 5 成功所需 seed 运行；无需把 10 个截图初态全部跑完。
- 若折叠需要第 11–20 个 seed，按固定顺序生成；不跳 seed。

## 5. 机时与容量估算

| 项目 | 估算 |
|---|---|
| 30 份初态 | 约 1–1.5 h；约 15 MB |
| 期望 episode（5/档，共 15） | 4.5–5 h |
| 可能 episode（至 30，共 30） | 9–10 h |
| 最坏（60） | 约 18 h |
| 磁盘 | 15–60 episodes × ≤20.1 MB ≈ 0.3–1.3 GB；加初态/截图/日志 <1.5 GB |
| 远端可用 | 14 GB |

## 6. 结果报告

按档报告 successes、attempts、rejected、error、rejection_rate、stop_reason；明确采集规则。验收通过仅当三档均 ≥5 有效成功。正式 Stage 4 成功计数仍以实际执行为准；本轮登记为 0，未运行。
