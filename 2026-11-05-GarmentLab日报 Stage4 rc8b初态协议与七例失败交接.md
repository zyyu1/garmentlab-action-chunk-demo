# 2026-11-05 GarmentLab 日报 · Stage 4 rc8b/L2 初态敏感性与暂停交接

> 时间说明：rc8b 与后续 L2 诊断运行在远端（UTC+8）2026-11-05 凌晨至上午；本地 Europe/Berlin 仍是 2026-11-04 晚间。按远端运行日命名。

**暂停位置**　Stage 4 暂停在 **L2 初态敏感性诊断完成、单变量对照尚未运行**之处，**未冻结**。rc8b 把任务协议补到初态生成（L1 0.0、L2/L3 1.0，初态记录任务/绑定/scale/生成器身份，正式 preflight 拒绝旧/错初态）；七例 **4/6 阳性**：4100/4302 s/a accepted，**4202 s/a rejected**（7.4809/11.5382 mm，stationary 29.9 mm），4201 也拒绝，verify-dev 失败于 4202。随后离线定位、位姿匹配单次诊断与两例重复性均完成：l2pose **accepted 0.7396/1.5397 mm（中间行为）**；l2pose/rc8b 两例重复**逐位重现**（阶段/目标/trace 最大差 0.0）；固定初态差异可重复，仿真重复性不是来源。局部几何显示 #91（0.302 mm）位于多层折叠区、距折线约 55 mm；单变量局部层高对照已设计、**未运行**。正式 Stage 4 成功仍为 **0**；无回执、无扩批。

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

## 5. 下一步（暂停点；需批准后执行）

1. **单变量局部层高对照（已设计、未运行）**：取 new 初态，只把 #91 的 3×3 网格邻域（9 个顶点）的 z 改为 derived 初态对应值，其余不变；同 rc8b rollout、4202 single 一次、独立账本。
   - accepted（接近 old/l2pose）→ 该局部层高 patch 足以改变结果，支持“局部层序/高度敏感”；
   - 仍 rejected → patch 不足，再查更大范围层高或释放瞬间状态；不扫摩擦参数。
2. 在决定前不改生成/rollout 协议、不重跑七例、不生成/运行 held-out 或正式批次；正式成功保持 0。
3. 本轮不扩批、不冻结；rc8b 失败与两例重复证据全部保留。

## 6. 产物

- [rc8b 七例审查](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/review.md)
- [初态生成审查](day4-actionchunk-test/results/RC8B_INITIALS_20261105/review.md)
- [cases.csv](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/cases.csv) · [local_recompute.json](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/local_recompute.json) · [verify-dev 日志](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/rc8b-verify-dev.log)
- [视频帧接触表](day4-actionchunk-test/results/RC8B_SEVEN_CASE_20261105/rc8b_contact_sheet.png)
- [rc8b 版本登记](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8b/README.md) · [registration.json](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8b/registration.json)
- **L2 诊断：** [离线定位](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/review.md) · [l2pose 审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/l2pose_review.md) · [重复性与几何](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/repeat_review.md)
- **数据：** [repeat_compare.json](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/repeat_compare.json) · [geometry_check.json](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/geometry_check.json) · [geometry_check.png](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/geometry_check.png)
- **诊断登记：** [l2pose](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-l2pose/registration.json) · [l2pose-repeat1](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-l2pose-repeat1/registration.json) · [rc8b-repeat1](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8b-repeat1/registration.json)
- 前序：[2026-11-05 rc8 冻结暂停交接](2026-11-05-GarmentLab日报%20Stage4%20rc8七例RC与冻结暂停交接.md)

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
- **单变量对照设计（未运行）：** new 初态仅把 #91 的 3×3 网格邻域 z 改为 derived 对应值，其余不变，同 rc8b rollout、4202 single 一次。若 accepted → 局部层高 patch 足以改变结果；若仍 rejected → 该 patch 不足，再查更大范围层高/释放状态。本轮不扩批、不冻结。
- 详见 [重复性与几何审查](day4-actionchunk-test/results/RC8B_L2_DIAG_20261105/repeat_review.md)。

## 10. 暂停点

- **已完成并保留：** rc8b 七例（4/6，未冻结）、L2 离线定位、l2pose 位姿匹配单次（accepted 0.7396/1.5397，中间行为）、两例重复（逐位重现，0.0 差）、局部几何检查。
- **未做：** 单变量局部层高对照（已设计）、七例重跑、协议修改、held-out/正式批次、freeze/gate、任何回执写入。
- **状态：** 正式 Stage 4 成功仍为 **0**；rc8b 失败、l2pose 中间行为、两例重复证据全部保留；无重试、无扩批。
- **恢复入口：** 批准并运行“单变量局部层高对照”（new 初态仅改 #91 3×3 邻域 z 为 derived 值，4202 single 一次），再按其 accepted/rejected 判读；不直接改生成/rollout 协议，不扫摩擦。
