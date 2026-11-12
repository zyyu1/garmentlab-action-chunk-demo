# a5-rc2-pfs1-observation-v2-4302：4302 single 单次扩展（已登记；预检通过）

本目录是固定候选 **a5-rc2-pfs1-observation-v2** 的单次跨 seed 扩展：只把登记范围从 4202 single 扩展到预登记的 **4302 single**，物理参数、控制、采样、评价器与观测代码与 v2 **逐字节相同**（63 项 manifest 中 61 项不变；仅登记 JSON 与 runner 脚本变化）。旧 v2 目录、4202 结果、v2 完成标记与旧锁全部保留。

**状态：4302 single 已完成并通过。** 远端预检 63/63；单次运行 `overall_valid=true`、质量 **accepted**、几何全窗口通过、正式窗口质心 **0.2390 mm** / P95 **0.3524 mm**（RC2 4302 single：1.9102 / 4.1231 mm），无重试。完整对照见 [review.md](../results/PFS1_V2_EXT_4302_20261104/review.md)。这是单 seed 单次结果，不是跨 seed 统计，也不确认具体摩擦机制；正式 Stage 4 成功仍为 0。

## 1. 身份

| 项目 | 值 |
|---|---|
| 版本 | `a5-rc2-pfs1-observation-v2`（extension `4302-single`） |
| 父版本 | `a5-rc2-pfs1-observation-v2` |
| 父 manifest | `d97bf349dc8a7813ab274da52c4a16c69a11b9135717a6851abbd6192cf3b73f`（63 项） |
| 新 manifest | `6d1958f5b1c6828d79821dc7831dcc1c1bcf3bed07cca9b17c6e04de0eaaccc3`（63 项） |
| config | `577931aaacde3177b01080c2c04b27a5378a6fbfdc6cd8a06d83ab803b2dfbd5` |
| runner | `550efa6576d82d45786d2c1179da2ae8ad548b01f1da6c99dff39c7624fa453e` |
| 4302 初态 | `day4-square-initial-stripfold-20261103-094143-137994`；`result.json` `1bed437f…`、`initial_geometry.npz` `1c27514f…`；**不重生** |
| 新锁/账本 | `<remote-root>/a5-rc2-pfs1-observation-v2-4302-runs`（`completed`、`attempts.jsonl`、`journal/`） |
| 登记/审计 | [registration.json](registration.json)、[static-audit.json](static-audit.json)、[source-diff.md](source-diff.md)、[runner-v2-to-4302.diff](runner-v2-to-4302.diff) |

## 2. 唯一变化：登记范围与编排

| 文件 | 角色 | 变化 |
|---|---|---|
| `app/a5-rc2-pfs1-observation-v2.json` | 登记/范围 | seed 4302、level crumpled、新锁、extension 块；**仿真代码不读取该文件** |
| `app/run-a5-rc2-pfs1-observation-v2.sh` | 编排 | 4302 范围断言、新锁/账本、父 manifest 改为 v2、61/63 身份检查、4302 初态检查、ledger seed 4302 |
| 其余 61 项 | 物理/控制/观测/资产 | **SHA256 与 v2 完全相同** |

因此 4302 与 4202 的差异只应来自**初态与 seed**，不来自候选代码。

## 3. 与 v2 保持不变的项

- `particleFrictionScale=1.0`、`friction=0.3`、地面/碰撞/材质绑定不变；
- 12 个公开动作、动作逻辑、call horizon、退让目标不变；
- evaluator `stage4_success_v1` 与阈值 **1 mm / 3 mm** 不变；
- 观测语义：世界顶点 backward finite difference 速度、raw readback 标 unvalidated、五阶段材料读回、contact 能力边界；
- 4202 初态文件不重生（4302 复用自己的原登记初态，不重生）。

## 4. 远端预检（已通过）

| 检查 | 结果 |
|---|---|
| 新 manifest 63/63 路径与 SHA256 | 通过 |
| `a5-manifest.json` 与 manifest 字节一致 | 通过 |
| 父 v2 manifest SHA256 | `d97bf349…` 一致 |
| 61 项与 v2 逐字节一致；2 项按预期变化 | 通过 |
| config：extension id、scope、新锁、物理不变量、阈值 | 通过 |
| 源码：`particle_friction_scale = 1.`、无 D1/D2-C 残留、五阶段材料钩子、FD 速度 | 通过 |
| 4302 初态：目录、`result.json`、`initial_geometry.npz`、`passed=True`、level=crumpled、plan 唯一匹配 | 通过 |
| 新账本无未完成尝试；旧 v2 完成标记不复用 | 通过 |
| `bash -n`、`py_compile`（44 个 py） | 通过 |

日志：`PFS1_V2_EXT_PREFLIGHT_OK 63 d97bf349… <remote-root>/day4-square-initial-stripfold-20261103-094143-137994`。

## 5. 运行结果（单次 4302 single）

- tmux 单次 `bash run-a5-rc2-pfs1-observation-v2.sh 4302 single`；退出 0；`completed` 写入；无重试。
- 结果目录：`day4-a5-rc2-pfs1-observation-v2-20261104-201557-235290`（104 文件，remote↔local 104/104 哈希一致）。
- `file_complete=true`、`observation_semantics_valid=true`、`quality_status=accepted`、`overall_valid=true`；`errors=[]`。
- 12 个公开动作；labels/commands/horizons 与 RC2 一致。
- 评价器：`geometry_entire_window=true`、`stable=true`、`held=true`、`released_continuously=true`、`failed_geometry_frames=[]`。
- 正式 210–330：质心 **0.2390 mm**、P95 **0.3524 mm**；trace 端点 0.2390 / 0.3509 mm。
- 释放后 0.5 s：粒子 **15.70 mm/s**、质心 **12.40 mm/s**；1.5–8.0 s：质心 **0.372 mm/s**、粒子 **0.659 mm/s**、角速度 **0.092°/s**。
- 粘滞检查：release 后无 attachment/holding/latch 重新激活；OPEN 锁存仅前 10 步；夹爪张开到 0.080 m；布料不跟随 retreat 的 EE；z_min 9.867 mm，无穿透。
- 材料五阶段 live 读回：friction 0.3、particleFrictionScale 1.0、binding `/World/Garment/particleMaterial`、self/non-particle true；`solver_effective` 仍 unverified。
- 与 RC2 的 fold 目标差 7.7–8.0 mm、yaw −3.28°，原因是 recovery 末态相对 RC2 平移 10.27 mm 后 expert 按未改逻辑重算目标；这是端到端对比，不是固定动作对照。

## 6. 判定规则、结果与后续

| 4302 结果 | 后续 |
|---|---|
| **质量接受且证据完整（本次）** | **固定最终候选，准备完整七例 RC** |
| 质量拒绝但证据完整 | 保留跨 seed 失败，分析后决定修正 |
| 执行或证据异常 | 保留现场，先解决异常 |

通过条件均满足：文件完整、观测语义有效、几何全窗口通过、质心 0.2390 mm ≤ 1 mm、P95 0.3524 mm ≤ 3 mm；recovery、释放与粘滞检查通过。

下一步（需另行明确指令）：准备七例 RC 的例表、身份与停止条件；本轮**不**运行七例、不冻结、不跑 held-out/正式批次、不扫参数、不重跑 4202/4302。

## 7. 边界

- 只跑 **4302 single 一次**；不重跑 4202、不跑七例 RC、不冻结、不跑 held-out、不跑正式批次、不扫参数。
- 单例通过只说明该 seed 在该候选下通过，不足以宣称跨 seed 普遍有效，也不确认具体摩擦机制。
- cloth-ground 力/冲量不可得，0 事件不是无接触；材料读回是 scene/USD，`solver_effective` 仍为 unverified。
- 正式 Stage 4 成功计数仍为 **0**；不宣称“地面摩擦已修复”。
