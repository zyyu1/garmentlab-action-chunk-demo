# 4302 single 扩展对照审查（a5-rc2-pfs1-observation-v2-4302）

**结论：** 4302 single 一次运行通过全部门槛：`file_complete=true`、`observation_semantics_valid=true`、质量 **accepted**、`overall_valid=true`；几何全窗口通过；正式 210–330 窗口质心 **0.2390 mm**、顶点 P95 **0.3524 mm**（RC2 4302 single：1.9102 / 4.1231 mm），低于 1 mm / 3 mm。恢复、释放与粘滞检查通过。这是**单 seed 单次**结果，不构成跨 seed 统计结论，也不确认具体摩擦机制；正式 Stage 4 成功仍为 0。

## 1. 运行与身份

| 项目 | 值 |
|---|---|
| 结果目录 | `day4-a5-rc2-pfs1-observation-v2-20261104-201557-235290` |
| 远端目录 | `<remote-root>/day4-a5-rc2-pfs1-observation-v2-20261104-201557-235290` |
| 版本 / 扩展 | `a5-rc2-pfs1-observation-v2` / `4302-single` |
| manifest | `6d1958f5…`（63 项；61 项与 v2 逐字节相同，2 项为登记/编排） |
| config / runner | `577931aa…` / `550efa65…` |
| 初态 | `day4-square-initial-stripfold-20261103-094143-137994`；`result.json` `1bed437f…`、`initial_geometry.npz` `1c27514f…`；未重生 |
| 运行 | tmux 单次；runner/entry 退出 0；`PFS1_V2_EXT_SINGLE_RUN_COMPLETE`；无重试 |
| 动作 | 12 个公开动作；labels/commands/horizons 与 RC2 完全一致 |
| 账本 | `a5-rc2-pfs1-observation-v2-4302-runs`：attempts 2 行（started + finished）、journal 1 个、`completed` 已写入；v2 的 4202 完成标记未复用、未改动 |
| 下载核验 | 104/104 文件 remote↔local SHA256 全部一致 |

## 2. 文件与证据完整性

| 检查 | 结果 |
|---|---|
| 必需文件（19 项 + 4 个 stage） | 全部存在 |
| ledger 文件哈希 | **19/19**，`ledger_bad=[]` |
| `evidence/manifest.json` | **73/73**，`evidence_bad=[]` |
| 结果目录文件数 / 大小 | 104 / 17 MB |
| `errors` | `[]` |
| `entry_assess_exit` | 0 |

## 3. 观测语义

12/12 语义检查全部通过：FD 速度策略已记录、release 区间 FD 有效样本存在、raw readback 标 unvalidated、五阶段材料读回齐全且值匹配、self/non-particle collision 为 true、`solver_effective` 标 unverified、contact 能力边界记录、release 时钟边界记录、质量状态记录。

材料读回（scene/USD readback）：

| 阶段 | friction | particleFrictionScale | binding | self / non-particle |
|---|---:|---:|---|---|
| after_construction | 构建期证据（非 live 读回） | — | — | — |
| after_reset | 0.3000 | 1.0 | `/World/Garment/particleMaterial` | true / true |
| after_initial_settle | 0.3000 | 1.0 | 同上 | true / true |
| after_recovery | 0.3000 | 1.0 | 同上 | true / true |
| pre_release | 0.3000 | 1.0 | 同上 | true / true |

`raw readback` 仍标 unvalidated；所有物理速度用世界顶点有限差分。cloth-ground 力/冲量不可得，0 事件不是无接触，不是新增门槛。

## 4. 评价器门槛

| 检查 | 结果 |
|---|---|
| `checks.definition / budget / no_runtime_error` | true / true / true |
| `held`（保持） | true（位置 14.16 mm、臂速 0.00215 rad/s、锚点 2.13 mm） |
| `released_continuously`（释放） | true |
| `geometry_entire_window`（几何全窗口） | **true**；`failed_geometry_frames=[]` |
| `stable` | **true** |
| 质心漂移上限 | **0.2390 mm ≤ 1 mm** |
| 顶点 P95 上限 | **0.3524 mm ≤ 3 mm** |
| 其余稳定量 | 顶点最大 0.3808 mm；速度 P95 3.438 mm/s、最大 9.990 mm/s |

`first_window_geometry` 与 `final_geometry` 的 9 项几何检查（crossed/overlap/alignment/material_target/stationary_half/free_edge/fold_extent/tangent_extent/height）全部 true；`crossed_fraction=1.0`，IoU **0.6617 → 0.6494**，对齐 6.185 / 6.181 mm。

## 5. 与 RC2 4302 single 对照

| 指标 | RC2 4302 single | pfs1-v2 4302 | 变化 |
|---|---:|---:|---:|
| 评价器质心漂移 | 1.9102 mm | **0.2390 mm** | −87.5% |
| 评价器顶点 P95 | 4.1231 mm | **0.3524 mm** | −91.5% |
| trace 210–330 质心 | 1.9102 mm | 0.2390 mm | — |
| trace 210–330 P95 | 4.1231 mm | 0.3509 mm | — |
| 质量 | rejected | **accepted** | — |
| fold crossed | 1.0 | 1.0 | 相同 |
| fold extent (m) | 0.2847 × 0.4360 | 0.2688 × 0.4332 | 略窄 |
| fold z_p95 | 68.14 mm | 68.92 mm | +0.78 mm |
| held 位置误差 | 15.12 mm | 14.16 mm | −0.96 mm |
| held 锚点间隙 | 2.20 mm | 2.13 mm | −0.07 mm |
| 质量状态 | rejected（稳定性） | accepted | — |

fold 动作目标与 RC2 不同：recovery 末态相对 RC2 平移 **10.27 mm**（P95 10.94 mm、旋转 −0.188°、刚体 RMS 0.0006 mm），expert 按未改逻辑从恢复后状态重算目标，导致 fold 目标差 7.7–8.0 mm、yaw −3.28°；recovery 动作差 ≤0.37 mm，`rec_spread`/`rec_release` 为 0。这是候选改变 recovery 动力学后的**端到端**对比，不是“同一动作、只改摩擦”的受控对比。

## 6. 释放、恢复与粘滞

- **恢复**：recovery 后布料展平，extent 0.4791×0.4791 m，刚性残差 6.42 µm，z_p95 9.900 mm；与 RC2 形状一致、位置平移约 10.27 mm。
- **释放边界**：pre_release step 2380（holding=true、attached=true、aperture 1.7e-8 m）→ boundary step 2381（holding=false、attachment=false，z_min 9.8676 mm）→ released sample step 2388。这里有两个不同量，分开写清：**边界定位精度 `sampling_error_steps=1`**（实际解除发生在 2380→2381 之间，只能报区间）；**released sample 延迟 7 步**（2381→2388，约 116.7 ms，对应 OPEN 完成到 retreat 命令发出之间的采样点），不是边界定位误差。
- **释放后 0.5 s**：31 帧 / 0.500 s；粒子平均 **15.70 mm/s**、质心 **12.40 mm/s**（最大 34.30 / 32.00）；首区间 20.06 / 10.97 mm/s；方向 −22.1°。
- **持续段 1.5–8.0 s**：质心 **0.372 mm/s**、粒子 **0.659 mm/s**、角速度 **0.092°/s**；0.5 s 分箱在 1.5–8.5 s 稳定在 0.32–0.44 mm/s 质心，无继续衰减或增大。
- **粘滞检查**：release 后 485 步内 `attachment_enabled_any` / `logical_attached` / `holding` / `enabled_slots` **全部 false**；OPEN 命令锁存恰为前 **10 步**且之后不再出现；夹爪 aperture 1.7e-8 → 0.080 m、state 2 → 0；retreat 期间布料质心位移与 EE 位移方向余弦 **−0.169**（布料未跟随 EE），幅值比 1.41 来自释放初期布料自身松弛（约 2.6 mm）与 EE 刚起步（约 1.9 mm），非粘附；EE 到顶后静止，布料仍以约 0.37 mm/s 滑移；z_min 全程 9.867 mm，无地面穿透，低于 10 mm contact offset 约 0.133 mm（几何事实，不是接触力）。

## 7. 解释与限制

1. **两个 dev seed 各一次 single 均通过质量门槛**（4202：0.2642/0.3792 mm；4302：0.2390/0.3524 mm）。这支持“候选在该初态族上改善稳定性”，但仍是**两次单例**，不能替代七例 RC，也不是跨 seed 统计结论。
2. **不是固定动作对照**：候选改变 recovery 动力学后，recovered 状态平移 10.27 mm，expert 按未改逻辑重算 fold 目标（差约 8 mm）。因此 4302 的改善是端到端结果，不能拆成“同一轨迹 + 摩擦效应”。
3. **机制未确认**：材料读回只是 scene/USD 值（0.3 / 1.0），`solver_effective` 仍 unverified；没有 cloth-ground 力/冲量。不能宣称“地面摩擦已修复”或确认粒子间摩擦缩放就是唯一原因。
4. **单例边界**：只跑了一次 4302 single，无重试；失败/部分结果保留机制未触发（本次成功）。z_min 低于 contact offset 0.13 mm 是几何证据，不等于接触状态或冲量。

## 8. 判定与下一步

按预登记判定表：**质量接受且证据完整 → 固定最终候选，准备完整七例 RC**。

- 本轮**不**运行七例 RC、不冻结 RC2、不跑 held-out/正式批次、不扫参数、不重跑 4202/4302。
- 正式 Stage 4 成功计数仍为 **0**；本次只把“候选改善”从 4202 单例扩展到 4302 单例。
- 若继续：下一步应是明确指令下的七例 RC 准备（例表、身份、上限与失败处理），而不是自动扩批。

## 9. 产物

- [comparison.json](comparison.json)（完整对照）
- [summary.json](summary.json)（关键数值）
- [windows.csv](windows.csv)、[bins.csv](bins.csv)
- [sticking_checks.json](sticking_checks.json)
- [download_audit.json](download_audit.json)（104/104 文件哈希核验；[远端清单](download_audit_remote_hashes.txt)）
- [pfs1_v2_4302_windows.png](pfs1_v2_4302_windows.png)（释放后速度/转速/高度）
- [formal_compare_4302.png](formal_compare_4302.png)（正式窗口质心/P95 vs RC2）
- 原始结果：[day4-a5-rc2-pfs1-observation-v2-20261104-201557-235290](day4-a5-rc2-pfs1-observation-v2-20261104-201557-235290)
- 版本登记：[a5-rc2-pfs1-observation-v2-4302](../../a5-rc2-pfs1-observation-v2-4302/README.md)
