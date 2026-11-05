# recovery-hold120 单次诊断：accepted，候选衔接改进（需审查后再扩展）

**结论：** 在 recovery 正常完成后固定保持 **120 步 / 2.0 s**，4202 single 从 rc8b 的 **rejected 7.4809/11.5382 mm** 变为 **accepted 0.2374/0.3484 mm**（stationary 6.69 mm，无几何失败；old 为 0.2642/0.3792）。保持期间世界顶点运动已接近零（质心 ~0.0001 mm/s、粒子 P95 ~0.007 mm/s、旋转 ~1e-5°、EE 漂移 0、附件全关），没有“运动衰减”可观察；额外 120 个静态物理步改变了后续 fold 结果。单次 accepted 只能作为候选衔接改进，需审查后再扩展；不能据此认定接触/应力机制，也不计入正式 Stage 4 成功。

## 1. 运行身份与审计异常

| 项目 | 值 |
|---|---|
| 候选 | `a5-rc8b-recovery-hold120`；manifest `b61fd56e…`（63 项；60 项与 rc8b 相同） |
| 父版本 | rc8b `cce573dd…` |
| 初态 | rc8b 新 4202 `…015817-115841`；protocol `stage4-initial-v2-task-scoped`，scale 1.0 |
| 唯一干预 | `a5_recovery.py` 新增 `run_recovery_hold(steps=120)`；其余 rollout/评价/资产同 rc8b |
| 运行 | `day4-a5-rc2-pfs1-observation-v2-20261105-064625-336724`，single 一次；无重试 |
| 下载核验 | **112/112** 哈希一致 |
| 质量 / 证据 | **accepted**；`HOLD120_CASE_AUDIT` 全部通过（`recovery_hold=true`、`initial_protocol=true`） |
| 退出码 | **entry=0，runner=3**：runner 在 audit 打印阶段触发 `KeyError: 'recovery_hold'`（audit 的 out 缺该键），属于审计脚本缺陷；结果文件已完整写出。修正 audit 后对**同一结果**重跑审计（不推进物理）→ exit 0、`overall_valid=true`。未重跑仿真。 |

**证据完整性：** hold trace、事件、动作、评价、release 窗口均存在；审计缺陷不影响仿真记录，但本轮记录 runner 非零退出，不把该 run 标成干净完成。

## 2. 保持阶段（121 帧 / 120 区间 / 2.0 s）

事件：`recovery_retreat_end` step 1027；`recovery_hold_begin` step 1028 / t=17.166668；`recovery_hold_end` step 1148 / t=19.166668；`fold_observation` step 1148（与 hold_end 同一时刻）。每步 `holding=false`、逻辑附件关闭、command holding=false、所有附件槽关闭；控制目标恒定；`b._env.step()` 恰好 120 次；无位置/速度重置、无控制调用、无材料变更。

| 窗口 (s) | 质心速度 (mm/s) | 粒子 P95 (mm/s) | 旋转 (°) | 质心位移 (mm) | z_p95 变化 (mm) | EE 漂移 (mm) |
|---|---:|---:|---:|---:|---:|---:|
| 0.0–0.5 | 0.0001 | 0.0074 | 1e-5 | 1.5e-5 | 0.0 | 0.0 |
| 0.5–1.0 | 0.0001 | 0.0072 | 1e-5 | 5e-6 | 0.0 | 0.0 |
| 1.0–1.5 | 0.0001 | 0.0054 | 0.0 | 2.2e-5 | 0.0 | 0.0 |
| 1.5–2.0 | 0.0001 | 0.0054 | 1e-5 | 9e-6 | 0.0 | 0.0 |

- 保持开始时运动已接近零，**没有可观察的衰减过程**；2 s 内几何与 EE 基本不变。
- 因此本结果**不能**解释为“静置让残余运动衰减”；额外静态步改变了下游 fold 行为，具体机制未隔离。

## 3. 后续流程 vs rc8b 4202

| 指标 | old rc8（0.0 初态） | new rc8b（1.0） | **hold120** |
|---|---:|---:|---:|
| 质量 | accepted | rejected | **accepted** |
| 质心 / P95 (mm) | 0.2642 / 0.3792 | 7.4809 / 11.5382 | **0.2374 / 0.3484** |
| stationary half (mm) | 7.24 | 29.91 | **6.69** |
| 首次失败 | 无 | step 249 | **无** |
| fold extent (m) | 0.2283 × 0.4199 | 0.1958 × 0.4078 | **0.2252 × 0.4190** |

- fold_yaw 与 new 差 **4e-5°**；公开动作目标最大差 **0.0014 mm**、yaw 4e-5°；专家路径几乎相同。
- pre-release / release boundary 与 new 的顶点差 max **0.98 / 1.00 mm**、mean 0.22 mm；fold extent 恢复到接近 old。
- 释放后质心速度：hold 前 1.5 s 约 4 mm/s（释放瞬态），1.5–2.0 s 出现 10.98 mm/s 单窗（释放过渡），随后衰减到 1.62 → 0.77 → 0.53 → 0.38 mm/s；new 持续 ~4 mm/s，因此 hold 没有进入持续滑移。
- 正式窗口全部通过；无几何失败帧。release_retreat 完成仍为 step 0，采样窗口/评价器/阈值未改。

## 4. 判读（按预登记 C）

- **accepted 且证据完整（扣除审计脚本缺陷后）：** 固定保持 120 步可作为**候选衔接改进**，等待审查后再扩展；不计入正式成功。
- 保持期间运动已稳定，后续仍改变结果 → 不是“静置不足/运动衰减”问题；但也不能据此认定接触、层序或应力机制。额外 120 个静态步的作用未被隔离。
- 不扩大保持时长、不扫摩擦、不扩展 seed、不重跑七例、不冻结、不跑 held-out。

## 5. 产物

- [hold120_compare.json](hold120_compare.json)
- 运行：[hold120_run/…064625-336724](hold120_run/day4-a5-rc2-pfs1-observation-v2-20261105-064625-336724)
- 保持轨迹：`recovery_hold_trace.npz`、`recovery_hold_metadata.json`
- 审计：[postrun_semantics.json](hold120_run/a5-rc8b-recovery-hold120-runs/postrun_semantics.json)
- 版本登记：[a5-rc8b-recovery-hold120/registration.json](../../a5-rc8b-recovery-hold120/registration.json)
