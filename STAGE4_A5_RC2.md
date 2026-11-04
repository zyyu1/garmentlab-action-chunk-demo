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

**预期**：释放步及前 5 步速度相对 D1 下降；若释放冲量是主因，等待/退让/正式窗口漂移下降；若不变，则释放顺序不是主因。按释放后 elapsed time 对齐，保留 0–0.5 s 瞬态和后续滑移证据；布料接触只能用高度/穿透/粒子速度，不能声称接触力。

**离线验证**：manifest 66/66、基础 60 项不变；release-order fixture 8/8、delay fixture 5/5、release fixture 1/1、`py_compile`、`bash -n` 通过；21/21 action/horizon 行与 D1 相同，`start_ee`/退让目标/`release(target)` 相同，recovery diff 仅版本字符串与 `release_order` 元数据（11 行）。**预运行补查：** preopen 10 步每步检查 holding/attachment 一致并调用 `control.assert_exclusive()`；`audit_episode_evidence.py`/`episode_evidence.py` 与 D1 字节相同，全程状态检查未关闭。释放 t=0 用附件解除后立即的 `released` sample，不用首个全关 state；记录 boundary/released step 与 delta，delta 非零报告采样误差。**该版本随后已按 D2-D 上传、远端预检并单次运行 4202 single；见上。** 正式成功 0。

## 2026-11-04 D2-D：释放顺序对照完成（单次 4202 single）

运行 `day4-a5-rc2-d2c-release-order-20261104-090032-412133`：退出码 0，episode `passed=True`、`absolute_step=2219`、等待 1955–2075、trace 331 步，与 D1 完全一致；`DIAG_ASSESS complete=True`、`quality=rejected`。预检 66/66、未启动仿真；`completed` 已写入、无重试；下载证据与 ledger SHA256 一致。详见 [D2-D 对照](day4-actionchunk-test/results/D2_D_COMPARE_20261104/review.md)。

**预运行补查：** preopen 10/10 步每步检查 holding/attachment 一致并调用 `control.assert_exclusive()`；`audit_episode_evidence.py`/`episode_evidence.py` 与 D1 字节相同，全程检查未关闭。D2-C 边界 `released` sample 与最后 preopen state 同 step/time（delta=0），首个全关 state 为 +1 步；D1 anchor→首个自由 state 为 1 步（16.7 ms）。

**对照：** 干预前 action target 最大差 0.0、anchor 顶点/EE/关节 0.0；release t=0 质心差 0.0113 mm、P95 0.0293 mm、最大 0.0375 mm；释放一步粒子速度 17.4197 vs 17.4223 mm/s；free 0–30 质心 1.9092 vs 1.9119 mm、P95 12.2286 vs 12.2044 mm；free 30–120 −3.02%/−2.65%；退让 −2.83%/−1.27%；正式窗口 2.0409→1.9823 mm（−2.87%）、P95 4.4134→4.3426 mm（−1.60%），仍超阈值、quality rejected。

**结论：** 释放顺序未降低释放瞬态/前 0.5 s 速度，**不是该例漂移的主要因素**；正式窗口小幅下降不能归因于释放冲量减少；单例、无接触力/冲量，不能声称碰撞因果。正式成功 0。
