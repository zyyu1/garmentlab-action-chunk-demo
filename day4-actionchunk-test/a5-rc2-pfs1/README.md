# a5-rc2-pfs1：粒子间摩擦缩放敏感性候选（已运行；质量 accepted，观测 caveat）

本候选从 **RC2 原流程**派生，只把活动 `ParticleMaterial` 的 **`particleFrictionScale` 从 0.0 改为 1.0**。`friction` 保持 0.3；地面、碰撞、材料绑定、12 个公开动作/目标/命令/horizon、退让目标、评价器和 1 mm / 3 mm 阈值不变。

**状态：已登记、离线验证通过、4202 single 已运行一次。** episode `passed=True`，质量 **accepted**；但粒子速度读回未通过一致性校验，且没有运行时材料读回。**不扩展 4302 single**，不跑七例、不冻结、不跑 held-out；正式成功计数仍为 0。没有 D1-120 的 120 步等待，也没有 D2-C 的 preopen、第二次 open 抑制或释放顺序改动。

**后续观测修订（2026-11-04）：** [a5-rc2-pfs1-observation-v2](../a5-rc2-pfs1-observation-v2/README.md) 已单次复验 4202：`file_complete=true`、`observation_semantics_valid=true`、质量 accepted、`overall_valid=true`；物理结果与本 pfs1 逐值相同，说明只修订了观测。旧 pfs1 结果继续保留，不被覆盖。详见 [v2 对照](../results/D2_E_PFS1_V2_COMPARE_20261104/review.md)。

## 1. 身份

| 项目 | 值 |
|---|---|
| 版本 | `a5-rc2-pfs1` |
| 父版本 | `stage4-a5-rc2` |
| 父 manifest | `39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d`（60 项） |
| 父 candidate | `10a6cb452b9fafd5907f245b68fd02d49c7af1e12fa6cb0f755f1791a5af27a5` |
| candidate manifest | `bad4b59a0baecd08bd814bc98cfc28e7a0197fb9fed2effd21282ef40563c51b`（63 项） |
| deployment manifest | 与 candidate manifest 相同 63 项；SHA256 `bad4b59a0baecd08bd814bc98cfc28e7a0197fb9fed2effd21282ef40563c51b` |
| config | `2d72a40565b3f63269fff861231255a45318618ed969bc7cf132bd041c34d32c` |
| runner | `3f9e38e3dde535d754ab01f3319d1914872bd669d1ebf3d62e6cef6c625dfa80` |
| observation module | `9482847357eade07b27799134379fdf611b5e9db3dbd5fa3dea8df0acb40ed04` |
| 4202 初态 | `day4-square-initial-stripfold-20261103-062710-242560`；`result.json` `4472f4df…`，`initial_geometry.npz` `a6646d66…`；**不重新生成** |
| 登记/审计 | [registration.json](registration.json)、[static-audit.json](static-audit.json)、[source-diff.md](source-diff.md) |

## 2. 唯一物理改动

`a5_recovery.py` 的活动 `ParticleMaterial` 包装器：

```python
k['particle_friction_scale'] = 1.  # was 0.
```

- **语义：** `particleFrictionScale` 控制**粒子间摩擦缩放**，不是地面摩擦，也不称为“恢复地面摩擦”。
- **假设：** 粒子间摩擦变化可能通过层间接触、折形或释放状态影响后续整体滑移。
- **若无变化：** 只能说明本次设置下未观察到敏感性，不能排除其他摩擦/接触机制。
- **范围：** 参数从 episode 开始生效，影响 initial dynamics、recovery、fold、release 和 retreat；**不是“仅释放后接触对照”**。
- **初态：** 原 4202 初态文件复用，不重新生成；其哈希保持不变，但新 episode 从第一步起使用 1.0。
- **L1：** `a5_l1.py` 保持 RC2（其中仍为 0.0），本候选不运行 L1。

## 3. 观测与阶段

新增 [pfs1_observation.py](app/pfs1_observation.py) 只做被动读取，不增加 `world.step`、不调用控制、不写布料：

- 阶段文件 `pfs1_stages/`：
  - `initial_loaded`：场景构建及初态载入后；
  - `after_recovery`：recovery 完成后；
  - `pre_release`：最终释放前；
  - `release_boundary`：首个 detached 物理步。
- 每步文件：
  - `pfs1_release_steps.npz/json`：release action 和 331 步 trace；
  - `pfs1_first_0_5s.npz`：释放边界后前 0.5 s；
  - `pfs1_formal_210_330.npz`：原正式窗口；
- 每阶段含顶点、**实际粒子世界速度**（view 读回；缺失时标记 `velocity_present=false` 并令运行不完整）、EE、关节、夹爪和 attachment 状态。
- `pfs1_release_clock.json` 记录 release t=0 定义：pre-release 最后 attached state；首个 detached 物理步为 boundary sample；RC2 原流程没有零步 post-disable sample，必须报告 pre→boundary 的 step/time 采样区间，不能声称精确瞬间。

## 4. 离线验证

| 检查 | 结果 |
|---|---|
| 63/63 candidate/deployment manifest | 通过 |
| 父 60 项中 58 项不变 | 通过；仅 `a5_recovery.py`、`a5_capture.py` 改变 |
| action/horizon 行 | RC2 与候选 20/20 相同 |
| `start_ee` / 退让目标 / `release(target)` | 相同 |
| D1/D2-C 残留 | 无 `hold_open_for_steps`、`internal_delay`、`release_order`、`preopen`、`suppressed_open` |
| `a5_l1.py` / evaluator / candidate / thresholds | 未变；L1 不运行 |
| 初态哈希 | 未变 |
| `py_compile` / `bash -n` | 通过 |
| 静态审计 | [static-audit.json](static-audit.json) 全部布尔检查 true |

源码差异分类与完整 diff 见 [source-diff.md](source-diff.md)：唯一物理参数改动是 `particle_friction_scale 0→1`；其余为被动观测、输出前缀和候选身份文件。

## 5. 运行结果（4202 single，一次）

只允许 **4202 single**，一次运行；runner 使用 `completed` 标记和 `PFS1_ALLOW_RERUN` 显式重跑门。本轮已完成一次；无效的第一次观测尝试保留在 `results/PFS1_INVALID_OBS_ATTEMPT_20261104/`，不计为物理运行。

| 项目 | 结果 |
|---|---|
| 结果目录 | `results/PFS1_RUN_4202_20261104/day4-a5-rc2-pfs1-20261104-102101-983000` |
| 运行 | tmux 单次；runner 退出 0；entry 评估退出 0；无重试 |
| episode | `passed=True`、12 个动作、`call_horizons` 全 1、无 runtime error |
| 质量 | **accepted**；`geometry_entire_window=True`、`stable=True` |
| 正式窗口（evaluator max） | 质心 **0.2642 mm**、顶点 P95 **0.3792 mm**（RC2：2.0429 / 4.4141 mm） |
| 首个 0.5 s（位置差分） | 质心 **11.555 mm/s**、粒子 **15.000 mm/s**、角速度 **2.252°/s** |
| 持续 1.5–8.0 s（位置差分） | 质心 **0.595 mm/s**、粒子 **1.375 mm/s**、角速度 **0.104°/s** |
| 证据 | `evidence/manifest.json` 73/73 哈希一致；ledger 15/16，缺 `contact_report.json`（非必需） |
| 观测 caveat | 速度读回不一致；无运行时材料读回（见下） |

**速度读回问题：** `ClothPrimView.get_velocities()` 的 formal 读回粒子平均 28.76 mm/s，而同一 physics view 的世界顶点位置差分仅 1.29 mm/s；读回场在 2 s 内几乎不变（首尾相关 0.998），与位置差分向量相关约 −0.006。EE 静止、attachment/holding 均为 false，不能由机器人运动解释。该读回**不能当作实际粒子速度或冲量**；本报告所有速度改用世界顶点有限差分。原始读回保留在 NPZ 中并标记 unvalidated。

**材料读回缺口：** 源码确实把构造参数设为 `particle_friction_scale=1.0`，但没有保存运行时 `particleFrictionScale`/`friction`/self-collision/particle collision filter 的读回；D2-A 的 `0.3 / 0.0` 是未修改基线，不是 pfs1 运行时证据。不能据此声称 solver-effective 值已被读回确认。

**合规缺口：** 速度读回一致性检查和运行时材料读回本应在运行前完成。第一次尝试因 API 不存在被停止；第二次改用 `get_velocities()` 后直接执行，没有在运行前验证读回与位置差分一致；材料读回也未实现。这是观测/预检缺口，不能事后补成“已验证”。物理运行和几何结果保留，但扩展前必须修正观测设计并重新登记。

完整对照与 caveat：[review.md](../results/D2_E_PFS1_COMPARE_20261104/review.md) · [comparison.json](../results/D2_E_PFS1_COMPARE_20261104/comparison.json) · [velocity_readback_diagnostic.json](../results/D2_E_PFS1_COMPARE_20261104/velocity_readback_diagnostic.json) · [evidence_verification.json](../results/D2_E_PFS1_COMPARE_20261104/evidence_verification.json)。

## 6. 判定与边界

- **几何/评价器：通过。** 原几何全程通过、质心 0.2642 mm ≤1 mm、顶点 P95 0.3792 mm ≤3 mm，质量 accepted；这是候选改善证据。
- **观测完整性：不完整。** 速度读回不可用、运行时材料读回缺失；按“证据异常时保留现场并停止”的边界，**不扩展 4302 single**，不重跑 pfs1，不扫描参数。
- 动作 target 与 RC2 不同：fold 约 +2.0 mm、退让约 +2.0 mm；这是 recovery 后重新计算 pick/yaw 的结果，不是同一 target 对照。
- 本轮只跑 4202 single；不跑七例 RC、不冻结、不跑 held-out；正式 Stage 4 成功计数仍为 0。
- 即使几何通过，也不能宣称地面摩擦问题已修复；本轮只检验粒子间摩擦缩放的敏感性。
