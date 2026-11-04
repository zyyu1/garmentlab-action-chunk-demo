# a5-rc2-pfs1-observation-v2：观测修订后的 4202 single 复验

日期：2026-11-04。本版本保持 `a5-rc2-pfs1` 的物理参数和控制逻辑不变，只修订观测：固定世界顶点有限差分速度、补材料场景读回、分离文件/语义/质量判据、明确 contact 能力边界。新 manifest、新一次性锁、新账本；旧 pfs1 结果保留。

**结论：** 4202 single 复验 `file_complete=true`、`observation_semantics_valid=true`、`quality_status=accepted`、`overall_valid=true`。正式窗口质心 **0.2642 mm**、顶点 P95 **0.3792 mm**，与 pfs1 完全一致；动作 target、recovery/pre-release 状态和 formal 轨迹也与 pfs1 相同（0 差）。因此这是 **观测-only 修订通过**，不是新的物理改善，也不是正式 Stage 4 成功。下一步仍应先审查，再决定是否运行 4302 single；本轮不运行 4302、七例、冻结、held-out。

## 1. 运行与身份

| 项目 | 值 |
|---|---|
| 结果目录 | `results/PFS1_V2_RUN_4202_20261104/day4-a5-rc2-pfs1-observation-v2-20261104-111514-134428` |
| manifest | `d97bf349dc8a7813ab274da52c4a16c69a11b9135717a6851abbd6192cf3b73f`（63 项） |
| config | `bce2d51dd16b50f97653e8436e444a9fd3da927e80d7e56ea053b1ed6c63e9b9` |
| runner | `25c57699c8eef22d8bfe2ba02c1b99e8f51e51891b8fc3dfb2c73d831128a69e` |
| observation | `abd459feb7adcddf4f1adf45d925e710ca65fb0ef0e7af41437222b4adef6d35` |
| 运行 | runner/entry 退出 0；4202 single 一次；新锁；无重试 |
| episode | `passed=True`、12 个动作、`call_horizons` 全 1、无 runtime error |
| 质量 | **accepted**：definition/budget/no_runtime_error/held/released_continuously/geometry/stable 全部 true |
| 证据 | ledger 19/19 文件 SHA256 一致；`evidence/manifest.json` 73/73 一致；runtime source 与候选逐项一致 |
| 旧结果 | pfs1 结果、invalid-attempt 现场均未覆盖 |

`result.json` 的 `formal_day4_success=false`；正式 Stage 4 成功仍为 0。本轮只完成 4202 观测复验。

## 2. 三项判据分开记录

| 判据 | 结果 |
|---|---|
| 文件完整 | 19/19 必需结果/证据文件存在且哈希一致；stage 文件齐全 |
| 观测语义有效 | 12/12 检查 true |
| 质量接受 | **accepted** |
| 总判定 | `overall_valid=true` |

语义检查全部为 true：

- `fd_policy_recorded`、`fd_velocity_valid_present`
- `raw_readback_marked_unvalidated`
- `material_stages_present`、`material_values_match`、`material_binding_match`
- `self_collision_true`、`non_particle_collision_true`
- `solver_effective_boundary_recorded`
- `contact_capability_recorded`
- `release_clock_boundary_recorded`
- `quality_status_recorded`

## 3. 速度语义

- `ClothPrimView.get_velocities()` 原始读回仍保存在 NPZ 中，标记 `readback_velocity_validated=false`、`readback_velocity_status=unvalidated; not used as physical velocity`。
- 物理速度固定为 **世界顶点 backward finite difference**：
  - `fd_method=backward_difference_world_vertices`
  - `fd_time_source=world.current_time at each passive post-step snapshot`
  - `fd_interval=dt = sim_time_s[k] - sim_time_s[previous distinct frame]`
- 完整 release 记录：**484 个有效 FD 区间、1 个无效**（首帧没有前一帧，原因 `no_previous_unique_frame`）。
- 单帧 stage 快照不伪造 FD 速度，标记 `not_computed_single_frame`；原始 readback 仍保留为 unvalidated。
- 旧 pfs1 的 28.76 mm/s 读回不再参与本报告任何物理结论。

## 4. 材料场景读回

`material_readbacks.json` 覆盖构建后、reset 后、初始 settle 后、recovery 后、释放前五个阶段：

| 阶段 | friction | particleFrictionScale | binding | self-collision | non-particle | solver 边界 |
|---|---:|---:|---|---|---|---|
| after_construction | 0.3000000119 | 1.0 | 构造期对象 | — | — | unverified |
| after_reset | 0.3000000119 | 1.0 | `/World/Garment/particleMaterial` | true | true | unverified |
| after_initial_settle | 0.3000000119 | 1.0 | 同上 | true | true | unverified |
| after_recovery | 0.3000000119 | 1.0 | 同上 | true | true | unverified |
| pre_release | 0.3000000119 | 1.0 | 同上 | true | true | unverified |

- 材料 prim：`/World/Garment/particleMaterial`；particle system：`/World/Garment/particleSystem`。
- `particleContactOffset=0.009999999776482582`；`particleGroup=0`；filter 原始属性存在（`filter attrs present in raw readback`）。
- 所有阶段 `expected_ok=true`；如 reset/recovery/pre-release 与登记不一致，运行会在释放前停止。
- **证据边界：** 这些是 scene/USD readback，不是 solver-effective 值；`solver_effective=unverified` 已记录，不能把构造参数或 USD 值当作求解器内部生效证明。
- 旧 pfs1 观测缺口中的材料读回问题在本轮得到补足；这是观测修订的主要完成项。

## 5. 物理结果与 pfs1 一致性

| 项目 | pfs1 | v2 | 差 |
|---|---:|---:|---:|
| 动作 target 最大差 | — | — | **0.0 mm** |
| 动作返回 EE 最大差 | — | — | **0.0 mm** |
| recovery 后状态质心/P95/max | — | — | **0.0 / 0.0 / 0.0 mm** |
| pre-release 状态质心/P95/max | — | — | **0.0 / 0.0 / 0.0 mm** |
| formal 210–330 质心 max | 0.2642 mm | **0.2642 mm** | 0 |
| formal 210–330 顶点 P95 max | 0.3792 mm | **0.3792 mm** | 0 |
| formal 端点质心/P95 | 0.2572 / 0.3668 mm | **0.2572 / 0.3668 mm** | 0 |
| formal 端点旋转 | −0.03344° | −0.03344° | 0 |
| formal z_min | 9.8782 mm | **9.8782 mm** | 0 |
| 质量 | accepted | **accepted** | 同 |

- 首个 0.5 s（位置差分）：质心平均 **11.555 mm/s**、粒子平均 **15.000 mm/s**、角速度 **2.252°/s**，与 pfs1 相同。
- 1.5–8.0 s 持续：质心 **0.595 mm/s**、粒子 **1.375 mm/s**、角速度 **0.104°/s**，与 pfs1 相同。
- 与 RC2 的对照不变：RC2 formal **2.0429 / 4.4141 mm**、quality rejected；v2 的改善仍是 **pfs1 参数**带来的，不是 v2 观测带来的。
- 该一致性（动作/状态/formal 逐值 0 差）支持“v2 仅修订观测、不改变物理/控制”的声明。

## 6. 释放、退让、穿透与粘滞

- release boundary step **1948**、time **32.466668 s**；pre-release step 1947；`sampling_error_steps=1`；boundary attachment/holding false。
- release clock 校验通过；退让向上位移 `0.1460 m`；无隐藏 step、无布料 reset。
- formal z_min **9.8782 mm** > 0，无地面穿透；低于 10 mm contact offset 约 0.122 mm，这是几何量，不是接触力。
- 持续质心 0.595 mm/s、粒子 1.375 mm/s、角速度 0.104°/s，非零；没有证据表明“异常粘滞”，但净漂移较低仍可能反映粒子间摩擦增加后的低滑移状态，不能仅凭单例区分“改善”与“过度锁定”。
- fold 指标、recovery 指标与 pfs1 相同；fold held accepted。

## 7. Contact 能力边界

`contact_capability.json` 明确记录：

- 当前通道只覆盖 **robot-rigid contacts**；
- **cloth-ground force/impulse 不可得**；
- 0 事件 **不是**“无接触”；
- `required_for_acceptance=false`；
- 物理证据使用世界顶点、z_min、有限差分速度。

因此本轮不要求不支持的 cloth-ground 通道产生数据，也没有把接触力/冲量新增为验收门槛。接触机制解释仍受限制。

## 8. 判定与下一步

- **观测修订通过：** 文件完整、观测语义有效、质量 accepted，`overall_valid=true`。
- **物理结论不升级：** v2 与 pfs1 逐值相同，说明本轮只验证观测修订；没有新的物理改善，也不改变“粒子间摩擦敏感性候选”的结论。
- **下一步：** 先审查本报告与 v2 证据；审查通过后，按预登记再决定是否运行一次 4302 single。**本轮未运行 4302、七例 RC、未冻结、未运行 held-out；正式 Stage 4 成功仍为 0。**
- 不宣称地面摩擦已修复；cloth-ground 力/冲量仍不可得。
- 旧 pfs1 结果继续保留为“质量 accepted、观测存在缺口”的开发证据；v2 是观测修订后的复验，不覆盖旧结果。

## 9. 产物

- [comparison.json](comparison.json) · [v2_bins.csv](v2_bins.csv) · [v2_vs_pfs1.png](v2_vs_pfs1.png)
- [evidence_verification.json](evidence_verification.json)
- 结果目录内的 [material_readbacks.json](../PFS1_V2_RUN_4202_20261104/day4-a5-rc2-pfs1-observation-v2-20261104-111514-134428/material_readbacks.json)、[pfs1_semantics.json](../PFS1_V2_RUN_4202_20261104/day4-a5-rc2-pfs1-observation-v2-20261104-111514-134428/pfs1_semantics.json)、[contact_capability.json](../PFS1_V2_RUN_4202_20261104/day4-a5-rc2-pfs1-observation-v2-20261104-111514-134428/contact_capability.json)
- 候选登记：[registration.json](../../a5-rc2-pfs1-observation-v2/registration.json) · [README](../../a5-rc2-pfs1-observation-v2/README.md)
- 旧 pfs1：[pfs1 对照](../D2_E_PFS1_COMPARE_20261104/review.md)
