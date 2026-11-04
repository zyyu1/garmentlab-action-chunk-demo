# rc8b 七例 RC 审查：初态协议通过，4202/4201 阳性失败 → 未冻结

**结论：** rc8b 的初态协议已补齐并通过全部离线/远端检查（初态记录任务、材料绑定、scale 读回、生成器身份；正式 preflight 拒绝旧/错初态），七例也全部执行且证据完整、三组配对 0 差；但**新生成的 L2 初态导致 4202 s/a 与 4201 阳性/负例都出现大幅滑移**：4202 质量拒绝（质心 7.4809 mm、P95 11.5382 mm、`stationary_half` 29.9 mm > 25 mm、速度 P95 25.7 mm/s），4201 也拒绝。六阳性只有 4 个 accepted → **不冻结、不释放**；按预登记保留失败，**不回退旧初态、不沿用 rc8 结果补齐**。正式 Stage 4 成功仍为 0。

## 1. 登记与协议

| 项目 | 值 |
|---|---|
| 版本 / manifest | `a5-rc2-pfs1-observation-v2`（rc8b）/ `cce573dd…`（63 项；52 项与 rc8 逐字节相同） |
| 任务协议 | L1 flat 0.0；L2/L3 1.0；初态生成、reset、rollout 同一配置；路由只按任务身份 |
| 初态 | 4100 `…20261105-014501-526555`、4201 `…014825-318974`、4202 `…015817-115841`、4302 `…020706-026048`，各生成一次、无重试 |
| 初态协议 | `stage4-initial-v2-task-scoped`；记录 task/level/seed、expected+readback scale、材料绑定、生成器脚本+files manifest 哈希 |
| 正式 preflight | 接受新初态；拒绝旧 4100（无 protocol）、错误 scale、缺失绑定、生成器不符、缺失 protocol（离线测试 7/7） |
| 批次账本 | `…-rc8b-runs`；attempts 14 行（7 started + 7 finished）；`completed` 写入 |

## 2. 新初态与任务定义

| seed | 初态族 | 宽度 | extent (m) | 旧 extent (m) | 初态 final 差异（新 vs 旧） |
|---:|---|---|---|---|---|
| 4100 | flat | — | 0.4129 × 0.4129 | 同值 | 逐位相同 |
| 4201 | perturbed | bottom 0.1793 | 0.4283 × 0.2669 | 0.4286 × 0.2678 | 质心 0.98 mm / max 1.51 mm |
| 4202 | perturbed | bottom 0.1714 | 0.4213 × 0.2558 | 0.4206 × 0.2541 | 质心 2.80 mm / max 3.74 mm |
| 4302 | crumpled | left 0.2000 | 0.2674 × 0.4315 | 0.2847 × 0.4357 | 质心 5.40 mm / max 24.14 mm |

L2 条宽仍在冻结范围；L3 为 width 0.20 的 left 条，z_p95≈0.069 m，未摊平。L3 的 extent 变化较大（x −17 mm，局部最大 24 mm），但本 seed 的 rollout 仍 accepted；L2 的初态差异虽小（约 3 mm），rollout 却失败——说明 L2 对初态细节敏感，不能按差异大小推断结果。

## 3. 七例结果

| 槽 | seed / 模式 | 质量 | 质心 / P95 (mm) | 几何 | stable | 配对差 | 初态协议 |
|---:|---|---|---:|---|---|---:|---|
| 1–2 | 4100 single/arc4 | **accepted** | 0.1435 / 0.2072 | true | true | 0.0 | 0.0 |
| 3–4 | 4202 single/arc4 | **rejected** | 7.4809 / 11.5382 | **false** | false | 0.0 | 1.0 |
| 5–6 | 4302 single/arc4 | **accepted** | 0.2756 / 0.4125 | true | true | 0.0 | 1.0 |
| 7 | 4201 single | rejected（有效） | 7.0657 / 10.4252 | **false** | false | — | 1.0 |

- 六阳性：4100 s/a + 4302 s/a = 4/6 accepted；4202 s/a rejected → 放行条件 1 失败。
- 三组配对 target 差 0.0；`initial_protocol=true` 7/7；材料读回 scale 与任务一致。

## 4. 4202/4201 失败分析

- 4202：`final_geometry.stationary_half=false`（82 帧失败），`stationary_drift_mean=29.9 mm > 25 mm`；稳定性质心 7.4809 mm、P95 11.5382 mm、速度 P95 25.7 mm/s、最大 39.8 mm/s。
- 4201：同类失败（`stationary_drift_mean=30.1 mm`，质心 7.0657、P95 10.4252，88 帧）。
- 4202 的 recovery 仍完全展平（rigid residual 9.2 µm，extent 0.4410×0.4410），失败发生在 fold 之后：新初态的 fold 最终 extent **0.1958×0.4078**，旧初态同流程为 **0.2283×0.4199**；折后半片在形式窗口中整体滑移约 30 mm。
- 这不是评价器/阈值变化（未改），也不是初态协议检查失败（7/7 通过）；是新初态（1.0 下 settle）改变了 L2 的折叠后保持行为。具体机制未隔离，不能写成“摩擦导致”的因果结论。

## 5. 门禁

| 门禁 | 结果 |
|---|---|
| 六阳性全部接受 | **失败（4/6）** |
| 4201 有效评价 | 是（有效拒绝） |
| 七例证据完整 + 三组配对 | 通过（7/7 语义；配对 0.0） |
| 下载核验 | **765/765** 哈希一致 |
| 本地复算 | 7/7 status/stability 逐值相同 |
| 视频 | 4202/4201 末帧布料随臂靠近、滑移；4100/4302 末帧机械臂撤离、布料在桌面 |
| 原版 verify-dev | **失败**于 4202 arc4（`Expected positive smoke case failed`，exit 1） |

## 6. 判定与下一步

- **不冻结、不释放**；`verified-dev.json` / `E_RELEASE.json` 未写；rc8b 的失败七例保留，不用 rc8 的通过结果补 4202/4201。
- 不把“初态协议补齐”当成通过：协议实现与初态身份检查通过，但新初态使 L2 阳性失败；这是本轮的有效结果。
- 下一步需要决定（不在本轮自动执行）：
  1. 调查 L2 初态在 1.0 下的敏感性/折叠后保持（例如对比新初态的条带内部状态、recovery 后残余接触），再决定是否调整初态生成参数；
  2. 或显式修订协议（例如 L2/L3 初态生成 0.0、rollout 1.0），把它作为新的、登记过的任务配置，再重跑七例。
- 不能通过回退旧初态、复用 rc8 结果或改阈值来绕过；正式成功仍为 0。

## 7. 产物

- [初态生成审查](../RC8B_INITIALS_20261105/review.md)
- [cases.csv](cases.csv) / [cases.json](cases.json) / [rc8b_cases.png](rc8b_cases.png)
- [local_recompute.json](local_recompute.json) / [verify-dev 日志](rc8b-verify-dev.log)
- [视频帧接触表](rc8b_contact_sheet.png)（[帧目录](rc8b_frames)）
- 批次账本：[batch_summary.json](a5-rc2-pfs1-observation-v2-rc8b-runs/batch_summary.json)、[batch.jsonl](a5-rc2-pfs1-observation-v2-rc8b-runs/batch.jsonl)、[attempts.jsonl](a5-rc2-pfs1-observation-v2-rc8b-runs/attempts.jsonl)、[batch.log](a5-rc2-pfs1-observation-v2-rc8b-runs/batch.log)
- 逐槽语义：[slot1](a5-rc2-pfs1-observation-v2-rc8b-runs/slot1-semantics.json) … [slot7](a5-rc2-pfs1-observation-v2-rc8b-runs/slot7-semantics.json)
- 版本登记：[rc8b](../../a5-rc2-pfs1-observation-v2-rc8b/README.md)
