# rc7 七例 RC 审查（最终候选：uniform particleFrictionScale=1.0）

**结论：** 队列完整执行，7/7 槽证据完整，三组 single/arc4 配对目标差 **0.0**；但六个阳性中只有 **4 个 accepted**（4202 s/a、4302 s/a），**4100 s/a 质量拒绝**（L1 回归失败），4201 有效拒绝。放行条件 1（六阳性全部接受）**未满足** → **不放行、不冻结**；原版 `verify-dev` 按预期在 4100 处失败。正式 Stage 4 成功仍为 0。

## 1. 运行与身份

| 项目 | 值 |
|---|---|
| 版本 / manifest | `a5-rc2-pfs1-observation-v2`（rc7）/ `bcba8c11…`（63 项；60 项与 v2 逐字节相同） |
| 变化项 | `a5_l1.py`（pfs 0→1 + 观测接入）、登记 JSON、runner |
| 批次账本 | `<remote-root>/a5-rc2-pfs1-observation-v2-rc7-runs`（7 槽 × started/finished，共 14 条；`completed` 写入） |
| 执行 | 顺序 7 槽，每槽一次 `a5_entry.py run`，无自动重试；`errors=[]` |
| 下载核验 | **765/765** 文件 remote↔local SHA256 一致 |
| 预检 | `RC7_PREFLIGHT_OK 63 bcba8c11… cases 7` |
| 中途事件 | 第一次会话在 Isaac 启动阶段被操作者终止（无 episode 结果），保留于 `runs.aborted-20261104T1304Z`；同一 manifest 于 13:09:21Z 重新开始，未计入任何槽结果 |

## 2. 矩阵结果

| 槽 | seed / 档位 / 模式 | 质量 | 质心 mm | P95 mm | 几何全窗口 | stable | 配对差 | 判定 |
|---:|---|---|---:|---:|---|---|---:|---|
| 1 | 4100 L1 / single | **rejected** | 0.7031 | 1.7764 | **false** | false | — | 冻结失败 |
| 2 | 4100 L1 / arc4 | **rejected** | 0.7031 | 1.7764 | **false** | false | 0.0 | 冻结失败 |
| 3 | 4202 L2 / single | accepted | 0.2642 | 0.3792 | true | true | — | 通过 |
| 4 | 4202 L2 / arc4 | accepted | 0.2642 | 0.3792 | true | true | 0.0 | 通过 |
| 5 | 4302 L3 / single | accepted | 0.2390 | 0.3524 | true | true | — | 通过 |
| 6 | 4302 L3 / arc4 | accepted | 0.2390 | 0.3524 | true | true | 0.0 | 通过 |
| 7 | 4201 L2 / single | rejected | 0.9409 | 2.8073 | true | false | — | 有效拒绝 |

四例 accepted 的 `held` / `released_continuously` 均为 true；`errors=[]`；动作数 7（L1）/12（L2-L3），horizon 符合登记（arc4：`[1,1,4,1]` / `[1]*7+[4,1]`）。

## 3. 4100（L1）为什么被拒绝

L1 在 uniform `particleFrictionScale=1.0` 下折叠仍完成（`crossed_fraction=1.0`），但几何与稳定检查失败：

| 指标 | RC2 4100（pfs=0） | rc7 4100（pfs=1） | L1 阈值 |
|---|---:|---:|---|
| `free_edge_overrun` | 40.68 mm | **15.43 mm** | 20–60 mm → 失败 |
| `free_edge_height_p90` | 10.07 mm | **24.43 mm** | ≤15 mm → 失败 |
| `geometry_entire_window` | true | **false**（121/121 帧） | — |
| `vertex_speed_max` | 16.53 mm/s | **64.64 mm/s** | ≤50 → 失败 |
| 质心 / P95 | 0.144 / 0.207 mm | 0.703 / 1.776 mm | 1 / 3 mm → 通过 |

**机制解释：** 自由边只越过折线约 15 mm（要求 ≥20 mm），且停在桌面以上约 24 mm（要求 ≤15 mm），说明提高粒子间摩擦后 flap 没有像 pfs=0 那样滑过静止半片并落到边缘外桌面；L1 过折依赖的“自由边落到桌面、自重锁住”没有发生，随后仍有约 64.6 mm/s 的残余运动（速度上限 50 mm/s）。这不是评价器阈值变化（阈值未改），而是该物理参数与 L1 折形定义不相容。

4100 的 single 与 arc4 逐项相同（质心/P95/几何/速度、target 差 0.0），说明失败是确定性的，不是模式或采样噪声。

## 4. 4201（历史失败对照）

- `geometry_entire_window=true`、9 项几何检查全过、`crossed=1.0`（这次折形过线），但 `vertex_speed_p95 = 20.27 mm/s > 10 mm/s` → `stable=false`，质量 **rejected**。
- 质心 0.9409 mm、P95 2.8073 mm 虽在 1/3 mm 内，但速度判据独立失败。
- 按预登记，“4201 有效拒绝或接受均可继续；不得强制其失败”——本槽按有效拒绝记录，未重跑、未调参。

## 5. 4202 / 4302（pass）

| 指标 | 4202 s/a | 4302 s/a |
|---|---:|---:|
| 质心 / P95 | 0.2642 / 0.3792 mm | 0.2390 / 0.3524 mm |
| 释放后 0.5 s 质心 / 粒子 | 11.56 / 15.00 mm/s | 12.40 / 15.70 mm/s |
| 1.5–8.0 s 质心 / 粒子 | 0.595 / 1.375 mm/s | 0.372 / 0.659 mm/s |
| z_min | 9.8676 mm | 9.8670 mm |

与先前两次 4202/4302 单例逐值相同（同一初态、同一物理/代码、确定性运行），说明本轮没有引入新的物理差异；这是它们第一次在**同一 manifest、同一批次、同一账本**下与 L1/4201 一起运行。

## 6. 表示配对

- 4100：`target_max_abs = 0.0`；质心、P95、几何、速度逐值相同。
- 4202：`target_max_abs = 0.0`；五项指标逐值相同。
- 4302：`target_max_abs = 0.0`；五项指标逐值相同。
- 三组 labels/commands/horizons 完全一致；arc4 的 chunk 边界没有引入目标漂移。

## 7. 证据完整性与 verify-dev

- 7/7 槽：`file_complete=true`、`observation_semantics_valid=true`（12/12 检查）、ledger/evidence 哈希全过；材料读回 live 值 friction 0.3 / particleFrictionScale **1.0**（含 L1），`solver_effective` 仍 unverified；contact 能力边界记录。
- 原版 `a5_entry.py verify-dev --journal …`（同一入口、新 manifest、逻辑与阈值未改）：**失败**，`ValueError: Expected positive smoke case failed: …/day4-a5-rc2-l1-20261104-212326-225911`，exit 1。它正确地拒绝了“阳性 4100 被质量拒绝”的候选。
- 放行条件核对：① 六阳性全部接受 **未满足**（4/6）；② 证据完整 + 三组配对 **满足**；③ 视频目视：4202/4302 末帧机械臂已撤离、布料在桌面；4100 末帧 flap 仍立起而未摊到边缘外桌面；4201 布料已折但持续滑移；④ 本地复算与远端一致（765/765 哈希；用未修改的 `stage4_success_v1.evaluate` 对 7 例本地重算，status 与 stability 全部逐值相同，见 [local_recompute.json](local_recompute.json)）；⑤ verify-dev **失败**。

## 8. 判定与建议

**本轮不冻结、不放行。** uniform `particleFrictionScale=1.0` 对 L2/L3 有效（0.26/0.38、0.24/0.35 mm，均 accepted），但对 L1 过折不兼容（自由边未落到桌面、残余滑移超速）。

建议下一版本（需另行授权，不在本轮执行）：登记 **task-scoped** 物理配置——L1 `particleFrictionScale=0.0`（保留其冻结折形与已验证的过折行为），L2/L3 `=1.0`；保留本轮全部观测接入与 `a5_l1.py` 只读钩子，manifest 重新计算，七例矩阵在新版本下**全部重跑**（本轮结果保留但不插入新矩阵）。这样 4100 承担的是 L1 观测接入的回归，而不是一个与 L1 折形定义冲突的物理改动。

不得在赛后切换参数来“补救”本轮结果；本轮结论保持为：uniform 版本 4/6 阳性通过，L1 回归失败。

## 9. 产物

- [cases.csv](cases.csv) / [cases.json](cases.json) / [rc7_cases.png](rc7_cases.png)
- [local_recompute.json](local_recompute.json)（本地 evaluator 重算，7/7 status 与 stability 逐值一致）
- [rc7_contact_sheet.png](rc7_contact_sheet.png)（7×6 视频帧；[帧目录](rc7_frames)）
- 批次账本：[batch_summary.json](a5-rc2-pfs1-observation-v2-rc7-runs/batch_summary.json)、[batch.jsonl](a5-rc2-pfs1-observation-v2-rc7-runs/batch.jsonl)、[attempts.jsonl](a5-rc2-pfs1-observation-v2-rc7-runs/attempts.jsonl)、[batch.log](a5-rc2-pfs1-observation-v2-rc7-runs/batch.log)
- 逐槽语义：[slot1](a5-rc2-pfs1-observation-v2-rc7-runs/slot1-semantics.json)、[slot2](a5-rc2-pfs1-observation-v2-rc7-runs/slot2-semantics.json)、[slot3](a5-rc2-pfs1-observation-v2-rc7-runs/slot3-semantics.json)、[slot4](a5-rc2-pfs1-observation-v2-rc7-runs/slot4-semantics.json)、[slot5](a5-rc2-pfs1-observation-v2-rc7-runs/slot5-semantics.json)、[slot6](a5-rc2-pfs1-observation-v2-rc7-runs/slot6-semantics.json)、[slot7](a5-rc2-pfs1-observation-v2-rc7-runs/slot7-semantics.json)
- verify-dev：[rc7-verify-dev.log](rc7-verify-dev.log)
- 版本登记：[a5-rc2-pfs1-observation-v2-rc7](../../a5-rc2-pfs1-observation-v2-rc7/README.md)
