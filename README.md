# Garment Folding with Action Chunking

研究 single-step behavior cloning 与 H=4 action-chunk BC 在三档衣物初态下的折叠成功率、恢复能力和推理开销。当前工作集中在 GarmentLab / Isaac Sim 中建立可靠的 expert 和动作接口，尚未进入策略训练或正式对比实验。

## 当前状态（2026-11-05，暂停）

**开发候选已冻结，正式批次未运行；正式 Stage 4 成功仍为 0。**

- **rc8b**（task-scoped：L1 0.0、L2/L3 1.0，含初态生成；manifest `cce573dd…`）七例 **4/6 阳性**：4100 s/a、4302 s/a accepted（0.1435/0.2072、0.2756/0.4125 mm）；**4202 s/a rejected**（7.4809/11.5382 mm，`stationary_half` 29.9 mm > 25 mm，速度 P95 25.7 > 10 mm/s）；4201 也拒绝。三组配对 0 差、7/7 证据完整、765/765 下载哈希一致、本地复算 7/7 一致；原版 verify-dev **失败于 4202**。
- **初态协议检查通过**：4100/4201/4202/4302 各生成一次，记录 task/材料绑定/scale/生成器身份；正式 preflight 接受新初态并拒绝旧/错初态。4202 失败不是身份或协议失败，而是新初态（1.0 下 settle）改变了 L2 折后保持行为（具体机制未隔离）。
- **未执行 freeze**，未写 `verified-dev.json`/`E_RELEASE.json`；未回退旧初态、未用 rc8 结果补 4202/4201、未改阈值。正式 Stage 4 成功仍为 **0**；held-out 与正式批次未运行。
- **L2 离线定位（无新增仿真）：** 新旧 4202 在载入时是 2.80 mm / −0.26° 的**整体位姿差**；recovery 后内部形状差仅 1 µm（纯平移 2.02 mm），pre-release 折形差 <0.8 mm；放大发生在**释放后**（新初态持续 ~4 mm/s 滑移，首个几何失败在 release 后 4.15 s）。9.2 µm 只是几何指标，recovery 残余速度/接触/应力仍未知；“3 mm→30 mm”是相关观察，不是因果。
- **l2pose 位姿匹配诊断（单次，已完成）：** 旧折叠几何 + 新位姿 → **accepted，中间行为**（质心 0.7396 / P95 1.5397 mm、stationary 7.63 mm、稳态 0.418 mm/s、无失败；old 0.2642/0.3792，new 7.4809/11.5382）。专家目标跟随新位姿（与 new 差 0.209 mm），但不是失败原因。2.8 mm 位姿变化**不足以**单独重现失败；l2pose 与 new 只剩亚毫米 `final` 几何差（P95 0.067 / max 0.302 mm），与该例失败相关但不能归因隐藏应力。
- **两例重复性（已完成）：** `l2pose-repeat1` 与 `rc8b-4202-repeat1` 各一次、原候选/原初态/完整哈希；**两例逐位重现原行为**（所有阶段、目标、success_trace 最大差 0.0 mm；l2pose accepted 0.7396/1.5397，rc8b rejected 7.4809/11.5382，首次失败 step 249 相同）。这两个固定配置下的结果可重复；不能全面排除所有初始化或状态恢复问题。
- **局部几何：** #91（0.302 mm）位于多层折叠区，距折线代理约 55 mm；25 mm 内 4 层 z≈9.9/40.6/53.75（含 #91）/66.4 mm，层间距约 13 mm；xy 最近点 99.3% <0.1 mm。层间距/投影仅为代理，不认定真实接触/穿透。
- **九点 z patch（已完成）：** new 初态仅改 #91 3×3 邻域九点 z 为 derived 值（索引 69/70/71/90/91/92/111/112/113，运行前固定）；派生初态 `initial_diagnostic=true`，审计恰好九点改变、其余逐位不变。结果仍 **rejected 7.2532/11.4799 mm**（new 7.4809/11.5382；first 251 vs 249），pre-release 0.50 mm、trace max 2.14 mm；响应很小、轨迹基本不变，不能认定层序/接触机制，也不能手工修补正式初态。
- **recovery 后固定保持 120 步（r1 诊断 + r2 干净复验 + 4302 扩展，均已完成）：** 4202 r1 accepted 0.2374/0.3484 mm；审计入口修复后 **4202 r2 干净复验**（entry/runner/audit 均 0）**accepted 0.2374/0.3484**、stationary 6.69、无失败，且与 r1 逐阶段 0.0 差；**4302 扩展**（均 0）**accepted 0.2386/0.3468**、stationary 7.16、无失败（rc8b 参照 0.2756/0.4125）。保持 2 s 内运动已接近零（质心 ~0.0001 mm/s、P95 ~0.005–0.007 mm/s、EE 漂移 ~0、附件全关），不是“运动衰减”；额外静态步改变下游 fold，机制未隔离。
- **七例 RC（已完成，六阳性 accepted）：** `a5-rc8b-recovery-hold120-rc7`（manifest `41db790f…`）slot1 4100 single **accepted 0.1435/0.2072**；初次 audit exit 5 为 L1 `hold_applicable` 契约缺陷，同结果修订审计 exit 0。修订候选 `…-r2`（manifest `40858efc…`，仅 config 差异；继承记录仅 slot1）续跑 slots2–7：4100 arc4/4202 s,a/4302 s,a **全部 accepted**，4201 **有效 rejected 7.2583/11.0030**。三组配对目标差 0.0；L2/L3 hold 均 120 步/121 帧/2.0 s；下载 118+664 哈希一致；本地复算 7/7；来源兼容验证 `RC7_SOURCE_VERIFIED` exit 0。原版 verify-dev 未使用（单一 manifest 限制），不称原版通过。
- **冻结与门禁（已完成）：** 使用来源兼容 `freeze_rc7_sources.py --execute`（exit 0），独占创建 `verified-dev.json`（`67c64a55…`）与 `E_RELEASE.json`（`9042e88e…`）；`verification-manifest.json` `7d328159…`，83/83 条目核验通过；`gate_rc7_sources.py` exit 0（`A5_GATE_OK_SOURCE 7`）。临时副本 10/10 负测通过；未使用旧 single-manifest freeze 入口。
- **正式批次离线预检（已完成，未运行）：** 固定 60 初态 / 120 槽（L1 4110–4129、L2 4210–4229、L3 4310–4329），seed/plan 逐项一致、无 dev 重叠；部署层 `formal_driver.py` 先调 `gate_rc7_sources.py`，再使用冻结初态/rollout/audit 入口；deployment manifest `1a36b8c4…`（18/18 条目）；离线桩测试 10/10；预检 exit 0。容量约 2.9 GB、机时约 35 h，远端可用 14 GB。见 [FORMAL_PREFLIGHT](day4-actionchunk-test/formal_hold120/FORMAL_PREFLIGHT.md)。
- **正式验收改为最低完成方案（执行异常暂停）：** 原 60 初态/120 槽计划**未启动**，保留并标记为被取代；新计划每档只跑 single，固定顺序 L1 4110–4129、L2 4210–4229、L3 4310–4329；**每档取得 5 个不同 seed 有效成功即停，最多 20 seed**，不换 seed/不重试/不调阈值。每档先生成并保存 10 份初态截图。独立 `minimum_hold120` 部署/账本；运行 30/30 初态截图后，flat 档 4112 因 L1 waypoint 非收敛执行异常暂停；0 有效成功，最低验收未通过。单次只读诊断已复现：arc135 最后 120 tick 中关节速度 118 tick 超 0.1 rad/s（首 tick 0.2529），位置前 10 tick 通过、tick10 后越界；block ≤1.655 mm 合格。深诊断：目标交接一致（差 2.8e-17 m）；关节0 的 RMP 位置目标步进等效 0.204–0.236 rad/s、速度字段仅 0.018–0.102，实际 0.253–0.290；关节2 实际 0.109–0.147 但目标 <0.1。证据同时指向 RMP 位置轨迹过快与底层跟踪过冲；缺底层 apply_action 消费/增益证据。详见 [深诊断](day4-actionchunk-test/results/MINIMUM_ACCEPTANCE_20261105/diag_4112_deep/4112_DEEP_DIAGNOSIS.md)。
- **下一步：** 最低方案执行异常暂停；不自动重试/不换 seed；需明确指令决定诊断后重登记或终止。正式成功仍为 0。

[交接日报（L2 诊断与暂停）](2026-11-05-GarmentLab日报%20Stage4%20rc8b初态协议与七例失败交接.md) · [L2 定位](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/review.md) · [l2pose 审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/l2pose_review.md) · [重复性与几何](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/repeat_review.md) · [九点 z patch](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/l2patch9_review.md) · [hold120 r2/4302](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_r2_review.md) · [七例 rc7](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_rc7_review.md) · [冻结归档](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_rc7_r2_resume/freeze/FREEZE_ARCHIVE.md) · [正式预检](day4-actionchunk-test/formal_hold120/FORMAL_PREFLIGHT.md)

**前序：rc7 uniform 七例 RC 未通过（4/6）。** 固定候选 rc7（manifest `bcba8c11…`，60/63 与 v2 相同），uniform `particleFrictionScale=1.0`（含 L1）：4100 s/a **rejected**（自由边 15.4 < 20 mm、高度 24.4 > 15 mm、速度 64.6 > 50 mm/s），4202/4302 s/a accepted，4201 有效拒绝；配对 0.0、证据完整，但六阳性未全过、verify-dev 失败于 4100。结论：uniform 1.0 在 4100 这个开发例上造成 L1 回归失败（自由边未落桌/自重锁未发生的解释为视频支持，尚未独立确认因果）；rc7 保留为失败候选。[rc7 审查](day4-actionchunk-test/results/RC7_SEVEN_CASE_20261104/review.md) · [rc7 版本](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc7/README.md)

**前序：4302 single 扩展通过（质量 accepted + 证据完整）。** 固定 `a5-rc2-pfs1-observation-v2` 候选，只扩登记范围到 4302 single（61/63 manifest 项与 v2 逐字节相同）；单次运行 `day4-a5-rc2-pfs1-observation-v2-20261104-201557-235290`：`overall_valid=true`、`geometry_entire_window/stable/held/released_continuously` 全 true，正式 210–330 质心 **0.2390 mm**、P95 **0.3524 mm**（RC2 4302 single 1.9102 / 4.1231，−87.5% / −91.5%），无重试、下载 104/104 哈希一致。[4302 对照](day4-actionchunk-test/results/PFS1_V2_EXT_4302_20261104/review.md) · [4302 版本](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-4302/README.md)

**前序：a5-rc2-pfs1-observation-v2 单次 4202 观测修订复验。** D1-120 的延迟退让没有降低漂移；D2-A/B 完成实际场景与接触通道核查；D2-C 预登记“附着保持期间完成夹爪张开、随后解除附件”的单变量干预；D2-D 仅运行一次 4202 single：episode `passed=True`、诊断 `complete=True`、质量 `rejected`（质心 **1.9823 mm**、P95 **4.3426 mm**，仍超 1 mm / 3 mm）。释放一步粒子速度 **17.4197 vs 17.4223 mm/s**，free 0–30 基本不变 → **释放顺序不是该例漂移的主要因素**。随后 `a5-rc2-pfs1` 只改 `particleFrictionScale 0.0→1.0`：4202 single 质量 **accepted**（0.2642/0.3792 mm），但速度读回与材料读回有观测缺口；v2 观测-only 修订后 4202 复验 `overall_valid=true`，物理指标 0 差。v2 的行为证据见 [v2 对照](day4-actionchunk-test/results/D2_E_PFS1_V2_COMPARE_20261104/review.md)。

**D2-E 步骤2（仅离线）：** 支撑/摩擦核查完成。默认地面是唯一与布料存在有效碰撞候选的表面（z=0、水平、50 m 代码值、enabled）；室内地面 disabled；附件块/机器人手/指与布料碰撞组过滤，附件块释放后仍保留但不能承托。布料材质绑定在 `particleSystem -> particleMaterial`（friction 0.3、particleFrictionScale 0）；地面 CollisionPlane 无直接 material binding，代码 0.5/0.5/0.8 未确认生效；附件块 0.2/1.0/0 是刚体默认且与布料无关。布料 z_min≈9.876 mm，比 10 mm particleContactOffset 低约 0.123–0.124 mm；几何证据，不是接触力。当前不选择修正；有效摩擦需步骤5单变量敏感性，步骤3纯读回非前置条件。[D2-E 审查表](day4-actionchunk-test/results/D2_E_SUPPORT_MATERIAL_AUDIT_20261104/review.md)

**D2-E 步骤4（仅离线）/步骤5决定：** 复用 D1/D2-C 轨迹：首个释放后速度约 11.0 mm/s 质心、17.4 mm/s 粒子（速度测量，不是冲量）；前 1 s 快速衰减，随后 1.5–10 s 近恒定 **~1.0 mm/s、~0.36°/s**（D1 1.024、D2-C 0.993 mm/s），持续方向约 **26–27°**、比释放方向转约 25°；z_min≈9.871–9.876 mm，无地面穿透，低于 contact offset 约 0.124–0.129 mm。步骤5选择 **`particleFrictionScale: 0.0 → 1.0`** 单变量敏感性；候选 `a5-rc2-pfs1` 从 RC2 原流程派生，不保留 120 步等待或 D2-C 释放顺序；该参数全局影响 recovery/fold/release，不是仅释放后接触对照。**候选已创建并单次运行 4202 single；pfs1 质量 accepted，其观测缺口随后由 a5-rc2-pfs1-observation-v2 复验补齐（`overall_valid=true`）。4302 已按预登记单次扩展并通过（见上）；正式成功 0。** [步骤4报告](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/review.md) · [步骤5预登记草案](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/step5_decision.md) · [pfs1 版本](day4-actionchunk-test/a5-rc2-pfs1/README.md) · [v2 版本](day4-actionchunk-test/a5-rc2-pfs1-observation-v2/README.md)

## 历史进度（截至 2026-11-04）

| 工作项 | 状态与证据 |
| --- | --- |
| 仿真与动作接口 | 已有 `GarmentLabBackend`、动作/观测 schema、状态导出和视频记录；仍有待整合项。 |
| 物理配置与诊断 | 已完成配置读取、质量/迭代数对照及抓取、释放、控制诊断；历史结果和失败记录已保留。 |
| 原服装折叠 | 多次动作流程完成，但未得到已验收的释放后保持折叠；旧服装与被动载体探索分支已冻结。 |
| 单层方巾 L1 | 转向原计划范围内的 40 cm 单层方巾、单 Franka；441 顶点、800 三角形。先打通一个符合公共接口的 L1，再扩展三档。 |
| L1 折叠（开发） | yaw-aware 7 动作 + 独立“过折”折形（place 多伸 2 cm）：seeds 4100–4109 共 10/10 通过 runner 断言，释放后稳定（crossed 1.000、IoU 0.37–0.42、z_p95≈67.5 mm）。只算开发复验，不是验收。 |
| L2/L3 组合（开发） | 12 动作（5 recovery + 7 fold）在 L2/L3 的 right 槽位各有一个通过例；left（默认折向）在 4200/4300 释放后回弹。 |
| 任务定义冻结 | L1（过折）与 L2/L3（nominal 20/20）是两个折形任务，L2/L3 是同一任务下的两种初态族；三档汇总只能称多任务平均。见 [冻结文档](STAGE4_TASK_DEFINITION_FREEZE.md)。 |
| 表示层（single vs H=4） | 两个折叠脚本支持 `--execution single` / `arc4`，只把四个 arc 目标合成一个 H=4 chunk。L1/4100 与 L2/4200 各跑 single+arc4 配对：审计 `PAIRS_COMPARABLE`，同一对内快照**逐字节相同**、指标差全为 0 → 只证明专家轨迹在两种表示下等价，**不构成 H=4 收益证据**。 |
| 分任务报告 | 按 L1（过折）与 L2/L3（nominal 20/20）分别汇总：冻结版 seed 级 L1 1/1、L2/L3 0/2（L2/4200、L3/4300 left，共 4 次尝试全失败），多任务平均 0.50（A n=1、B n=2 个 seed）**不是难度曲线**；失败均为释放后回弹摊平，且补充的两例与既有同条件运行逐字节相同。见 [分任务报告](day4-actionchunk-test/results/STAGE4_PER_TASK_20261102/review.md)。 |
| 正式批次准备 | 每档 20 个 held-out seeds（L1 4110–4129、L2 4210–4229、L3 4310–4329）已登记并写入初态 plan；两个初态 runner 的 seed 断言已放宽，批次驱动与拒绝率汇总工具已就位，两份初态 manifest 已在远端无排除项核对通过。**未运行**（按 `b-right-dev-v1` 暂停），且正式成功判据阈值未冻结。见 [正式批次准备](STAGE4_FORMAL_BATCH_PLAN.md)。 |
| D2 释放顺序对照（2026-11-04） | D2-A/B 场景/接触核查；D2-C 单变量版本；D2-D 4202 single 一次：诊断 complete、quality rejected。释放瞬态/前 0.5 s 基本不变，正式窗口 2.0409→1.9823 mm、4.4134→4.3426 mm，仍拒绝。见 [D2-D 对照](day4-actionchunk-test/results/D2_D_COMPARE_20261104/review.md)。 |
| pfs1 粒子间摩擦敏感性（2026-11-04） | 从 RC2 原流程只改 `particleFrictionScale 0.0→1.0`；4202 single 一次，episode passed、quality **accepted**，正式窗口质心 **0.2642 mm**、P95 **0.3792 mm**。但速度读回不可用、无运行时材料读回；几何改善证据成立，观测完整性不足，不扩展 4302、正式成功不增加。见 [pfs1 对照](day4-actionchunk-test/results/D2_E_PFS1_COMPARE_20261104/review.md)。 |
| pfs1 观测修订（2026-11-04） | `a5-rc2-pfs1-observation-v2` 只改观测：FD 速度、材料读回、语义/质量分离、contact 能力。4202 single 复验：`overall_valid=true`、质量 accepted；动作/状态/formal 与 pfs1 0 差。尚未运行 4302；正式成功不增加。见 [v2 对照](day4-actionchunk-test/results/D2_E_PFS1_V2_COMPARE_20261104/review.md)。 |
| 正式验收与学习 | 三档正式成功轨迹、Stage 5 demonstrations、BC 训练及正式评估均未完成。正式 Stage 4 成功仍为 0。 |

截至 11 月 4 日的进度以 [Stage 4 下一步](DAY4_NEXT_STEPS.md) 和 [验收记录](DAY4_ACCEPTANCE_TRACKER.md) 为准。历史日报和旧脚本用于追溯，不应作为当前运行入口。

## 历史抓取诊断与修正候选

此前方巾试跑先后在抓取距离检查和下降运动中失败，均未证明 L1 折叠成功。源码审查确认：共享 Backend 尚未使用动作中的 `yaw`，位置运动也未固定末端姿态；使用下降前姿态一次性换算抓取偏移，不能保证到达时对齐。

独立开发候选 [square_pose_backend.py](day4-actionchunk-test/square_pose_backend.py) 采用统一定义：

- 公共动作保持 `XYZ + yaw + gripper_command`。
- `XYZ` 表示世界系 `right_gripper` 位置，单位为米；`yaw` 为世界 Z 轴角，单位为弧度。
- Backend 统一使用 `Rz(yaw) Rx(pi)`，固定局部 Z 轴向下，不由 expert 额外传入俯仰指令。
- 抓取代理参考点采用 URDF 命名指尖中点，相对 `right_gripper` 的局部偏移为 `+3.4 mm`；这不是经过真实夹持校准的接触模型。

该候选尚未替换共享 Backend。离线运动学解不代表动态执行成功：完整折叠末段仍出现关节解跳变；抓取段的 URDF 手指网格对地余量约 1 mm，不能据此认证实际 USD 碰撞或稳定性。v5 接触正控已验证，但发现双指触地 356 条事件；接触明细位置、法向和冲量均为零，不能解释为零接触力。机器人与附件组已有过滤，robot_block=0 不能证明无碰撞。

详见 [末端接口审查](DAY4_SQUARE_FRAME_AUDIT.md)、[离线运动学结果](day4-actionchunk-test/frame_audit/pose_audit.json) 和 [网格间隙检查](day4-actionchunk-test/frame_audit/clearance_audit.json)。

## 2026-11-02 交接记录

当时状态以 [2026-11-02 日报](2026-11-02-GarmentLab日报%20Stage4%20L2L3初态与6b交接.md) 为准：任务定义与表示层已冻结，表示层配对、分任务报告与任务 B 的冻结版 single 证据均已完成。第 7 步正式批次已**登记但未运行**：每档 20 个 held-out seeds（L1 4110–4129、L2 4210–4229、L3 4310–4329）与初态 plan/批次工具已就位，详见 [正式批次准备](STAGE4_FORMAL_BATCH_PLAN.md)。开跑前还差两件事：冻结正式成功判据阈值；决定是先跑 left 基线还是先解决 B 的释放后回弹。当前按 `b-right-dev-v1` 先做 right 的开发验证，批次保持暂停。

此前的 v5 短程保持/释放结论（位置误差 0.4733 mm、末臂速 0.00860 rad/s、锚点间隙 1.361 mm；双指触地 356 条事件、接触明细全零）仍是有效证据，但已被折叠开发例取代为“最新运行”。历史日报与旧脚本仅用于追溯，不作为当前运行入口。

详见 [11 月 2 日交接日报](2026-11-02-GarmentLab日报%20Stage4%20L2L3初态与6b交接.md)、[Stage 4 下一步](DAY4_NEXT_STEPS.md) 与 [v5 预登记](day4-actionchunk-test/SQUARE_GRASP_HOLD_V5.md)。后续下载由用户手动执行。

仓库是代码与精简证据归档，不是完整环境镜像。实验依赖 Isaac Sim 4.0、现有 GarmentLab/Backend 环境及对应文件清单；历史入口不代表当前应运行的实验。

## Stage 4 原验收计划（历史）

1. 得到完整释放、退让和静置后仍保持重叠的 L1 候选，并独立重复确认。
2. 将有效控制整合到正式 Backend，验证 `reset(seed, difficulty)`、episode 内重抓取及连续 10 次 reset/rollout；折叠与 recovery 合计不超过 12 个高层动作。
3. 固定 L1/L2/L3 初态协议和 seeds，每档保存 10 张可复现、肉眼可区分的初态截图，共 30 张。
4. 实现有明确触发与停止条件的 recovery：全局最多两次，但当前 7+5 动作模板在 12 步预算内仅能执行一次；在开发回合上冻结指标、测量时刻和阈值。
5. 正式批次每档至少取得 5 条成功 expert episodes，共至少 15 条。保留全部尝试、失败原因、动作/状态/视频，并报告 `rejection rate = 被拒绝的尝试数 / 总尝试数`。
6. 完成公共接口隔离检查及验收材料后，再进入 Stage 5 demonstrations 批量生成。

详细要求见 [最低完成计划](DAY4_MINIMUM_PLAN.md) 和 [十阶段执行计划](Marian_Frei_GarmentLab_2024_10_stage_execution_plan.md)。

## 仓库导航与数据范围

| 路径 | 内容 |
| --- | --- |
| `backends/`、`schemas/` | 共享 Backend 与动作/观测定义；实验候选不等于正式整合版本。 |
| `configs/`、`envs/` | 难度配置与接口；存在配置不代表三档已验收。 |
| `day4-actionchunk-test/` | Stage 4 实验脚本、依赖清单、离线审查及精简结果。 |
| `day4/upstream/` | 当前 GarmentLab 适配 patch 与部分源码快照。 |
| `runs/2026-10-13-third-grasp/` | Stage 2 历史图像、数组与日志证据。 |
| `docs/`、根目录日报 | 早期报告、假设与交接记录。 |

[2026-10-31 检查点说明](CHECKPOINT_20261031.md) 记录归档范围。Stage 4 原始视频、完整粒子数组、大型日志、环境和外部资产仍在本地及服务器，未随本次检查点全部上传。精简结果不能替代原始实验数据备份。离线审查使用的 SDK URDF/STL 网格也未打包；重跑审查需从对应安装版本取得。

## 后续研究安排

Stage 4 验收完成后，依次进行 demonstrations 与 dataset 构建、single-step BC、H=4 action-chunk BC、三档正式评估、结果分析与复现整理。当前不报告策略性能或折叠成功率结论。

## 上游与环境记录

本项目复用 [GarmentLab](https://github.com/GarmentLab/GarmentLab) 的场景、机器人、布料和控制组件，新增动作分块接口、实验控制与审查流程。当前适配快照的基线与覆盖范围见 [检查点说明](CHECKPOINT_20261031.md)；早期改动见 [AutoDL 适配 patch](third_party/autodl_adaptations.patch)。

更多背景：[环境记录](environment_log.md)、[Stage 2 报告](docs/2026-10-13_stage2_report.md)、[真机迁移假设](docs/sim2real_assumptions.md)。早期环境与硬件记录属于对应实验日期，不代表当前实例配置。


## 2026-11-02 b-right-dev-v1 开发复验与移交后审计完成

汇总器缺失结果分母修复与8项离线测试已通过；原项目代码与已测试副本SHA256一致（9a757d34…）。一次通过+一次无结果error的合成回归输出2次尝试、50%拒绝率；空批次保持null。

L2 4200的right single/arc4由本聊天在移交前完成；L3 4300采用另一聊天产出的最早外部single/arc4，按目录启动时间选择而非passed。两对均通过原版PAIRS_COMPARABLE，四份选定结果held gate通过、crossed=1.0，L2 IoU=0.559091、L3 IoU=0.562997；各对目标差及五项指标差值精确为0。底层21项代码不变，四份结果的独立23项变体manifest、配置和初态文件哈希均核对一致。

共下载核验66个远端文件，包含6份完整开发结果：选定4份配对结果与2份额外L3 single重复尝试。额外尝试原样保留，不增加独立seed覆盖，不计算正式成功率。用户移交后本聊天仅下载审计，未再提交GPU仿真，未终止已在途远端进程。

结论仅为每档一个开发seed在OPEN后30 release ticks+settle(180)终态保持；没有独立退让、第二retention样本或长期稳定性验证，不能外推整个开发集/held-out，更不能解释为BC策略或H=4性能提升。right为独立变体，不替换left失败或默认定义。held-out与正式批次保持暂停，正式Stage 4成功仍为0。

完整报告：[right开发复验与移交后审计](../thesis/day4-actionchunk-test/results/TASK_B_RIGHT_DEV_V1_20261102-183740/review.md)。

补充交叉核对（2026-11-02）：把主审计未采用的 4200 arc4 尝试 `025355-106410` 与 4300 single 重复尝试 `031535-711404` 一并核对，5 个目录 77 项检查全部通过；同 seed 全部 7 次已下载尝试（4200 三例、4300 四例）的 `final.npz` 441 个顶点逐位相同（max|Δ|=0），包括并发在途的 4200 arc4 两例。该核对不新增 seed、不改任何阈值、不改变上述结论。[补充审计](../thesis/day4-actionchunk-test/results/B_RIGHT_DEV_AUDIT_SUPPLEMENT_20261102/review.md)。

right 开发覆盖扩展 `b-right-dev-v2` 已登记、未运行：L2 4201–4209、L3 4301–4309 共 18 个剩余开发 seed，先登记初态哈希再跑 right single；不跑 arc4、不冻结阈值、held-out 不动。见 [扩展计划](STAGE4_B_RIGHT_DEV_V2_PLAN.md)。

## 2026-11-04 D2 释放顺序对照（暂停点）

D1-120 的 120 步延迟退让没有降低漂移（等待 2.0783/4.5603 mm、退让 2.4590/5.3214 mm、正式窗口 2.0409/4.4134 mm；与基线在相同 elapsed 时间点逐位相同），说明问题不在等待时长。D2-A/B 完成实际支撑、材质、释放时序和 contact-report 核查：支撑面只有 PhysX 默认材质；particle material 已绑定（friction 0.3、particleFrictionScale 0）；附件在 1944 断开而夹爪到 1954 才报告 open，释放一步速度跳至 17.42/11.04 mm/s；cloth-ground contact report 不支持，0 事件不是无接触。

D2-C 因此只改释放顺序：夹爪在附件仍启用时完成 10 步张开，再解除附件；抑制原 `ungrasp` 内第二次 `open()`。120 步等待、12 个公开动作/目标/命令/horizon 和退让目标保留；总物理步数与 D1 相同。preopen 10/10 步每步检查 holding/attachment 一致并调用 `control.assert_exclusive()`；全程 evidence 检查未关闭。D2-C 的 `released` sample 与最后 preopen state 同 step/time（delta=0），首个全关 state 为 +1 步。

D2-D 仅运行一次 4202 single `day4-a5-rc2-d2c-release-order-20261104-090032-412133`：退出码 0、episode `passed=True`、`DIAG_ASSESS complete=True`、`quality=rejected`、`absolute_step=2219`、等待 1955–2075、trace 331 步，与 D1 完全一致；无重试，下载证据与 ledger SHA256 一致。

| 对照项 | D1 | D2-C |
|---|---:|---:|
| 干预前 action target / EE / anchor 最大差 | — | **0.0** |
| release t=0 质心 / P95 / 最大差 | — | **0.0113 / 0.0293 / 0.0375 mm** |
| 释放一步粒子平均速度 | 17.4197 mm/s | 17.4223 mm/s |
| free 0–30 质心 / P95 | 1.9092 / 12.2286 mm | 1.9119 / 12.2044 mm |
| free 30–120 质心 / P95 | 1.4730 / 3.2355 mm | 1.4284 / 3.1499 mm |
| 正式窗口 210–330 质心 / P95 | 2.0409 / 4.4134 mm | 1.9823 / 4.3426 mm |
| quality | rejected | rejected |

**结论：** 正式窗口质心/P95 小幅下降 2.87%/1.60%，可以表述为“释放顺序改变降低了本例正式窗口漂移”；但释放一步速度、release transition 和 free 0–30 基本不变，**不能说是降低了首个释放后速度**，也不能把下降归因于释放后速度变化。释放顺序不是该例漂移的主要因素；仍超 1 mm / 3 mm，质量 rejected。正式 Stage 4 成功仍为 0；held-out 与正式批次暂停；恢复工作时优先核查附件约束释放能量/接触状态、支撑面材质和布料—地面接触观测，不继续微调开爪顺序，不直接提高摩擦或清零速度。

详见 [D2-D 对照](day4-actionchunk-test/results/D2_D_COMPARE_20261104/review.md)、[交接日报](2026-11-04-GarmentLab日报%20Stage4%20D2释放顺序对照交接.md) 与 [D2-C 版本](day4-actionchunk-test/a5-rc2-d2c-release-order/README.md)。

## 2026-11-04 a5-rc2-pfs1 粒子间摩擦敏感性（当前暂停点）

`a5-rc2-pfs1` 从 RC2 原流程派生，只把 `particleFrictionScale` 从 0.0 改为 1.0；`friction=0.3`、地面/碰撞、12 个公开动作/命令/horizon、退让目标和 evaluator 不变；manifest `bad4b59a…`（63 项）、config `2d72a405…`；4202 初态复用。单次运行 `day4-a5-rc2-pfs1-20261104-102101-983000`：runner/entry 退出 0，episode `passed=True`，质量 **accepted**，正式窗口质心 **0.2642 mm**、P95 **0.3792 mm**（RC2 2.0429/4.4141 mm）；首个 0.5 s 位置差分质心 11.555 mm/s、粒子 15.000 mm/s；1.5–8.0 s 持续质心 0.595 mm/s、粒子 1.375 mm/s、角速度 0.104°/s；z_min≈9.867–9.879 mm，无穿透。证据 manifest 73/73；ledger 15/16，缺 `contact_report.json`（非必需）。

**观测 caveat：** `ClothPrimView.get_velocities()` formal 读回粒子 28.76 mm/s，而位置差分 1.29 mm/s；读回场 2 s 内几乎不变、与位置差分向量相关约 −0.006，不能当作实际速度或冲量。EE 静止、attachment/holding=false，不能由机器人运动解释。另无运行时 `particleFrictionScale`/`friction`/self-collision 读回；D2-A 的 `.3/0` 是未修改基线。contact-report 缺失且不覆盖 cloth-ground，0 事件不是无接触。

**判定：** 几何/评价器通过，属于候选改善证据；但观测完整性不足，**不扩展 4302 single**，不重跑、不扫描参数，不宣称地面摩擦已修复。正式 Stage 4 成功仍为 0。详见 [pfs1 对照](day4-actionchunk-test/results/D2_E_PFS1_COMPARE_20261104/review.md) 与 [evidence_verification](day4-actionchunk-test/results/D2_E_PFS1_COMPARE_20261104/evidence_verification.json)。

## 2026-11-04 a5-rc2-pfs1-observation-v2 观测修订复验

`a5-rc2-pfs1-observation-v2` 保持 pfs1 物理/控制不变，只修订观测：世界顶点 backward FD 速度、raw API readback 标 unvalidated、构建后/reset 后/初始 settle/recovery 后/释放前五阶段材料读回、文件完整/观测语义/质量分开记录、contact 能力边界。新 manifest `d97bf349…`（63 项）、新一次性锁；旧 pfs1 结果保留。

单次 4202 复验 `day4-a5-rc2-pfs1-observation-v2-20261104-111514-134428`：`file_complete=true`、`observation_semantics_valid=true`、质量 **accepted**、`overall_valid=true`。formal 质心 **0.2642 mm**、P95 **0.3792 mm**；首个 0.5 s 质心 11.555 mm/s、粒子 15.000 mm/s；1.5–8.0 s 质心 0.595 mm/s、粒子 1.375 mm/s、角速度 0.104°/s。材料读回五阶段均为 friction .3 / particleFrictionScale 1.0 / binding `/World/Garment/particleMaterial` / self/non-particle true；solver-effective 仍标 unverified。动作 target、recovery/pre-release 状态、formal 指标与 pfs1 **0 差**，确认只改观测。

**判定：** 观测修订通过，但这是观测-only 复验，不增加新的物理改善，也不是正式 Stage 4 成功。**尚未运行 4302 single**；先审查 v2，正式成功仍为 0；不宣称地面摩擦已修复；cloth-ground 力/冲量不是新增验收门槛。详见 [v2 对照](day4-actionchunk-test/results/D2_E_PFS1_V2_COMPARE_20261104/review.md) 与 [v2 版本](day4-actionchunk-test/a5-rc2-pfs1-observation-v2/README.md)。
