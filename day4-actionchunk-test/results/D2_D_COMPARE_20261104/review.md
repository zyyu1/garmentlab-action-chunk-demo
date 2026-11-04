# D2-D：D2-C 释放顺序对照（4202 single，单次运行）

日期：2026-11-04。D2-C 独立版本 `a5-rc2-d2c-release-order` 在远端仅运行一次 4202 single；episode `passed=True`，诊断审计 `complete=True`，质量 `rejected`（稳定性）。**正式 Stage 4 成功仍为 0。**

## 1. 运行与身份

| 项目 | 值 |
|---|---|
| 结果目录 | `day4-a5-rc2-d2c-release-order-20261104-090032-412133` |
| D2-C manifest | 66 项 `778935ab…`（本地/远端一致） |
| D2-C config | `96acc5fa…` |
| 运行入口 | [run-a5-rc2-d2c-release-order.sh](../../a5-rc2-d2c-release-order/app/run-a5-rc2-d2c-release-order.sh) |
| 远端预检 | `D2C_PREFLIGHT_OK 66`；`PREFLIGHT_ONLY_OK`；未启动仿真 |
| tmux 单次运行 | 退出码 0；`completed` 标记已写入；无重试 |
| episode | `passed=True`、`errors=[]`、12 个公开动作、horizon 12 |
| 诊断审计 | `complete=True`、`quality=rejected`、release_rows=277、contact_events=0 |
| 总步数 | `absolute_step=2219`，等待 world 1955–2075，trace 331 步；与 D1 完全一致 |

运行账本：[attempts.jsonl](../D2_D_RUN_4202_20261104/attempts.jsonl)、[run_ledger.json](../D2_D_RUN_4202_20261104/day4-a5-rc2-d2c-release-order-20261104-090032-412133/run_ledger.json)；预检/退出码：[预检日志](../D2_D_RUN_4202_20261104/a5-rc2-d2c-preflight.log)、[console.log](../D2_D_RUN_4202_20261104/a5-rc2-d2c-console.log)、[exit](../D2_D_RUN_4202_20261104/a5-rc2-d2c-console.exit)。

**证据完整性：** ledger 列出的全部证据文件本地 SHA256 一致；`result.code_files` 与 66 项 manifest 完全一致；`success_meta.manifest_sha256=778935ab…`；初态哈希 `4472f4df…`/`a6646d66…`。

## 2. 预运行补查

### 2.1 开爪与附着一致性

D2-C 的 preopen 记录：

| 项目 | 值 |
|---|---:|
| preopen world steps | 1945 → 1955（10 步） |
| `preopen_state_checks` | 10/10 |
| `holding_before` / `holding_after_preopen` | true / true |
| `attachment_enabled_before` / `after_preopen` | true / true |
| `gripper_aperture` | 1.15e-8 → 0.0800 |
| `suppressed_second_open` | true |
| attachment disabled step | 1955（preopen 结束同一步） |

`preopen_while_attached()` 在每一步 `world.step` 后同时检查 `active.holding`、`active.attachment_enabled()`、`control.holding`、`control.attachment_enabled()`，并调用 `control.assert_exclusive()`。`audit_episode_evidence.py` 与 `episode_evidence.py` 和 D1 字节相同，全程 `state_consistent` 检查未关闭。preopen 期间 `gripper_state` 仍是命令 latch=2，但实际夹爪开合量已从 0 增至 0.08 m；这是预登记的“夹爪张开、布料仍持住”阶段，holding 与真实附件状态始终一致。

### 2.2 释放边界采样

| 运行 | 最后持布状态 | 释放边界 | 首个自由物理步 | 采样误差 |
|---|---:|---:|---:|---|
| D1 | anchor 1943（attached） | 1944 首个 detached state | 1944 | 边界落在 1943→1944 之间；**1 步（16.7 ms）** |
| D2-C | preopen 末态 1953（attached） | `released` sample 1953（零物理步，detached） | 1954 | **0 步**；sample 与最后 preopen state 同 step/time |

D2-C `release_order` 记录：`preopen_last_state_observed_step=1953`、`release_boundary_observed_step=1953`、`released_sample_observed_step=1953`、`release_boundary_sample_step_delta=0`、`first_wait_state_observed_step=1954`。因此 D2-C 的释放瞬间有零步边界 sample，**没有把首个全关 state 当作精确解除瞬间**；首个全关 state 是 1954，晚一步。D1 没有这种零步 sample，t=0 取 anchor，首个自由物理步为 +1 步，报告 16.7 ms 采样区间。

## 3. 干预前一致性

| 检查 | 结果 |
|---|---|
| 12 个公开动作 label/command | 完全相同 |
| action target 最大差 | **0.0** |
| 12 个动作返回 EE 最大差 | **0.0** |
| 前 11 个动作 | 完全相同 |
| `call_horizons` / 总数 | 12 / 12，均为 1 |
| release anchor 顶点最大差 | **0.0** |
| anchor EE 最大差 | **0.0** |
| anchor 9 关节最大差 | **0.0** |
| anchor time / observed step | 0 / 0 |
| D1 `pre_release_hold` 末帧 = anchor | true |
| D2-C `pre_release_hold` 末帧 = anchor | true |

**结论：干预开始前轨迹逐位一致**，差异从 preopen/释放阶段开始。

## 4. release t=0 布料状态与速度（单独比较，不要求相同）

t=0 定义：D1 为 `release_start_anchor`（最后 attached state）；D2-C 为最后一个 attached preopen state。二者都是附件解除前的状态。

| 指标 | D1 | D2-C | D2-C − D1 |
|---|---:|---:|---:|
| 质心位置差 | — | — | **0.01125 mm** |
| 顶点 P95 差 | — | — | **0.02934 mm** |
| 顶点最大差 | — | — | **0.03747 mm** |
| 2D 旋转差 | — | — | **−0.00455°** |
| 刚体 RMS 差 | — | — | **0.00493 mm** |
| z min / max | 0.009877 / 0.072324 m | 0.009877 / 0.072321 m | 约 0 / −0.000003 m |
| 粒子平均速度 | 0.26168 mm/s | 0.25967 mm/s | −0.00201 mm/s |
| 质心速度 | 0.04078 mm/s | 0.05473 mm/s | +0.01395 mm/s |
| 角速度 | 0.000235 °/s | 0.007504 °/s | +0.00727 °/s |

速度由各运行最后两个 attached state 的 backward difference 计算（D1 用 `pre_release_hold` 末两帧；D2-C 用最后两个 preopen state）。**释放 t=0 的布料位置几乎相同（≤0.037 mm），速度差异仅在 0.01 mm/s / 0.007°/s 量级。**

## 5. 释放后窗口

`release_transition`：t=0（最后 attached）→ 首个自由物理步（+1 步）。`free_*`：从首个自由物理步起算，按 release elapsed steps 对齐，D1 与 D2-C 使用相同定义。

| 窗口 | D1 质心 mm | D2-C 质心 mm | Δ质心 | D1 P95 mm | D2-C P95 mm | ΔP95 |
|---|---:|---:|---:|---:|---:|---:|
| release transition（1 步） | 0.1840 | 0.1835 | −0.0005 | 0.7420 | 0.7474 | +0.0054 |
| free 0–30 步（0–0.5 s） | 1.9092 | 1.9119 | +0.0027 (+0.14%) | 12.2286 | 12.2044 | −0.0242 (−0.20%) |
| free 30–120 步 | 1.4730 | 1.4284 | **−0.0445 (−3.02%)** | 3.2355 | 3.1499 | **−0.0856 (−2.65%)** |
| free 0–120 步 | 2.8069 | 2.7508 | −0.0561 (−2.00%) | 13.0361 | 12.9798 | −0.0562 (−0.43%) |
| retreat phase（action-relative） | 2.4389 | 2.3699 | −0.0690 (−2.83%) | 5.2665 | 5.1996 | −0.0669 (−1.27%) |
| formal 210–330（action-relative） | 2.0409 | 1.9823 | **−0.0586 (−2.87%)** | 4.4134 | 4.3426 | **−0.0710 (−1.60%)** |

速度：

| 窗口 | D1 粒子平均 mm/s | D2-C 粒子平均 mm/s | D1 质心速度 mm/s | D2-C 质心速度 mm/s |
|---|---:|---:|---:|---:|
| release transition | **17.4197** | **17.4223** | 11.0397 | 11.0113 |
| free 0–30 | 15.4333 | 14.7150 | 9.5025 | 8.9675 |
| free 30–120 | 1.8701 | 1.8453 | 1.3207 | 1.3005 |
| formal 210–330 | 1.2795 | 1.2510 | 1.0217 | 0.9931 |

**注意：** `wait_phase`（D1 1.9920/4.2460 mm；D2-C 2.7400/12.9681 mm）不是 release-elapsed 对齐的公平比较——D2-C 的 120 步等待紧接释放，包含释放瞬态；D1 的等待比释放晚 10 步开始，瞬态已在前 10 步内。该差异是窗口定义效应，不能解释为物理退化。`sample_*` 窗口同样是 released-sample 对齐，D1 的 released sample 在释放后 10 步，D2-C 在释放边界，二者也不应直接横比。

## 6. 正式窗口与质量

| 指标 | D1 | D2-C | 阈值 | 结果 |
|---|---:|---:|---:|---|
| 质心漂移 | 2.040882 mm | **1.982336 mm** | ≤1 mm | 仍拒绝 |
| 顶点 P95 | 4.413414 mm | **4.342617 mm** | ≤3 mm | 仍拒绝 |
| 顶点最大 | 4.837389 mm | 4.777344 mm | — | — |
| 旋转 | −0.720876° | −0.719400° | — | 几乎相同 |
| 刚体 RMS | 0.001574 mm | 0.001996 mm | — | 略高 |
| quality | rejected | rejected | — | 证据完整、有效对照 |

D2-C 的正式窗口质心/P95 相对 D1 **下降 2.87% / 1.60%**，但仍远高于 1 mm / 3 mm；质量仍为 rejected。

## 7. 解释与边界

1. **释放顺序没有降低释放冲量。** D1 与 D2-C 的首个自由物理步粒子平均速度几乎相同（17.4197 vs 17.4223 mm/s），质心速度 11.0397 vs 11.0113 mm/s；release transition 的质心/P95 位移也几乎相同。释放 t=0 的布料位置差 ≤0.037 mm。说明“把夹爪张开移到附件解除之前”没有改变解除瞬间的布料状态或第一步冲量。
2. **0–0.5 s 也基本不变。** free 0–30 的质心 1.9092 vs 1.9119 mm，P95 12.2286 vs 12.2044 mm（±0.2%）。释放瞬态仍然存在。
3. **后续窗口有小幅下降。** free 30–120、retreat 和 formal 窗口的质心/P95 低 1.3–3.0%，但幅度小；其中 formal 与 retreat 是 action-relative，D2-C 比 D1 晚 10 步释放，存在相位差异。**可以表述为“释放顺序改变降低了本例正式窗口漂移”，但不能表述为“降低了释放冲量”**；单例也不足以外推。
4. **不能归因于接触冲量。** PhysX contact-report 仍只覆盖机器人刚体接触；cloth-ground 接触力/冲量不可用，contact_events=0 不是“无接触”。本报告只用位置、速度、高度和穿透代理。
5. **结论：释放顺序不是该例漂移的主要因素。** 释放瞬态和前 0.5 s 未变，正式窗口仅小幅下降且仍拒绝。若继续追因，应优先考虑释放时附件约束的能量/接触状态、布料—地面接触参数或支撑面材质，而不是继续调整开爪顺序。

## 8. 产物

- [download_audit.json](../D2_D_RUN_4202_20261104/download_audit.json)：上传/预检/一次性账本/证据哈希/动作与步数核验
- [comparison.json](comparison.json)：完整数值、边界、步数和 verdict
- [windows.csv](windows.csv)：各窗口质心/P95/旋转/速度
- [d2c_release_compare.png](d2c_release_compare.png)：first-free 后的质心、P95、粒子速度曲线
- D1 对照数据：[d1/](d1/)
- D2-C 运行证据：[D2_D_RUN_4202_20261104](../D2_D_RUN_4202_20261104/)
