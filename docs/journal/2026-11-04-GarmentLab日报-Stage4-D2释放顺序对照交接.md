# 2026-11-04 GarmentLab 日报 · Stage 4 D2 释放顺序对照 / pfs1 观测修订

> 后续交接见 [2026-11-05 日报](2026-11-05-GarmentLab日报-Stage4-rc8七例RC与冻结暂停交接.md)：rc8 七例 RC 通过，冻结前检查因正式初态生成协议不符而暂停。

**暂停位置**　本轮从 D1-120 的延迟退让转入 D2 场景/接触核查和释放顺序对照：D2-A/B 确认了实际支撑、释放时序和 contact-report 的适用范围；D2-C 实现“附着保持期间完成夹爪张开、随后解除附件”；D2-D 只运行一次 4202 single，episode `passed=True`、诊断审计 `complete=True`、质量 `rejected`。**释放顺序没有降低释放瞬态或前 0.5 s 速度，不是该例漂移的主要因素。**

随后完成 **a5-rc2-pfs1** 粒子间摩擦缩放敏感性单次运行：质量 accepted，正式窗口质心 **0.2642 mm**、P95 **0.3792 mm**，但速度读回/材料读回存在观测缺口。再用 **a5-rc2-pfs1-observation-v2** 做观测-only 修订并单次复验 4202：`file_complete=true`、`observation_semantics_valid=true`、质量 accepted、`overall_valid=true`；动作/状态/formal 与 pfs1 **0 差**，确认只修订观测、未改变物理/控制。**4302 single 单次扩展随后已完成并通过（见 §12）。** 正式 Stage 4 成功仍为 **0**；held-out、正式批次和冻结均暂停。

## 1. 为什么从 D1 转到 D2

D1-120 在末次 OPEN 内插入 120 个物理步等待，保持 12 个公开动作/目标/命令/horizon 不变。结果：等待窗口质心 **2.0783 mm**、顶点 P95 **4.5603 mm**；退让 **2.4590 / 5.3214 mm**；正式窗口 **2.0409 / 4.4134 mm**，仍超 1 mm / 3 mm。D1 与基线的布料在相同 elapsed 时间点 **486 点逐位相同**；延迟只改变相位，不改变滑移率。因此问题不在“等待多久”，而在释放瞬态、回弹或地面接触。

[D1-120 分析](day4-actionchunk-test/results/D1_120_STEP8_ANALYSIS_20261104/review.md)

## 2. D2-A/B：实际场景与接触通道核查

[D2-A/B 报告](day4-actionchunk-test/results/D2_A_B_SCENE_CONTACT_20261104/review.md)

- 实际支撑为 `/World/defaultGroundPlane/GroundPlane/CollisionPlane`（启用）；室内地面 collider 已禁用。
- 支撑面**没有显式 physics material binding**，只有 PhysX 默认材质；地面/布料没有可读 filter group。
- particle material 已绑定，`friction=0.3`、`particleFrictionScale=0.0`（initial protocol 明确断言），`particleContactOffset=0.01`、`nonParticleCollisionEnabled=true`、self-collision/CCD=true。
- 释放前持布最后 5 步：粒子平均 **0.262 mm/s**、质心 **0.055 mm/s**；附着在 **1944** 断开，1944 一步跳至 **17.42 / 11.04 mm/s**，前 5 步 **35.95 / 19.42 mm/s**；但 `gripper_state=2`/`command_holding=true` 持续到 **1953**，**1954** 才报告 open。附件关闭早于夹爪张开完成 10 步。
- D2-B：rigid 已知接触在原 `ContactRecorder` 配置下 0 事件；API 同时加到 cube+ground 且在 `world.reset()` 前应用时捕获 **166** 事件。粒子布料从 z≈0.184 m 落到 0.0099 m（contact offset 0.01），即使 API 加到 ground/particle system/cloth 仍 **0 事件**。当前 contact-report 通道不支持 cloth-ground；0 事件不是“无接触”，也不能当作接触力。

因此 D2-C 选择只改**释放顺序**：让夹爪在附件仍启用时完成 10 步张开，再解除附件；不改摩擦、不清零布料速度。

## 3. D2-C：预登记与预运行补查

[D2-C README](day4-actionchunk-test/a5-rc2-d2c-release-order/README.md) · [registration](day4-actionchunk-test/a5-rc2-d2c-release-order/registration.json) · [static-audit](day4-actionchunk-test/a5-rc2-d2c-release-order/static-audit.json)

- 独立版本 `a5-rc2-d2c-release-order`，父 D1-120；manifest 66 项 `778935ab…`、config `96acc5fa…`；基础 60 项与 RC2 一致。
- 唯一改动：`preopen_while_attached()` 在 `measure_ungrasp()` 内先执行 `active.robot.open()` **10 步**；原 `ungrasp` 内第二次 `open()` 被抑制；随后解除附件。总物理步数与 D1 相同（同样的 10 步张开移到解除之前），120 步等待、12 个公开动作/目标/命令/horizon 和退让目标保留。
- **开爪与附着一致性：** 10/10 步每步检查 `active.holding`、`active.attachment_enabled()`、`control.holding`、`control.attachment_enabled()`，并调用 `control.assert_exclusive()`；`audit_episode_evidence.py`/`episode_evidence.py` 与 D1 字节相同，全程状态检查未关闭。允许夹爪张开但布料仍持住。
- **释放边界：** 记录最后 preopen state、boundary、released sample 的 step 与 delta。D2-C `released` sample 与最后 preopen state 同 step/time（delta=0），首个全关 state 是随后一步；D1 无零步 sample，anchor→首个自由 state 为 1 步（16.7 ms）采样区间。分析不把首个全关 state 当作精确解除瞬间。

离线验证：manifest 66/66、release-order fixture 8/8、delay fixture 5/5、release fixture 1/1、`py_compile`、`bash -n`、静态动作身份 21/21 通过。

## 4. D2-D：单次运行与下载核验

[D2-D 对照报告](day4-actionchunk-test/results/D2_D_COMPARE_20261104/review.md) · [download_audit](day4-actionchunk-test/results/D2_D_RUN_4202_20261104/download_audit.json)

| 项目 | 结果 |
|---|---|
| 结果目录 | `day4-a5-rc2-d2c-release-order-20261104-090032-412133` |
| 远端预检 | `D2C_PREFLIGHT_OK 66`；`PREFLIGHT_ONLY_OK`；未启动仿真 |
| 运行 | tmux 单次；退出码 0；`completed` 已写入；无重试 |
| episode | `passed=True`、12 个公开动作、`absolute_step=2219`、等待 1955–2075、trace 331 步 |
| 诊断 | `DIAG_ASSESS complete=True`、`quality=rejected`、release_rows=277、contact_events=0 |
| 与 D1 总步数 | 完全一致（2219 / 1955–2075 / 331） |
| 证据 | ledger 证据 SHA256 全部一致；`code_files` 与 66 项 manifest 一致；初态哈希不变 |

预运行补查结果：preopen world 1945→1955（10 步），开合量 `1.15e-8 → 0.0800 m`，holding/attachment 前后均 true，attachment 在 preopen 结束同一步解除；`preopen_state_checks=10`。

## 5. 对照结果

**干预前：** 12 个动作 target 最大差 **0.0**、动作返回 EE 最大差 **0.0**、release anchor 顶点/EE/关节差 **0.0**；D1/D2-C 的 `pre_release_hold` 末帧都等于 anchor。

**release t=0（单独比较，不要求相同）：**

| 指标 | D1 | D2-C |
|---|---:|---:|
| 质心位置差 | — | **0.0113 mm** |
| 顶点 P95 / 最大差 | — | **0.0293 / 0.0375 mm** |
| 旋转差 | — | **−0.0045°** |
| 粒子平均速度 | 0.2617 mm/s | 0.2597 mm/s |
| 质心速度 | 0.0408 mm/s | 0.0547 mm/s |
| 角速度 | 0.000235 °/s | 0.00750 °/s |

**释放后窗口（按 release elapsed 对齐，从首个自由物理步起算）：**

| 窗口 | D1 质心 / P95 | D2-C 质心 / P95 | 变化 |
|---|---:|---:|---:|
| release transition | 0.1840 / 0.7420 mm | 0.1835 / 0.7474 mm | 基本不变 |
| free 0–30 步（0–0.5 s） | 1.9092 / 12.2286 mm | 1.9119 / 12.2044 mm | ±0.2% |
| free 30–120 步 | 1.4730 / 3.2355 mm | 1.4284 / 3.1499 mm | −3.02% / −2.65% |
| retreat | 2.4389 / 5.2665 mm | 2.3699 / 5.1996 mm | −2.83% / −1.27% |
| formal 210–330 | 2.0409 / 4.4134 mm | 1.9823 / 4.3426 mm | **−2.87% / −1.60%** |

释放一步粒子平均速度：**17.4197 vs 17.4223 mm/s**；质心速度 11.0397 vs 11.0113 mm/s。

**窗口说明：** `wait_phase` 的 D2-C 2.74/12.97 mm 与 D1 1.99/4.25 mm 不是公平的 release-elapsed 比较；D2-C 的 120 步等待紧接释放，包含释放瞬态，D1 的等待晚约 10 步。不要把它当作物理退化。

## 6. 解释与暂停结论

1. **释放顺序没有降低首个释放后速度。** 首个自由物理步的粒子平均速度 17.4197 vs 17.4223 mm/s，质心速度 11.0397 vs 11.0113 mm/s；release transition 的质心/P95 位移几乎相同；t=0 布料位置差 ≤0.037 mm。
2. **0–0.5 s 也基本不变**（质心 1.9092 vs 1.9119 mm，P95 12.2286 vs 12.2044 mm）。把夹爪张开移到解除之前，并没有改变布料离开约束后的初始运动。
3. **后续窗口有小幅下降。** free 30–120、retreat、formal 的质心/P95 低 1.3–3.0%；正式窗口质心 2.0409→1.9823 mm、P95 4.4134→4.3426 mm。可以表述为“**释放顺序改变降低了本例正式窗口漂移**”，但不能说是降低了首个释放后速度；正式窗口仍是 action-relative，D2-C 比 D1 晚 10 步释放，存在相位差异。单例也不足以外推。
4. **仍拒绝。** 1.98 mm > 1 mm、4.34 mm > 3 mm；质量 `rejected`。证据完整，保留为有效对照。
5. **接触边界。** contact_events=0 不是“无接触”；cloth-ground 接触力/冲量不可用。不能把下降归因于某种碰撞冲量。
6. **暂停判断：** 释放顺序不是该例漂移的主要因素。恢复工作时，优先核查附件约束释放时的能量/接触状态、支撑面材质和布料—地面接触观测；不要继续微调开爪顺序，也不要直接提高摩擦或清零速度来充当修复。

## 7. 当前边界与恢复入口

- 正式 Stage 4 成功仍为 **0**；RC2 未冻结；held-out 未运行；正式批次暂停。
- 原阈值 **1 mm / 3 mm** 不变；开发集证据不能替代正式验收。
- D2-C 仅 4202 single 一次；`completed` 已写入，不自动重试。
- 恢复入口：[DAY4_NEXT_STEPS](DAY4_NEXT_STEPS.md)、[DAY4_ACCEPTANCE_TRACKER](DAY4_ACCEPTANCE_TRACKER.md)、[STAGE4_A5_RC2](2026-11-03-GarmentLab日报-Stage4-A5-RC2登记.md)。
- 关键产物：[D2-D 对照](day4-actionchunk-test/results/D2_D_COMPARE_20261104/review.md)、[comparison.json](day4-actionchunk-test/results/D2_D_COMPARE_20261104/comparison.json)、[windows.csv](day4-actionchunk-test/results/D2_D_COMPARE_20261104/windows.csv)、[对比曲线](day4-actionchunk-test/results/D2_D_COMPARE_20261104/d2c_release_compare.png)、[D2-C 版本](day4-actionchunk-test/a5-rc2-d2c-release-order/README.md)。

## 8. D2-E 步骤2：支撑面与摩擦配置核查（仅离线）

离线读取 D2-A 场景读回、D2-C 已保存几何/轨迹和源码；**未启动新 episode，未改物理参数**。审查表：[review](day4-actionchunk-test/results/D2_E_SUPPORT_MATERIAL_AUDIT_20261104/review.md)、[JSON](day4-actionchunk-test/results/D2_E_SUPPORT_MATERIAL_AUDIT_20261104/support_material_audit.json)、[CSV](day4-actionchunk-test/results/D2_E_SUPPORT_MATERIAL_AUDIT_20261104/support_material_table.csv)。

- **唯一与布料存在有效碰撞候选的表面是默认地面** `/World/defaultGroundPlane/GroundPlane/CollisionPlane`：z=0、水平、50 m 代码值、collision enabled。
- 室内地面 `/World/Room/.../CollisionPlane` 为 **enabled=false**。
- 三个附件块 `/World/Attachment/attach*/block` 碰撞体存在且释放后仍保留，但与 garment/robot/rigid 碰撞组过滤，并有 ground `FilteredPairsAPI`；**不能承托或碰撞布料**。机器人手/指与布料同样被组过滤；布料自碰撞开启，但不是外部支撑。
- 布料 mesh 无直接物理材质；材质链为 `particleSystem -> particleMaterial`，读回 `friction=0.3`、**`particleFrictionScale=0.0`**。
- 默认地面 CollisionPlane **没有直接 physics material binding**；Isaac `add_default_ground_plane` 代码创建 0.5/0.5/0.8 的 `physics_material`，但 `GroundPlane` 的应用分支被 `physics_material is None` 守卫挡住；0.5/0.5/0.8 **未确认生效**。附件块 0.2/1.0/0 是刚体默认值且碰撞被过滤，**不是布料有效摩擦**。
- 几何：布料最低点约 **9.876 mm**（高于地面 9.876 mm），比 `particleContactOffset=10 mm` 低约 **0.123–0.124 mm**；这是几何证据，不是接触力/冲量。
- **当前不选择修正。** 支撑/过滤拓扑已足够明确；有效摩擦不能由读回确定。步骤3纯读回不是选择修正的前置条件（若需要精确块/地面 transform、祖先材质绑定和完整 filter 列表，可登记一次只读 4202 single）；有效摩擦需步骤5单变量敏感性；步骤4可先离线复用 D1/D2-C 轨迹检查持续滑移特征。

## 9. D2-E 步骤4：持续滑移特征（仅离线）+ 步骤5决定

[步骤4 报告](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/review.md) · [JSON](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_summary.json) · [CSV](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_bins.csv) · [速度/转速/方向](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_speed_rotation.png) · [高度](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_height.png) · [支撑几何](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/support_geometry.png)

复用 D1-120/D2-C 轨迹，未启动仿真。首个释放后速度约 **11.0 mm/s 质心 / 17.4 mm/s 粒子**（速度测量，不是冲量）；前 1 s 快速衰减，随后 **1.5–10 s 近恒定 ~1.0 mm/s、~0.36°/s**（D1 1.024、D2-C 0.993 mm/s），没有继续衰减或增大。持续方向约 **26–27°**，比释放方向（~0.7–1.1°）转约 **25°**，约 1–1.5 s 后稳定。z_min≈9.871–9.876 mm，无地面穿透，低于 10 mm contact offset 约 0.124–0.129 mm；几何证据，不是接触力。两版稳态差约 3%，持续滑移几乎相同。

**步骤5决定：** 选择 **`particleFrictionScale: 0.0 → 1.0`** 的单变量敏感性对照；不选地面材质绑定作为本轮干预（地面材质未绑定是独立发现，但它是刚体材质，不能直接当作粒子摩擦）。候选拟名 `a5-rc2-pfs1`，从 **RC2 原流程**派生，不保留 120 步等待或 D2-C 释放顺序；`friction=0.3`、地面/碰撞、12 个动作/目标/horizon/退让目标不变。该参数从 episode 开始全局生效，影响 recovery/fold/release，**不是“仅释放后接触对照”**；4202 初态文件不重生，但新动力学从第一步开始。只跑 4202 single 一次；通过条件为原几何 + 质心 ≤1 mm + P95 ≤3 mm + 证据完整。[步骤5预登记草案](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/step5_decision.md)。**候选随后已创建、离线验证并单次运行；见下。**

## 10. a5-rc2-pfs1：粒子间摩擦缩放单次 4202 single

候选 [a5-rc2-pfs1](day4-actionchunk-test/a5-rc2-pfs1/README.md) 从 RC2 原流程派生，只改 `particleFrictionScale 0.0→1.0`；`friction=0.3`、地面/碰撞、12 个动作/命令/horizon、退让目标与 evaluator 不变；manifest `bad4b59a…`（63 项）、config `2d72a405…`；初态复用未重生。

运行 `day4-a5-rc2-pfs1-20261104-102101-983000` 一次：runner/entry 退出 0，episode `passed=True`，质量 **accepted**；正式 210–330 evaluator 质心 **0.2642 mm**、P95 **0.3792 mm**（RC2 2.0429/4.4141 mm），几何全程通过；首个 0.5 s 位置差分质心 **11.555 mm/s**、粒子 **15.000 mm/s**；1.5–8.0 s 持续质心 **0.595 mm/s**、粒子 **1.375 mm/s**、角速度 **0.104°/s**；z_min≈9.867–9.879 mm，无穿透。证据 manifest 73/73；ledger 15/16，缺 `contact_report.json`（非必需）。动作 target 与 RC2 不同：fold 约 +2.0 mm、退让约 +2.0 mm，来自 recovery 后重新计算 pick/yaw。

**观测 caveat：** `ClothPrimView.get_velocities()` formal 读回粒子 28.76 mm/s，而位置差分 1.29 mm/s；读回场 2 s 内几乎不变、与位置差分向量相关约 −0.006。EE 静止、attachment/holding=false，不能由机器人运动解释。该读回不能当作实际速度/冲量；所有报告速度改用世界顶点有限差分，原始读回保留为 unvalidated。另无运行时材料读回；D2-A 的 `.3/0` 是未修改基线。contact-report 缺失且不覆盖 cloth-ground，0 事件不是无接触。

**判定：** 几何/评价器通过，属于候选改善证据；但速度读回与材料读回 caveat 使观测完整性不足，**不扩展 4302 single**，不重跑、不扫描参数。正式 Stage 4 成功仍为 0；不宣称地面摩擦已修复。详见 [pfs1 对照](day4-actionchunk-test/results/D2_E_PFS1_COMPARE_20261104/review.md)、[evidence_verification](day4-actionchunk-test/results/D2_E_PFS1_COMPARE_20261104/evidence_verification.json)。

## 11. a5-rc2-pfs1-observation-v2：观测修订复验

按新的六步方案完成观测修订并单次复验 4202：[a5-rc2-pfs1-observation-v2](day4-actionchunk-test/a5-rc2-pfs1-observation-v2/README.md)。只改观测，不改物理/控制；新 manifest `d97bf349…`（63 项）、新一次性锁；旧 pfs1 结果保留。

运行 `day4-a5-rc2-pfs1-observation-v2-20261104-111514-134428` 一次：`file_complete=true`、`observation_semantics_valid=true`、质量 **accepted**、`overall_valid=true`。formal 质心 **0.2642 mm**、P95 **0.3792 mm**；动作 target、recovery/pre-release 状态、formal 指标与 pfs1 **0 差**。材料五阶段 friction .3 / particleFrictionScale 1.0 / binding `/World/Garment/particleMaterial` / self/non-particle true；solver-effective 仍标 unverified。FD 484 个有效区间、1 个首帧无效；raw readback 标 unvalidated。contact 能力：robot-rigid only，cloth-ground 力/冲量不可得，0 事件不是无接触；不新增验收门槛。

**判定：** 观测修订通过，但只是观测-only 复验，不增加新的物理改善，也不是正式 Stage 4 成功。**4302 single 单次扩展随后已完成并通过（见 §12）**；正式成功仍为 0；不宣称地面摩擦已修复。详见 [v2 对照](day4-actionchunk-test/results/D2_E_PFS1_V2_COMPARE_20261104/review.md)。

## 12. 4302 single 扩展：质量 accepted + 证据完整（单次）

按 v2 预登记的下一道门槛，固定 v2 候选并登记单次 4302 扩展：[a5-rc2-pfs1-observation-v2-4302](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-4302/README.md)。63 项 manifest 中 **61 项与 v2 逐字节相同**，仅登记 JSON 与 runner 变化（新 manifest `6d1958f5…`、config `577931aa…`、runner `550efa65…`）；新锁 `a5-rc2-pfs1-observation-v2-4302-runs`，4202 结果、v2 完成标记与旧锁全部保留。4302 初态复用 `day4-square-initial-stripfold-20261103-094143-137994`（`1bed437f…` / `1c27514f…`），未重生。

**预检：** 远端 63/63（父 manifest、61/63 身份、4302 初态、level=crumpled、plan 唯一、新账本无未完成尝试、`bash -n`、py_compile）。

**运行：** tmux 单次 `day4-a5-rc2-pfs1-observation-v2-20261104-201557-235290`，退出 0、12 动作、`completed` 写入、无重试；下载 **104/104** 文件哈希一致。

| 项目 | 结果 |
|---|---|
| `file_complete` / `observation_semantics_valid` | **true / true**（12/12 语义检查） |
| 质量 / `overall_valid` | **accepted / true**；`errors=[]` |
| 评价器检查 | geometry_entire_window、stable、held、released_continuously 全 **true**；`failed_geometry_frames=[]` |
| 正式 210–330 | 质心 **0.2390 mm**、P95 **0.3524 mm**（RC2 4302 single 1.9102 / 4.1231，−87.5% / −91.5%） |
| fold | crossed 1.0；IoU 0.6617→0.6494；对齐 6.19 mm；z_p95 68.92 mm |
| held | 14.16 mm / 0.00215 rad/s / 2.13 mm，accepted |
| 释放后 0.5 s | 粒子 15.70 mm/s、质心 12.40 mm/s；首区间 20.06 / 10.97 |
| 1.5–8.0 s | 质心 0.372 mm/s、粒子 0.659 mm/s、角速度 0.092°/s |
| z_min / 穿透 | 9.867 mm / 0 mm；低于 contact offset 0.133 mm（几何） |
| 粘滞 | 通过：release 后无 attachment/holding/latch 复活；OPEN 锁存仅 10 步；夹爪 0.080 m；布料不跟随 retreat 的 EE |
| 材料读回 | 五阶段 live：friction 0.3、particleFrictionScale 1.0、binding `/World/Garment/particleMaterial`、self/non-particle true；solver-effective 仍 unverified |
| 证据 | ledger 19/19、evidence 73/73 |

**解释：** recovery 末态相对 RC2 平移 **10.27 mm**（刚体 RMS 0.0006 mm），expert 按未改逻辑重算 fold 目标，导致 fold 目标差 7.7–8.0 mm、yaw −3.28°；因此这是**端到端**对比，不是“同一动作、只改摩擦”的受控对照。4202（0.2642/0.3792）与 4302（0.2390/0.3524）两个 dev seed 各一次 single 均通过，但仍不足以推断跨 seed 普遍有效，也不确认具体摩擦机制。

**判定：** 按预登记表“质量接受且证据完整 → 固定最终候选，准备完整七例 RC”。本轮不跑七例、不冻结、不跑 held-out/正式批次、不扫参数、不重跑 4202/4302；正式 Stage 4 成功仍为 **0**。详见 [4302 对照审查](day4-actionchunk-test/results/PFS1_V2_EXT_4302_20261104/review.md)。

## 13. 下一步（需明确指令）

1. 准备七例 RC：例表（哪些 seed/模式）、身份与上限、失败/拒绝的停止条件；
2. 在七例 RC 通过后，才讨论显式冻结与正式批次；
3. 继续保持：不宣称地面摩擦已修复、不把单例通过写成跨 seed 结论、正式成功计数 0。

## 14. rc7 七例 RC 执行结果：4/6 阳性，未放行

按第 13 节的顺序，登记并执行 [rc7](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc7/README.md)：把 4202/4302 单例的物理/控制固定为一个最终候选，L1 runner 接入同一观测；**uniform `particleFrictionScale=1.0`（含 L1）在运行前登记**；manifest `bcba8c11…`（63 项，60 项与 v2 逐字节相同）、新批次账本 `…-rc7-runs`；七槽顺序、每槽一次、无自动重试。

| 槽 | seed / 模式 | 质量 | 质心 / P95 (mm) | 几何窗口 | stable | 配对差 |
|---:|---|---|---:|---|---|---:|
| 1 | 4100 single | **rejected** | 0.7031 / 1.7764 | **false** | false | — |
| 2 | 4100 arc4 | **rejected** | 0.7031 / 1.7764 | **false** | false | 0.0 |
| 3 | 4202 single | accepted | 0.2642 / 0.3792 | true | true | — |
| 4 | 4202 arc4 | accepted | 0.2642 / 0.3792 | true | true | 0.0 |
| 5 | 4302 single | accepted | 0.2390 / 0.3524 | true | true | — |
| 6 | 4302 arc4 | accepted | 0.2390 / 0.3524 | true | true | 0.0 |
| 7 | 4201 single | rejected（有效） | 0.9409 / 2.8073 | true | false | — |

**4100 失败机制：** `free_edge_overrun` **15.4 mm**（要求 20–60）、`free_edge_height_p90` **24.4 mm**（≤15）、`vertex_speed_max` **64.6 mm/s**（≤50）；RC2 4100（pfs=0）为 40.7 / 10.1 / 16.5，全部通过。uniform pfs=1.0 下 flap 没有滑过静止半片落到边缘外桌面，L1 过折依赖的“自重锁”没有发生；single/arc4 逐项相同。**4201** 几何全过、`crossed=1.0`，但速度 P95 20.3 > 10 mm/s → 有效拒绝（未强制、未重跑）。4202/4302 与先前单例逐值相同。

**证据与门禁：** 7/7 槽 `file_complete` + 观测语义通过；三组配对 target 差 **0.0**；下载 **765/765** 哈希一致；原版 `verify-dev` **失败**（`Expected positive smoke case failed: …l1-…212326-225911`，exit 1）。中途一次会话在 Isaac 启动阶段被操作者终止（无 episode 结果），保留于 `runs.aborted-20261104T1304Z`，未计入槽结果。

**判定：不冻结、不释放。** 放行条件 1（六阳性全部接受）与条件 5（verify-dev）未满足。下一版本应另行登记 **task-scoped** 物理配置（L1=0.0、L2/L3=1.0，保留本轮观测接入），并重跑整个七例矩阵；本轮结果保留、不插入新矩阵，赛后不得切换参数。正式 Stage 4 成功仍为 **0**。详见 [rc7 审查](day4-actionchunk-test/results/RC7_SEVEN_CASE_20261104/review.md)。

## 15. rc8 task-scoped 七例 RC：6/6 阳性通过（冻结材料已整理，未冻结）

按 §13 的下一版本建议登记 [rc8](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8/README.md)：**L1 flat `particleFrictionScale=0.0`，L2/L3 `=1.0`**，在材料构造时设置、早于 reset/物理步；路由只按任务身份，不读取 seed/mode/结果；材料五阶段读回按任务核对（0.0 / 1.0）。manifest `68930010…`（63 项，59 项与 v2 逐字节相同），新批次账本；七槽顺序、每槽一次、无重试；attempts 14 行。

| 槽 | seed / 模式 | 质量 | 质心 / P95 (mm) | 协议 expected |
|---:|---|---|---:|---:|
| 1–2 | 4100 single/arc4 | **accepted** | 0.1435 / 0.2072 | **0.0** |
| 3–4 | 4202 single/arc4 | **accepted** | 0.2642 / 0.3792 | 1.0 |
| 5–6 | 4302 single/arc4 | **accepted** | 0.2390 / 0.3524 | 1.0 |
| 7 | 4201 single | rejected（有效） | 0.9409 / 2.8073 | 1.0 |

**门禁：** 六阳性全部接受；4201 有效拒绝；三组 single/arc4 配对 target 差 **0.0**；7/7 证据完整；807/807 下载哈希一致；本地 `stage4_success_v1.evaluate` 重算 7/7 status/stability 逐值相同；视频审查通过（末帧机械臂撤离、布料在桌面；L1 flap 落桌）；原版 `verify-dev` **通过**（`A5_DEV_VERIFIED 7`，exit 0）。4100 与 RC2 4100（pfs=0）逐值相同，支持“rc7 的 L1 失败来自 uniform 1.0”的机制解释——仍按视频支持的机制解释报告，不写成已确认因果。

**判定：** 候选 **rc8 通过本轮 task-scoped 七例 RC**。冻结材料已整理：[FREEZE_DOSSIER](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/FREEZE_DOSSIER.md)、[freeze_manifest.json](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/freeze_manifest.json)。但**冻结前检查未通过**：正式 L2/L3 初态生成脚本仍强制 `particleFrictionScale=0.0`（应为 1.0，`day4-square-initial-stripfold.py:196/261`，由 `run-stage4-formal-batch.sh:73` 调用），因此**未执行 freeze、未写 `verified-dev.json`/`E_RELEASE.json`**，现场保持为“RC 通过、冻结待修正”。建议 rc8b 最小修正初态生成并重跑七例后重新冻结；在此之前不启动 held-out/正式批次。正式 Stage 4 成功仍为 **0**。报告口径：结果按任务报告，不是统一物理条件下的纯初态难度比较；rc7 被操作者终止的启动记录继续列入运行历史（未形成可评价 episode，不计入质量分母）。详见 [FREEZE_PRECHECK](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/FREEZE_PRECHECK.md) 与 [rc8 审查](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/review.md)。
