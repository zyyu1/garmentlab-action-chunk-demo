# A5 RC2 漂移定位：基线索引与事件分段（2026-11-03）

本轮执行第 1、2 项：整理 RC2 基线，并从已有轨迹生成事件分段表和漂移曲线。**没有新增仿真、没有运行 held-out、没有产生正式成功。** RC2 仍未冻结；原始 RC2 审计目录未被修改。

## 1. 交付物

| 交付物 | 内容 |
|---|---|
| [baseline.json](baseline.json) | RC2 代码版本、候选配置、60 项 manifest、原版 verify-dev 输出、七例摘要 |
| [case-index.json](case-index.json) / [case-index.md](case-index.md) | 七例索引：结果目录、初态、视频、评价窗口帧、拒绝原因、稳定性指标 |
| [diagnostic-config.json](diagnostic-config.json) | 独立诊断批次 `a5-rc2-drift-diag-v1` 登记（未运行） |
| [source-snapshot/app](source-snapshot/app) | RC2 代码快照；60 项 manifest 逐项复核通过 |
| [baseline/verify-dev.json](baseline/verify-dev.json) | 原版 verify-dev 输出（未改写） |
| [file-hashes.json](file-hashes.json) / [analysis/file-hashes.json](analysis/file-hashes.json) | 基线与分析产物哈希 |
| [analysis/phase-events.json](analysis/phase-events.json) | 4202/4302 事件表（observed step、world step、sim time、来源） |
| [analysis/phase-segments.json](analysis/phase-segments.json) | 相邻事件分段指标与原评价器交叉核对 |
| [analysis/event-table.csv](analysis/event-table.csv) / [analysis/segment-metrics.csv](analysis/segment-metrics.csv) | 可直接复算的平面表 |
| [analysis/plots/drift_4202_single.png](analysis/plots/drift_4202_single.png) / [drift_4302_single.png](analysis/plots/drift_4302_single.png) | 质心位移与 P95 曲线，标注事件 |
| [analysis/diagnosis.md](analysis/diagnosis.md) | 事件表、分段表、原评价器交叉核对、缺口清单 |

## 2. RC2 基线

- 版本：`stage4-a5-rc2`，父版本 `stage4-a5-rc1`；候选配置 SHA256 `10a6cb452b9fafd5907f245b68fd02d49c7af1e12fa6cb0f755f1791a5af27a5`。
- manifest：`39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d`，共 60 项；原始目录与本地快照均逐项通过。
- **原版 verify-dev：`exit_code=1`，`release_exists=false`。** 失败点是正样本 4202 arc4（`day4-a5-rc2-recovery-20261104-024310-304319`）的稳定性拒绝，不是 RGB/视频/持布证据失败。七例的 13 项 `evidence_checks` 全部为 true（`video_and_samples`、`actual_sim`、`source`、`input_hashes`、`identity`、`actual_budget`、`horizons`、`final_open`、`upward_public_target`、`clock_origin`、`absolute_clock`、`double_hold`、`terminal_matches`）。因此 RGB、视频与持布状态修复作为已通过基础保留，但 RC2 整体仍不可冻结。
- 七例索引（完整字段见 [case-index.md](case-index.md)）：

| 用例 | 结果 | 失败项 | 质心最大/上限 | P95 最大/上限 | 评价窗口视频帧 |
|---|---|---|---:|---:|---|
| 4100 single / arc4 | accepted | — | 0.144 / 1 mm | 0.207 / 3 mm | 843–904 |
| 4202 single / arc4 | rejected | stable | 2.043 / 1 mm | 4.414 / 3 mm | 1157–1218 |
| 4302 single / arc4 | rejected | stable | 1.910 / 1 mm | 4.123 / 3 mm | 1367–1428 |
| 4201 single | rejected | geometry 121/121；运行门槛 | 0.0002 / 1 mm | 0.0026 / 3 mm | 1298–1359 |

- 诊断对象：**4202 single 为首个诊断对象，4302 single 用于后续复验**；4201 single 保留为有效负对照（折形未过线）。
- 诊断批次：`a5-rc2-drift-diag-v1`，状态 `registered_not_run`；D0/D1/D2 只登记，未运行。D0 为原流程 + 诊断记录；D1 为延迟退让；D2 待接触/距离证据后设计。所有新实验使用独立 tag/目录，不覆盖 RC2；公开动作预算仍为 L1=7、任务 B=12。

## 3. 事件分段

两例的时钟关系：证据 `observed_step` 与 success-trace `absolute_step` 相差 2；**`sim_time_s` 是共同时钟**。事件表的 pre-trace world step 按 `observed_step + 2` 推断并明确标注；trace 段 world step 直接取自 `success_meta.absolute_step`。

| case | 事件 | observed | world | sim (s) | 来源 |
|---|---|---:|---:|---:|---|
| 4202 | E1 最后一次保持帧 | 1942 | 1944 | 32.400 | pre_release_hold |
| 4202 | E3 附着解除 / 夹爪有效打开 | 1944 | 1946 | 32.433 | 状态：holding=false, attached=false, 三槽 enable=false |
| 4202 | E4 released 快照 | 1953 | 1955 | 32.583 | evidence sample |
| 4202 | E5 退让指令开始 | 1954 | 1956 | 32.600 | command_holding=false |
| 4202 | E7 退让结束 / trace t0 | 2097 | 2099 | 34.983 | action_end + success_meta |
| 4202 | E9 正式窗口开始 | 2307 | 2309 | 38.483 | trace step 210 |
| 4202 | E11 正式窗口结束 | 2427 | 2429 | 40.483 | trace step 330 |
| 4302 | E1 最后一次保持帧 | 2359 | 2361 | 39.350 | pre_release_hold |
| 4302 | E3 附着解除 / 夹爪有效打开 | 2361 | 2363 | 39.383 | 状态 |
| 4302 | E4 released 快照 | 2370 | 2372 | 39.533 | evidence sample |
| 4302 | E5 退让指令开始 | 2371 | 2373 | 39.550 | command_holding=false |
| 4302 | E7 退让结束 / trace t0 | 2517 | 2519 | 41.983 | action_end + success_meta |
| 4302 | E9 正式窗口开始 | 2727 | 2729 | 45.483 | trace step 210 |
| 4302 | E11 正式窗口结束 | 2847 | 2849 | 47.483 | trace step 330 |

- **同一步事件**：E3 同时是附着解除与夹爪有效打开（由三槽 enable/holding 状态推断；实际开合量未记录），已合并记录。
- **无法定位/缺失**：E12 手指/夹爪—布料接触；释放到退让之间的逐物理步布料顶点；夹爪开合量。原因见 §5。
- 完整 E1–E12 见 [event-table.csv](analysis/event-table.csv) 与 [analysis/diagnosis.md](analysis/diagnosis.md)。

## 4. 分段漂移结果

### 4.1 相邻事件分段

| case | 分段 | 时长 s | 质心 mm | 旋转 deg | P95 mm | 最大 mm | 刚体拟合 RMS mm | 逐物理步顶点 | 接触记录 |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 4202 | 保持最后 60 帧 | 0.983 | 0.074 | −0.032 | 0.202 | 0.241 | 0.039 | 有 | 缺失 |
| 4202 | 保持末帧→released | 0.183 | 0.848 | 0.069 | **13.831** | **25.619** | **1.894** | **无（仅快照）** | 缺失 |
| 4202 | released→retreated | 2.400 | **2.485** | **−0.912** | 5.403 | 6.281 | 0.414 | 无（仅快照） | 缺失 |
| 4202 | retreated→trace t0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 有 | 缺失 |
| 4202 | trace t0→窗口开始 | 3.500 | 3.586 | −1.267 | 7.758 | 8.500 | 0.0013 | 有 | 缺失 |
| 4202 | 正式窗口 210–330 | 2.000 | **2.043** | **−0.720** | **4.414** | 4.838 | 0.0011 | 有 | 缺失 |
| 4202 | trace t0→末尾 | 5.500 | 5.629 | −1.987 | 12.171 | 13.338 | 0.0008 | 有 | 缺失 |
| 4302 | 保持最后 60 帧 | 0.983 | 0.070 | −0.044 | 0.255 | 0.309 | 0.051 | 有 | 缺失 |
| 4302 | 保持末帧→released | 0.183 | 0.981 | 0.074 | **15.031** | **27.649** | **2.085** | **无（仅快照）** | 缺失 |
| 4302 | released→retreated | 2.450 | **2.438** | **−0.943** | 5.490 | 6.453 | 0.518 | 无（仅快照） | 缺失 |
| 4302 | retreated→trace t0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 有 | 缺失 |
| 4302 | trace t0→窗口开始 | 3.500 | 3.338 | −1.177 | 7.217 | 7.903 | 0.0012 | 有 | 缺失 |
| 4302 | 正式窗口 210–330 | 2.000 | **1.910** | **−0.672** | **4.123** | 4.517 | 0.0009 | 有 | 缺失 |
| 4302 | trace t0→末尾 | 5.500 | 5.248 | −1.848 | 11.340 | 12.420 | 0.0010 | 有 | 缺失 |

- 分段平均速度（点位移 P95 / 时长）：4202 保持 0.206 mm/s、released 瞬态 **75.44 mm/s**（最大 139.74）、退让 2.25 mm/s（最大 2.62）；4302 保持 0.259、瞬态 **81.99 mm/s**（最大 150.81）、退让 2.24 mm/s（最大 2.63）。正式窗口的逐帧速度 P95/最大为 3.445/16.468 mm/s（4202）与 3.523/16.576 mm/s（4302）。
- 原评价器交叉核对：窗口的 `centroid_drift_max`、`vertex_drift_p95_max`、`vertex_drift_max`、`vertex_speed_p95_max`、`vertex_speed_max` 五项在两例上**逐项零差**（见 [analysis/diagnosis.md](analysis/diagnosis.md) §Original evaluator cross-check）。因此分段表的 P95 与原拒绝依据一致，不是另算指标。
- Trace 侧相邻子段 E7→E8（t0→hold_3s）、E8→E9（hold_3s→窗口开始）、E9→E10（窗口开始→hold_4s）、E10→E11（hold_4s→窗口结束）已逐段计算，完整数值见 [segment-metrics.csv](analysis/segment-metrics.csv)；正式验收仍以 E9→E11 的 210–330 窗口为准。

### 4.2 运动主要发生在哪些阶段

1. **释放前保持稳定。** 最后 60 帧质心 0.074/0.070 mm、P95 0.202/0.255 mm、刚体 RMS 0.039/0.051 mm；没有在保持阶段积累漂移。RC2 把保持从 60 步延长到 180 步后，窗口漂移反而略高于 RC1（4202 1.72→2.04 mm、P95 3.76→4.41 mm；4302 1.79→1.91 mm、P95 3.88→4.12 mm；RC1 数值取自既有审查，比较为描述性，不能单独归因）。这说明“保持不足/残余动量”不是主要解释。
2. **释放/开爪瞬态是局部运动的最大来源。** 保持末帧→released 的 0.183 s 内，质心只移动 0.848/0.981 mm，但顶点 P95 达 **13.831/15.031 mm**、最大 **25.619/27.649 mm**、刚体拟合 RMS **1.894/2.085 mm**；这是非刚体的局部变形，且速度远高于后续阶段。该快照在附着解除后 9 个证据步才采到，实际峰值可能更早、更大。
3. **退让阶段是质心/旋转的最大来源。** released→retreated 的 2.4 s 内，质心 **2.485/2.438 mm**、旋转 **−0.912/−0.943°**、P95 5.403/5.490 mm，刚体 RMS 0.414/0.518 mm——以刚体平移/转动为主，叠加少量局部运动。
4. **退让后的正式窗口是持续刚体滑移/转动。** trace t0→窗口开始的 3.5 s 已有 3.586/3.338 mm、−1.267/−1.177°，刚体 RMS 仅 0.0013/0.0012 mm；正式窗口再增加 2.043/1.910 mm 与 −0.720/−0.672°，P95 4.414/4.123 mm，刚体 RMS 0.0011/0.0009 mm。窗口内几乎整块布在平移+旋转，不是局部松弛；因此 1 mm/3 mm 超限是整体滑移/转动导致的。
5. **阶段结论**：漂移的起点在释放/开爪，局部瞬态最大；退让阶段贡献最大的质心/旋转；退让结束后以近乎刚体的方式持续滑移/转动，直到 5.5 s 评价窗口结束。**仅凭现有数据不能把瞬态唯一归因于机器人接触、脱附回弹或地面摩擦**；接触记录缺失，见 §5。

### 4.3 距离证据（不是接触证据）

EE 点到最近布料顶点的距离（几何代理，不是指尖表面距离，也不是接触力）：

| 时点 | 4202 single | 4302 single |
|---|---:|---:|
| 保持末帧 | 3.804 mm | 2.047 mm |
| released 快照 | 21.075 mm | 21.595 mm |
| retreated 快照 | 165.997 mm | 166.567 mm |
| 窗口开始/结束 | 166.261 / 166.471 mm | 166.852 / 167.067 mm |

- 保持期间 EE 距布料仅 2–4 mm；释放后到 21 mm；退让结束到约 166 mm；窗口内 EE 基本静止在约 166–167 mm 远处。距离代理**提示**窗口内机器人本体远离布料，但手指可能比 EE 点更近，且没有指尖/接触记录，**不能据此认定无碰撞或无接触**。
- 释放瞬态发生在 EE 从 2–4 mm 远离到 21 mm 的过程中；该阶段是否存在手指接触/支撑，现有证据不能判定。

## 5. 现有证据缺口

1. **释放到退让之间的逐物理步布料顶点缺失。** `pre_release_hold.npz` 只有 180 帧保持末段；`success_trace.npz` 从退让结束的 t0 开始；中间只有 `released`（附着解除后约 10 步）与 `retreated`（退让结束）两个快照。因此：
   - 释放瞬态的实际起点、峰值和恢复过程无法定位；
   - 释放后的开爪/指令等待与退让动作对布料运动的贡献无法分开；
   - 表中 released→retreated 的 5.4/5.5 mm P95 是两快照之差，不是逐帧积分。

   按相邻事件对，**E1→E2、E2→E3、E3→E4、E4→E5、E5→E6、E6→E7 无法逐段计算**（缺逐物理步顶点）；只能给出 E1→E4（0.183 s）与 E4→E7（2.4 s）的快照级结果。Trace 侧的 E7→E8、E8→E9、E9→E10、E10→E11 已单独计算，见 [segment-metrics.csv](analysis/segment-metrics.csv)。
2. **夹爪开合量缺失。** 时间线有 holding、logical_attached、三槽 enable、command 与 EE 位姿，但没有逐步夹爪开合量/指尖位置；无法判断释放瞬态期间指尖是否仍接触或支撑布料。
3. **接触力/冲量缺失。** 七例中只有 `room_collision_audit.json`（房间 collider），没有 `contacts.jsonl` 或手指—布料接触记录；`square_contact_recorder.py` 存在于 RC2 源码，但未在 recovery 链路中产生逐例接触文件。**不得把距离代理写成接触记录，也不得据此认定“没有碰撞”。**
4. **`released` 快照不是释放瞬间。** 它在附着解除后 9 个证据步才被采集；瞬态的 P95 13.8/15.0 mm 是“该快照相对保持末帧”的值，不是已证明的峰值。
5. **RC2 与原评价器的关系已核对。** 分段表的窗口 P95 与原评价器五项零差；问题不是评价器口径，而是物理运动本身。

## 6. 结论与下一步

- **第 2 项完成标准已满足**：明确了漂移主要发生在释放/开爪瞬态、退让阶段和退让后的刚体滑移；也明确了缺少逐物理步顶点、夹爪开合量和接触记录。
- **暂不进入第 4 项 D1/D2。** 现有证据支持“释放/退让阶段是运动起点”，但无法区分释放回弹、机器人接触/支撑与地面摩擦；此时直接改延迟退让会把多个假设混在一起。
- **下一步（第 3 项）**：在 4202 single 上补齐从释放动作开始到退让结束的逐物理步记录——布料顶点、EE 位姿、夹爪开合量、holding/attachment、可用的接触对象/时刻/力/冲量；若只能得到距离，明确标为距离证据。保持物理步进、控制频率和动作目标不变；如必须改变，先登记新版本并重建基线。
- 补齐后用 4202 single 做 D0 基线复现；D0 可复现才进入 D1 延迟退让；D2 的脱离路径在接触/距离证据之后再设计。4302 single 作为后续复验。
- 公开动作预算保持 L1=7、任务 B=12；新增动作不得藏成内部 waypoint。正式 Stage 4 成功仍为 0；RC2 仍未冻结；held-out 未运行。

## 7. 边界

- 本轮没有新增仿真，没有修改 RC2 原始结果或代码；`source-snapshot` 是只读副本。
- `diagnostic-config.json` 是诊断批次登记，不是可执行的正式批次；D0/D1/D2 尚未运行。
- right 仍是独立开发变体；本次不改变折向、任务定义或成功阈值。
- 所有指标是仿真几何代理，不是真实接触力、材料质量或自交认证。

## 8. 第 3 项实现与 v1.1 干净轨迹（2026-11-03）

新增独立诊断版本 **`a5-rc2-drift-diag-v1`**，不修改 RC2 原始文件。实现说明与运行命令见 [a5-rc2-drift-diag/README.md](../../../a5-rc2-drift-diag/README.md)。

- 新增 `release_diag.py`：被动子类，在 release 动作开始前的锚点到 `retreated` 快照之间逐物理步记录 441 顶点、EE 位姿/四元数、全部关节位置、finger joint 索引与开合量、holding/attachment/command、EE 与 finger 到布料的最小距离；不调用 `world.step`/`execute`/`apply_action`。
- 新增 `a5_capture_diag.py`：只在同一个 `release(target)` 前后调用 `start_release_diag`/`finish_release_diag`；331 步 success trace、采样时钟、`zero` 和物理步数不变。
- 新增 `a5_recovery_diag.py`：RC2 runner 的观察副本；输出前缀 `day4-a5-rc2-drift-diag-`；额外创建可用的 `ContactRecorder` 机器人刚体接触通道（零事件不等于无接触），并写 `contact_report.json`。
- 新增 `a5_diag_assess.py`：运行后核对诊断 manifest、12 动作、state dt/step、release action 目标、原 B v1 证据与质量；不升级正式成功。
- 离线测试 `test_release_diag.py` **1/1 通过**：验证 441 顶点、9 关节、开合量、距离、released/retreated 标签、state dt=1/60、state step 连续、action 目标，且没有额外物理步。
- 诊断 manifest 66 项（60 基础 + 6 诊断），v1.1 SHA256 `13c1f20a…`；配置 SHA256 `aa5da98b…`；release_diag `dbb7801c…`；assessor `fcdc3383…`；基础 manifest `39dc5055…` 未变。
- v1 4202 已执行：`day4-a5-rc2-drift-diag-20261104-050739-915052`，157 行（155 state 步 + released/retreated），contact 0 事件，quality rejected（稳定性，符合 baseline）。`complete=False` 原因是：(1) action target 用 float32 记录、float64 比较且 atol=1e-9 过严（float32 转换后完全相等，float64 最大差 1.26e-8 m）；(2) 起始锚点被写成额外 `state` 行，原 evidence `continuous_steps` false；release_diag 自身 155 个 state 步连续。
- v1.1 修复：锚点改为 `release_anchor`（非 state），action target 按 float32 比较；不动物理/控制/动作目标；离线测试 1/1。v1.1 4202 已运行 `day4-a5-rc2-drift-diag-20261104-053151-197013`，得到 **`DIAG_ASSESS complete=True`**、25/25 诊断检查、18/18 evidence 检查、release_rows=157、contact_events=0、quality=rejected（稳定性，符合 baseline）。
- v1.1 与 v1 已逐位比较：release_diag 全部数组（finger 距离全 NaN、掩码相同）、12 个动作目标（最大差 0）、success_trace、final/recovered/pre_release_hold/cloth_constructed、五个证据快照、2427 条 state、1219 条 frame 全部相同；唯一差异是 v1 的 1943 重复 state 锚点改为 `release_anchor`，以及三个诊断文件 hash。与 RC2 4202 single `022718-388270` 的目标序列最大差 0，success_trace/快照/success_meta 物理字段相同，`quality` 与 RC2 `criteria` 逐项相等。**没有改变物理步进、控制频率或动作目标；不需要新物理版本或重建 baseline。** 详见 [v1.1 比较](../STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103/v1_1_compare.md)。
- v1.1 分段（与 v1 物理数组逐位相同）：[release diag 分析](../STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103/review.md)。开爪/释放 1944–1953 为局部非刚体瞬态（质心 0.848 mm、P95 13.831 mm、最大 25.619 mm、RMS 1.894 mm；质心在 1948 峰值约 1.236 mm 后回落）；退让 1955–2097 近刚体（质心 2.277 mm、旋转 −0.804°、P95 4.887 mm、RMS 0.094 mm）；正式窗口延续刚体滑移/转动。
- 运行入口（v1.1；重跑 4202）：
  ```bash
  cd <remote-root>/a5-rc2-drift-diag/app
  bash run-a5-rc2-drift-diag.sh 4202 single
  ```
  输出 `day4-a5-rc2-drift-diag-<timestamp>`；v1.1 已得到 `DIAG_ASSESS complete=True`，且与 v1、RC2 4202 single 物理轨迹逐位相同；比较见 [v1.1 比较](../STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103/v1_1_compare.md)。
- 接触/距离边界：`contact_report.json` 是机器人刚体接触通道，scope 不是布料粒子接触认证；零事件不得写成无接触。EE/finger 距离只是距离证据。若接触通道为零，真实轨迹仍能区分释放、开爪和退让（顶点/EE/关节/attachment），但不能据此唯一归因于机器人接触。
- 物理/控制/动作不变的证据：runner/capture 的 diff 仅限上述观察钩子；离线测试的 state dt/step 与无额外步；运行后 `a5_diag_assess.py` 再核对 12 动作与 release action 目标，并可与 RC2 4202 single 的目标序列逐项比较。
