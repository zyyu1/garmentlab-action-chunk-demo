# 当前验收状态（最新：2026-11-05 **rc8b 初态协议补齐后七例 4/6 阳性：4100/4302 s/a accepted，4202 s/a 与 4201 rejected（stationary half ~30 mm，fold 后整体滑移）；配对 0 差、证据完整、verify-dev 失败于 4202；l2pose 位姿匹配单次 accepted 0.7396/1.5397 mm（中间行为，未重现失败）；l2pose/rc8b 两例重复逐位重现原行为（阶段/目标/trace 最大差 0.0），固定初态差异可重复；未冻结、未写回执，正式成功仍为 0**；前序：2026-11-05 **rc8 task-scoped 七例 RC 通过：6/6 阳性 accepted、4201 有效拒绝、配对 0 差、verify-dev 通过；冻结前检查发现正式 L2/L3 初态生成仍为 0.0（应为 1.0），freeze 暂停、未写回执，正式成功仍为 0**；2026-11-04 **rc7 七例 RC 完成，4/6 阳性通过（4202/4302 s/a accepted；4100 s/a 质量拒绝），4201 有效拒绝，三组配对 0 差，verify-dev 失败，未放行**；2026-11-04 **4302 single 扩展通过**（`overall_valid=true`、质量 accepted、质心 0.2390 mm / P95 0.3524 mm）；2026-11-04 pfs1-observation-v2 4202 single 观测修订复验通过（0.2642/0.3792 mm）；2026-11-04 D2-E 步骤4 持续滑移核查完成（仅离线），步骤5 决定 particleFrictionScale 0→1.0 敏感性对照（已创建并单次运行）；D2-E 步骤2 支撑/摩擦配置核查完成（仅离线）；D2-D 释放顺序对照完成（4202 single 单次；质量仍 rejected）；D2-C 版本已登记并运行一次；D2-A/B 场景与接触核查完成；2026-11-03 D0 4202/4302 基线复现 + A5 RC2 漂移诊断第 1–3 项；2026-11-02 折形口径定稿 + 任务定义冻结 + 表示层配对 + 分任务报告 + A1 预检）

## 2026-11-05 rc8b 初态协议补齐：七例 4/6 阳性，未冻结

[rc8b](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8b/README.md) 把 L1=0、L2/L3=1 的协议补到初态生成：初态结果记录 task/材料绑定/scale/生成器身份；正式 preflight 拒绝旧/错初态；生成入口改为 app-relative。4100/4201/4202/4302 各生成一次（4100 几何与旧初态逐位相同；L2 条宽在冻结范围；L3 extent 变化已记录）。

七例（manifest `cce573dd…`，14 行账本）：4100 s/a **accepted**（0.1435/0.2072 mm）、4302 s/a **accepted**（0.2756/0.4125）、**4202 s/a rejected**（7.4809/11.5382 mm；`stationary_half` 29.9 mm > 25；速度 P95 25.7 > 10）、4201 rejected（7.0657/10.4252；`stationary_half` 30.1 mm）。三组配对 0.0；7/7 `initial_protocol=true`；765/765 下载哈希一致；本地复算 7/7 一致；`verify-dev` 失败于 4202。

**判定：** 六阳性 4/6 → **不冻结、未写回执**；保留失败，不回退旧初态、不用 rc8 结果补 4202/4201、不改阈值。失败在 fold 后整体滑移（4202 fold extent 0.196×0.408，旧流程 0.228×0.420），机制未隔离。详见 [rc8b 审查](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/review.md)。

**L2 离线定位（无新增仿真）：** 新旧 4202 在载入时是 2.80 mm / −0.26° 的整体位姿差；recovery 后内部形状差仅 1 µm（纯平移 2.02 mm），pre-release 折形差 <0.8 mm；放大在**释放后**（持续 ~4 mm/s 滑移，首个几何失败在 release 后 4.15 s）。9.2 µm 只是几何指标，recovery 残余速度/接触/应力未知；“3 mm→30 mm”是相关观察，不是因果。已预登记一次位姿匹配单例对照（未运行、待批准），见 [L2 定位](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/review.md) 与 [单例预登记](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/SINGLE_COMPARISON_PLAN.md)。

**l2pose 单次诊断（已完成）：** 旧折叠几何 + 新位姿 → **accepted 0.7396/1.5397 mm**、stationary 7.63 mm、稳态 0.418 mm/s、无失败；old 为 0.2642/0.3792，new 为 7.4809/11.5382。专家目标跟随新位姿（与 new 差 0.209 mm）。2.8 mm 位姿变化不足以单独重现失败；也不是完整旧行为，而是中间行为。l2pose 与 new 只剩亚毫米 `final` 几何差（P95 0.067 / max 0.302 mm），相关但不能归因隐藏应力；未做重复性。详见 [l2pose 审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/l2pose_review.md)。单次、无重试、未冻结。

**两例重复性（已完成）：** `l2pose-repeat1`（manifest `a529ec05…`）与 `rc8b-4202-repeat1`（`cb28ae4c…`）各一次、原候选/原初态/完整哈希；**逐位重现原行为**（所有阶段、目标、trace 最大差 0.0；l2pose accepted 0.739646/1.539675，rc8b rejected 7.480913/11.538153，首次失败 step 249 相同）。下载 111/111 ×2。固定初态差异可重复；仿真重复性不是来源。**局部几何：** #91（0.302 mm，z 0.264 mm）位于多层折叠区，距折线代理约 55 mm；25 mm 内 4 层 z≈9.9/40.6/53.75（含 #91）/66.4 mm，层间距约 30.7/13.15/12.64 mm；网格近邻差 0.003–0.246 mm；xy 最近点 99.3% <0.1 mm。层间距/投影仅为代理，不认定真实接触/穿透。详见 [重复性与几何审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/repeat_review.md)。**单变量对照设计（未运行）：** new 初态仅改 #91 的 3×3 邻域 z 为 derived 值，4202 single 一次；本轮不扩批、不冻结。

## 2026-11-05 rc8 task-scoped 七例 RC：通过但冻结被正式初态生成阻塞

[rc8](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8/README.md) 按任务固定物理：L1 flat **0.0**、L2/L3 **1.0**，材料构造时设置、早于 reset/物理步；manifest `68930010…`（63 项，59 项与 v2 不变）、新账本；七槽顺序、每槽一次、无重试。

| 槽 | seed / 模式 | 质量 | 质心 / P95 (mm) | 协议 expected |
|---:|---|---|---:|---:|
| 1–2 | 4100 single/arc4 | accepted | 0.1435 / 0.2072 | 0.0 |
| 3–4 | 4202 single/arc4 | accepted | 0.2642 / 0.3792 | 1.0 |
| 5–6 | 4302 single/arc4 | accepted | 0.2390 / 0.3524 | 1.0 |
| 7 | 4201 single | rejected（有效） | 0.9409 / 2.8073 | 1.0 |

六阳性全部接受；配对 target 差 **0.0**；7/7 证据完整；807/807 哈希一致；本地 evaluator 重算 7/7 一致；视频审查通过；原版 `verify-dev` **通过**（`A5_DEV_VERIFIED 7`）。4100 与 RC2 4100（pfs=0）逐值相同。

**判定：** 通过本轮 RC；冻结材料已整理（[FREEZE_DOSSIER](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/FREEZE_DOSSIER.md)）。但**冻结前检查未通过**：正式 L2/L3 初态生成仍强制 `particleFrictionScale=0.0`（应为 1.0），因此**未执行 freeze、未写回执**；建议 rc8b 修正初态生成并重跑七例后重新冻结。正式成功仍为 **0**。结果按任务报告，不是统一物理条件下的纯初态难度比较。详见 [FREEZE_PRECHECK](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/FREEZE_PRECHECK.md) 与 [rc8 审查](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/review.md)。

## 2026-11-04 rc7 七例 RC：4/6 阳性通过，未放行

[rc7](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc7/README.md) 固定 4202/4302 单例的物理/控制并接入 L1 观测；**uniform particleFrictionScale=1.0（含 L1）**；manifest `bcba8c11…`、新批次账本；七槽顺序、每槽一次、无重试。

| 槽 | seed / 模式 | 质量 | 质心 / P95 (mm) | 几何 | 配对 |
|---:|---|---|---:|---|---:|
| 1–2 | 4100 single/arc4 | rejected | 0.7031 / 1.7764 | false | 0.0 |
| 3–4 | 4202 single/arc4 | accepted | 0.2642 / 0.3792 | true | 0.0 |
| 5–6 | 4302 single/arc4 | accepted | 0.2390 / 0.3524 | true | 0.0 |
| 7 | 4201 single | rejected（有效） | 0.9409 / 2.8073 | true | — |

**4100：** `free_edge_overrun` 15.4 mm（<20）、`free_edge_height_p90` 24.4 mm（>15）、`vertex_speed_max` 64.6 mm/s（>50）；RC2 pfs=0 为 40.7 / 10.1 / 16.5。uniform pfs=1.0 使 flap 未滑到边缘外桌面，L1 过折自重锁未发生。4201 几何全过但速度 P95 20.3 > 10 → 有效拒绝。7/7 证据完整、765/765 哈希一致；`verify-dev` 失败于 4100。

**判定：不冻结、不释放**。放行条件 1 与 5 未满足。下一版本需登记 task-scoped（L1=0.0、L2/L3=1.0）并重跑七例；本轮结果保留、不并入新矩阵。详见 [rc7 审查](day4-actionchunk-test/results/RC7_SEVEN_CASE_20261104/review.md)。

## 2026-11-04 4302 single 扩展：质量 accepted + 证据完整（单次）

[a5-rc2-pfs1-observation-v2-4302](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-4302/README.md) 固定 v2 候选，只扩登记范围到 4302 single；61/63 manifest 项与 v2 逐字节相同。新 manifest `6d1958f5…`、新锁 `a5-rc2-pfs1-observation-v2-4302-runs`；预检 63/63；tmux 单次 `day4-a5-rc2-pfs1-observation-v2-20261104-201557-235290`，退出 0、无重试、下载 104/104 哈希一致。

**结果：** `file_complete=true`、`observation_semantics_valid=true`、质量 **accepted**、`overall_valid=true`；`geometry_entire_window/stable/held/released_continuously` 全 true、`failed_geometry_frames=[]`；正式 210–330 质心 **0.2390 mm**、P95 **0.3524 mm**（RC2 4302 single 1.9102 / 4.1231）。释放后 0.5 s 15.70/12.40 mm/s；1.5–8.0 s 0.372/0.659 mm/s、0.092°/s；z_min 9.867 mm；粘滞检查通过（无 attachment/latch 复活、OPEN 锁存 10 步、夹爪 0.080 m、布料不跟随 EE）；材料 live 读回 0.3/1.0、binding 正确。

**边界：** recovery 末态相对 RC2 平移 10.27 mm，fold 目标按未改 expert 重算（差 7.7–8.0 mm、yaw −3.28°），是端到端对比；两个 dev seed 各一次 single 通过不等于跨 seed 统计；机制未确认；正式 Stage 4 成功仍为 **0**。判定：固定最终候选，准备七例 RC（本轮未跑七例/未冻结/未跑 held-out）。详见 [4302 对照](day4-actionchunk-test/results/PFS1_V2_EXT_4302_20261104/review.md)。

## 2026-11-04 D2-E 步骤2：支撑面与摩擦配置核查（仅离线）

离线读取 D2-A 场景读回、D2-C 已保存几何/轨迹和源码；**未启动新 episode，未改物理参数**。审查表：[D2-E review](day4-actionchunk-test/results/D2_E_SUPPORT_MATERIAL_AUDIT_20261104/review.md)、[JSON](day4-actionchunk-test/results/D2_E_SUPPORT_MATERIAL_AUDIT_20261104/support_material_audit.json)、[CSV](day4-actionchunk-test/results/D2_E_SUPPORT_MATERIAL_AUDIT_20261104/support_material_table.csv)。

关键事实：

- **唯一与布料存在有效碰撞候选的表面是默认地面** `/World/defaultGroundPlane/GroundPlane/CollisionPlane`：z=0、水平、50 m（代码值）、collision enabled；室内地面 collider **enabled=false**。
- **三个附件块** `/World/Attachment/attach*/block` 碰撞体存在且释放后仍保留，但与 garment/robot/rigid 碰撞组过滤，并有 ground `FilteredPairsAPI`；**不能承托或碰撞布料**。机器人手/指与布料同样被组过滤。布料自碰撞开启，但不是外部支撑。
- 布料 mesh 无直接物理材质；材质链为 `/World/Garment/particleSystem -> /World/Garment/particleMaterial`，读回 `friction=0.3`、**`particleFrictionScale=0.0`**、damping/cohesion/adhesion=0。
- 默认地面 CollisionPlane **没有直接 physics material binding**；`add_default_ground_plane` 代码创建 0.5/0.5/0.8 的 `physics_material`，但 `GroundPlane` 的应用分支被 `physics_material is None` 守卫挡住；0.5/0.5/0.8 **未确认生效**。附件块的 0.2/1.0/0 是刚体默认值，且碰撞被过滤，**不是布料有效摩擦**。
- 几何：布料最低点约 **9.876 mm**（高于地面 9.876 mm），比 `particleContactOffset=10 mm` 低约 **0.123–0.124 mm**；这是几何证据，不是接触力/冲量。
- **当前不选择修正。** 支撑/过滤拓扑已足够明确；有效摩擦不能由读回确定。步骤3的纯读回不是选择修正的前置条件；若需要精确块/地面 transform、祖先材质绑定和完整 filter 列表，可登记一次只读观测（4202 single）。有效摩擦需步骤5的单变量敏感性；步骤4可先离线复用轨迹检查持续滑移特征。

## 2026-11-04 D2-E 步骤4：持续滑移特征（仅离线）+ 步骤5决定

步骤4 复用 D1-120/D2-C 轨迹，未启动仿真。报告：[D2-E 步骤4](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/review.md)；数据：[slip_summary.json](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_summary.json)、[slip_bins.csv](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_bins.csv)；图：[速度/转速/方向](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_speed_rotation.png)、[高度](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/slip_height.png)、[支撑几何](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/support_geometry.png)。

**事实：** 释放冲量约 11.0 mm/s 质心/17.4 mm/s 粒子；前 1 s 快速衰减；**1.5–10 s 近恒定 ~1.0 mm/s、~0.36°/s**（D1 稳态 1.024 mm/s、D2-C 0.993 mm/s），没有继续衰减或增大。持续方向约 **26–27°**，比释放方向（~0.7–1.1°）转约 **25°**，约 1–1.5 s 后稳定。布料 z_min 约 9.871–9.876 mm，无地面穿透，低于 10 mm contact offset 约 0.124–0.129 mm；几何证据，不是接触力。两版稳态差约 3%，持续滑移几乎相同。

**步骤5决定：** 选择 **`particleFrictionScale: 0.0 → 1.0`** 的单变量敏感性对照；不选地面材质绑定作为本轮干预（地面材质未绑定是独立发现，但它是刚体材质，不能直接当作粒子摩擦）。候选拟名 `a5-rc2-pfs1`，从 **RC2 原流程**派生，不保留 120 步等待或 D2-C 释放顺序；`friction=0.3`、地面/碰撞、12 个动作/目标/horizon/退让目标不变。该参数从 episode 开始全局生效，影响 recovery/fold/release，不是“仅释放后接触对照”；4202 初态文件不重生，但新动力学从第一步开始。只跑 4202 single 一次；通过条件为原几何 + 质心 ≤1 mm + P95 ≤3 mm + 证据完整。[步骤5决定/预登记草案](day4-actionchunk-test/results/D2_E_STEP4_SLIP_20261104/step5_decision.md)。**尚未创建候选、manifest/config，未运行。**

## 2026-11-04 D2-D：释放顺序对照完成（单次 4202 single）

D2-C `a5-rc2-d2c-release-order` 已按 D2-D 流程单次运行：`day4-a5-rc2-d2c-release-order-20261104-090032-412133`，tmux 退出码 0，episode `passed=True`、12 个公开动作、`absolute_step=2219`、等待 world 1955–2075、trace 331 步；`DIAG_ASSESS complete=True`、`quality=rejected`。manifest 66 项 `778935ab…`、config `96acc5fa…`；远端预检 66/66、未启动仿真；`completed` 已写入、无重试；下载证据与 ledger SHA256 全部一致。详见 [D2-D 对照报告](day4-actionchunk-test/results/D2_D_COMPARE_20261104/review.md)。

**预运行补查：** preopen 10/10 步每步检查 active/control 的 holding 与 attachment 一致并调用 `control.assert_exclusive()`；`audit_episode_evidence.py`/`episode_evidence.py` 与 D1 字节相同，全程状态检查未关闭；D2-C 边界 `released` sample 与最后 preopen state 同 step/time（delta=0），首个全关 state 为 +1 步，未被当作精确解除瞬间；D1 anchor→首个自由 state 为 1 步（16.7 ms）采样区间。

**对照结果：** 干预前 12 个动作 target 最大差 0.0，anchor 顶点/EE/关节差 0.0；release t=0 布料质心差 0.0113 mm、P95 0.0293 mm、最大 0.0375 mm；释放一步粒子速度 17.4197 vs 17.4223 mm/s、质心 11.0397 vs 11.0113 mm/s；free 0–30 质心 1.9092 vs 1.9119 mm、P95 12.2286 vs 12.2044 mm；free 30–120 质心 −3.02%、P95 −2.65%；退让 −2.83%/−1.27%；正式窗口 2.0409→1.9823 mm（−2.87%）、P95 4.4134→4.3426 mm（−1.60%），仍超 1 mm/3 mm、质量 rejected。

**结论：** 释放顺序改变没有降低释放瞬态或前 0.5 s 速度（第一步仍约 17.42 mm/s），因此**释放顺序不是该例漂移的主要因素**；正式/退让窗口的小幅下降不能归因于释放冲量减少，且为单例。不能声称接触力/冲量；contact_events=0 不是无接触。正式 Stage 4 成功仍为 0。完整交接见 [2026-11-04 日报](2026-11-04-GarmentLab日报%20Stage4%20D2释放顺序对照交接.md)。

## 2026-11-04 D2-C：释放顺序单变量干预已登记（随后单次运行，见 D2-D）

独立目录 [a5-rc2-d2c-release-order](day4-actionchunk-test/a5-rc2-d2c-release-order/README.md)，从 D1-120 复制并重定向身份；父 D1 manifest `cd1d7f83…`、config `a6884eab…`，基础 RC2 `10a6cb45…`/`39dc5055…`（60 项），4202 初态 `day4-square-initial-stripfold-20261103-062710-242560`（`result.json` `4472f4df…`、`initial_geometry.npz` `a6646d66…`）。新 manifest 66 项 `778935ab…`、config `96acc5fa…`；[registration.json](day4-actionchunk-test/a5-rc2-d2c-release-order/registration.json) 与 [static-audit.json](day4-actionchunk-test/a5-rc2-d2c-release-order/static-audit.json) 已登记。

**唯一干预：** 在末次释放时，先在 `holding=true` 且 `attachment_enabled=true` 的状态下完成夹爪张开的 10 个物理步，再让原 `ungrasp` 解除附件；其内部第二次 `open()` 被抑制。120 步等待、12 个公开动作/目标/命令/horizon、退让目标、事件和 1 mm / 3 mm 阈值全部保留。与 D1 相比总物理步数不变（同样的 10 步张开移到解除之前）；不提高摩擦、不清零布料速度。

**预期现象：** 释放步及前 5 步粒子/质心/角速度相对 D1 下降；若释放冲量是主因，等待/退让/正式窗口漂移随之下降；若不变，则释放顺序不是主因。比较按释放后的 elapsed time 对齐，分等待、退让、正式窗口报告。

**离线验证：** manifest 66/66、基础 60 项不变；`test_d2c_release_order.py` 13/13（等待 5 + 释放顺序 8）、`test_release_diag.py` 1/1、`py_compile`、`bash -n` 通过；静态核对 21/21 action/horizon 行、`start_ee`/退让目标/`release(target)` 与 D1 相同；`a5_recovery_diag.py` 仅版本字符串和 `release_order` 元数据行不同（11 行，精确重建验证）。**预运行补查：** 10 个 preopen 步每步检查 active/control 的 holding 与 attachment 一致并调用 `control.assert_exclusive()`；`audit_episode_evidence.py`/`episode_evidence.py` 与 D1 字节相同，全程状态检查未关闭。释放 t=0 用附件解除后立即的 `released` sample，不用首个全关 state；记录最后 preopen state、boundary、released sample 的 step 与 delta，delta 非零时报告采样误差。**该版本随后已按 D2-D 上传、远端预检并单次运行 4202 single（见上）。** 正式 Stage 4 成功仍为 0。

## 2026-11-03 D0 4202/4302 基线复现（两例均逐项审计通过）

远端 `day4-a5-rc2-recovery-20261104-042325-295743`（journal `stage4-rc2-d0-4202-XaDTIjGX`）对照 RC2 4202 single `022718-388270`：审计 **97/97 通过**（[D0_4202_REPRO_AUDIT](day4-actionchunk-test/results/D0_4202_REPRO_AUDIT_20261103/review.md)）。12 个 action target 最大差 **0.0**；`final`/`recovered`/`pre_release_hold`/`cloth_constructed`/`success_trace` 顶点逐位相同；五个 evidence 快照、timeline state/action 行、summary 物理字段与 sources 哈希相同；verdict、geometry、stability、evidence_checks 相同。稳定性拒绝为质心 **2.042884 mm**、P95 **4.414119 mm**；runner_exit=0，entry exit 1 是评价器有效拒绝。只有 `summary.json`/`timeline.jsonl`/`episode.mp4` 哈希不同（UTC/单调时钟/视频编码，非物理）；视频本地未解码。

结论：**D0 4202 确定性复现 RC2 4202 single**。注意这是 RC2 基线，不是 `a5-rc2-drift-diag-v1` 的 release_diag；诊断版 v1.1 4202 已完成，逐物理步数据见第 3 项。

D0 4302 已下载并逐项审计 **97/97 通过**（[D0_4302_REPRO_AUDIT](day4-actionchunk-test/results/D0_4302_REPRO_AUDIT_20261103/review.md)）：`day4-a5-rc2-recovery-20261104-044048-912242`（journal `stage4-rc2-d0-4302-AKnlgSH2`）对照 RC2 4302 single `025702-598075`；12 个 action target 0 差，final/recovered/pre_release_hold/cloth_constructed/success_trace 顶点逐位相同，五个 evidence 快照与 timeline state/action 行相同，verdict/geometry/stability/evidence_checks 相同。稳定性拒绝为质心 **1.910233 mm**、P95 **4.123147 mm**；runner_exit=0，entry exit 1 是评价器拒绝。只有 summary/timeline/video 哈希不同（时间戳/编码，非物理）。

两例 D0 均确定性地复现对应 RC2 baseline。注意两例都是 RC2 基线，不是 `a5-rc2-drift-diag-v1` 的 release_diag；诊断版 4202 v1.1 已完成，D1-120 步骤 6–8 已完成：4202 single 单次运行 `passed=True`、120 步等待/事件完整；标准 assessor 因 3D/4D target 形状崩溃，独立 postfix 评估 `complete=True`、`quality=rejected`（稳定性）。无重试；步骤 7 下载核验 46/46 通过；步骤 8 显示等待 2.0783 mm、退让 2.4590 mm、窗口 2.0409 mm，且 D1/基线布料在相同 elapsed 时间点逐位相同（486 点、0 差）。120 步延迟不改变滑移率；优先检查释放瞬态/回弹/地面接触。正式成功仍为 0。

## 2026-11-03 A5 RC2 漂移诊断：第 1–2 项完成（仅离线）

RC2 基线、七例索引与独立诊断批次 `a5-rc2-drift-diag-v1` 已写入 [诊断报告](day4-actionchunk-test/results/STAGE4_A5_RC2_DRIFT_DIAGNOSIS_20261103/review.md)。原版 verify-dev 为 **exit 1、release_exists=false**，失败点是正样本 4202 arc4 的稳定性拒绝；七例 RGB/视频/持布 evidence_checks 全过。RC2 仍未冻结，正式成功 0。

4202/4302 single 事件分段：保持最后 60 帧稳定（质心 0.074/0.070 mm，P95 0.202/0.255 mm）；释放/开爪瞬态出现非刚体局部变形（P95 **13.83/15.03 mm**、最大 **25.62/27.65 mm**、刚体 RMS 1.89/2.09 mm）；退让阶段质心 **2.48/2.44 mm**、旋转 **−0.91/−0.94°**；正式窗口 210–330 为近刚体滑移/转动（质心 **2.04/1.91 mm**、P95 **4.41/4.12 mm**、刚体 RMS 0.0011/0.0009 mm），超 1 mm/3 mm。原评价器五项逐项零差。第 3 项 v1.1 已补齐释放→退让的逐物理步顶点、夹爪位姿/开合量和几何距离；仍无接触力/冲量，零接触事件不能据此认定无碰撞。

第 3 项已在 4202 single 完成（见下）：逐物理步记录顶点、EE、夹爪开合、attachment、距离，物理步进、控制频率和动作目标不变；D1/D2 仍不启动。4302 single 作为后续复验；公开动作预算 7/12 不变。

**2026-11-03 第 3 项状态**：v1 4202 已完成（`day4-a5-rc2-drift-diag-20261104-050739-915052`）：release_diag 157 行（155 state 步）、开合量/EE 距离有限、contact 0 事件、quality rejected（稳定性，符合 baseline）。`complete=False` 的原因是两个审计/接口问题，不是物理变化：float32/float64 action target 比较过严（float32 相等，float64 差 1.26e-8 m）；锚点被写成额外 state 行（release_diag 自身 state dt/step 连续）。v1.1 已修复：manifest `13c1f20a…`、config `aa5da98b…`、release_diag `dbb7801c…`、assessor `fcdc3383…`；已完成干净重跑 4202，获得 `complete=True`。

v1.1 分段（与 v1 逐位相同）：开爪/释放 1944–1953 是局部非刚体瞬态（质心 0.848 mm、P95 13.831 mm、最大 25.619 mm、RMS 1.894 mm；质心 1948 峰值约 1.236 mm 后回落）；退让 1955–2097 近刚体（质心 2.277 mm、旋转 −0.804°、P95 4.887 mm、RMS 0.094 mm）；正式窗口延续刚体滑移。接触通道 0 事件，EE 距离只是距离证据。详见 [release diag 分析](day4-actionchunk-test/results/STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103/review.md)、[README](day4-actionchunk-test/a5-rc2-drift-diag/README.md) 与 [诊断报告 §8](day4-actionchunk-test/results/STAGE4_A5_RC2_DRIFT_DIAGNOSIS_20261103/review.md)。

**v1.1 4202 已运行并完成比较**：`day4-a5-rc2-drift-diag-20261104-053151-197013`，`DIAG_ASSESS complete=True`、25/25 诊断检查、18/18 evidence 检查、release_rows=157、contact_events=0、quality=rejected（稳定性，符合 baseline）。与 v1 逐位相同：release_diag 全部数组（finger 距离全 NaN、掩码相同）、12 个动作目标、success_trace、final/recovered/pre_release_hold/cloth_constructed、五个证据快照、2427 条 state、1219 条 frame；唯一差异是锚点 kind 和三个诊断文件 hash。与 RC2 4202 single 的目标序列最大差 0、success_trace/快照/success_meta 物理字段/quality 与 criteria 均相同。**无需新物理版本或重建 baseline。** 详见 [v1_1_compare.md](day4-actionchunk-test/results/STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103/v1_1_compare.md)。

**2026-11-04 D1-120 步骤 6–8（运行 + 下载核验 + 分段分析）**：独立目录 [a5-rc2-d1-120](day4-actionchunk-test/a5-rc2-d1-120/README.md)，父 v1.1 `13c1f20a…`/`aa5da98b…`，基础 RC2 `10a6cb45…`/`39dc5055…`（60 项）；4202 初态 `day4-square-initial-stripfold-20261103-062710-242560`，`result.json` `4472f4df…`、`initial_geometry.npz` `a6646d66…`。新 manifest 66 项 `cd1d7f83…`、config `a6884eab…`；[registration.json](day4-actionchunk-test/a5-rc2-d1-120/registration.json) 记录身份哈希。`hold_open_for_steps` 在末次 OPEN 内恰好插入 120 步，无控制调用/目标改变/布料重置；等待位于第 12 个公开动作 `release_retreat` 内，12 个动作/目标/命令/horizon 静态核对未改。五个命名事件 `ungrasp_return`/`delay_begin`/`delay_end`/`retreat_begin`/`retreat_end` 写入 `release_diag.json:events` 和 `release_diag_events.csv`；phase 区分 `delay`（120 行）与 `retreat`。仅 4202 single；delay fixture 5/5、release fixture 1/1（含事件/CSV）、manifest/`py_compile`/`bash -n` 通过。**步骤 5 离线预检 65/65 通过**（[D1_120_PREFLIGHT](day4-actionchunk-test/results/D1_120_PREFLIGHT_20261103/review.md)）：身份/manifest/插入位置/动作计数/采集逻辑/recovery 隔离/4202 single 范围均通过。RC2 与 v1.1 未修改；正式成功 0。步骤 6 运行见下；步骤 8 分析见 [D1_120_STEP8_ANALYSIS](day4-actionchunk-test/results/D1_120_STEP8_ANALYSIS_20261104/review.md)。

**步骤 6 运行结果（2026-11-04）**：`day4-a5-rc2-d1-120-20261104-071602-499516`，episode `passed=True`、12 个公开动作、120 步等待（`start_step=1955/end_step=2075`）、五个事件完整、`release_diag` 277 行（delay 120/retreat 144）；视频/证据/ledger 全部保存。标准 `a5_diag_assess.py` 在收尾时因 3D/4D target 形状 bug 崩溃（`ValueError: shapes (3,) (4,)`），不是 episode 失败；执行后 app/manifest 未改，独立 [postfix 评估](day4-actionchunk-test/results/D1_120_RUN_4202_20261104/review.md) `complete=True`、`quality=rejected`（质心 2.040882 mm、P95 4.413414 mm）。无重试；正式成功 0。

## 2026-11-04 D2-A/B：场景、释放速度与接触通道

[D2-A/B 报告](day4-actionchunk-test/results/D2_A_B_SCENE_CONTACT_20261104/review.md)：实际支撑为 `/World/defaultGroundPlane/GroundPlane/CollisionPlane`（启用），室内地面 collider 已禁用；支撑面**没有显式 physics material binding**，只有 PhysX 默认材质；地面/布料无可读 filter group；particle material 已正确绑定，`friction=0.3`、**`particleFrictionScale=0.0`**（initial protocol 明确断言该 profile）；particleContactOffset=0.01、nonParticleCollisionEnabled=true、self-collision/CCD=true。释放前持布最后 5 步粒子平均 0.262 mm/s、质心 0.055 mm/s；附着在 **1944** 断开，1944 一步速度跳至 17.42/11.04 mm/s，前 5 步 35.95/19.42 mm/s；但 `gripper_state=2`/`command_holding=true` 持续到 1953，1954 才报告 open。D2-B：rigid 已知接触在原 `ContactRecorder` 配置下 0 事件，API 同时加到 cube+ground 且在 reset 前应用时捕获 166 事件；粒子布料从 z .184 落到 .0099（contact offset 0.01），即使 API 加到 ground/particle system/cloth 仍 **0 事件**，故当前 contact-report 通道不支持 cloth-ground；需改用高度/穿透/粒子速度观测。D2-C 已选择“附着保持期间完成夹爪张开、随后解除附件”的单变量干预并登记，随后已单次运行（见下 D2-C/D2-D）；不直接提高摩擦，原阈值与暂停状态不变。

## 2026-11-02 A1：b-right-dev-v2 预检完成（仅离线）

`stage4_a1_right_v2_preflight.py` 48/48 检查通过；未启动仿真、未生成 held-out、正式成功仍为 0。预检发现并修正一处登记描述与实际采样不一致：配置原写 `settle(180 for perturbed, 240 for crumpled)`，实际 runner 对两档都在 fold OPEN 后执行 30 release ticks + `settle(180)`；`settle(240)` 只在 recovery 展开后，180/240 是初态生成 settle。配置已修正为 v2.1（仅描述字段，无行为改动），新哈希：config `91c0fe7f…`、variant manifest `c3e34c91…`（旧 `adf4c9a8…` / `2fff0bf9…` 记录在 A1 报告）。入口 `3822bd98…`、批次驱动 `d4c00162…`、21 项底层 `cb947b85…`、初态 manifest `70b1793b…` 均未变；B/C 新增文件不在 21/23 项身份中，登记 runner 未导入它们。初态 registry 本地不存在，A2 首次生成时在远端创建。

下一步 A2：上传修正后的 4 个 v2 文件（按原字节，不转换行尾），远端复核 `V2_MANIFEST_BAD [] 23` 与四个新哈希后，按 4201→4209、4301→4309 运行 right single。证据：[A1 预检报告](day4-actionchunk-test/results/STAGE4_A1_PREFLIGHT_20261102/review.md)。

## 2026-11-02 B项：正式成功判据 v1.0.0 已交付（仅离线）

以 [STAGE4_SUCCESS_CRITERIA_V1.md](STAGE4_SUCCESS_CRITERIA_V1.md) 与 `day4-actionchunk-test/stage4-success-v1.json` 为当前成功判据。A/L1过折和B/nominal分任务评价；新增OPEN完成后逐物理步0..330采集、3.5–5.5秒连续几何及稳定窗口。原目标、held门槛和7/12动作预算不变。独立评价manifest登记新成功层，旧折叠manifest/runner未修改。

13项离线测试通过；31个历史目录复算20个满足对应终态几何、11个不满足，但全部缺新协议完整时序证据，不能追认正式成功。稳定阈值为预登记工程容差，尚待开发复验。评价配置与分类器已完成，不等于runner采样接入或正式批次已解锁。下一步需单独接入记录并用开发seed复验；held-out保持暂停，正式成功0。right是否正式采用仍需独立登记。下方“数值阈值未冻结”等段落保留为本次之前的历史状态。

> 命名约定：Stage 表示按验收推进的工作阶段，每个阶段可跨多天；原 Day N 对应 Stage N。为兼容既有入口，`DAY4_*.md`、脚本名和结果目录名保留；日报文件名已统一改为 Stage。

## 三档折形与难度归因口径（2026-11-02 定稿；第二步已冻结定义）

**L1 保留独立的“过折”折形定义，L2/L3 脚本本轮不改。** 目标、held gate、评价器与 seed 规则的完整冻结见 [STAGE4_TASK_DEFINITION_FREEZE.md](STAGE4_TASK_DEFINITION_FREEZE.md)。

| 档 | 初态（固定） | 折形目标（冻结） |
|---|---|---|
| L1 | flat，seeds 4100–4109 | 过折：只把 place 末目标沿折向多伸 2 cm（`L1_XFOLD_OVERHANG=0.02`），45/90/135 三弧目标不变；拱形：释放后 flap 自由边落到边缘外桌面并再外滑 1.5–1.8 cm，最终行均值越边 39–40 mm、拱高 62–63 mm、最终 IoU 0.37–0.42 |
| L2 | perturbed：bottom 折条 0.1615–0.1793 m，seeds 4200–4209 | nominal 20/20 左半折：width 0.20、无 overhang、place 横向 0.40 |
| L3 | crumpled：left 折条 0.20 m，seeds 4300–4309 | nominal 20/20 左半折：width 0.20、无 overhang、place 横向 0.40 |

**口径修正（2026-11-02 第二步，核对脚本后）**：此前把 L2 的 “width 0.16–0.18” 写成折形目标，实际那是**初态 bottom 折条宽度**；L2/L3 的 commanded 折形目标是同一个 nominal 20/20。因此不是“三个不同折形任务”，而是 **L1 与 L2/L3 两个折形任务**，L2/L3 是同一任务下的两种初态族。

由此得出的验收约束：

- **机制已核实（2026-11-02，离线）**：overhang 属最终目标偏移，不是轨迹补偿。place 到位误差 ≤2.3 mm；折形拟合残差与基础例相同（仅平移从 +4 mm 变 +21…+25 mm）；差别来自释放后 flap 自由边落到边缘外桌面（基础例悬空 16–20 mm 后摊平）。限制：零扰动控制例用名义目标也能保持，因此不得写成“修复了机器人能力缺陷”。详见 `day4-actionchunk-test/results/L1_OVERHANG_MECHANISM_20261102/review.md`。
- **L1 与 L2/L3 是不同折形任务**：L1 vs L2/L3 的成功率差异不得归因于“初态难度”。
- **L2 与 L3 是同一折形目标下的两种初态族**（扰动方式与条宽不同），可以对比，但两族不是受控难度梯度。
- 每档必须按自己冻结的折形定义单独判定成功率、单独报告；三档汇总只能称为**多任务平均**，不能称为难度曲线，也不产出难度梯度类结论。
- 本轮不把 overhang 移植到组合脚本重验。
- **表示层（2026-11-02 第三步，已实现并完成两任务各一对开发配对）**：single-step 与 H=4 共用同一目标规则（四个 arc 目标 `local_arc` 在同一位置各算一次）、同一评价器（`stage4_fold_metrics.py` 复算 `fold_metrics_yaw`，自校验哈希）与同一 seed 列表；H=4 只把四个 arc 目标合成一个 chunk，抓取/释放仍 H=1。配对结果：L1/4100 两侧均 `passed=true`、L2/4200 两侧均 `passed=false`，两组审计均 `PAIRS_COMPARABLE`，`code_files` 与本地 manifest 零差异，同一对内所有可比快照**逐字节相同**、指标差全为 0。因此本步只证明**专家轨迹在两种表示下等价**（后端逐行发出同一串 `control.move`），**不构成 H=4 收益的证据**，也不得写成“H=4 已验证”；策略层的 chunk 效应属后续 BC 阶段，结果不并入单步成功率。见 [冻结文档 §7.1](STAGE4_TASK_DEFINITION_FREEZE.md)。
- **分任务报告（2026-11-02 第四步，已完成；任务 B 冻结版证据已补齐）**：按 L1（过折）与 L2/L3（nominal 20/20）两个折形任务分别汇总，single 与 arc4 并排。冻结版 seed 级：L1 1/1、L2/L3 **0/2**（L2/4200 left、L3/4300 left，共 4 次尝试全失败），多任务平均 0.50（A n=1、B n=2 个 seed），**不是难度曲线，也不能用 L1 vs L2/L3 的成功率差解释初态难度**。开发历史：L1 过折 10/10、基线 0/3；L2 left 含冻结版共 5 次尝试、1 次通过（通过例在 recovered-yaw 之前）、L3 left 共 3 次尝试 0 次通过。失败形态均为释放后回弹摊平，held gate 通过。补充的两例与既有同条件运行逐字节相同，属确定性可复现失败。见 [分任务报告](day4-actionchunk-test/results/STAGE4_PER_TASK_20261102/review.md) 与 [任务 B single 证据](../thesis/day4-actionchunk-test/results/TASK_B_SINGLE_EVIDENCE_20261102-173708/review.md)。
- **正式批次准备（2026-11-02 第 7 步，已登记，未运行）**：held-out seeds 每档 20 个（L1 4110–4129、L2 4210–4229、L3 4310–4329），与开发集不重叠、批次前固定、single/arc4 共用；已写入 `square-initial-plan.json`（30→90 条）与 `stage4-heldout-seeds.json`，并放宽两个初态 runner 的 seed 断言（折叠 manifest 与折叠脚本未改）。同批提供 `run-stage4-formal-batch.sh`（60 初态 + 120 次尝试）与 `stage4_formal_report.py`（拒绝率 `(rejected+error)/总尝试`，空批次报空）。**远端状态**：4 个新文件与两份刷新后的初态 manifest 均已上传并核对通过（两份 manifest 无排除项 `bad` 为空，哈希 `bccf3e15…` / `70b1793b…`；`square-initial-files.json` 共修正 5 项落后条目，其中三项依赖取自折叠/条带 manifest 已在远端验证的值）。批次**暂停**，按 `b-right-dev-v1` 先用开发 seeds 4200/4300 验证 right 的释放后保持；未生成任何 held-out 初态。**硬前置**：正式成功判据阈值仍未冻结，因此批次数据只能给开发门槛 `passed` 与拒绝率；另需先决定“先跑基线”还是“先解决 B 的 left 释放后回弹”。见 [批次准备](STAGE4_FORMAL_BATCH_PLAN.md)。
- 正式 Stage 4 成功仍为 0；L1 过折 10/10（4100–4109）只算开发复验，不构成任何一档的正式成功。

## 最新交接：2026-10-31 v5 已审查，今日暂停

以 [2026-10-31 交接日报](2026-10-31-GarmentLab日报%20Stage4%20v5保持与接触审查交接.md) 为最新状态，下方冲突段落仅作历史记录。

v5 两次结果已下载读取：112822-203913 因 KeyError('attachment_bodies') 失败；113930-047613 短程保持/释放和接触正控通过。位置误差 0.4733 mm、末臂速 0.00860 rad/s、锚点间隙 1.361 mm。发现双指持续触地共 356 条事件；接触明细位置、法向、冲量全零，不能据此认定接触力为零。robot_block=0 受已有碰撞过滤限制。正式折叠成功仍为 0。

下次先核对夹爪坐标偏移、手指碰撞几何、地面间隙及辅助块实际/目标高度，判定触地是否符合设计，再决定最小修正与短程复验；尚不直接解锁完整 L1 或正式批次。今天不启动实验。后续下载只给命令，由用户手动执行。

## 最新准备：v5 接触正控修复已上传，待运行

v4 正控为 0 的根因按代码时序定位为：`PhysxContactReportAPI` 在 `env.reset()` 之后才应用，PhysX 已创建刚体；辅助块还可能进入 sleeping，而 sleeping body 不产生接触报告。v5 只改接触诊断：reset 前对 3 个辅助块和 12 个机器人刚体写入 API；reset 后校验；新增 3 块 `RigidPrimView` 净接触力采样作为独立正控（块 sleep threshold 设为 0，`disable_stablization=False`）。公共四动作、路径、物理、保持/释放时长和 held gate 阈值不变。

远端 21 文件 SHA256 全部一致，Python/Bash 语法通过；尚未运行，正式成功 0。预登记判读见 [SQUARE_GRASP_HOLD_V5.md](day4-actionchunk-test/SQUARE_GRASP_HOLD_V5.md)。运行入口：`bash /root/autodl-tmp/run-square-grasp-hold-v5.sh`。

## v4 结果：关节锁定保持通过 held gate，接触正控失败，第 1 步未解锁

用户已运行 v4（`day4-square-grasp-hold-20261031-104528-426384`），已下载并审查。held gate 通过：末端位置误差 0.474 mm、保持末臂速 0.0086 rad/s、姿态到达、锚点间隙 1.36 mm；60 步内末端漂移 0.003 mm、姿态漂移 0.0005°。保持阶段仅 60 次 joint_indices 0–6 的 apply_action（位置+零速度），controller.forward 为 0；全轨迹无 Python 层位姿/关节设置调用。00_initial、01_before_close、02_grasp 与 v3 逐顶点/逐位姿相同；v3 保持末端漂移 19.12 mm，v4 为 0.003 mm。release 步数 731（v3 753），公共动作仍为 4。

接触通道无效：callback_count、event_count、块-地正控均为 0。保持时块中心 z 恒为 15.000 mm、目标 10.207 mm，块持续被地面挡住；robot_group 与 attach_group 本就互相过滤，robot_block 记录不能独立证明机械隔离。按预登记规则第 1 步不解锁，不进入 L1，正式成功 0。下一步先修复并验证接触正控，不延长保持、不改阈值、不调 RMP 增益。详见 [review.md](day4-actionchunk-test/results/day4-square-grasp-hold-20261031-104528-426384/review.md) 与 `day4-actionchunk-test/SQUARE_GRASP_HOLD_V4.md`。

## 最新离线审查：12个真实负例快照

已运行review_real_negative_examples.py，报告位于 [真实负例指标](day4-actionchunk-test/results/REAL_NEGATIVE_EVALUATION/review.md)，逐项数据和源文件/评价器哈希见同目录metrics.json。

10个L1平整初态IoU均为0、材料反射误差约220mm；同一次失败抓取的保持/释放后两个快照IoU为0、误差约217mm。所有success字段仍为空，未追加正式尝试。10个初态以自身为基线，仅刻画未折叠状态；两个抓取快照非独立episode，不能宣称12次独立验证。

折线数值容差统一为1微米，用于吸收float32中心线误差，不是成功阈值。物料分半来自初始资产索引，不能按最终位置重分。尚无真实正例，分类准确率和最终阈值未验证。

不依赖抓取的接口/预算/记录工具及负例审查已具备。下一项能推动物理验收的工作仍是恢复有效L1候选；用户暂停抓取调试的决定继续有效。本轮未启动仿真，未上传新实验脚本。L1初态10/10，L2/L3各0/10，正式成功0。


## 最新离线交付：评价与批次记录工具

开发版day4_evaluation.py与day4_attempt_log.py已完成，详见 [评价与记录说明](day4-actionchunk-test/DAY4_EVALUATION_RECORDING.md)。合成理想对折/未折叠/整件搬移/整体平移对折/释放后回弹检查通过；追加日志的失败分母、终态不可覆盖、重试独立、未完成批次拒绝率为空、未冻结成功拒绝检查通过。

评价success仍为null，无最终阈值，粒子IoU仅代理，不是正式重叠验收。工具未接入Backend，未新增正式episode。L1初态10/10，L2/L3各0/10，正式折叠成功0；抓取调试保持暂停。本次无上传、无仿真。后续物理验收仍需先恢复有效L1候选，不能靠离线工具替代。


## 最新离线交付：接口、动作预算与 recovery 规范

已完成 [公共接口与 recovery 开发规范](day4-actionchunk-test/DAY4_INTERFACE_RECOVERY_CONTRACT.md) 和纯离线 day4_action_budget.py。保留5维XYZ+yaw+gripper schema；每个waypoint计一次动作，chunk内H行计H次。对折7步、一次recovery5步，总计12；两次需17步，因此本模板实际最多一次，第二次预算不足则记失败，不能隐藏路点或截断。

同一参数化recovery模板的触发、选点、停止及版本/失败统计规范已明确。7/12准入、17拒绝、失败重试预算、非有限坐标拒绝及既有ActionChunk兼容检查通过。尚无冻结阈值或经物理验证的路径，未接入正式Backend，不计recovery执行完成。

当前：L1初态10/10，L2/L3各0/10，正式折叠成功0。抓取调试继续暂停。本轮无上传、无仿真、无新运行命令。下一项独立工作是评价和批次记录工具；实际L1、重抓取/reset和L2/L3生成仍是未完成项。


## 最新进度：L1 初态图 10/10 已下载审查

seeds4100–4109全部生成通过；新增306份文件哈希一致，10张640×480截图、固定参数、441点变换及静置几何逐例核验通过。汇总：[L1十例审查](day4-actionchunk-test/results/L1_INITIAL_BATCH_REVIEW/review.md)。

图像存在机器人中央遮挡及部分回合背景材质不一致，正式视觉数据前需处理；当前计为L1开发初态生成完成，不计折叠或连续reset验收。L2/L3各0/10、正式成功0。三档视觉区分及重复生成一致性仍待验收。

抓取调试继续暂停，不运行旧L2/L3抓起放落代码。下一独立工作为公共接口、≤12高层动作预算、最多两次参数化recovery模板及结果记录规范。本轮只下载审查，未启动新实验。下方“运行剩余9例”为已完成历史步骤。


## 最新状态：L1 首例初态已审查，推进其余9例

seed4100（day4-square-initial-20261031-094446-203825）生成及保存通过：34文件哈希一致，PNG已查看，441点几何与预登记变换一致。机器人遮挡图像中央，局部形状判断需结合几何；尚未验收三档视觉区分。当前已有1/10张L1截图，L2/L3为0/10，正式折叠成功0。

下一步只运行L1 seeds4101–4109，失败即停，完成后逐例下载核验。L2/L3角点lift/drop仍未验证，抓取失稳分支继续暂停。本轮未启动实验。审查见 day4-actionchunk-test/results/day4-square-initial-20261031-094446-203825/review.md。


## 当前主线调整：暂停抓取调试，先做难度初态

用户要求暂缓保持失稳问题，推进独立工作。v3 已反馈失败，本轮没有复跑或宣称通过；其完整结果仍待下载审查。正式成功0，L1折叠尚未解锁。

三档候选参数沿用原 difficulty.yaml 数值，精确采样已存入 day4-actionchunk-test/square-initial-plan.json：L1 seeds 4100–4109、L2 4200–4209、L3 4300–4309，每档10例。平移dx/dy独立从原正区间采样，yaw绕布料质心。此版本只为开发初态批次固定，尚非正式评价冻结。

已有 _lift_drop_once 实现选中心而非角点，且依赖未验证的抓取；L2/L3生成因此阻塞。计划中的corner/lift/drop参数已登记，未用人工变形替代物理生成，也未宣称30张截图完成。

当前唯一运行入口：bash /root/autodl-tmp/run-square-initial.sh 4100。仅L1平移、yaw、清零初态速度、静置120步和截图；无抓取动作。新进程隔离不是重复reset可靠性验收。先审查首例后再生成剩余9例；L2/L3显式拒绝运行。运行后保存参数、变换前/读回/静置后几何、初态PNG、源码、质量及日志。渲染不额外推进物理步。

本地30例唯一性、刚性变换距离保持、无执行抓取动作及AST检查通过；21份远端哈希和Python/Bash语法通过。本次未启动实验。下方抓取诊断“待运行”均为历史入口，暂不执行。


## 最新准备：v3 控制时序诊断已上传，待运行

保留 v2 路径、四个公共动作、物理配置、60步保持/30步释放及原门槛，仅增加 control_trace.jsonl。记录 controller.forward 输出、apply_action 输入、get_applied_action 读回，以及每步前后的关节位置/速度和末端位姿，均带物理步、逻辑步、阶段和序号。Python 位姿/关节设置入口记录调用栈；不声称覆盖原生 PhysX 调用。

本地桩验证原样转发参数/返回值、无额外控制调用和恢复钩子；19份远端依赖哈希及Python/Bash语法通过。当前可执行 bash /root/autodl-tmp/run-square-grasp-pose.sh，一次诊断后审查目标突变与实际响应的先后；不凭零接触事件判定无碰撞，不调整阈值或路径。未启动实验，仍为第1步，正式成功0。此节覆盖下方“尚无新入口/暂停复跑”的历史状态。


## 最新状态：v2 四动作完成，保持失稳，暂停复跑

短程 v2 结果 20261031-091703-655195 已下载：54 文件哈希一致、视频264帧。保持结束位置误差19.188mm、最大臂关节速度0.518rad/s，未过10mm/0.1rad/s门槛；姿态检查和附件误差通过，释放后所有附件disabled。第685–690步间出现速度突增，不能按等待不足处理。正式成功0，第1步仍未通过。

唯一下一步：针对保持失稳区间核对每步控制目标与实际关节响应，追查日志非法setGlobalPose调用来源；尚无因果结论。当前不原样运行旧命令，不增加保持时间、不改阈值、不接回L1。下方运行命令及“待复测”描述仅保留为历史入口。本次未启动实验。

详见 [v2 审查](day4-actionchunk-test/results/day4-square-grasp-pose-20261031-091703-655195/review.md)。


## 最新结果：短程抓取脚本错误已修正，待复测

v1 已执行接近、下降和 CLOSE，但保持阶段姿态 list 类型错误，异常保存又遇到 NumPy JSON 序列化错误，之后出现退出 139。保持及释放未完成，不能计通过。完整结果已下载：45 文件哈希一致、视频 217 帧。修正版 v2-serialization-fix 已上传并通过 18 文件远端静态核验，路径、物理和阈值不变。本次未启动复测。下一步仍运行 run-square-grasp-pose.sh，其他步骤未解锁。

审查：[短程抓取 v1](day4-actionchunk-test/results/day4-square-grasp-pose-20261031-090844-326265/review.md)。


正式成功 0，Stage 4 尚未完成。本次只更新计划，没有启动实验。当前唯一推进项为已上传的 run-square-grasp-pose.sh：接近、下降、抓住、释放，审查位置、姿态、速度和附件状态。通过后依次完成 L1 保持及独立重复、Backend/≤12 动作/重抓取/reset、三档 30 张初态图与最多两次 recovery、冻结指标后的每档至少 5 条正式成功。连续 10 次 reset/rollout 检查并入正式批次，保留全部失败分母。

完整当前计划见 [Stage 4 收尾计划](DAY4_NEXT_STEPS.md)。旧服装、翻腕和参数扫描分支冻结。GitHub README 已更新至 Stage 4；下方历次“待运行”“下一步”均为历史记录，不构成当前执行指令。

---

## 2026-10-31：统一姿态抓取候选已上传，待运行

URDF指尖中点局部+3.4mm；SquarePoseBackend统一实现XYZ+yaw+gripper，固定向下姿态。抓取段离线IK/FK与网格对地检查完成，实际动态和接触未验证；完整折叠末段IK解跳变尚未解决。run-square-grasp-pose.sh仅四动作抓取/释放诊断。18文件远端静态核验通过，正式成功0。

## 2026-10-31：短程下降仍失败，接触负记录未验证

结果day4-square-descent-20261031-081630-012836已完整下载校验；263帧解码通过。最后下降段失稳，最终位置误差131.699mm、姿态变化124.563度。接触回调0次，不能排除碰撞。未抓取，正式成功0。下一步统一Backend姿态与抓取参考点，先离线审查，不重复旧路径。

## 2026-10-31：末端接口审查与短程诊断已准备

确认Backend忽略yaw且位置控制不固定姿态。新增run-square-descent.sh：两次OPEN、无抓取，沿用v2目标，补充接触与同步状态记录。16文件上传及静态核验完成，待用户运行。正式成功0。详见DAY4_SQUARE_FRAME_AUDIT.md。

## 2026-10-31：square-L1-v2下降失败，先统一抓取参考点

结果完整下载，517帧视频解码通过。位置误差15.73mm，速度未收敛，姿态变化50.92度；未CLOSE，正式成功0。v2单次姿态换算不完整；现有日志不能确定地面碰撞。下一步先做Backend frame/姿态语义审查，再准备定向抓取验证，不重复v2。详见本次结果目录review.md。

## 2026-10-31：square-L1-v1 失败，v2坐标修正待运行

完整结果已下载并校验，视频196帧解码通过。approach/descend完成，CLOSE因21.1mm距离超过20mm门限失败，未开始折叠。v2仅修正抓点到EE坐标换算，静态测试及远端哈希通过；尚未GPU验证。正式成功0。详细审查见 `day4-actionchunk-test/results/day4-square-l1-20261031-075156-218313/review.md`。

## 2026-10-31：方巾 L1 v1 已就绪，待用户运行

- 入口：`day4-actionchunk-test/run-square-l1.sh`；服务器同名文件位于 `/root/autodl-tmp/`。
- 15个上传文件哈希一致，远端Python AST及Bash语法通过；离线几何检查通过。
- 单层40cm方巾，441顶点，9个公开动作。没有启动GPU；未证明保持折叠，正式成功0。
- 下一步：单次开发试跑，自动下载结果并核验完整释放、退让及3秒/4秒保持；不可凭pipeline标志进入正式验收。

# L1路线收敛至原计划优先的单层方巾

已确定下一候选：原计划第5.1节优先范围内的40cm单层方巾+现有单Franka，保留XYZ+yaw+gripper接口与Isaac/GarmentLab。旧双层上衣及被动载体分支冻结，旧结果保留。决策见DAY4_L1_ROUTE_DECISION.md；资产与离线几何审查已生成，尚未加载仿真。

唯一下一步：准备独立square-L1入口、替换资产专用配置/索引并验证9公开动作计划，完成静态检查和上传后给单次运行命令。不能运行旧服装脚本。新方巾结果须单独标记，不冒充原服装成功。L2/L3 recovery预算仍待解决。当前没有新GPU实验，正式成功0。

# v2审查完成：停止被动载体分支

v2结果已下载审查：21个粒子各约1g，总21g，起止一致；三组已有轨迹字段与v1逐步完全相同。质量配置不符已排除，持有期0.02396rad仍低于0.05rad门槛。停止当前被动转动载体接入L1，不追加参数扫描。报告day4-actionchunk-test/results/day4-attachment-canary-v2-e5aV7xe4/review.md。正式成功0。

下一步回到L1方案决策：基于现有失败证据明确抓取模型、公共接口及≤12动作预算，形成有依据的可执行候选；若需要改变任务/执行器能力，明确列出修订选项，不能隐含修改。当前没有待执行实验命令，不重跑短测试、不降阈值、不增加v3扫描。本轮未启动GPU。

# v2质量测量已就绪

v2质量测量修订已准备上传，远端Python/Shell语法及3文件哈希核验通过。cloth_prim_view.py:408–424确认get_particle_masses底层为cloth tensor view.get_masses()。本地确认场景构造和仿真循环与v1完全一致；阳性、响应未达阈值和质量不匹配判读用例通过。

唯一下一步由用户执行 `bash /root/autodl-tmp/run-attachment-canary-v2.sh`。只补充逐粒子质量（0/120/180步）、质量加权质心和绕枢轴重力矩，不修改物理配置、模拟时长或0.05rad能力门槛。质量总和对USD0.021kg容差0.2%，起止数组须一致。重力矩不是附件实际传递力矩。旧版数据/脚本保留；本轮未启动GPU，正式成功0。

# 短场景审查：小幅响应未达门槛

短场景已完成并自动下载：day4-actionchunk-test/results/day4-attachment-canary-YqYxWGf9/review.md。球关节、关闭对照、附件保持及OPEN通过；持有阶段转动0.02396rad未达0.05rad门槛。存在小幅响应，不能称完全无反作用。原passed=false保留，正式成功0。

下一步先核对cloth运行时逐粒子质量读回，补齐定量解释缺口；当前仅载体质量/惯量有运行时证据，cloth总质量仅USD写入。只准备同配置测量修订，不改惯量/质量/时长/门槛凑通过，不启动完整fold。此轮未启动新实验。

# 2026-10-31 短测试已就绪

短场景约束能力测试已准备、上传并完成远端Python/Shell语法及3文件SHA256核验。判读程序的合成阳性、有效阴性、无效附件记录测试通过；不能将这些静态检查称为物理验证。

下一步由用户执行 `bash /root/autodl-tmp/run-attachment-canary.sh`。依次独立进程运行rigid、disabled、enabled；每组180个1/120秒物理步，应用启动耗时另计。任一失败立即停止，保留完整日志/场景/轨迹/读回。助手收到完成后自动下载审查。当前未启动GPU，正式成功0。

# 2026-10-31 约束API审查

Isaac4.0安装API审查已完成，见day4-actionchunk-test/constraint_api_review/API_REVIEW.md。布料附件+动态载体+球关节可表达候选结构，但cloth附件反作用力矩尚无证据；不能声称已实现自由转动夹持。

唯一下一步：准备独立短场景能力验证脚本，先验证刚体球关节，再比较cloth附件enabled/disabled对动态载体转动的影响，最后验证OPEN。全部通过才接入衣摆短程抓取；当前未编写/运行该测试，无新GPU实验，正式成功0。停止材料/路径参数扫描。

# 2026-10-31 抓取结构审查

已完成离线抓取结构审查：当前中央单点不在网格边界，初始邻近上下材料点在过线/放置时分离244/148mm。不能把此代理称为双层衣摆夹持，也不能将该现象认定为唯一根因。报告day4-actionchunk-test/structural_review/review.md。

唯一下一步：核对已安装Isaac4.0约束API能否实现平移跟随且允许局部自由转动、可完整OPEN解除的夹持代理。可行才准备短抓取能力测试，通过后才接回L1；不直接将两层刚性锁到恒定姿态块，不隐藏俯仰，不重启参数扫描。本轮无新GPU实验，正式成功0。

# 2026-10-31 bend对照结束

bend100/10已完成审查：构造/USD及运行时数组证实B生效（22726项100→10），但两组均释放回弹约0.5m，保持时越线比例0。B视频643帧、几何340帧完整，仍无L1候选，正式成功0。报告：day4-actionchunk-test/results/day4-minimum-half-fold-20261031-070836-491946/pilot_review.md。

下一步仅进行离线抓取/材料拓扑与路径结构审查：检查上下材料层和当前附件的作用，核对原抓取语义，形成符合XYZ+yaw+gripper的一个可检验L1方案，再决定是否准备实验。停止bend及质量/迭代数、高度、锚点数量和速度扫描；不重复失败组。本轮未启动新实验。

# Stage 4 验收主线（2026-10-25 起）

最新：bend100基准20261031-065311-595489已自动下载审查，完整复现v5动作/阶段顶点，参数和运行时数组读回有效。基准折叠失败，正式成功0；允许进入预注册bend10一次对照，尚未运行。

当前决定：停止v1–v7微调分支，进行文档预注册的bend100/10单次对照，先100基准组。顺序修订及停止规则见day4-actionchunk-test/BEND_PAIR_DECISION.md；当前计划已整理为DAY4_NEXT_STEPS.md，历史另行归档。已上传核验，尚未运行，正式成功0。

最新审查：v7（20261031-063759-844425）已自动下载并核验12份源码、133步网格、314帧视频和457条持布tick日志；arc25材料附件误差10.451mm超界停止，未OPEN。降低块线速度到1/3未解决超界，停止速度系数扫描，不提高界限、不原样重跑。侧边单点分支未取得可执行完整候选，正式成功0；回到最小L1要求重新评估抓取模型与expert可行性，暂无新实验。详见day4-actionchunk-test/results/day4-minimum-half-fold-20261031-063759-844425/pilot_review.md。

最新待运行：v6误差拆分为末端6.792mm、块0.570mm、材料附件10.119mm。已准备v7：仅将持布辅助块线速度指令乘1/3（含有效cap降至0.1m/s），路径、抓点、物理和10mm界限不变；新增逐tick误差时序。本地验证及远端12份哈希通过，未启动实验。运行bash /root/autodl-tmp/run-minimum-half-fold-v7.sh。见day4-actionchunk-test/SLOW_BLOCK_V7.md。

最新审查：v6（20261031-062447-146263）已自动下载，12份源码哈希、130步连续记录、313帧视频通过。侧边单点1547生效，但hem_low_arc_24时锚点残差10.119mm超过10mm诊断界限；未OPEN，不能评价折叠保持，也不能仅凭略超界认定数值发散。完成30动作，正式成功0。先离线区分目标/末端/块/材料误差，不放宽界限或原样重跑。详见day4-actionchunk-test/results/day4-minimum-half-fold-20261031-062447-146263/pilot_review.md。

最新待运行：依据实际网格上下高度区域连接，已准备v6侧边下摆单点抓取（1547，仿真适配层内部固定资产oracle）；仅改抓取位置，保留v5路径公式/物理/释放。12份源码哈希已远端核验，未启动实验。运行bash /root/autodl-tmp/run-minimum-half-fold-v6.sh，结束后自动下载。详见day4-actionchunk-test/SIDE_HEM_V6.md。

最新材料审查：v5释放前左/中/右越线约80.1%/71.1%/80.0%，并非仅中心移动；初始上/下层越线88.8%/61.7%，下层高度中位数83.6mm。抓点仅锚定上层；空间相邻下层点相距19.7mm且网格路径34条边。下一步离线定位实际下摆/侧缝连通边，评估能带动两层的抓取语义；不直接刚性绑两点，不扫描锚点数量或高度，不启动新实验。报告：day4-actionchunk-test/results/day4-minimum-half-fold-20261031-060323-618705/material_coverage_review.md。

最新审查：v5结果20261031-060323-618705已自动下载。11份源码哈希、340步记录和642帧视频通过，实际单锚点6174，最大跟随误差9.196mm。折线带抬升减小，但释放前源材料z中位数68.67mm、近层比例18.28%、速度P95 0.375m/s；原地释放回移501.76mm，越线比例0。单点抓取未解决折叠，停止锚点数量对照分支，正式成功0；下一步先离线核对材料任务几何和单点搬运覆盖，暂无新实验。详见day4-actionchunk-test/results/day4-minimum-half-fold-20261031-060323-618705/pilot_review.md。

最新状态：用户已明确授权后续自动上传本任务所需实验文件；此前自动下载授权继续有效。v5四份新文件已上传至nmb2:23636的/root/autodl-tmp，服务器11份依赖哈希全部通过（V5_REMOTE_MANIFEST_OK 11）。尚未启动实验。下一步运行bash /root/autodl-tmp/run-minimum-half-fold-v5.sh；结束后由助手下载结果。

最新准备：v5仅将下摆42点片区改为一个附件点，沿用v4路径和物理。依据为片区铺下仍保持原纵向朝向（斜率+0.984），不是根因定论。一次对照，不扫描锚点数量；本地检查通过，上传被自动审批拒绝，未运行。见day4-actionchunk-test/SINGLE_HEM_ANCHOR_V5.md。

最新审查：v4（20261031-053919-868025）完整审查通过，但折叠失败；前缀与v3一致。提前下降后到达时折线带仍49.15mm；释放前近层比例14.49%、材料速度P95约0.494m/s，原地释放后抓点回移537.24mm。停止该类高度扫描；下一步先审查已有材料网格/锚点/目标几何，确定新假设，暂不启动新仿真或bend对照。详见day4-actionchunk-test/results/day4-minimum-half-fold-20261031-053919-868025/pilot_review.md。

最新待运行（2026-10-30）：已准备v4提前下降候选，唯一修改越线后arc的z时间形状，保留XY、前半段和终点；其余物理、材料目标修正和释放流程保持。本地语法/哈希与路径边界通过，远端尚未运行。只运行一次后审查，不开展高度扫描。见day4-actionchunk-test/EARLY_DESCENT_V4.md。

最新审查（2026-10-30）：v3逐步记录已下载并审查（20261031-051637-969766）。358步连续、源码哈希及642帧视频通过；56个动作和12个共有阶段顶点与v1完全一致。固定半片y漂移：越线−3.97mm→到达未保持−15.93mm→保持后−22.43mm；折线带z为20.01→49.86→55.80mm，说明搬运已发生拖动与抬升，保持继续加重。停止复跑旧路线或扩大终段追踪，下一步依据材料/末端目标关系设计越线后更早铺下的单一路径修正，尚无新候选待运行；暂不改bend，正式成功0。详见day4-actionchunk-test/results/day4-minimum-half-fold-20261031-051637-969766/pilot_review.md。

以下保留此前记录，状态以本段为准。

最新准备：离线分阶段定位显示下层y漂移从越线−4.0mm到原放置−22.4mm，实际折线带z从约20mm升至56mm，早于支撑调整。原放置含60步保持，无法进一步拆分。已准备day4-minimum-half-fold-v3.py，仅给v1增加越线后逐步网格和保持前快照，动作/物理不变；不运行v2追踪。目的为区分搬运与保持，非新的成功候选。本地AST动作表达式一致、语法及manifest通过，远端待运行。见day4-actionchunk-test/POSTCROSS_TRACE_V3.md。

最新审查：v2结果day4-minimum-half-fold-20261031-045719-273006已完整下载，663帧解码/源码哈希通过。只追加一次20mm，支撑簇累计移动92.35mm触发60mm漂移边界；placement_ready=false。实际材料限幅指令误差0.370mm，未限幅目标误差28.54mm不可混用。支撑覆盖14.62%降至13.56%，原地释放后展开。停止扩大支撑追踪，未满足bend对照前提，正式成功0。下一步先复查更早搬运阶段的固定半片拖动与实际折线，不运行新实验。详见该结果目录pilot_review.md。

最新待运行：已准备day4-minimum-half-fold-v2.py，有界跟踪原支撑簇，最多3次、单步20mm、含首次放置累计目标预算60mm；增加材料速度/支撑覆盖等开发筛查。筛查失败后的释放仅用于失败诊断，不计成功、不直接进入bend对照。旧60帧离线拒绝检查与预算边界通过，远端未运行。说明见day4-actionchunk-test/BOUNDED_SUPPORT_V2.md。下一步只试跑此一个候选。

## 最新结果：2026-10-30 单次终段候选已审查

结果day4-minimum-half-fold-20261031-043028-240166已下载；源码哈希与641帧解码通过，56动作流程完成但折叠失败。抓点目标误差0.456mm，然而所选下层13点支撑簇移动48.37mm，源半片仍悬高、未收敛；释放原地60步已展开，早于退让。未达到弯曲对照前提，正式成功仍0。详情见结果目录pilot_review.md与independent_audit.json。下一步先定位放置时下层漂移，不重跑成功重复、不直接改bend。

## 当前授权主线：最低完成版（2026-10-26）

用户已明确恢复工作并指定最低完成版，覆盖下方旧暂停/扩展要求。以DAY4_MINIMUM_PLAN.md和DAY4_NEXT_STEPS.md为准：先一条释放退让静置后保持的L1单次half-fold，再开发重复一次；随后仅做必要Backend/≤12动作预算/0–2次recovery、三档30张截图、冻结评价、正式每档5条成功、完整拒绝率与合并10次reset/rollout检查。无需翻腕根因或完整三阶段整衣折叠。

当前已复核旧下摆放置：抓点与邻近固定半片投影相距约25mm、源半片悬高，缺乏铺下支撑证据。第一份候选仅修正终段材料相对支撑放置，复用多槽位控制并只抓下摆；本地准备/检查完成，GPU未运行。正式成功仍为0，禁止把流程passed当成half-fold成功。

## 最新暂停状态：2026-10-26

用户明确要求在此暂停。最新交接：[Stage 4多次抓取与折叠回弹](2026-10-26-GarmentLab日报%20Stage4多次抓取与折叠回弹交接.md)。两/三区域同回合抓取生命周期已实测；三阶段102动作完成但折叠回弹失败，随后单点首袖34动作严格对照也失败，不推广三阶段。正式成功仍为0，Stage 4未完成。没有新脚本待执行，不自动重跑旧实验。后续以该日报和DAY4_NEXT_STEPS顶部为准，下面早期恢复/待运行段落均为历史记录。

## 恢复工作

用户已要求读取交接及剩余计划并继续。已读两份文档；本地未找到v5 result.json。助手只读SSH尝试连接被拒绝，尚不能确定远端是否已有v5结果；需从已连接的VS Code终端核实。未启动或重跑任何实验。下方暂停状态是历史记录。

## 当前执行顺序（2026-10-26 更新）

**先打通一个符合接口要求的L1折叠，再扩展到三档验收。** 完整任务与通过条件见 [Stage 4后续执行计划](DAY4_NEXT_STEPS.md)，该计划优先于下方历史建议。当前仍暂停，仅更新文档；服务器是否已有v5结果尚未核实。

1. 核实v5结果、版本及接触记录有效性，形成明确诊断结论。
2. 修正空载路径，补充速度收敛条件并完整通过。
3. 明确唯一公共动作定义，解决俯仰侧通道冲突。
4. 取得可重复、符合接口的带布料L1折叠开发候选。
5. 整合Backend，支持episode内重抓取，通过10次reset/rollout。
6. 固定三档难度及seeds，保存30张可复现初态截图。
7. 实现最多两次recovery，核对12个high-level actions上限，冻结评价标准。
8. 正式批次每档至少5次成功，保留全部尝试及rejection rate分母。
9. 检查接口隔离，更新完整验收材料；全部完成后进入Stage 5。

恢复时先查服务器已有v5结果，有则下载，没有才运行。当前不启动检查或实验，不重跑旧版本，不继续质量或求解器迭代数扫描。

## 已暂停：2026-10-26

用户要求在此暂停，交接入口为 `2026-10-26-GarmentLab日报 Stage4翻腕控制与接触诊断交接.md`。v4结果已下载分析；v5接触记录脚本仅本地准备完成，尚无远端运行确认。不要自动继续。Stage 4尚未完成，无新增正式成功episode。下列内容为阶段历史记录。

最新接续：抬高版v4（072444-531501）25、26点末端收敛且关节速度小；27点虽reached=true，末帧joint5速度4.7165 rad/s，属于位置阈值通过而非动态稳定。异常在27点插值第26步已开始，28点第20步joint6误差0.224565 rad停止。两轮异常开始时joint2约0.78–0.81 rad，但其他关节不同，不能判定碰撞或控制器根因。准备v5保留v4路径及阈值，增加PhysX机器人接触事件/对象/冲量记录，独立contacts.jsonl；无报告不证明无碰撞。仅本地语法与步数包装检查通过，运行时API待验证。正式Stage 4成功数不变。

最新接续：v3结果071411-159644已分析；已应用速度目标全零，前14步关节误差约0.0012 rad，第15–16步异常开始，腕部速度随后剧烈波动，第36步joint6误差0.150894 rad停止。不能归因于未清除旧速度目标，也尚无接触证据确认碰撞。准备v4，将整条空载路径抬高15 cm（包含起点与终点），保留翻腕、控制器、阈值，检查高度/姿态构型对执行的影响；即使通过也不证明碰撞根因或折叠成功。本地验证30个圆弧点均为原点+[0,0,.15]，远端待运行。

最新接续：IK执行v2（20261026-070558-187726）在首次速度目标提交时因CUDA→NumPy转换异常停止，不能用于判断末段动态可达性。下载的控制器源码确认：joint_indices=None分支直接np.isnan(CUDA速度标量)。独立v3显式传入全部关节索引，位置/零速度目标转为与机器人同设备同dtype的Torch张量；保持轨迹和阈值。已用导出的真实apply_action函数及设备标量桩复现旧分支失败、验证显式索引分支转发目标；这不是Isaac/GPU执行验证。v3待远端运行。

最新接续：空载IK执行 v1（20261026-065716-750384）在第25路点、第36/40插值步停止，关节最大跟踪误差0.21016 rad。该版仅提交位置目标，未记录逐关节误差或已应用速度目标，根因不能确定。已准备独立v2脚本，保持路径、每步0.005 rad、0.15 rad停止阈值，显式提交零速度控制目标并记录逐步关节位置/速度/目标，导出运行时控制器源码。不设置实际关节速度、不瞬移。v2本地语法及命令点检查通过，待远端试跑；正式Stage 4成功数未新增。

最新接续：IK审计 day4-wrist-ik-audit-20261026-065126-175358 已下载，25–30路点都有通过FK和关节限位复核的解，终点最小限位余量约6.84°。准备 ik-tail-execution-v1：前24点保持RMP，末段从实时关节状态求IK，FK验证后用关节位置目标插值（每步≤0.005 rad），限制单段变化≤0.35 rad，跟踪误差>0.15 rad停止。无抓取、不瞬移、不重置速度；不证明无碰撞。仅本地Python3.10语法通过，远端待运行。通过空载后才考虑接回折叠。正式Stage 4成功回合仍未新增。

最新接续：opposite-delayed-pitch-v2 已下载（day4-wrist-reach-20261026-063936-107749），第24路点通过，第25路点位置误差94.52 mm、姿态误差0.09315 rad，未通过。q4≈−123.09°、q6≈56.75°，不能沿用上次接近硬限位的解释。已准备 wrist-ik-audit，对同一路径末段25–30点计算逆运动学，并以正运动学和关节限位复核；不执行解、不验证碰撞。仅本地语法与文件哈希检查通过，待远端运行。Stage 4仍无新增正式成功回合。以下为历史记录。

当前接续：空载延迟翻腕在第18路点失败，位置误差88.6 mm；q4/q6距已保存模型边界仅约2.65°/3.04°，姿态误差很小。准备 opposite-delayed-pitch-v2，只反转翻腕方向、保持位置路径及判定阈值，仍为空载可达性检查，尚未运行。没有新增正式Stage 4成功回合。

下一步已准备 hem-v12-pitch-arc-probe：审查发现辅助块搬运时角速度恒为零，多点锚定可能限制局部翻转。新试跑保持v11低圆弧，增加腕部180度翻转，辅助块跟随实测腕部旋转并检查角度误差。已做本地旋转数学/语法检查，远端可达性和效果未验证。俯仰通过试跑侧通道传入，超出现有XYZ+yaw接口，因此不得计入示范或正式验收。详情见 day4-actionchunk-test/HEM_PITCH_PROBE.md。

当前接续：hem-v11 结果已下载分析。低路径放下越线 .975，但释放后回弹为0；放下最大网格边长比1.934（高路径1.387）。低路径减少固定半片拖动却增加局部伸长，不能再靠盲试高度推进。下一步先审查抓取约束姿态自由度与末段放置目标，再提出有依据的动作修正。尚未创建v12或要求新试跑。详情见 results/day4-l1-hem-fold-20261026-055645-888101/pilot_review.md。

最新：hem-v10 圆弧候选导致整件翻转而非对折；最终名义固定半片向后移动约20 cm，两半基本相邻而非重叠。已准备 hem-v11-low-arc-fold，将抬升分量降至12 cm（最高绝对 z≈14.5 cm），水平路点与终点不变，记录阶段固定半片位移，待运行。仍无正式 Stage 4 成功回合。

最新接续：hem-v9 固定候选摩擦配置已完整运行，末段中心稳定但折叠回弹失败。放下时越线 .969，名义固定半片被拖动 8.3 cm；松开静置后越线为 0、抓点回弹约 60 cm。已准备 hem-v10-arc-fold，以绕初始折线的半圆弧替代旧抬升/斜向搬运路径，其他配置和阈值不变，待远端验证。详见 results/day4-l1-hem-fold-20261026-052424-872450/pilot_review.md。

## 当前接续点：hem-v8 已分析，hem-v9 待运行

仅关闭 room 碰撞未解决飞离；零总摩擦仍导致持续滑动。hem-v8 保留材料摩擦 .3、松开前将粒子间摩擦比例置零后，释放运动明显稳定：最后一秒中心变化不足 .2 mm，但衣物重新展开，折叠验收失败。已准备 hem-v9，从构造阶段固定该候选配置，去掉释放时参数切换，验证完整过程后继续修正折叠动作。此配置不是现实材料标定，Stage 4 尚未完成。详细数据见 results/day4-l1-hem-fold-20261026-051004-961491/pilot_review.md。

用户明确要求：以原阶段计划的 Stage 4 内容为首要目标。物理参数扫描退出当前主线；16→32 次迭代对照已有通过截图，完整结果未下载，不作为 Stage 4 必须验收。

## 最新状态：2026-10-25 收工

恢复工作更新：hem-v5 已下载；源码哈希通过，日志确认约束移除。与 hem-v4 的 85 帧中心/包围盒/末端/辅助块数值完全相同。准备 hem-v6-room-isolation，在首次 reset 前审计并关闭导入 room 的碰撞、保留默认地面；若无 room 碰撞体则直接停止。此为待运行的场景碰撞隔离假设测试，不是已证实修复；详见 hem-v5 结果目录 pilot_review.md。下列收工状态是历史记录。

Stage 4 尚未完成，没有新增正式验收成功 episode。下文“准备试跑”段落为历史记录，最新进度以本节及 `2026-10-25-GarmentLab日报 Stage4折叠与释放异常交接.md` 为准。

左袖 pilot 折叠失败；下摆 hem-v2 在撤离时超时；hem-v3 修改撤离后动作完成，但布料释放后飞离几十米；hem-v4 逐帧记录确认夹爪原地不动时布料已持续加速。hem-v5 尝试松开时移除约束，最新截图仍出现 2 m 越界停止，根因未确定。

下一步先下载 `/root/autodl-tmp/day4-l1-hem-fold-20261025-081458-011222`，核实移除日志并比较 hem-v4/v5 轨迹，不直接重跑或放宽指标。当前本地脚本版本 hem-v5，完整结果尚未下载。用户要求今日暂停，未启动后续实验。

## 最终完成标准

- [ ] Flat / Perturbed / Crumpled 有固定生成参数和 seed。
- [ ] 每档 10 张初态截图，共 30 张，三档肉眼可区分。
- [ ] 参数化 scripted expert 能自动完成 half-fold。
- [ ] L2/L3 最多两次 recovery moves，可再次抓取。
- [ ] 明确定义 alignment / overlap / success threshold，训练前冻结。
- [ ] 每档至少 5 个成功 expert episodes，共至少 15 条，保存完整成功/失败记录。
- [ ] 记录每档 expert rejection rate，失败不能从分母删除。
- [ ] 检查 state-oracle expert 的 simulator-only 状态没有泄漏到 policy action / backend 公共接口。

## 推进顺序

1. 取回服务器当前两份工程的源码/config/git 状态，避免基于旧补丁改写实际项目。
2. 先接通 L1：approach→grasp→lift→transfer→place→release，保存视频和状态；不再以原地抬升成功替代折叠成功。
3. 收敛到支持独立 episode 的 backend，验收重复运行。每进程新建环境可以作为早期 L1 测试隔离手段，但不能据此宣称原计划的可重复 reset 已完成，也不能代替 L2/L3 episode 内再次抓取。
4. 定义折叠评价和阈值，冻结后取得 L1 五个成功 episode；随后补 L2/L3 与最多两次 recovery，并完成三档批量验收。
5. Stage 4 验收完成后进入 Stage 5 数据集生成，不提前把诊断轨迹计作 demonstrations。

## 已有可复用基础与边界

- Torch/CUDA 环境，固定区域机器人驱动单次抓取、公开 ActionChunk、锚点 points1 对齐已通过局部验证。
- 显式轻质量每粒子 0.0001 kg 作为当前开发候选配置，实际总质量约 0.995 kg；这不是现实材料标定。
- 当前正式 backend 未完成这些实验修正的整合，单次抓取限制仍在，独立 reset 未验收。
- 轻质量保持结束局部最大边长比约 1.407，作为已知限制记录；是否继续优化由它是否阻碍完整折叠/数据生成决定。
- 远程交互仍由用户通过 PowerShell 上传/下载、VS Code 远程 Bash 运行；助手没有成功的 SSH 登录凭据。

本次实际交付：源码打包工具 export-day4-sources.py（只读代码/config，普通 Python，无 Isaac 启动），用于下一次实现所需上下文。尚未声称完成新的 L1 折叠或 Stage 4 验收。

## 最新推进：已取得源码并准备 L1 试跑

已下载 day4-source-handoff-20261025-063847-681950.zip，186 份文件哈希验证通过，解压到 results 同名目录。没有发现现成 expert；官方 FoldDemo 为三次连续抓取，当前 prepared 控制仍限一次抓取。源码中的 difficulty.yaml 与 difficulty.py 已取回，后续需逐项验证物理生成路径，不以文件存在代替通过。

新增 day4-l1-fold-pilot.py、l1_fold_geometry.py、run-l1-fold-pilot.sh、l1-fold-files.json。仅做固定名义平整初态的一次抓取折叠候选，尚无平移/yaw seed 批次，不计入正式 L1 五条成功验收。沿用显式轻质量与 points1 对齐，以初态 x 范围中线定义 world-y 折线，抓取左侧既有区域、抬升 0.18 m、跨中线移动至镜像位置、分层放置、释放、退让并 settle 180 步。

保存 episode.mp4、七阶段 PNG/NPZ、完整动作与质量记录，计算 XY 双向最近点对齐误差、粒子栅格投影 IoU、源半区越线比例、P95 高度和材料点反射目标误差。阈值明确标为 provisional：对齐均值 ≤4 cm、IoU ≥0.5、越线比例 ≥0.8、P95 高度 ≤6 cm。它们是试跑检查，不能充当已冻结的真实表面重叠定义。需看视频与几何后在正式批次前完善/冻结。

本地语法和合成理想对折/未折叠区分测试通过。GPU 动作与视频尚未验证。使用 L1_FOLD_PILOT_ARTIFACTS_OK 表示动作和保存通过；provisional_fold_success 单独记录，formal_day4_success 始终 false，避免把动作跑完当作正式折叠验收。

用户补充截图显示此前迭代对照出现 ITERATION_PAIR_COMPARISON_OK，显示三次读回质量相同、settled_state_difference=0、锚点索引相同。完整迭代结果当前未下载，不推断其伸长改善或收敛；该项不阻塞 Stage 4 主线。


## 2026-11-02 汇总器修复与 right 开发验证登记（尚未运行）

stage4_formal_report.py 已把缺失结果转换为 error 尝试，按档/表示/任务计入 attempts 和 (rejected+error)/attempts；空批次保持 null。新增 test_stage4_formal_report.py，8 项纯离线测试通过（一次通过+一次缺失结果得到2次尝试、50%拒绝率）。已有结果与日志不重复计数，非 held-out 日志不纳入，重试独立计数。

按冻结文档最新 b-right-dev-v1 条目，仅以开发 seeds 4200/4300 各运行 single/arc4 验证 right 的释放后保持；独立 manifest 与目录白名单在任何新结果前登记。held-out 与正式批次暂停，正式成功仍为0。检查范围仅现有 OPEN+30ticks+180settle 的终态，不宣称第二时刻保持或长期稳定。


## 2026-11-02 right 验证执行分工更新（用户指定）

用户明确指定“另一聊天继续；本聊天只下载和审计其结果”。本聊天已停止自动提交控制器，之后不再提交 GPU 实验；此前已在途进程不终止。L2 4200 right single/arc4 已下载并通过原版 PAIRS_COMPARABLE，crossed均1.0、IoU约0.559；L3等待外部结果，尚不宣称验证完成。

后续下载保留外部结果的真实来源，核对同一初态、right、seed、execution_mode与21项底层代码身份；未经过本变体入口的外部结果不伪造23项wrapper身份。优先按目录启动时间选取结果，不按passed筛选；额外或失败尝试原样留存。并发运行不作耗时比较。held-out不运行，正式成功仍为0。


## 2026-11-02 b-right-dev-v1 开发复验与移交后审计完成

汇总器缺失结果分母修复与8项离线测试已通过；原项目代码与已测试副本SHA256一致（9a757d34…）。一次通过+一次无结果error的合成回归输出2次尝试、50%拒绝率；空批次保持null。

L2 4200的right single/arc4由本聊天在移交前完成；L3 4300采用另一聊天产出的最早外部single/arc4，按目录启动时间选择而非passed。两对均通过原版PAIRS_COMPARABLE，四份选定结果held gate通过、crossed=1.0，L2 IoU=0.559091、L3 IoU=0.562997；各对目标差及五项指标差值精确为0。底层21项代码不变，四份结果的独立23项变体manifest、配置和初态文件哈希均核对一致。

共下载核验66个远端文件，包含6份完整开发结果：选定4份配对结果与2份额外L3 single重复尝试。额外尝试原样保留，不增加独立seed覆盖，不计算正式成功率。用户移交后本聊天仅下载审计，未再提交GPU仿真，未终止已在途远端进程。

结论仅为每档一个开发seed在OPEN后30 release ticks+settle(180)终态保持；没有独立退让、第二retention样本或长期稳定性验证，不能外推整个开发集/held-out，更不能解释为BC策略或H=4性能提升。right为独立变体，不替换left失败或默认定义。held-out与正式批次保持暂停，正式Stage 4成功仍为0。

完整报告：[right开发复验与移交后审计](../thesis/day4-actionchunk-test/results/TASK_B_RIGHT_DEV_V1_20261102-183740/review.md)。

补充交叉核对（2026-11-02）：把主审计未采用的 4200 arc4 尝试 `025355-106410` 与 4300 single 重复尝试 `031535-711404` 一并核对，5 个目录 77 项检查全部通过；同 seed 全部 7 次已下载尝试（4200 三例、4300 四例）的 `final.npz` 441 个顶点逐位相同（max|Δ|=0），包括并发在途的 4200 arc4 两例。该核对不新增 seed、不改任何阈值、不改变上述结论。[补充审计](../thesis/day4-actionchunk-test/results/B_RIGHT_DEV_AUDIT_SUPPLEMENT_20261102/review.md)。

right 开发覆盖扩展 `b-right-dev-v2` 已登记并完成 A1 预检（48/48，仅离线；v2.1 修正 sampling 描述，config `91c0fe7f…`、manifest `c3e34c91…`），尚未运行任何 seed：L2 4201–4209、L3 4301–4309 共 18 个剩余开发 seed，先登记初态哈希再跑 right single；不跑 arc4、不冻结阈值、held-out 不动。见 [扩展计划](STAGE4_B_RIGHT_DEV_V2_PLAN.md) 与 [A1 预检](day4-actionchunk-test/results/STAGE4_A1_PREFLIGHT_20261102/review.md)。

## 2026-11-04 a5-rc2-pfs1 开发单例（不计正式成功）

`a5-rc2-pfs1` 4202 single 一次：`passed=True`、质量 accepted，正式窗口质心 0.2642 mm、P95 0.3792 mm（RC2 2.0429/4.4141 mm）。但速度读回与位置差分不一致、无运行时材料读回；只作为候选改善证据，**不扩展 4302、不计入正式 Stage 4 成功**，正式成功仍为 0。见 [pfs1 对照](day4-actionchunk-test/results/D2_E_PFS1_COMPARE_20261104/review.md)。

`a5-rc2-pfs1-observation-v2` 随后完成观测-only 修订并单次复验 4202：`file_complete=true`、`observation_semantics_valid=true`、质量 accepted、`overall_valid=true`；动作/状态/formal 与 pfs1 0 差。仍只作为观测修订通过，**不计入正式 Stage 4 成功**；尚未运行 4302。见 [v2 对照](day4-actionchunk-test/results/D2_E_PFS1_V2_COMPARE_20261104/review.md)。
