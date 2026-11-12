# 2026-11-05 GarmentLab 日报 · Stage 4 rc8b/L2 诊断与 hold120 七例交接

> 时间说明：rc8b 与后续 L2 诊断运行在远端（UTC+8）2026-11-05 凌晨至上午；本地 Europe/Berlin 仍是 2026-11-04 晚间。按远端运行日命名。

**暂停位置**　Stage 4 暂停在 **开发候选已冻结、正式批次离线预检完成但未运行** 之处；正式 Stage 4 成功计数仍为 **0**。hold120 七例开发回归：六阳性 accepted、4201 有效 rejected；来源兼容 freeze/gate 已完成。正式矩阵固定 60 初态 / 120 槽，部署层 source gate、固定清单、离线桩测试 10/10、容量/机时估算与运行命令已整理；本轮未启动仿真、未生成 held-out 初态、未执行正式 episode。

## 1. 本轮做了什么

1. **协议实现（rc8b）**：`day4-square-initial.py`（L1）保持 pfs=0；`day4-square-initial-stripfold.py`（L2/L3）0→1；两者新增 `protocol` 块（task/level/seed、expected+readback scale、material binding、generator script/files manifest 哈希、generated_utc）。
2. **正式入口绑定**：`stage4_batch_preflight.initial()` 逐项核对上述字段，拒绝旧初态/错 scale/缺失绑定/生成器不符；`run-square-initial*.sh` 与 `run-stage4-formal-batch.sh` 改为 app-relative，不再读 `/root/autodl-tmp` 共享根的旧副本。
3. **离线验证**：manifest 63/63（52 项与 rc8 相同）；协议测试接受新 4100/4202/4302，拒绝旧 4100、错误 scale、缺失绑定、生成器不符、缺失 protocol；`py_compile` 通过。
4. **开发初态生成**：4100、4201、4202、4302 各一次、无重试；哈希写入 `a5-candidate.json` 与登记。
5. **七例 RC**：顺序 7 槽、每槽一次、无重试；新账本、14 行 attempts。

## 2. 新初态与任务定义

| seed | 初态族 | 宽度 | extent (m) | 旧 extent (m) | 初态 final 差异 |
|---:|---|---|---|---|---|
| 4100 | flat | — | 0.4129 × 0.4129 | 同值 | 逐位相同 |
| 4201 | perturbed | bottom 0.1793 | 0.4283 × 0.2669 | 0.4286 × 0.2678 | 0.98 / 1.51 mm |
| 4202 | perturbed | bottom 0.1714 | 0.4213 × 0.2558 | 0.4206 × 0.2541 | 2.80 / 3.74 mm |
| 4302 | crumpled | left 0.2000 | 0.2674 × 0.4315 | 0.2847 × 0.4357 | 5.40 / 24.14 mm |

L2 条宽仍在冻结范围；L3 为 width 0.20 的 left 条，z_p95≈0.069 m，未摊平。L3 的 extent 变化较大但本轮 accepted；L2 初态差异较小却失败——说明 L2 对初态细节敏感，不能按差异大小推断。

## 3. 七例结果

| 槽 | seed / 模式 | 质量 | 质心 / P95 (mm) | 几何 | stable | 配对差 | 初态 scale |
|---:|---|---|---:|---|---|---:|---:|
| 1–2 | 4100 single/arc4 | **accepted** | 0.1435 / 0.2072 | true | true | 0.0 | 0.0 |
| 3–4 | 4202 single/arc4 | **rejected** | 7.4809 / 11.5382 | **false** | false | 0.0 | 1.0 |
| 5–6 | 4302 single/arc4 | **accepted** | 0.2756 / 0.4125 | true | true | 0.0 | 1.0 |
| 7 | 4201 single | rejected（有效） | 7.0657 / 10.4252 | **false** | false | — | 1.0 |

- 六阳性 4/6；`stationary_half` 失败：4202 29.9 mm、4201 30.1 mm（阈值 25 mm）；速度 P95 25.7 / 20.3 mm/s（阈值 10）。
- 4202 的 recovery 仍展平（9.2 µm），失败在 fold 后：fold extent 0.1958×0.4078，旧初态同流程 0.2283×0.4199；布料整体滑移。
- 7/7 `initial_protocol=true`；材料读回 scale 与任务一致；三组配对 0.0；765/765 下载哈希一致；本地复算 7/7 逐值相同；verify-dev 失败于 4202。

## 4. 判定

**不冻结、不释放。** 放行条件 1（六阳性全部接受）与 verify-dev 均失败；按预登记保留失败，**不回退旧初态、不用 rc8 结果补 4202/4201、不改阈值**。`verified-dev.json` / `E_RELEASE.json` 未写。

**结论的边界：** 协议实现与初态身份检查通过；失败是新初态（1.0 下 settle）改变 L2 折后保持行为，具体机制未隔离，不能写成“摩擦导致”的因果结论。

## 5. 下一步（已冻结；正式批次未运行）

1. **hold120 r2/4302 通过**：4202 r2 accepted 0.2374/0.3484（与 r1 逐阶段 0.0）；4302 accepted 0.2386/0.3468；均 exit 0。
2. **七例 rc7 完成**：slot1 4100 single accepted 0.1435/0.2072（初次 audit 5，同结果修订审计 0）；slots2–7 续跑后 4100 arc4 / 4202 s,a / 4302 s,a 全部 accepted，4201 有效 rejected 7.2583/11.0030。
3. **freeze/gate 已完成**：来源兼容 freeze exit 0、gate exit 0；回执已独占创建；archive 已整理。
4. **未做：** held-out、正式批次、成功计数增加。不延长保持、不扩大 patch、不扫摩擦。

## 6. 产物

- [rc8b 七例审查](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/review.md)
- [初态生成审查](day4-actionchunk-test/results/RC8B_INITIALS_20261105/review.md)
- [cases.csv](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/cases.csv) · [local_recompute.json](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/local_recompute.json) · [verify-dev 日志](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/rc8b-verify-dev.log)
- [视频帧接触表](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/rc8b_contact_sheet.png)
- [rc8b 版本登记](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8b/README.md) · [registration.json](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8b/registration.json)
- **L2 诊断：** [离线定位](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/review.md) · [l2pose 审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/l2pose_review.md) · [重复性与几何](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/repeat_review.md) · [九点 z patch](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/l2patch9_review.md) · [hold120 r2/4302](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_r2_review.md) · [七例 rc7](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_rc7_review.md) · [冻结归档](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_rc7_r2_resume/freeze/FREEZE_ARCHIVE.md) · [七例准备](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/SEVEN_CASE_PLAN.md)
- **数据：** [repeat_compare.json](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/repeat_compare.json) · [geometry_check.json](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/geometry_check.json) · [geometry_check.png](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/geometry_check.png) · [patch_definition.json](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/patch_definition.json) · [l2patch9_compare.json](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/l2patch9_compare.json) · [hold120_compare.json](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_compare.json) · [hold120_4302_compare.json](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_4302_compare.json)
- **诊断登记：** [l2pose](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-l2pose/registration.json) · [l2pose-repeat1](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-l2pose-repeat1/registration.json) · [rc8b-repeat1](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8b-repeat1/registration.json) · [l2patch9](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-l2patch9/registration.json) · [hold120 r1](day4-actionchunk-test/a5-rc8b-recovery-hold120/registration.json) · [hold120 r2](day4-actionchunk-test/a5-rc8b-recovery-hold120-r2/registration.json) · [4302](day4-actionchunk-test/a5-rc8b-recovery-hold120-r2-4302/registration.json)
- 前序：[2026-11-05 rc8 冻结暂停交接](2026-11-05-GarmentLab日报-Stage4-rc8七例RC与冻结暂停交接.md)

## 7. 追加：4202 L2 初态敏感性离线定位

只读 old/new 4202 的已保存数据，无新增仿真（[报告](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/review.md)）。

| 阶段 | 质心差 | 旋转差 | 对齐后残差 P95 |
|---|---:|---:|---:|
| 初态 final | 2.796 mm | −0.256° | 0.043 mm |
| 载入后 | 2.795 mm | −0.257° | 0.046 mm |
| recovery 后 | 2.022 mm | −0.042° | **0.001 mm** |
| pre-release | 1.718 mm | −0.371° | 0.649 mm |

- 差异在载入时是**整体位姿差**，recovery 后内部形状几乎逐点相同；pre-release 折形差 <0.8 mm；**放大发生在释放后**：新初态 0.5 s 后持续 ~4 mm/s 滑移，旧初态衰减到 0.5–0.8 mm/s；首个几何失败在 release 后 **4.15 s**（formal 窗口内 0.65 s），stationary half 29.9 mm。
- 专家目标仅差 1.9–2.7 mm、fold_yaw 差 0.042°；不是路径大幅不同。
- 9.2 µm 只是几何展平误差；recovery 无逐物理步轨迹，残余速度/接触/应力为**未知**；“3 mm→30 mm”是相关观察，不是因果。
- **已运行位姿匹配单例**（旧初态几何 + 新初态位姿，rc8b rollout，4202 single 一次），结果见 §8；不改生成/rollout 协议、不重跑七例、不扫摩擦。

## 8. 追加：l2pose 位姿匹配单次诊断（已完成）

派生初态 = 旧折叠几何经 +0.2564° / (−1.94, +2.71) mm 变换到新位姿；`flat_settled` 不变、速度不恢复；rollout 源与 rc8b 逐字节相同（60/63 manifest 项），独立账本，只跑一次。

**结果：accepted，中间行为。** 质心 **0.7396 mm**、P95 **1.5397 mm**、stationary half **7.63 mm**、稳态质心 **0.418 mm/s**、无几何失败；old 为 0.2642/0.3792，new 为 7.4809/11.5382。专家目标与 new 差 0.209 mm（跟随新位姿），l2pose vs old 差 2.755 mm。

**判读：** 2.8 mm 的整体位姿变化**不足以**单独重现失败；也不是完整旧行为，而是明显退化但通过。l2pose 与 new 的已知差异只剩亚毫米 `final` 几何（P95 0.067 mm、max 0.302 mm、z max 0.264 mm）——与该例失败**相关**，但不能据此认定隐藏应力/接触是关键；重复性见 §9（两例逐位重现），不强行二选一。详见 [l2pose 审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/l2pose_review.md)。

**边界：** 单次诊断，无重试、无扩批、未冻结；不是正式任务协议，不进入七例/held-out/正式批次；正式成功仍为 0。重复性检查见 §9：两例逐位重现，未把中间行为归因于隐藏应力。

## 9. 追加：两例重复性与局部几何（已完成）

- `l2pose-repeat1`（manifest `a529ec05…`）与 `rc8b-4202-repeat1`（manifest `cb28ae4c…`）各一次、独立账本；均用原候选、原初态和完整哈希；single；不改控制/物理/评价/采样。
- **两例逐位重现原行为**：所有阶段（载入、recovery 后、释放前、释放边界）、动作目标、success_trace 的最大差均 **0.0 mm**；l2pose repeat accepted 0.739646/1.539675、stationary 7.6258；rc8b repeat rejected 7.480913/11.538153、stationary 29.9144、首次失败 step 249 相同。下载各 111/111。
- **固定初态下 accepted/rejected 差异可重复**；仿真重复性/初始化/状态恢复不是来源。
- **局部几何：** 最大差 #91（0.302 mm，z 0.264 mm）位于多层折叠区；25 mm 内 z 层 9.899/40.599/53.750（含 #91）/66.389 mm，层间距约 30.7/13.15/12.64 mm；#91 距折线代理（y≈−340 mm）约 55 mm；网格近邻差 0.003–0.246 mm；xy 最近点 99.3% <0.1 mm、100% <0.2 mm。层间距/投影仅为代理，不认定真实穿透/接触。
- **九点 z patch（已运行，见 §11）：** new 初态仅把 #91 的 3×3 网格邻域 z 改为 derived 对应值，其余不变，同 rc8b rollout、4202 single 一次。结果仍 **rejected 7.2532/11.4799 mm**（first 251 vs 249），响应很小、轨迹基本不变；本轮不扩批、不冻结。
- 详见 [重复性与几何审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/repeat_review.md)。

## 10. 暂停点

- **已完成并保留：** rc8b 七例（4/6）、L2 离线定位、l2pose、两例重复、九点 z patch、hold120 r1、4202 r2、4302、七例 rc7（六阳性 + 4201 有效 rejected）、**来源继承 freeze 与 gate（均 exit 0）**。
- **未做：** held-out、正式批次、成功计数增加。
- **状态：** **开发候选已冻结，正式批次未运行**；正式 Stage 4 成功仍为 **0**；slot1 audit exit 5、暂停账本、复审计、续跑账本全部保留。
- **恢复入口：** 冻结已完成；正式/held-out 仍需单独授权。不延长保持、不扩大 patch、不扫摩擦。

## 11. 九点 z patch 诊断（已完成，拒绝，响应很小）

- **固定定义：** 21×21 row-major，#91=(4,7)；索引 **69,70,71,90,91,92,111,112,113**；仅 z 替换为 l2pose derived 值；[patch_definition.json](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/patch_definition.json) 运行前写入，哈希 `68fd2610…`。
- **派生初态：** `day4-square-initial-stripfold-20261104-221219-l2patch9`；`initial_diagnostic=true`；审计恰好 9 点 z 改变，xy/其余 432 点/`before/applied/flat_settled` 逐位不变；边缘长最大变化 0.1236 mm，相邻高度差最大变化 0.2606 mm；无平滑/额外移动。
- **运行身份：** 候选 manifest `ef80bf75…`（60/63 与 rc8b 相同）、父 rc8b、rollout 同 rc8b；single 一次；预检通过；111/111 下载一致。
- **结果：** 仍 **rejected**：质心 **7.2532 / P95 11.4799 mm**（new 7.4809/11.5382）、stationary **29.68 mm**（new 29.91）、首次失败 **251**（new 249）、失败帧 80（new 82）。
- **逐阶段（patch vs new）：** 载入 0.039 mm；recovery 后 0.021 mm；pre-release 0.502 mm；释放边界 0.768 mm；success_trace max **2.137 mm** / mean **0.662 mm**；目标 0.016 mm。影响从 pre-release 起可见，但未改变失败模式。
- **判读：** 九点 z 修改在本配置下**不足以改变验收结果**，响应很小、轨迹基本不变；不能据此认定层序/接触机制，也不能推广为正式初态的手工修补。若未来出现 accepted，也应寻找可推广的生成/控制修正。
- 只跑一次；无重试、无扩批、未冻结；不改控制/物理/评价/采样。详见 [l2patch9 审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/l2patch9_review.md)。

## 12. recovery 后固定保持 120 步（r1 诊断完成；r2/4302 见 §13）

- **唯一干预：** `a5_recovery.py` 在 `rec_release` + 正常 240 步 settle 之后、重新观测/计算 fold pick/yaw 之前，精确增加 **120 × `b._env.step()`**（2.0 s）；保持当前控制目标，不移动/开闭爪、不重置布料、不清零速度、不改材料。
- **身份：** 候选 `a5-rc8b-recovery-hold120`，manifest `b61fd56e…`（60/63 与 rc8b 相同）；父 rc8b；初态 rc8b 新 4202 `…015817-115841`（pfs=1，完整哈希）；只跑 4202 single 一次。
- **保持轨迹：** 121 帧 / 120 区间 / 2.0 s；每步 holding=false、附件全关、步数 +1、dt=1/60；质心 ~0.0001 mm/s、粒子 P95 ~0.007 mm/s、旋转 ~1e-5°、EE 漂移 0、z_p95 不变——**保持开始时运动已接近零，没有可观察的衰减**。
- **结果：** **accepted 0.2374 / 0.3484 mm**、stationary **6.69 mm**、无几何失败（new 7.4809/11.5382、first 249；old 0.2642/0.3792）。fold_yaw 差 4e-5°、动作目标 max 0.0014 mm；pre-release/release 边界与 new 差 max ~1.0 mm。
- **审计异常：** entry exit 0；runner exit 3 是 audit 打印 `KeyError: recovery_hold`（out JSON 已写，仅投影缺键）。修正 audit 后对同一结果复审计 exit 0、`overall_valid=true`；**未重跑仿真**，不把该 run 标成干净完成。
- **判读：** 单次 accepted 只作为**候选衔接改进**，等待审查后再决定是否扩展；保持期间已稳定，仍改变下游 fold，机制未隔离；不能认定接触/应力机制，不计入正式成功。
- 不延长保持、不扩大 patch、不扫摩擦、不扩展 seed、不重跑七例、不冻结、不跑 held-out。详见 [hold120 审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_review.md)。

## 13. 审计修复、4202 r2 干净复验与 4302 扩展（均通过）

- **审计修复：** audit 增加 `check_output_contract()`（打印前校验 `recovery_hold` 等必需字段）；`test_audit_output.py` 覆盖 complete / missing / non-bool；对同一 r1 结果重跑完整审计 → exit 0、`overall_valid=true`。r1 的 runner exit 3、日志与复审计记录保留，不改写历史。
- **4202 r2：** 新候选 `…-r2`（manifest `60733a6b…`，61/63 与 r1 相同，仅 config/runner；`a5_recovery.py` 哈希相同）；entry/runner/audit **均 0**；**accepted 0.2374/0.3484**、stationary 6.69、无失败；与 r1 的载入/recovery/pre-release/release/trace/targets/hold trace 最大差 **0.0**。
- **4302：** 同代码、同规则、同 120 步；entry/runner/audit **均 0**；**accepted 0.2386/0.3468**、stationary 7.16、无失败（rc8b 参照 0.2756/0.4125）。保持 2 s 内质心 ~0.0001 mm/s、P95 0.0045–0.0062 mm/s、EE 漂移 ≤0.00016 mm、附件全关；目标差 0.0025 mm、fold_yaw 差 ~0；pre-release/release 边界差 max 1.74/1.65 mm。
- **判读：** 两例通过，hold120 可作为候选衔接改进；不能解释为残余运动衰减，也未证明稳健修复。七例 rc7 已完成（见 §14、§15）：六阳性 accepted、4201 有效 rejected；正式成功仍为 0。
- 不延长保持、不扫摩擦、不扩批、不冻结、不跑 held-out。详见 [hold120 r2/4302 审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_r2_review.md)。

## 14. hold120 七例 rc7：slot1 审计暂停与修复（历史）

- **候选：** `a5-rc8b-recovery-hold120-rc7`，manifest `41db790f…`；slot1 4100 single **accepted 0.1435/0.2072**；下载 118/118。
- **暂停原因：** 初次 audit exit 5，唯一失败项 `hold_applicable=false`——L1 N/A 被错误计入 `observation_semantics_valid`；不是质量或证据失败。
- **修复：** `hold_applicable` 移出必需语义；L1 要求无 hold；同结果复审计 exit 0；未重跑 slot1。
- **队列历史：** 原 `batch.log` 保留 `HOLD120RC7_QUEUE_PAUSED slot=1`；attempts 1 started + 1 paused；未改写。
- 后续在修订版续跑 slots2–7，见 §15。

## 15. hold120 rc7 七例最终结果（六阳性 accepted，4201 有效拒绝）

- **修订候选：** `a5-rc8b-recovery-hold120-rc7-r2`，manifest `40858efc…`（相对 rc7 仅 config；`a5_recovery.py` 哈希相同）；审计 `0d4a9d74…` + `hold_contract.py`；继承记录 `a9a106c2…` 仅 slot1。
- **续跑：** slots2–7 固定顺序；4100 arc4、4202 s/a、4302 s/a 全部 **accepted**；4201 **rejected 7.2583/11.0030**（stationary 30.6 mm，92 帧失败，有效）。
- **门禁：** 六阳性 accepted；配对目标差 0.0；L2/L3 hold 均 120 步/121 帧/2.0 s；下载 118+664 哈希一致；本地复算 7/7；视频检查通过；来源兼容验证 `RC7_SOURCE_VERIFIED` exit 0。
- **原版 verify-dev 未使用**（单一 manifest 限制）；不称原版直接通过。
- **续跑 runner 汇总只统计 slots2–7（accepted=5），不含继承 slot1；最终来源验证器明确六阳性为真。**
- **未 freeze、未写回执、未跑 held-out/正式批次**；正式成功仍为 0。冻结归档见 [FREEZE_ARCHIVE](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_rc7_r2_resume/freeze/FREEZE_ARCHIVE.md)。详见 [七例审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_rc7_review.md)。

## 16. 本次暂停交接

- **当前状态：** 开发候选已冻结，正式批次未运行；六阳性 accepted、4201 有效 rejected；正式 Stage 4 成功仍为 **0**。
- **审计口径：** slot1 首次审计退出 5（L1 `hold_applicable` 契约缺陷），同结果经修订审计通过；slots2–7 在修订版下续跑。**不称整批所有入口首次均干净退出。**
- **验证状态：** 配对 0.0；hold 120 步/121 帧/2.0 s；下载 118+664 哈希一致；本地复算 7/7；视频检查通过；来源兼容验证 `RC7_SOURCE_VERIFIED` exit 0；原版 verify-dev 未使用。
- **冻结：** `verified-dev.json` `67c64a55…`、`E_RELEASE.json` `9042e88e…`、verification manifest `7d328159…`；freeze/gate exit 0；83/83 条目核验；临时副本 10/10 负测。
- **未做：** held-out、正式批次、成功计数增加。
- **恢复入口：** 冻结已完成；正式/held-out 需单独授权。归档见 [FREEZE_ARCHIVE](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/hold120_rc7_r2_resume/freeze/FREEZE_ARCHIVE.md)。

## 17. 冻结与门禁记录

- **命令：** `python freeze_rc7_sources.py --execute` → exit **0**；`python gate_rc7_sources.py` → exit **0**（`A5_GATE_OK_SOURCE 7 manifest 40858efc…`）。
- **回执：** `verified-dev.json` `67c64a55b74db10ac85818cb0ed6ca1d00600e8b4ba326e5af4d6f01109cbbad`；`E_RELEASE.json` `9042e88ed8b4d082917151023705276230c1a4ba5c8e65b3c602337fa68ab66a`；`verification-manifest.json` `7d328159b72a2bd55be0254fd6844cb94408e1efa67e973148b67e8ffa3dcdae`。
- **核验：** verification manifest 83/83 条目哈希匹配；临时副本 10/10 负测（候选/审计/继承/验证代码/证据篡改、缺槽/重复槽/未完成、回执不可覆盖）全部按预期拒绝/通过。
- **来源：** slot1 父 manifest `41db790f…`；slots2–7 修订 manifest `40858efc…`；未使用旧 single-manifest freeze 入口。
- **状态：** 开发候选已冻结，正式批次未运行；正式成功计数 0。

## 18. 正式批次离线预检与运行清单

- **冻结身份：** 候选 `40858efc…`、验证 manifest `7d328159…`、`verified-dev` `67c64a55…`、`E_RELEASE` `9042e88e…`；gate exit 0；83/83 条目；无当前正式锁/活跃 tmux。
- **固定矩阵：** L1 4110–4129、L2 4210–4229、L3 4310–4329；60 初态/120 槽；seed/plan 逐项一致、无 dev 重叠；同 seed 两模式共享初态。
- **部署层：** `formal_hold120/formal_driver.py` 在任何初态生成前调用 `gate_rc7_sources.py`；使用冻结初态/rollout/audit 入口；deployment manifest `1a36b8c4…`（18/18 条目）。
- **离线测试：** 10/10 桩测试（gate 失败不生成、身份/缺结果暂停、复用初态、rejected 继续、未完成/锁/配对暂停、跳过已完成、空分母 null）。
- **容量/机时：** 120 episodes 均值 2.21 GB、最坏 2.41 GB；初态 28 MB；预留 2.9 GB；远端可用 14 GB；约 35 h。
- **状态：** 未启动仿真、未生成 held-out、未执行正式 episode；正式 Stage 4 成功仍为 **0**。
- 清单与命令见 [FORMAL_PREFLIGHT](day4-actionchunk-test/formal_hold120/FORMAL_PREFLIGHT.md)；预检结果 [JSON](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/formal_preflight/FORMAL_PREFLIGHT_RESULTS.json)。

## 19. 正式验收改为最低完成方案

- 原 60 初态/120 槽计划**未启动**，保留并标记为被取代；不删除历史。
- 新计划：每档 single，固定 seed 顺序；每档 5 个不同 seed 有效成功即停，最多 20 seed；不换 seed/不重试/不调阈值。
- 每档先生成并保存 10 份最终协议初态截图（共 30）；折叠只跑达到 5 成功所需 seed。
- 独立 plan/deployment/ledger；已登记停止规则后再运行。
- 机时估算：30 初态实测约 2.5 h（stripfold 较慢）；episode 约 14–19 min/个。
- **执行结果：** 30/30 初态截图完成（每档 10）；flat 档尝试 4110、4111、4112，**0 有效成功**。
  - 4110/4111：冻结 `a5_entry.py` 的 receipt 路径问题，入口在 episode 前失败；保留错误。
  - 4112：实际开始，9.3 min 后 **`RuntimeError('Square waypoint velocity/position did not converge')`**，`status=incomplete`，无完整 success_trace。
- 按执行异常规则**暂停**：未自动重试、未换 seed、未继续 4113；最低验收**未通过**。
- **4112 单次只读诊断（已复现）：** arc135 最后 120 tick 中速度 118 tick 超 0.1 rad/s（首 tick 0.2529），位置仅前 10 tick 在 10 mm 内、tick10 后越界，block ≤1.655 mm 合格；结论为速度未衰减/过冲优先，不是位置不可达。详见 [诊断](day4-actionchunk-test/results/MINIMUM_ACCEPTANCE_20261105/diag_4112_final/4112_DIAGNOSIS_FINAL.md)。
- **深诊断（RMP/关节指令）：** 目标交接一致（末段与判定 target 差 2.8e-17 m）；关节0 的 RMP 位置目标步进等效 0.204–0.236 rad/s，速度字段仅 0.018–0.102，实际 0.253–0.290；关节2 实际 0.109–0.147 而目标 <0.1。证据同时指向 RMP 位置轨迹过快与底层跟踪过冲；缺 `apply_action` 消费字段/增益证据。详见 [深诊断](day4-actionchunk-test/results/MINIMUM_ACCEPTANCE_20261105/diag_4112_deep/4112_DEEP_DIAGNOSIS.md)。
- 正式 Stage 4 成功仍为 0；原 120 槽批次未启动。
