# a5-rc2-pfs1 4202 single：粒子间摩擦敏感性结果

日期：2026-11-04。候选 `a5-rc2-pfs1` 只把活动 `ParticleMaterial` 的 `particleFrictionScale` 从 **0.0 改为 1.0**，`friction=0.3`、地面、碰撞、材料绑定、12 个公开动作/命令/horizon、退让目标和评价器均不变；从 RC2 原流程派生，不含 D1-120 等待或 D2-C preopen/释放顺序改动。

**结论先行：** 该次 4202 single 的 episode `passed=True`、质量 **accepted**；正式 210–330 窗口质心漂移 **0.2642 mm**、顶点 P95 **0.3792 mm**，低于 1 mm / 3 mm，较 RC2 的 **2.0429 / 4.4141 mm** 明显下降。但本轮存在两个**观测合规问题**：粒子速度读回与位置差分不一致，且没有运行时的粒子材料参数读回。因此这只能作为**候选改善证据**，不能当作完整通过；**不扩展到 4302 single，不运行七例、不冻结、不运行 held-out，正式成功计数仍为 0**。也不能宣称“地面摩擦已修复”。

## 1. 运行与身份

| 项目 | 值 |
|---|---|
| 结果目录 | `results/PFS1_RUN_4202_20261104/day4-a5-rc2-pfs1-20261104-102101-983000` |
| manifest | `bad4b59a0baecd08bd814bc98cfc28e7a0197fb9fed2effd21282ef40563c51b`（63 项） |
| config | `2d72a40565b3f63269fff861231255a45318618ed969bc7cf132bd041c34d32c` |
| runner | `3f9e38e3dde535d754ab01f3319d1914872bd669d1ebf3d62e6cef6c625dfa80` |
| observation | `9482847357eade07b27799134379fdf611b5e9db3dbd5fa3dea8df0acb40ed04` |
| 运行 | 远端预检通过；tmux 单次；runner 退出 0；无重试 |
| episode | `passed=True`、12 个动作、`call_horizons` 全 1、无 runtime error |
| 质量 | `accepted`；`geometry_entire_window=True`、`stable=True`、`held=True`、`released_continuously=True` |
| 证据 | `evidence/manifest.json` 73/73 哈希一致；ledger 15/16 一致，唯一缺失 `contact_report.json`（runner 记录为 present=false，非必需） |
| 源码身份 | runtime source 与本地候选逐项一致（见 [evidence_verification.json](evidence_verification.json)） |
| 初态 | 原 4202 初态复用；`result.json` `4472…`、`initial_geometry.npz` `a664…` 未变 |
| 无效尝试 | 第一次观测 API 失败保留在 [PFS1_INVALID_OBS_ATTEMPT_20261104](../PFS1_INVALID_OBS_ATTEMPT_20261104/review.md)，不计入物理对照 |

`a5-rc2-pfs1.json` 仍写着 `run_status: not_run`；它是运行前的冻结候选配置，未改动以保持 63 项 manifest 身份。运行状态记录在 `registration.json` 和本报告。**没有修改任何候选源码或 manifest。**

## 2. 结论摘要

| 指标（官方 evaluator，formal 210–330） | RC2 | pfs1 | 变化 |
|---|---:|---:|---:|
| 质心漂移 max | 2.0429 mm | **0.2642 mm** | −87.07% |
| 顶点 P95 max | 4.4141 mm | **0.3792 mm** | −91.41% |
| 顶点最大漂移 | 4.8379 mm | **0.4808 mm** | — |
| 顶点速度 P95 max | 3.4447 mm/s | **6.8672 mm/s** | 升高 |
| 顶点速度 max | 16.468 mm/s | **22.332 mm/s** | 升高 |
| 质量 | rejected | **accepted** | — |

- 几何通过、漂移阈值通过、释放/退让/证据资产完整；evaluator 判定 accepted。
- 但 pfs1 的**瞬时顶点速度 P95/max 反而高于 RC2**，说明“净漂移下降”不等于“所有运动都更平滑”。正式窗口的粒子平均速度也几乎不变（见 §7）。
- 动作 target 并未保持不变：fold 动作约 +2.0 mm、退让目标约 +2.0 mm；这是 recovery 状态变化后重新计算 pick/yaw 的结果，必须与漂移结果一起报告。
- release 前状态、recovery 后状态均与 RC2 不同；不能把 pfs1 当作“同初态、仅释放后摩擦不同”的对照。
- 本轮只跑 4202 single 一次；通过后原本应“审查再扩展 4302”，但观测问题使本轮不应直接扩展。

## 3. 关键观测问题：粒子速度读回不能作为物理速度

`pfs1_observation.py` 保存了 `ClothPrimView.get_velocities(clone=True)` 的原始读回，但该读回与同一 `PhysicsView` 的 `get_world_positions()` 位置差分**不一致**：

| formal 窗口 | 读回 | 位置差分 | 比值 |
|---|---:|---:|---:|
| 粒子平均速度 | 28.762 mm/s | 1.293 mm/s | **22.25×** |
| 质心速度 | 22.685 mm/s | 0.550 mm/s | **41.27×** |
| 读回逐粒子中位数 / P95 | 10.549 / 77.369 mm/s | — | — |
| 读回帧首尾场相关 | **0.9980** | — | 几乎不变 |
| 读回向量 vs 位置差分向量相关 | **−0.0060** | — | 无对应关系 |
| 2 s 内读回逐粒子变化 | 1.896（按读回单位） | 位置变化 0.262 mm | — |
| EE 速度 | 0.000237 mm/s | — | 机器人静止 |
| attachment / holding | false / false | — | 不是附件驱动 |

- 释放前 hold 的最后一步：读回粒子平均 **32.98 mm/s**，位置差分仅 **1.98 mm/s**（16.7×）。
- 释放第一步：读回 **38.95 mm/s**，位置差分 **17.42 mm/s**（2.24×）。
- 比例随阶段变化，不能解释为固定单位或固定帧变换；读回场在 formal 窗口几乎静止，而布料位置几乎不动，读回却不趋零。
- 读回可能表示某种内部 solver 量、局部/未投影量或其他量；**现有 API 与证据不足以确定其语义**。因此不能把它当作“实际粒子速度”，更不能据此计算冲量。
- 本报告所有速度均改为 **世界顶点有限差分**；原始读回仍保存在 NPZ 中并标记为 unvalidated，未删除。见 [velocity_readback_diagnostic.json](velocity_readback_diagnostic.json) 和 [velocity_readback_check.png](velocity_readback_check.png)。
- 这属于**观测证据缺陷**，不是物理运行失败；evaluator 的几何/漂移结论仍由位置数据支持。但它使“采集证据完整”不能无条件声明。
- runner/ledger 的 `observation_complete=true` 只表示所需文件和读回存在（`velocity_missing_count=0`），**不表示读回语义正确**；本报告不把它当作观测完整性的证明。

## 4. 动作与 target 差异

12/12 个动作 label、command、horizon 相同；target 不相同：

| 动作 | 最大绝对差 | 主要分量 |
|---|---:|---|
| `rec_approach` / `rec_pick` / `rec_lift` | 0.0509 mm | x/y 小量 |
| `rec_spread` / `rec_release` | 0.0000 mm | 无 |
| `fold_approach` … `fold_place` | 1.9688–1.9960 mm | 主要 +y，四元数约 −0.0685 |
| `release_retreat` | 1.9986 mm | +y 约 2.0 mm，z −0.015 mm |
| 动作返回 EE 最大差 | 2.0756 mm | — |

差异来自 recovery 状态下重新计算的 pick 点与 fold yaw；没有强制保留旧 pick 数值，也没有隐藏 waypoint。布料没有被重置位置或清零速度。比较漂移时必须同时考虑这 2 mm 的 target 差异。

## 5. Recovery 与 pre-release 状态

- pfs1 recovery 刚性残差 max `9.267e-6 m`、P95 `6.875e-6 m`；extent `[0.440745, 0.440750, 6.15e-8]`；fold held accepted。
- 与 RC2 的 recovery 后状态差：质心 **1.9819 mm**、P95 **1.9942 mm**、max **1.9966 mm**、旋转 **−0.00393°**。
- 与 RC2 的 pre-release 状态差：质心 **3.6128 mm**、P95 **11.5305 mm**、max **22.934 mm**、旋转 **0.00155°**、刚性 RMS **3.363 mm**。
- pre-release hold 最后一步有限差分：pfs1 粒子 **1.977 mm/s** / 质心 **1.172 mm/s**；RC2 **0.262 / 0.041 mm/s**。pfs1 持布末段不是完全静止，但仍远小于释放瞬态。
- 因此 pfs1 不是“同 recovery 状态”的对照；参数从 episode 开始就改变了 recovery/fold 形状和后续动作目标。这是候选设计的已知范围，不是隐藏改动。

## 6. Release t=0 与首个 0.5 s

**t=0 定义：** pfs1 pre-release 最后 attached 状态在 step **1947**；首个 detached 物理步为 boundary step **1948**；`released` sample 在 **1955**；采样误差 **1 步（16.7 ms）**。RC2 原流程没有零步 post-disable sample，不能声称精确解除瞬间。

- pfs1 pre-release→boundary：质心 **0.1053 mm**、P95 **0.3699 mm**、max **7.9294 mm**、旋转 **0.00406°**；boundary z_min **9.8679 mm**，无负 z。
- boundary→下一步（首个自由物理步的有限差分）：粒子平均 **17.420 mm/s**、质心 **9.771 mm/s**、角速度 **0.851°/s**。
- 首个 0.5 s（31 帧 / 30 个区间，boundary step 1948–1978）：粒子平均 **15.000 mm/s**、质心平均 **11.555 mm/s**（max 31.915）、角速度平均 **2.252°/s**；质心方向 **−4.99°**。
- 保存的 `pfs1_first_0_5s.npz` 为 30 帧 / 0.4833 s：其 boundary+0.5 比较使用 1e-9，frame 30 的时间比边界和晚 2.6e-8 s 被排除；本报告用 1e-6 边界容差纳入该帧，故为 31 帧 / 0.5 s。这是采样边缘问题，不改变物理结论。
- RC2 的 release 诊断（`STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103`）中，首个 detached→released 的 9 步段质心 4.858 mm/s，`released→command` 段 11.661 mm/s。事件定义与 pfs1 不同，**不能把 pfs1 的 11.56 mm/s 说成“冲量降低”**；这只是第一个 0.5 s 的质心速度测量。
- 作为**非同一时刻的描述性**比较：pfs1 boundary 与 RC2 `released` 帧的布料差为质心 **2.838 mm**、P95 **7.397 mm**、max **9.003 mm**、旋转 **0.440°**、刚性 RMS **2.184 mm**；pfs1 最近退让帧与 RC2 `retreated` 帧差为质心 **0.630 mm**、P95 **9.384 mm**、max **11.589 mm**、旋转 **1.635°**、刚性 RMS **2.547 mm**。两版事件与动作时序不同，这些差值只说明释放/退让状态不相同，不能当作干预效应。

## 7. 释放后速度衰减与持续滑移（全部为位置有限差分）

| 窗口 | 粒子平均 mm/s | 质心平均 mm/s | 角速度 °/s | z_min mm |
|---|---:|---:|---:|---:|
| 0–0.5 s | 15.000 | 11.555 | 2.252 | 9.868 |
| 0.5–1.0 s | 2.628 | 1.472 | 0.300 | 9.879 |
| 1.0–1.5 s | 1.444 | 0.674 | 0.135 | 9.877 |
| 1.5–2.0 s | 1.364 | 0.577 | 0.096 | 9.877 |
| 1.5–8.0 s（持续） | **1.375** | **0.595** | **0.104** | 9.877 |
| formal 210–330（trace） | **1.293** | **0.550** | **0.103** | 9.878 |

- 快速衰减发生在首个 0.5 s；1.5 s 后质心平均约 **0.59 mm/s**、粒子平均约 **1.38 mm/s**、角速度约 **0.10°/s**，没有继续明显衰减或增大。
- 持续质心方向约 **26.79°**，与 RC2 formal 的 **26.01°** 接近；pfs1 formal 方向 **26.22°**。
- 可用轨迹约 **8.05 s**，不是 10 s；因此“1.5–10 s”只能用 1.5–8.0 s 的可用窗口，不能延伸到未采集的 8–10 s。
- z_min 约 **9.867–9.879 mm**，比 10 mm contact offset 低约 **0.121–0.132 mm**；高于地面 z=0，**无地面穿透**。这是几何证据，不是接触力/冲量。
- 与 RC2 formal 的有限差分相比：pfs1 粒子平均 **1.293 vs 1.279 mm/s**（几乎相同，+1.1%）；质心 **0.550 vs 1.023 mm/s**（−46.2%）；角速度 **0.103 vs 0.360°/s**（−71.5%）。因此改善主要是**净平移/旋转**，不是局部粒子运动幅度。

## 8. 正式窗口与通过条件

| 项目 | RC2 | pfs1 |
|---|---:|---:|
| 几何全程 | pass | pass |
| `held` / `released_continuously` | true / true | true / true |
| 质心漂移 max（evaluator） | 2.0429 mm | **0.2642 mm** |
| 顶点 P95 max（evaluator） | 4.4141 mm | **0.3792 mm** |
| 顶点最大漂移 | 4.8379 mm | 0.4808 mm |
| 顶点速度 P95 / max | 3.445 / 16.468 mm/s | 6.867 / 22.332 mm/s |
| 端点质心 / P95（trace 210→330） | 2.0429 / 4.4141 mm | 0.2572 / 0.3668 mm |
| 端点旋转 | −0.7204° | −0.0334° |
| 端点刚性 RMS | 0.00111 mm | 0.01854 mm |
| 质量 | rejected | **accepted** |

- 1 mm / 3 mm 阈值以官方 evaluator 的 **max-over-window** 为准：pfs1 0.2642 / 0.3792 均通过。
- 这里的 `accepted` / evaluator `success=true` 是 **4202 single 开发质量判定**，不是 `formal_day4_success`；`result.json` 的 `formal_day4_success=false`，正式 Stage 4 成功计数仍为 0。
- 端点值（0.2572 / 0.3668）与 max 值略有差异，不矛盾；报告以 max 为准。
- pfs1 的刚性 RMS 反而高于 RC2（0.0185 vs 0.0011 mm），但绝对值仍很小；不能只说“所有几何指标都更好”。
- evaluator 的顶点速度不是通过阈值，但 pfs1 更高，提示净漂移下降与局部瞬时运动增加可能并存；需要审查，不应把它解释成“更稳定”或“更粘”。

## 9. Recovery/fold、异常粘滞、穿透

- fold：`crossed_fraction=1.0`、extent `[0.2283, 0.4199, 0.0603]`、`z_p95=0.06895`、`pick_index=230`；`fold_held_check.accepted=true`（position_error 0.01476 m，anchor_gap_max 0.00216 m）。
- recovery：见 §5；无 runtime errors。
- 释放/退让：boundary 后 attachment/holding 全 false；退让向上位移 `0.1460 m`；无隐藏 step、无布料 reset。
- 没有证据表明“异常粘滞”：持续质心 0.595 mm/s、粒子 1.375 mm/s、角速度 0.104°/s，均非零；但比 RC2 的净漂移低，可能反映粒子间摩擦增加后的锁定/低滑移状态，不能仅凭本轮区分“改善”与“过度锁定”。
- 无地面穿透：z_min > 0；低于 contact offset 约 0.12 mm 是几何量，不是穿透或接触力。

## 10. 材料与接触证据缺口

- **API/schema 核查：** 安装版 `isaacsim/exts/omni.isaac.core/.../particle_material.py` 的 `ParticleMaterial.__init__` 支持 `particle_friction_scale`，并把它传给 `ParticleMaterialView(particle_friction_scales=...)`；GarmentLab 的 `ParticleMaterial` 引用同一构造路径。源码包装器确实把构造参数设为 `1.0`，manifest/source 身份一致。这证明的是**构造参数路径**，不是 solver-effective 运行时值。
- **运行时材料读回缺失：** pfs1 结果没有 `material_readback`；没有读回 `particleFrictionScale`、`friction`、self-collision 或 particle collision filter 的运行时值。D2-A 的 `friction=0.3 / particleFrictionScale=0.0` 是**未修改基线的读回**，不能当作 pfs1 的运行时证据。
- **接触报告缺失：** `contact_report.json` 不存在；即使存在，当前通道也只覆盖 robot-rigid，不覆盖 cloth-ground。0 事件不等于“无接触”；几何高度不等于接触力或冲量。
- 因此本轮不能声称“参数已被运行时读回确认生效”，也不能把结果归因为某个接触力机制。候选结果只能表述为“在本设置下观察到与粒子间摩擦缩放相关的改善”。
- **合规说明：** 速度读回的一致性检查和运行时材料读回本应在运行前完成；第一次尝试因 API 不存在被停止，第二次改用 `get_velocities()` 后直接执行，没有在运行前验证读回与位置差分一致；材料读回也没有实现。这是本轮的**观测/预检缺口**，不能在事后补成“已验证”。物理运行和几何结果保留，但扩展前必须修正观测设计并重新登记。

## 11. 判定与下一步

**几何/评价器判定：通过。** 原几何全程通过，质心 0.2642 mm ≤1 mm，P95 0.3792 mm ≤3 mm，release/retreat/主要证据资产完整，质量 accepted。这是候选改善证据。

**完整观测判定：不完整。** 粒子速度读回不可用；运行时材料读回缺失。按“若身份或证据异常，保留现场并停止，不绕过检查”的边界，本轮**不扩展 4302 single**，不重跑 pfs1，不扫描参数。

建议的审查顺序（需用户明确授权后才执行）：

1. 决定正式运动学指标是否接受**世界顶点有限差分**；若接受，在候选/评价文档中明确弃用该速度读回，并保留原始数据。
2. 在下一候选或只读检查中加入 `particleFrictionScale`、`friction`、self-collision、particle collision/filter 的**运行时读回**；USD 写入或构造参数本身不是 solver-effective 证明。
3. 评估 fold target 约 2 mm 变化对比较的影响；本轮不能把 pfs1 当作完全同动作对照。
4. 只有在上述问题处理后，才审查是否扩展到 4302 single。**本轮不运行 4302、不运行七例 RC、不冻结、不运行 held-out；正式 Stage 4 成功仍为 0。**

## 12. 产物

- [comparison.json](comparison.json) · [pfs1_bins.csv](pfs1_bins.csv) · [pfs1_vs_rc2.png](pfs1_vs_rc2.png)
- [velocity_readback_diagnostic.json](velocity_readback_diagnostic.json) · [velocity_readback_check.png](velocity_readback_check.png)
- [evidence_verification.json](evidence_verification.json)
- 旧版使用未校验读回的分析保留在 [invalid_velocity_readback/](invalid_velocity_readback/)；不要把其中的 25–35 mm/s 数值当作物理速度。
- 候选身份与运行登记：[a5-rc2-pfs1/registration.json](../../a5-rc2-pfs1/registration.json) · [README](../../a5-rc2-pfs1/README.md)
- 基线：[RC2 结果副本](rc2/)；原始 RC2 release 诊断：[STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103](../STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103/release_diag_analysis.json)

## 13. 后续观测修订（2026-11-04）

[a5-rc2-pfs1-observation-v2](../D2_E_PFS1_V2_COMPARE_20261104/review.md) 已单次复验 4202：`file_complete=true`、`observation_semantics_valid=true`、质量 accepted、`overall_valid=true`；动作 target、recovery/pre-release 状态和 formal 指标与本 pfs1 **0 差**。本 pfs1 结果继续保留为“质量 accepted、观测缺口”的原始证据，不被覆盖或改写。
