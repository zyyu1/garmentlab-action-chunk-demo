# a5-rc2-pfs1-observation-v2：pfs1 观测修订版（已运行；观测语义通过）

本版本只修订 **观测完整性**，不改 pfs1 的物理参数和控制逻辑：`particleFrictionScale=1.0`、`friction=0.3`、地面/碰撞/材料绑定、12 个公开动作/命令/horizon、退让目标、evaluator 和 1 mm / 3 mm 阈值均与 `a5-rc2-pfs1` 相同。旧 pfs1 结果继续保留为“质量 accepted、观测存在缺口”的开发证据。

**状态：4202 single 一次已完成。** `file_complete=true`、`observation_semantics_valid=true`、`quality_status=accepted`、`overall_valid=true`。物理结果与 pfs1 逐值相同（动作 target、recovery/pre-release、formal 全 0 差）；这是观测-only 修订通过，不增加新的物理改善，也不是正式 Stage 4 成功。**未运行 4302、七例、冻结或 held-out。**

## 1. 身份

| 项目 | 值 |
|---|---|
| 版本 | `a5-rc2-pfs1-observation-v2` |
| 父版本 | `a5-rc2-pfs1` |
| 父 manifest | `bad4b59a0baecd08bd814bc98cfc28e7a0197fb9fed2effd21282ef40563c51b`（63 项） |
| 新 manifest/deployment | `d97bf349dc8a7813ab274da52c4a16c69a11b9135717a6851abbd6192cf3b73f`（63 项） |
| config | `bce2d51dd16b50f97653e8436e444a9fd3da927e80d7e56ea053b1ed6c63e9b9` |
| runner | `25c57699c8eef22d8bfe2ba02c1b99e8f51e51891b8fc3dfb2c73d831128a69e` |
| observation | `abd459feb7adcddf4f1adf45d925e710ca65fb0ef0e7af41437222b4adef6d35` |
| 4202 初态 | `day4-square-initial-stripfold-20261103-062710-242560`；`result.json` `4472…`、`initial_geometry.npz` `a664…`；不重生 |
| 登记/审计 | [registration.json](registration.json)、[static-audit.json](static-audit.json)、[source-diff.md](source-diff.md) |

## 2. 唯一修订：观测

- **速度：** 原始 `ClothPrimView.get_velocities()` 读回仍保存，但标记 **unvalidated**，不参与物理结论。逐步记录增加世界顶点 **backward finite difference**：`dt` 取相邻不同帧的 `world.current_time` 差，方法/时间源/区间写入 `fd_method`、`fd_time_source`、`fd_interval_s`。单帧阶段不伪造速度，标记 `not_computed_single_frame`。
- **材料读回：** 在 `after_construction`、`after_reset`、`after_initial_settle`、`after_recovery`、`pre_release` 读取材料 prim/path、`particleFrictionScale`、`friction`、particle-system binding、self-collision、non-particle collision、contact offset、particle group 和原始 filter 属性，以及支撑 collider material binding。读回值与登记不一致时在 reset 后/release 前停止。
- **求解器边界：** 材料读回标记为 **scene/USD readback**，`solver_effective` 为 `unverified`；不把构造参数/USD 值当作 solver-effective 证明。
- **语义判据分离：** `file_complete`、`observation_semantics_valid`、`quality_status` 分别记录；原始速度读回不再能让语义检查通过。
- **接触能力：** 输出 `contact_capability.json`：当前只覆盖 robot-rigid；cloth-ground 力/冲量不可得，0 事件不是无接触；`required_for_acceptance=false`。不要求不支持的通道产生数据。

## 3. 离线验证

| 检查 | 结果 |
|---|---|
| 63/63 candidate/deployment manifest | 通过 |
| 父 pfs1 的 58 项非专属/非改动条目 | 不变 |
| 改动 base 文件 | 仅 `a5_recovery.py`、`a5_capture.py`（观测钩子/导入/0.5 s 边界容差） |
| 新文件 | `pfs1_observation_v2.py`、config、runner |
| action/horizon、start_ee、退让目标、release 调用 | 与 pfs1 相同 |
| particleFrictionScale / friction / evaluator / thresholds / 初态 | 不变 |
| D1/D2-C 残留 | 无 |
| `py_compile` / `bash -n` | 通过 |
| 新一次性锁/ledger | `a5-rc2-pfs1-observation-v2-runs`；旧 pfs1 completed marker 不复用 |

源码差异见 [source-diff.md](source-diff.md)。

## 4. 运行结果

只允许 **4202 single** 一次，新 manifest + 新锁；不重试。本次已完成一次，未使用旧 pfs1 的 `completed` 标记。

| 项目 | 结果 |
|---|---|
| 结果目录 | `results/PFS1_V2_RUN_4202_20261104/day4-a5-rc2-pfs1-observation-v2-20261104-111514-134428` |
| 运行 | runner/entry 退出 0；12 个动作；无 runtime error |
| `file_complete` | **true**（19/19 必需文件；stage 齐全） |
| `observation_semantics_valid` | **true**（12/12 检查） |
| `quality_status` | **accepted** |
| `overall_valid` | **true** |
| formal 210–330 | 质心 **0.2642 mm**、顶点 P95 **0.3792 mm**；与 pfs1 相同 |
| 动作 target vs pfs1 | **0.0 mm**；EE 返回差 **0.0 mm** |
| recovery / pre-release 状态 vs pfs1 | **0.0 / 0.0 / 0.0 mm** |
| 首个 0.5 s | 质心 **11.555 mm/s**、粒子 **15.000 mm/s** |
| 1.5–8.0 s | 质心 **0.595 mm/s**、粒子 **1.375 mm/s**、角速度 **0.104°/s** |
| 材料读回 | friction **0.3000000119**、particleFrictionScale **1.0**；binding `/World/Garment/particleMaterial`；self/non-particle true；五个阶段全部 expected_ok |
| FD 速度 | 484 个有效区间、1 个首帧无效；raw readback 标记 unvalidated |
| 证据 | ledger 19/19、`evidence/manifest.json` 73/73、runtime source 全部匹配 |

完整报告：[v2 对照](../results/D2_E_PFS1_V2_COMPARE_20261104/review.md) · [evidence_verification](../results/D2_E_PFS1_V2_COMPARE_20261104/evidence_verification.json) · [material_readbacks](../results/PFS1_V2_RUN_4202_20261104/day4-a5-rc2-pfs1-observation-v2-20261104-111514-134428/material_readbacks.json)。

## 5. 通过条件与边界

- 通过：原几何全程通过、质心 ≤1 mm、顶点 P95 ≤3 mm、release/retreat/证据完整，且上述语义检查通过。
- 通过后仍只作为 **4202 单例审查通过**；再决定是否扩展 4302 single。
- 不运行七例 RC、不冻结、不运行 held-out；正式 Stage 4 成功计数不增加。
- 不宣称地面摩擦已修复；本轮只做 pfs1 的观测重验。
- cloth-ground 力/冲量不是新增验收门槛。
