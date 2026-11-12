# A5 RC2 开发登记

RC2 为独立候选，父版本 RC1。开发前固定 manifest 39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d，共 60 项。登记目录 a5-rc2 与 RC1 分开；原始 RC1 轨迹与旧失败继续保留。

|RC1 诊断|RC2 干预及验证|
|---|---|
|7 例启动 RGB 首读均无效，首次正常视频帧为观测步 2。|安装采集器时最多 12 次 render-only RGB 就绪探测；每次记录空缓冲形状和物理步，只向编码器提交真实、有限、非空的图像。要求物理步不变、启动帧为 0、每个偶数物理步有帧，后续错误照常拒绝。|
|CLOSE 的槽位已启用，后端持布 latch 在 grasp 返回时才置位；OPEN 的槽位已释放，后端 latch 在 ungrasp 返回时才复位。L1 7+10 步，B 两对抓放共 34 步。|后端在控制期间实时读控制器的槽位持布状态；保存原命令级 latch、逻辑附着和三个 USD enable 独立读回。逐步检查 holding / logical_attached / 真实槽位开关一致且最多一个槽启用，动作返回时还要求 latch 一致。正常物理过渡并未从账本删除。|
|4202/4302 的第 210–330 步，质心位移向量（毫米）约为 (+1.526,+0.795,-0.001) 与 (+1.770,+0.261,+0.0005)，两半片的平均位移相近。扣除质心平移后，顶点相对位移 P95 仍有 2.23 / 2.29 mm。single 与 arc4 一致。|物理表现为持续平面运动叠加局部运动，两秒窗口内高度变化极小。RC1 没有释放前的逐步顶点，无法单独确定是残余动量、释放瞬态还是接触滑移。任务 B 将既有放置后静止保持从 60 步固定延长到 180 步，记录每步的 pre_release_hold.npz 供检验；不重置速度、布料位置，不修改摩擦或重选窗口。L1 保持 60 步。|

对第 210 帧与第 330 帧的 441 个 XY 坐标进一步作平面刚体最小二乘拟合，4202 / 4302 的旋转分别约为 −0.623° / −0.641°，扣除平移和旋转后的 RMS 残差仅 0.0043 / 0.0048 mm。两例拟合均解释超过 99.99% 的平面位移平方和。超限主要来自已折布料的整体滑移和转动；这比仅从质心速度推测折形松弛更精确。接触摩擦与释放瞬态的因果贡献仍待对照。

B 数值阈值及原版评价器保持原始登记哈希。末次公开 OPEN 仍以实测 EE 上方 0.15 m 为目标，完成后固定采 0–330，评价 210–330 全部 121 帧。L1=7、任务 B=12 个公开动作。预登记的输入哈希、顺序、表示、阳性和对照角色与 RC1 一致：4100、4202、4302 各 single 和 arc4，最后 4201 single。

放行沿用 RC1：六个阳性须通过 B 与完整视频/状态证据，4201 可有效拒绝或接受，但证据须完整；三组实际公开目标容差 1e-6，并复核视频及退让。冻结须基于该 RC2 manifest 和本轮全部账本。开发失败单列，不替换用例。正式批次另行授权执行。

[本地 RC1 逐例诊断](../stage4-a5-delivery/rc1-drift-diagnosis.json) · [候选配置](day4-actionchunk-test/a5-rc2/a5-candidate.json) · [manifest](day4-actionchunk-test/a5-rc2/a5-manifest.json)

## 2026-11-03 漂移诊断（第 1–2 项，仅离线）

RC2 基线、七例索引、独立诊断批次登记、事件分段和曲线见 [诊断报告](day4-actionchunk-test/results/STAGE4_A5_RC2_DRIFT_DIAGNOSIS_20261103/review.md)。原版 verify-dev 为 exit 1、release_exists=false，失败点是 4202 arc4 稳定性拒绝；七例 RGB/视频/持布 evidence_checks 全过。

4202/4302 single：保持稳定；释放/开爪瞬态 P95 13.83/15.03 mm、最大 25.62/27.65 mm（非刚体局部变形）；退让阶段质心 2.48/2.44 mm、旋转 −0.91/−0.94°；正式窗口 210–330 为近刚体滑移/转动（质心 2.04/1.91 mm、P95 4.41/4.12 mm、刚体 RMS 0.0011/0.0009 mm），超 1 mm/3 mm。释放→退让之间只有 released/retreated 快照，缺逐物理步顶点、夹爪开合量和接触记录；不能据此认定无碰撞。该区间已由第 3 项诊断版 v1.1 补齐（见下），D1/D2 仍不启动。

## 2026-11-03 释放窗口诊断（第 3 项）

`a5-rc2-drift-diag-v1` v1.1 在 4202 single 完成（`day4-a5-rc2-drift-diag-20261104-053151-197013`）：`complete=True`，25/25 诊断检查、18/18 evidence 检查；release_diag 157 行 = 155 个 state 步（1943–2097）+ released/retreated，441 顶点、9 关节、开合量/EE 距离有限；contact 通道 0 事件、未独立验证（不得写成无接触）；finger-link 距离全 NaN，只有 EE 距离代理。质量仍为 rejected（稳定性），质心 2.042884 mm、P95 4.414119 mm，符合 RC2 4202 single。

与 v1 及 RC2 4202 single 逐位比较：release_diag 全部数组（finger 距离两边全 NaN、掩码相同）、12 个动作目标（最大差 0）、`success_trace`、`final/recovered/pre_release_hold/cloth_constructed`、五个证据快照、2427 条 state、1219 条 frame 完全相同；`success_meta` 物理字段（含 initial_hashes、absolute_step=2099、sim_time、dt、pick=230、yaw、upward）相同；`quality` 与 RC2 `criteria` 逐项相等。唯一差异是 v1 的 1943 重复 state 锚点改为 `release_anchor`，以及三个诊断文件 hash/manifest/protocol。**因此没有改变物理步进、控制频率或动作目标，不需要登记新物理版本或重建 baseline；RC2 目录未覆盖。** 详见 [release diag 分析](day4-actionchunk-test/results/STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103/review.md) 与 [逐位比较](day4-actionchunk-test/results/STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103/v1_1_compare.md)。

下一步为 D1-120（延迟退让 120 步）；步骤 6 已单次运行（见下），postfix 评估完成，正式成功仍为 0。

## 2026-11-03 D1-120 步骤 2–5：独立实现与预检；2026-11-04 步骤 6–8：运行、核验与分段分析

独立目录 [a5-rc2-d1-120](day4-actionchunk-test/a5-rc2-d1-120/README.md) 从已验证 v1.1 `053151-197013` 复制并重定向版本。父 v1.1 manifest `13c1f20a…`、config `aa5da98b…`；基础 RC2 candidate `10a6cb45…`、manifest `39dc5055…`（60 项）；4202 初态 `day4-square-initial-stripfold-20261103-062710-242560`，`result.json` `4472f4df…`、`initial_geometry.npz` `a6646d66…`。新 manifest 66 项 SHA256 `cd1d7f83…`、config `a6884eab…`；[registration.json](day4-actionchunk-test/a5-rc2-d1-120/registration.json) 记录父版本、初态、源码和配置哈希。

`hold_open_for_steps` 已在末次 OPEN 内、`ungrasp` 返回后、原退让目标前插入**恰好 120 个物理步**（2.0 s，dt=1/60）；不调用控制、不改变目标、不写布料位置/速度。等待位于第 12 个公开动作 `release_retreat` 内，代码断言 action 索引 12、horizon 总和 12；`a5_recovery_diag.py` 与 v1.1 的 action 调用/目标表达式未改，实际动作数组待运行后逐项比较。

步骤 4 已加入 `ungrasp_return`、`delay_begin`、`delay_end`、`retreat_begin`、`retreat_end` 五个事件，写入 `release_diag.json:events` 和 `release_diag_events.csv`；`release_diag.npz` 的 phase 区分 `delay`（120 个 state 行）与 `retreat`，事件行含 EE/关节/开合量/attachment/布料质心与哈希。离线检查：manifest 66/66、delay fixture 5/5、release fixture 1/1（含事件/CSV）、`py_compile`、`bash -n` 通过。**步骤 5 离线预检 65/65 通过**（[D1_120_PREFLIGHT](day4-actionchunk-test/results/D1_120_PREFLIGHT_20261103/review.md)）：身份/manifest/插入位置/动作计数/采集逻辑/recovery 隔离/4202 single 范围均通过。**未运行仿真，仅 4202 single。** RC2 与 v1.1 原目录均未修改。

**步骤 6 运行（2026-11-04）**：`day4-a5-rc2-d1-120-20261104-071602-499516`，episode `passed=True`，12 个公开动作，120 步等待（world step 1955–2075），事件 `ungrasp_return 1953 / delay_begin 1953 / delay_end 2073 / retreat_begin 2073 / retreat_end 2217`，phase delay 120 / retreat 144，`release_diag` 277 行，success trace 331 步。标准 assessor 因 3D/4D target 形状 bug 崩溃（审计问题）；执行后 app/manifest 未改，独立 [postfix 评估](day4-actionchunk-test/results/D1_120_RUN_4202_20261104/review.md) `complete=True`、`quality=rejected`（质心 2.040882 mm、P95 4.413414 mm）。无重试；步骤 7 下载核验 46/46 通过（[审计](day4-actionchunk-test/results/D1_120_STEP7_AUDIT_20261104/review.md)：远端/本地 97 文件 SHA256、动作目标 0 差、等待前轨迹逐位相同）。步骤 8：[分段分析](day4-actionchunk-test/results/D1_120_STEP8_ANALYSIS_20261104/review.md)显示等待 2.0783 mm/4.5603 mm P95、退让 2.4590/5.3214、窗口 2.0409/4.4134；D1 与基线布料在相同 elapsed 时间点 486 点逐位相同。120 步延迟不改变滑移率；优先检查释放瞬态/回弹/地面接触。正式成功 0。

## 2026-11-04 D2-A/B：场景与接触核查

[D2-A/B 报告](day4-actionchunk-test/results/D2_A_B_SCENE_CONTACT_20261104/review.md)：默认地面为实际支撑，室内地面 collider 禁用；支撑面无显式物理材质、无可读 filter group；particle material 绑定并可读（friction .3、particleFrictionScale 0、contactOffset .01、nonParticleCollisionEnabled true）。释放前 5 步粒子 0.262 mm/s、质心 0.055 mm/s；1944 断开附着时一步 17.42/11.04 mm/s，前 5 步 35.95/19.42 mm/s；gripper open 到 1954 才报告。D2-B：原 ContactRecorder 对已知 rigid 接触 0 事件；API 加到 cube+ground 且 reset 前应用时捕获 166 事件；粒子布料落到 contact offset 0.01 但 cloth-ground contact report 仍 0 事件，判定当前通道不支持布料接触，需改用高度/穿透/粒子速度观测。D2-C 已选择释放顺序干预并登记，随后已单次运行（见下）；不直接提高摩擦，正式成功 0。

## 2026-11-04 D2-C：释放顺序单变量干预已登记（未运行）

独立目录 [a5-rc2-d2c-release-order](day4-actionchunk-test/a5-rc2-d2c-release-order/README.md)，从 D1-120 复制并重定向。父 D1 manifest `cd1d7f83…`、config `a6884eab…`；基础 RC2 candidate `10a6cb45…`、manifest `39dc5055…`（60 项）；4202 初态 `day4-square-initial-stripfold-20261103-062710-242560`，`result.json` `4472f4df…`、`initial_geometry.npz` `a6646d66…`。新 manifest 66 项 `778935ab…`、config `96acc5fa…`；[registration.json](day4-actionchunk-test/a5-rc2-d2c-release-order/registration.json) 记录身份、源码、测试、预期现象和比较指标，[static-audit.json](day4-actionchunk-test/a5-rc2-d2c-release-order/static-audit.json) 记录静态动作身份与 diff。

**唯一改动**：末次释放时先在 `holding=true` 且附件仍启用时完成 10 步夹爪张开，再解除附件；原 `ungrasp` 内第二次 `open()` 被抑制。120 步等待、12 个公开动作/目标/命令/horizon、退让目标、事件和 1 mm / 3 mm 阈值保留；与 D1 相比总物理步数不变（同样的 10 步张开移到解除之前）。不提高摩擦、不清零布料速度。

**预期**：释放步及前 5 步速度相对 D1 下降；若首个释放后速度是主因，等待/退让/正式窗口漂移下降；若不变，则释放顺序不是主因。按释放后 elapsed time 对齐，保留 0–0.5 s 瞬态和后续滑移证据；布料接触只能用高度/穿透/粒子速度，不能声称接触力。

**离线验证**：manifest 66/66、基础 60 项不变；release-order fixture 8/8、delay fixture 5/5、release fixture 1/1、`py_compile`、`bash -n` 通过；21/21 action/horizon 行与 D1 相同，`start_ee`/退让目标/`release(target)` 相同，recovery diff 仅版本字符串与 `release_order` 元数据（11 行）。**预运行补查：** preopen 10 步每步检查 holding/attachment 一致并调用 `control.assert_exclusive()`；`audit_episode_evidence.py`/`episode_evidence.py` 与 D1 字节相同，全程状态检查未关闭。释放 t=0 用附件解除后立即的 `released` sample，不用首个全关 state；记录 boundary/released step 与 delta，delta 非零报告采样误差。**该版本随后已按 D2-D 上传、远端预检并单次运行 4202 single；见上。** 正式成功 0。

## 2026-11-04 D2-D：释放顺序对照完成（单次 4202 single）

运行 `day4-a5-rc2-d2c-release-order-20261104-090032-412133`：退出码 0，episode `passed=True`、`absolute_step=2219`、等待 1955–2075、trace 331 步，与 D1 完全一致；`DIAG_ASSESS complete=True`、`quality=rejected`。预检 66/66、未启动仿真；`completed` 已写入、无重试；下载证据与 ledger SHA256 一致。详见 [D2-D 对照](day4-actionchunk-test/results/D2_D_COMPARE_20261104/review.md)。

**预运行补查：** preopen 10/10 步每步检查 holding/attachment 一致并调用 `control.assert_exclusive()`；`audit_episode_evidence.py`/`episode_evidence.py` 与 D1 字节相同，全程检查未关闭。D2-C 边界 `released` sample 与最后 preopen state 同 step/time（delta=0），首个全关 state 为 +1 步；D1 anchor→首个自由 state 为 1 步（16.7 ms）。

**对照：** 干预前 action target 最大差 0.0、anchor 顶点/EE/关节 0.0；release t=0 质心差 0.0113 mm、P95 0.0293 mm、最大 0.0375 mm；释放一步粒子速度 17.4197 vs 17.4223 mm/s；free 0–30 质心 1.9092 vs 1.9119 mm、P95 12.2286 vs 12.2044 mm；free 30–120 −3.02%/−2.65%；退让 −2.83%/−1.27%；正式窗口 2.0409→1.9823 mm（−2.87%）、P95 4.4134→4.3426 mm（−1.60%），仍超阈值、quality rejected。

**结论：** 释放顺序未降低释放瞬态/前 0.5 s 速度，**不是该例漂移的主要因素**；正式窗口小幅下降不能归因于释放后速度下降；单例、无接触力/冲量，不能声称碰撞因果。正式成功 0。

## 2026-11-04 D2-E 步骤2：支撑面与摩擦配置核查（仅离线）

[D2-E 审查表](day4-actionchunk-test/results/D2_E_SUPPORT_MATERIAL_AUDIT_20261104/review.md) · [JSON](day4-actionchunk-test/results/D2_E_SUPPORT_MATERIAL_AUDIT_20261104/support_material_audit.json) · [CSV](day4-actionchunk-test/results/D2_E_SUPPORT_MATERIAL_AUDIT_20261104/support_material_table.csv)

离线读取 D2-A 场景读回、D2-C 几何/轨迹和源码；未启动新 episode、未改物理参数。默认地面是唯一与布料存在有效碰撞候选的表面（z=0、水平、50 m 代码值、enabled）；室内地面 disabled；附件块/机器人手/指与布料碰撞组过滤，附件块释放后仍保留但不能承托。布料材质绑定在 `particleSystem -> particleMaterial`（friction 0.3、particleFrictionScale 0）；地面 CollisionPlane 无直接 material binding，代码 0.5/0.5/0.8 未确认生效；附件块 0.2/1.0/0 是刚体默认且与布料无关。布料 z_min≈9.876 mm，比 10 mm particleContactOffset 低约 0.123–0.124 mm；几何证据，不是接触力。当前不选择修正；有效摩擦需步骤5单变量敏感性，步骤3纯读回非前置条件。

## 2026-11-04 D2-E 步骤4 + 步骤5决定

步骤4 复用 D1/D2-C 轨迹离线完成：[报告](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/review.md)、[JSON](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_summary.json)、[CSV](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_bins.csv)、[速度/转速/方向](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_speed_rotation.png)、[高度](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_height.png)、[支撑几何](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/support_geometry.png)。首个释放后速度约 11.0 mm/s 质心、17.4 mm/s 粒子（速度测量，不是冲量）；前 1 s 快速衰减；1.5–10 s 近恒定 ~1.0 mm/s、~0.36°/s（D1 1.024、D2-C 0.993 mm/s），持续方向约 26–27°、比释放方向转约 25°；z_min≈9.871–9.876 mm，无地面穿透，低于 contact offset 约 0.124–0.129 mm。两版稳态差约 3%。

**步骤5决定：** `particleFrictionScale: 0.0 → 1.0` 单变量敏感性，候选拟名 `a5-rc2-pfs1`，从 RC2 原流程派生，不保留 120 步等待或 D2-C 释放顺序；`friction=0.3`、地面/碰撞、动作/目标/horizon/退让目标不变。不选地面材质绑定作为本轮干预（刚体材质，不能直接当作粒子摩擦）。该参数从 episode 开始全局生效，影响 recovery/fold/release，不是仅释放后接触对照；4202 初态文件不重生。只跑 4202 single 一次；通过条件为原几何 + 质心 ≤1 mm + P95 ≤3 mm + 证据完整。[预登记草案](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/step5_decision.md)。**候选随后已创建、离线验证并单次运行；见下。**

## 2026-11-04 a5-rc2-pfs1：粒子间摩擦缩放敏感性单次运行

候选 [a5-rc2-pfs1](day4-actionchunk-test/a5-rc2-pfs1/README.md) 从 RC2 原流程派生，只把 `particleFrictionScale` 从 0.0 改为 1.0；`friction=0.3`、地面/碰撞、12 个公开动作/命令/horizon、退让目标和 `stage4_success_v1` 不变；不含 D1-120 等待或 D2-C preopen/释放顺序。manifest `bad4b59a…`（63 项）、config `2d72a405…`；4202 初态复用、未重生。

运行 `day4-a5-rc2-pfs1-20261104-102101-983000` 一次：runner 退出 0、entry 评估退出 0、episode `passed=True`、12 个动作、质量 **accepted**；正式 210–330 evaluator 质心 **0.2642 mm**、顶点 P95 **0.3792 mm**（RC2 2.0429 / 4.4141 mm），几何全程通过。首个 0.5 s 位置差分质心 **11.555 mm/s**、粒子 **15.000 mm/s**；1.5–8.0 s 持续质心 **0.595 mm/s**、粒子 **1.375 mm/s**、角速度 **0.104°/s**；z_min≈9.867–9.879 mm，无穿透。证据 manifest 73/73 一致；ledger 15/16，缺 `contact_report.json`（非必需）。动作 target 与 RC2 不同：fold 约 +2.0 mm、退让约 +2.0 mm，来自 recovery 后重新计算 pick/yaw。

**观测 caveat：** `ClothPrimView.get_velocities()` 的 formal 读回粒子平均 28.76 mm/s，而世界顶点位置差分 1.29 mm/s；读回场 2 s 内几乎不变、与位置差分向量相关约 −0.006。EE 静止、attachment/holding=false，不能由机器人运动解释。该读回不能当作实际速度或冲量；报告改用位置有限差分，原始数据保留为 unvalidated。另无运行时 `particleFrictionScale`/`friction`/self-collision 读回；D2-A 的 `.3/0` 是未修改基线，不是 pfs1 运行时证据。contact-report 缺失且不覆盖 cloth-ground，0 事件不能当作无接触。

**判定：** 几何/评价器通过，属于候选改善证据；但速度读回与材料读回 caveat 使观测完整性不足，**不扩展 4302 single**，不重跑、不扫描参数。正式 Stage 4 成功仍为 0；不宣称地面摩擦已修复。详见 [pfs1 对照](day4-actionchunk-test/results/D2_E_PFS1_COMPARE_20261104/review.md)、[evidence_verification](day4-actionchunk-test/results/D2_E_PFS1_COMPARE_20261104/evidence_verification.json)。

## 2026-11-04 a5-rc2-pfs1-observation-v2：观测-only 复验

[a5-rc2-pfs1-observation-v2](day4-actionchunk-test/a5-rc2-pfs1-observation-v2/README.md) 保持 pfs1 物理/控制不变，只修订观测：世界顶点 FD 速度、raw readback unvalidated、构建后/reset 后/初始 settle/recovery 后/释放前五阶段材料读回、文件/语义/质量分离、contact 能力边界。manifest `d97bf349…`（63 项）、新一次性锁；旧 pfs1 结果保留。

单次 4202 复验 `day4-a5-rc2-pfs1-observation-v2-20261104-111514-134428`：`file_complete=true`、`observation_semantics_valid=true`、质量 **accepted**、`overall_valid=true`；formal 质心 **0.2642 mm**、P95 **0.3792 mm**；动作 target、recovery/pre-release 状态、formal 指标与 pfs1 **0 差**。材料五阶段 friction .3 / particleFrictionScale 1.0 / binding `/World/Garment/particleMaterial` / self/non-particle true；solver-effective 仍标 unverified；FD 484 有效区间、1 首帧无效；raw readback unvalidated。

**判定：** 观测修订通过，但只是观测-only 复验，不增加新的物理改善，也不是正式 Stage 4 成功。**尚未运行 4302 single**；先审查 v2；正式成功仍为 0；不宣称地面摩擦已修复；cloth-ground 力/冲量不是新增门槛。详见 [v2 对照](day4-actionchunk-test/results/D2_E_PFS1_V2_COMPARE_20261104/review.md)。

## 2026-11-04 a5-rc2-pfs1-observation-v2-4302：4302 single 单次扩展通过

[a5-rc2-pfs1-observation-v2-4302](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-4302/README.md) 固定 v2 候选，只把登记范围扩到 4302 single：63 项 manifest 中 61 项与 v2 逐字节相同，仅登记 JSON 与 runner 变化（manifest `6d1958f5…`、config `577931aa…`、runner `550efa65…`）；新锁 `a5-rc2-pfs1-observation-v2-4302-runs`，4202 结果与 v2 标记保留。4302 初态 `day4-square-initial-stripfold-20261103-094143-137994`（`1bed437f…` / `1c27514f…`）；预检 63/63。

单次运行 `day4-a5-rc2-pfs1-observation-v2-20261104-201557-235290`（tmux，无重试，下载 104/104 哈希一致）：`file_complete=true`、`observation_semantics_valid=true`、质量 **accepted**、`overall_valid=true`；`geometry_entire_window/stable/held/released_continuously` 全 true；正式 210–330 质心 **0.2390 mm**、P95 **0.3524 mm**（RC2 4302 single 1.9102 / 4.1231）。释放后 0.5 s 15.70/12.40 mm/s；1.5–8.0 s 0.372/0.659 mm/s、0.092°/s；z_min 9.867 mm；粘滞检查通过；材料 live 读回 0.3/1.0。

**边界：** recovery 末态相对 RC2 平移 10.27 mm，fold 目标由未改 expert 重算（差 7.7–8.0 mm、yaw −3.28°），因此是端到端对比；两次 dev 单例（4202/4302）均通过不等于跨 seed 统计或机制确认。正式 Stage 4 成功仍为 **0**；不跑七例/不冻结/不跑 held-out。详见 [4302 对照](day4-actionchunk-test/results/PFS1_V2_EXT_4302_20261104/review.md)。

## 2026-11-04 rc7 七例 RC：4/6 阳性通过，L1 回归失败

[rc7](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc7/README.md) 把 4202/4302 单例的物理/控制固定为一个候选并把 L1 接入 v2 观测；**uniform particleFrictionScale=1.0（含 L1）**；manifest `bcba8c11…`（63 项，60 项与 v2 逐字节相同）、新批次账本、七槽顺序每槽一次。

结果：4100 s/a **rejected**（0.7031/1.7764 mm；`free_edge_overrun` 15.4 < 20 mm、`free_edge_height_p90` 24.4 > 15 mm、`vertex_speed_max` 64.6 > 50 mm/s；RC2 pfs=0 为 40.7/10.1/16.5）；4202 s/a **accepted**（0.2642/0.3792）；4302 s/a **accepted**（0.2390/0.3524）；4201 single **rejected 有效**（0.9409/2.8073；几何全过，速度 P95 20.3 > 10 mm/s）。三组配对 target 差 **0.0**；7/7 证据完整、765/765 下载哈希一致；原版 `verify-dev` **失败**于 4100。

**判定：不冻结、不释放**（六阳性未全过 + verify-dev 失败）。下一版本建议 task-scoped 物理配置（L1=0.0、L2/L3=1.0）并重跑七例；本轮结果保留、不并入新矩阵。正式成功仍为 0。详见 [rc7 审查](day4-actionchunk-test/results/RC7_SEVEN_CASE_20261104/review.md)。

## 2026-11-05 rc8 task-scoped 七例 RC：通过

[rc8](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8/README.md) 按任务固定物理：L1 flat **0.0**、L2/L3 **1.0**，在材料构造时设置、早于 reset/物理步；materials 读回按任务核对（0.0 / 1.0）。manifest `68930010…`（63 项，59 项与 v2 逐字节相同）、新账本；七槽顺序、每槽一次、无重试。

结果：4100 s/a **accepted**（0.1435/0.2072 mm，与 RC2 pfs=0 逐值相同）；4202 s/a **accepted**（0.2642/0.3792）；4302 s/a **accepted**（0.2390/0.3524）；4201 single **rejected 有效**（0.9409/2.8073；几何全过，速度 P95 20.3 > 10 mm/s）。六阳性全部接受；三组配对 target 差 **0.0**；7/7 证据完整；807/807 下载哈希一致；本地 evaluator 重算 7/7 一致；视频审查通过；原版 `verify-dev` **通过**（`A5_DEV_VERIFIED 7`，exit 0）。

**判定：通过本轮 task-scoped RC**；冻结材料已整理（[FREEZE_DOSSIER](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/FREEZE_DOSSIER.md)）。本轮**未执行**显式 freeze、held-out、正式批次；正式成功仍为 **0**；结果按任务报告，不是统一物理条件下的难度比较。详见 [rc8 审查](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/review.md)。

## 2026-11-05 rc8b 初态协议补齐：七例 4/6 阳性，未冻结

[rc8b](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8b/README.md) 把协议补到初态生成：L1 flat 0.0、L2/L3 1.0；初态结果记录 task/材料绑定/scale/生成器身份；正式 preflight 拒绝旧/错初态；生成与正式入口改为 app-relative。4100/4201/4202/4302 各生成一次；4100 几何与旧初态逐位相同，L2 条宽在冻结范围，L3 extent 变化已记录。

七例：4100 s/a **accepted**（0.1435/0.2072）；4302 s/a **accepted**（0.2756/0.4125）；**4202 s/a rejected**（7.4809/11.5382；`stationary_half` 29.9 mm > 25；速度 P95 25.7 > 10 mm/s）；4201 rejected（7.0657/10.4252；`stationary_half` 30.1 mm）。三组配对 0.0；7/7 `initial_protocol=true`；765/765 下载哈希一致；本地复算 7/7 一致；`verify-dev` 失败于 4202。

**判定：六阳性 4/6 → 不冻结、未写回执。** 失败在 fold 后整体滑移（4202 fold extent 0.196×0.408，旧流程 0.228×0.420），机制未隔离；不回退旧初态、不用 rc8 结果补齐、不改阈值。下一步：调查 L2 初态敏感性，或显式修订协议（L2/L3 初态生成 0.0、rollout 1.0）后重跑。正式成功仍为 0。详见 [rc8b 审查](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/review.md)。
