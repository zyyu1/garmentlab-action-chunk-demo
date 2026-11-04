# a5-rc2-pfs1-observation-v2-rc7：七例 RC 最终候选（已登记；预检通过后按槽执行）

本目录把两次单例验证（4202、4302）的物理/控制逻辑固定为**同一个最终候选**，并把 L1 runner 接入同一观测方案；七例 RC 全部使用这一版本、一个新 manifest 和一个新批次账本。旧的 4202/4302 单例与 RC2 结果保留，**不插入本轮矩阵**。

**状态：七例队列已完成，未放行。** 7/7 槽证据完整、三组 single/arc4 配对目标差 **0.0**；六个阳性中 **4 个 accepted**（4202 s/a、4302 s/a），**4100 s/a 质量拒绝**（L1 自由边未落到桌面、残余速度超限），4201 为有效拒绝。放行条件 1（六阳性全部接受）与 verify-dev 均失败 → **不冻结、不放行**；正式 Stage 4 成功仍为 0。完整审查见 [review.md](../results/RC7_SEVEN_CASE_20261104/review.md)。**后续：rc8 已按 task-scoped 协议（L1=0.0、L2/L3=1.0）修正并通过七例 RC，见 [rc8](../a5-rc2-pfs1-observation-v2-rc8/README.md)；本目录保留为失败候选，结果不并入 rc8 矩阵。**

## 1. 身份

| 项目 | 值 |
|---|---|
| 版本 | `a5-rc2-pfs1-observation-v2`（final candidate `rc7`） |
| 父版本 | `a5-rc2-pfs1-observation-v2` |
| 父 manifest | `d97bf349dc8a7813ab274da52c4a16c69a11b9135717a6851abbd6192cf3b73f`（63 项） |
| 新 manifest | `bcba8c11b5c65b179227a01feef343b3d90be415776f216d8aefb1424ed18a2a`（63 项） |
| 变化项 | `a5_l1.py`、`a5-rc2-pfs1-observation-v2.json`、`run-a5-rc2-pfs1-observation-v2.sh`（3 项） |
| 未变项 | **60/63** 与 v2 逐字节相同（含 `a5_recovery.py`、`a5_capture.py`、`pfs1_observation_v2.py`、`stage4_success_v1.py`） |
| 新锁/账本 | `/root/autodl-tmp/a5-rc2-pfs1-observation-v2-rc7-runs`（`batch.lock`、`attempts.jsonl`、`journal/`、`batch.jsonl`、`completed`） |
| 登记/审计 | [registration.json](registration.json)、[static-audit.json](static-audit.json)、[source-diff.md](source-diff.md)、[audit_rc7_case.py](audit_rc7_case.py) |

## 2. 物理配置范围（运行前固定）

| 档位 | particleFrictionScale | 说明 |
|---|---:|---|
| L1 flat（4100） | **1.0** | 统一应用；4100 single/arc4 承担该变更的 L1 回归检查 |
| L2 perturbed（4201/4202） | **1.0** | 与 4202 单例一致 |
| L3 crumpled（4302） | **1.0** | 与 4302 单例一致 |

- `friction=0.3`、地面/碰撞/材质绑定、公开动作数（L1 7 / L2-L3 12）、命令、horizon、退让目标、evaluator 与 **1 mm / 3 mm** 阈值不变。
- 无 task-scoped override；不在运行后切换。
- `a5_l1.py` 的唯一物理改动是 `particle_friction_scale` 0.0 → 1.0；另加只读观测钩子（材料读回、`initial_loaded`/`pre_release` 状态）。

## 3. 七例矩阵（顺序执行，每槽一次）

| 槽 | seed | 档位/任务 | 模式 | 动作 | 通过要求 |
|---:|---:|---|---|---:|---|
| 1 | 4100 | L1 独立过折 | single | 7 | 质量接受、证据完整 |
| 2 | 4100 | L1 独立过折 | arc4 | 7 | 同上；与槽 1 目标一致（1e-6） |
| 3 | 4202 | L2 nominal right | single | 12 | 质量接受、证据完整 |
| 4 | 4202 | L2 nominal right | arc4 | 12 | 同上；与槽 3 目标一致 |
| 5 | 4302 | L3 nominal right | single | 12 | 质量接受、证据完整 |
| 6 | 4302 | L3 nominal right | arc4 | 12 | 同上；与槽 5 目标一致 |
| 7 | 4201 | L2 历史失败对照 | single | 12 | 证据完整，接受或拒绝均可 |

初态全部复用 `a5-candidate.json` 登记的目录与哈希，不重生；同 seed 的 single/arc4 共用同一初态。

## 4. 证据与判定

- **原 RC 采集要求**：由原版 `a5_entry.py` 的 `assess()` 检查（video/samples、actual_sim、source、input hashes、identity、budget、horizons、final_open、upward target、clock、absolute clock、double hold、terminal）。
- **v2 观测语义**：由 [audit_rc7_case.py](audit_rc7_case.py) 逐例检查（必需文件、stage、FD 速度策略、raw readback unvalidated、材料四/五阶段读回、binding、self/non-particle、solver-effective 边界、contact 能力、release clock、证据 manifest 哈希）。L1 无 recovery，故材料/ stage 要求为 4 阶段。
- **速度**：只用世界顶点位置有限差分；raw readback 标 unvalidated。
- **接触**：cloth-ground 力/冲量不可得，0 事件不是无接触，不作为门槛。
- **配对**：同 seed single/arc4 的公开 target 绝对容差 **1e-6**；labels/commands/horizons 必须一致。

## 5. 停止规则

| 情况 | 处理 |
|---|---|
| 身份、manifest、初态哈希或预检不符 | 启动前停止（exit 4） |
| 缺结果、执行错误、采集不完整、观测语义失败 | 立即暂停队列（exit 3），保留现场 |
| 六个阳性之一质量拒绝但证据完整 | 记录冻结失败，继续其余登记例 |
| 同 seed 配对 target 超出 1e-6 | 暂停队列（exit 3） |
| 运行中需要改代码/参数/阈值 | 结束本候选批次；新版本另行登记 |

## 6. 队列结果

| 槽 | seed / 模式 | 质量 | 质心 / P95 (mm) | 几何窗口 | stable | 配对差 (m) |
|---:|---|---|---:|---|---|---:|
| 1 | 4100 single | **rejected** | 0.7031 / 1.7764 | **false** | false | — |
| 2 | 4100 arc4 | **rejected** | 0.7031 / 1.7764 | **false** | false | 0.0 |
| 3 | 4202 single | accepted | 0.2642 / 0.3792 | true | true | — |
| 4 | 4202 arc4 | accepted | 0.2642 / 0.3792 | true | true | 0.0 |
| 5 | 4302 single | accepted | 0.2390 / 0.3524 | true | true | — |
| 6 | 4302 arc4 | accepted | 0.2390 / 0.3524 | true | true | 0.0 |
| 7 | 4201 single | rejected（有效） | 0.9409 / 2.8073 | true | false（speed p95） | — |

- 4100 失败机制：`free_edge_overrun` 15.4 mm < 20 mm、`free_edge_height_p90` 24.4 mm > 15 mm、`vertex_speed_max` 64.6 mm/s > 50 mm/s（RC2 4100：40.7 / 10.1 / 16.5）。uniform pfs=1.0 使 flap 没有滑到边缘外桌面，L1 过折的自重锁没有发生。
- 4202/4302 与先前单例逐值相同（同初态、同代码、确定性）。
- 7/7 文件与语义完整；ledger/evidence 哈希全过；材料 live 读回含 L1 均为 particleFrictionScale 1.0。
- 原版 `verify-dev` 失败：`Expected positive smoke case failed: …l1-20261104-212326-225911`，exit 1。
- 下载核验 765/765；中途一次启动阶段终止的会话已保留于 `runs.aborted-20261104T1304Z`，不计入槽结果。

## 7. 放行判定与下一步

| 放行条件 | 结果 |
|---|---|
| 六个阳性全部接受 | **未满足（4/6）** |
| 七例证据完整 + 三组配对 | 满足 |
| 视频目视（释放/退让/无持续支撑） | 4202/4302 末帧机械臂撤离、布料在桌面；4100 flap 仍立起；4201 已折但滑移 |
| 本地复算与远端一致 | 满足（765/765 哈希） |
| 原版 verify-dev | **失败（4100）** |

**结论：不冻结、不释放。** 下一版本需另行登记 task-scoped 物理配置（L1=0.0、L2/L3=1.0）并重跑整个七例矩阵；本轮不得在赛后切换参数。本轮结果保留，不插入新矩阵。
