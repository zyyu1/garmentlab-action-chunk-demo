# 2026-11-04 GarmentLab 日报 · Stage 4 D2 释放顺序对照

**暂停位置**　D1-120 的延迟退让没有降低漂移后，D2 按“先核查场景/接触，再做单变量释放对照”的顺序完成。D2-A/B 确认了实际支撑、释放时序和 contact-report 的适用范围；D2-C 预登记并实现了“附着保持期间完成夹爪张开、随后解除附件”的单一改动；D2-D 只运行一次 4202 single，episode `passed=True`、诊断审计 `complete=True`、质量 `rejected`。**释放顺序没有降低释放瞬态或前 0.5 s 速度，不是该例漂移的主要因素。** 正式 Stage 4 成功仍为 0；held-out、正式批次和新的对照均暂停。

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

1. **释放顺序没有降低释放冲量。** 首个自由物理步的粒子平均速度 17.4197 vs 17.4223 mm/s，质心速度 11.0397 vs 11.0113 mm/s；release transition 的质心/P95 位移几乎相同；t=0 布料位置差 ≤0.037 mm。
2. **0–0.5 s 也基本不变**（质心 1.9092 vs 1.9119 mm，P95 12.2286 vs 12.2044 mm）。把夹爪张开移到解除之前，并没有改变布料离开约束后的初始运动。
3. **后续窗口有小幅下降。** free 30–120、retreat、formal 的质心/P95 低 1.3–3.0%；正式窗口质心 2.0409→1.9823 mm、P95 4.4134→4.3426 mm。可以表述为“**释放顺序改变降低了本例正式窗口漂移**”，但不能说是降低了释放冲量；正式窗口仍是 action-relative，D2-C 比 D1 晚 10 步释放，存在相位差异。单例也不足以外推。
4. **仍拒绝。** 1.98 mm > 1 mm、4.34 mm > 3 mm；质量 `rejected`。证据完整，保留为有效对照。
5. **接触边界。** contact_events=0 不是“无接触”；cloth-ground 接触力/冲量不可用。不能把下降归因于某种碰撞冲量。
6. **暂停判断：** 释放顺序不是该例漂移的主要因素。恢复工作时，优先核查附件约束释放时的能量/接触状态、支撑面材质和布料—地面接触观测；不要继续微调开爪顺序，也不要直接提高摩擦或清零速度来充当修复。

## 7. 当前边界与恢复入口

- 正式 Stage 4 成功仍为 **0**；RC2 未冻结；held-out 未运行；正式批次暂停。
- 原阈值 **1 mm / 3 mm** 不变；开发集证据不能替代正式验收。
- D2-C 仅 4202 single 一次；`completed` 已写入，不自动重试。
- 恢复入口：[DAY4_NEXT_STEPS](DAY4_NEXT_STEPS.md)、[DAY4_ACCEPTANCE_TRACKER](DAY4_ACCEPTANCE_TRACKER.md)、[STAGE4_A5_RC2](STAGE4_A5_RC2.md)。
- 关键产物：[D2-D 对照](day4-actionchunk-test/results/D2_D_COMPARE_20261104/review.md)、[comparison.json](day4-actionchunk-test/results/D2_D_COMPARE_20261104/comparison.json)、[windows.csv](day4-actionchunk-test/results/D2_D_COMPARE_20261104/windows.csv)、[对比曲线](day4-actionchunk-test/results/D2_D_COMPARE_20261104/d2c_release_compare.png)、[D2-C 版本](day4-actionchunk-test/a5-rc2-d2c-release-order/README.md)。
