# rc8 task-scoped 七例 RC 审查（通过）

**结论：** 七槽全部完成，**六个阳性全部 accepted**，4201 为有效拒绝；三组 single/arc4 配对 target 差 **0.0**；7/7 证据完整、807/807 下载哈希一致、本地 evaluator 重算 7/7 逐值相同；原版 `verify-dev` **通过**（`A5_DEV_VERIFIED 7`，exit 0）。候选通过本轮 RC 放行条件，已整理冻结材料；**本轮未执行 freeze / held-out**，正式 Stage 4 成功仍为 0。

## 1. 登记与执行

| 项目 | 值 |
|---|---|
| 版本 / manifest | `a5-rc2-pfs1-observation-v2`（rc8）/ `68930010…`（63 项；59 项与 v2 逐字节相同） |
| 任务协议 | L1 flat **0.0**；L2/L3 **1.0**；材料构造时设置，早于 reset/物理步；路由不读取 seed/mode/结果 |
| 变化项 | `a5_l1.py`、`pfs1_observation_v2.py`（expected scale 参数化）、登记 JSON、runner |
| 批次账本 | `…-rc8-runs`；attempts 14 行（7 started + 7 finished）；`completed` 写入；无重试 |
| 预检 | `RC8_PREFLIGHT_OK 63 68930010… cases 7` |
| 下载 | 807/807 remote↔local SHA256 一致（另含单独下载的 verify-dev 日志） |

## 2. 矩阵结果

| 槽 | seed / 档位 / 模式 | 质量 | 质心 / P95 (mm) | 几何 | stable | 配对差 | 材料 expected |
|---:|---|---|---:|---|---|---:|---:|
| 1 | 4100 L1 / single | **accepted** | 0.1435 / 0.2072 | true | true | — | **0.0** |
| 2 | 4100 L1 / arc4 | **accepted** | 0.1435 / 0.2072 | true | true | 0.0 | **0.0** |
| 3 | 4202 L2 / single | **accepted** | 0.2642 / 0.3792 | true | true | — | 1.0 |
| 4 | 4202 L2 / arc4 | **accepted** | 0.2642 / 0.3792 | true | true | 0.0 | 1.0 |
| 5 | 4302 L3 / single | **accepted** | 0.2390 / 0.3524 | true | true | — | 1.0 |
| 6 | 4302 L3 / arc4 | **accepted** | 0.2390 / 0.3524 | true | true | 0.0 | 1.0 |
| 7 | 4201 L2 / single | rejected（有效） | 0.9409 / 2.8073 | true | false | — | 1.0 |

- 全部 `held` / `released_continuously` true；`errors=[]`；动作数 7/12；arc4 horizon `[1,1,4,1]` / `[1]*7+[4,1]`。
- 4100 结果与 RC2 4100（pfs=0）**逐值相同**（0.1435 / 0.2072），支持“rc7 的 L1 失败来自 uniform pfs=1.0”这一解释；仍按报告口径把它写成视频支持的机制解释，而非已独立确认的因果。
- 4201：几何全过、`crossed=1.0`，`vertex_speed_p95 = 20.27 mm/s > 10` → 有效拒绝；未强制、未重跑。

## 3. 任务协议核对

- 五阶段材料读回逐槽检查：L1（槽 1–2）`particleFrictionScale = 0.0`；L2/L3（槽 3–7）`= 1.0`；`material_readbacks.expected` 与各 live stage 一致；`expected_ok=true`。
- `audit_rc8_case.py` 的 `task_protocol_expected_scale` 与槽位一致（0.0 / 1.0 / 1.0）。
- 同任务 single/arc4 的配置、目标与指标逐值相同（配对差 0.0）。
- 初态复用登记目录与哈希，未重生；正式初态生成/reset/rollout 的同协议要求已写入登记（本轮不重生，L2/L3 dev 初态仍为早期 0.0 settle 的结果）。

## 4. 证据与门禁

| 放行条件 | 结果 |
|---|---|
| 六个阳性全部接受 | **满足（6/6）** |
| 4201 有效评价 | 满足（有效拒绝） |
| 七例证据完整 + 三组配对 | 满足（7/7 语义有效；配对 0.0） |
| 视频目视（释放/退让/无持续支撑） | 槽 1–6 末帧机械臂已撤离、布料在桌面；L1 flap 平铺到边缘外；4201 已折但末段仍滑移 |
| 本地复算一致 | 满足（807/807 哈希；`stage4_success_v1.evaluate` 重算 7/7 status/stability 逐值相同，见 [local_recompute.json](local_recompute.json)） |
| 原版 verify-dev | **通过**（`A5_DEV_VERIFIED 7`，exit 0，[日志](rc8-verify-dev.log)） |

## 5. 报告口径（保留）

1. 本矩阵是**按任务报告**的 task-scoped 结果，不是统一物理条件下的纯初态难度比较。
2. rc7 的 uniform pfs=1 在 4100 这个开发例上导致 L1 回归失败；自由边未落桌、自重锁未发生是视频与几何支持的机制解释，尚不宜写成已独立确认的因果机制。
3. rc7 被操作者终止的启动记录继续列入运行历史：未形成可评价 episode，不计入质量分母，但不从执行记录中消失。
4. 4201 的拒绝属于有效评价，不是“必须失败”的目标。

## 6. 判定与冻结材料

- 候选 **rc8 通过七例 RC**；本轮**不执行 freeze**、不运行 held-out/正式批次；正式 Stage 4 成功仍为 **0**。
- 已整理 [FREEZE_DOSSIER.md](FREEZE_DOSSIER.md)：候选身份、矩阵与证据哈希、门禁结果、verify-dev 输出、未完成项（held-out、正式批次、正式阈值冻结）与冻结前检查清单。
- 冻结动作本身（写 `verified-dev.json` / `E_RELEASE.json`、进入 held-out）需另行明确指令。

## 7. 产物

- [cases.csv](cases.csv) / [cases.json](cases.json) / [rc8_cases.png](rc8_cases.png)
- [local_recompute.json](local_recompute.json) / [rc8-verify-dev.log](rc8-verify-dev.log) / [download_audit.json](download_audit.json)
- [rc8_contact_sheet.png](rc8_contact_sheet.png)（7×6 视频帧；[帧目录](rc8_frames)）
- 批次账本：[batch_summary.json](a5-rc2-pfs1-observation-v2-rc8-runs/batch_summary.json)、[batch.jsonl](a5-rc2-pfs1-observation-v2-rc8-runs/batch.jsonl)、[attempts.jsonl](a5-rc2-pfs1-observation-v2-rc8-runs/attempts.jsonl)、[batch.log](a5-rc2-pfs1-observation-v2-rc8-runs/batch.log)
- 逐槽语义：[slot1](a5-rc2-pfs1-observation-v2-rc8-runs/slot1-semantics.json) … [slot7](a5-rc2-pfs1-observation-v2-rc8-runs/slot7-semantics.json)
- 版本登记：[a5-rc2-pfs1-observation-v2-rc8](../../a5-rc2-pfs1-observation-v2-rc8/README.md)
