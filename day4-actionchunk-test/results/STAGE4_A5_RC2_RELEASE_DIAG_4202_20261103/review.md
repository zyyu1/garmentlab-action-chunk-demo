# RC2 释放窗口诊断：4202 single（v1.1 干净记录，v1 对照）

对象：`day4-a5-rc2-drift-diag-20261104-053151-197013`（v1.1，主记录）；`day4-a5-rc2-drift-diag-20261104-050739-915052`（v1，对照）；RC2 `day4-a5-rc2-recovery-20261104-022718-388270`（4202 single）。离线分析，无新增仿真。

## 结果概览

- v1.1 `DIAG_ASSESS complete=True`，25 项诊断检查全 true；`evidence.evidence_complete=True`，18 项证据检查全 true，1219 帧、12 个公开动作。`release_diag` 157 行 = 155 个 state 步（1943–2097）+ released/retreated 两个快照；441 顶点、9 关节、开合量 157 个有限值、EE 距离 157 个有限值；`state_dt_ok=true`、`state_step_ok=true`、`physics_mode=passive post-step reads only`。
- `quality=rejected`（稳定性，符合 RC2 4202 single）；几何全过、held 通过、释放连续、无运行错误。`quality` 字典与 RC2 的 `criteria` 逐项相等。
- `contact_report`: subscription 创建、callback/event 0；`diagnosis=configured_no_events_channel_not_independently_validated`。**不能写成无接触**。finger-link 距离不可用（157/157 NaN），只有 EE 到最近顶点距离代理。
- v1 `complete=False` **不是运行/物理失败**，原因是两个审计/接口问题（已由 v1.1 修复）：
  1. `release_diag_action_target`：诊断记录 execute() 的 float32 目标，`result.json` 存 float64 目标；float32 转换后完全相等，float64 最大差 1.26e-8 m。v1 的 atol=1e-9 过严。
  2. `evidence continuous_steps`：起始锚点被写成额外 `state` 行，和最后一次保持状态共享 step 1943；release_diag 自身 155 个 state 步连续。原 evidence timeline 因此多一条重复 state。
- v1.1 修复：锚点改为 `release_anchor`（非 state），action target 按 float32 比较；不动物理、控制频率或动作目标。v1.1 manifest `13c1f20a…`、config `aa5da98b…`、release_diag `dbb7801c…`、assessor `fcdc3383…`；runner/capture/entry 未变。
- **v1.1 与 v1 物理数据逐位相同**：release_diag 全部数组（finger 距离两边全 NaN、掩码相同）、12 个动作目标、final/recovered/pre_release_hold/cloth_constructed/success_trace、五个证据快照、2427 条 state、1219 条 frame 均相同；唯一差异是 v1 的 1943 重复 `state` 锚点改为 `release_anchor`，以及三个诊断文件 hash。**与 RC2 4202 single 的物理轨迹也逐位相同**（目标最大差 0；success_trace/快照逐位相同；success_meta 物理字段相同；quality 与 criteria 相同）。因此无需登记新的物理版本或重建 baseline。详见 [v1_1_compare.md](v1_1_compare.md)。

## 释放/开爪/退让分段（v1.1；与 v1 物理数组逐位相同）

| 阶段 | 步 | 时长 s | 质心 mm | 旋转 deg | P95 mm | 最大 mm | 刚体 RMS mm |
|---|---|---:|---:|---:|---:|---:|---:|
| 锚点→附着解除 | 1943–1944 | 0.0167 | 0.136 | 0.001 | 0.742 | 10.908 | 0.267 |
| 开爪/释放瞬态 | 1944–1953 | 0.1500 | 0.729 | 0.068 | 12.116 | 24.446 | 1.729 |
| released→退让指令 | 1953–1954 | 0.0167 | 0.194 | −0.057 | 0.696 | 1.086 | 0.228 |
| 退让指令→1 mm | 1954–1955 | 0.0167 | 0.195 | −0.052 | 0.949 | 1.885 | 0.249 |
| 退让 1 mm→结束 | 1955–2097 | 2.3667 | **2.277** | **−0.804** | 4.887 | 5.420 | **0.094** |
| 开爪总段 | 1943–1953 | 0.1667 | 0.848 | 0.069 | **13.831** | **25.619** | **1.894** |
| 退让总段 | 1953–2097 | 2.4000 | **2.485** | **−0.912** | 5.403 | 6.281 | 0.414 |
| 总段 | 1943–2097 | 2.5667 | 3.000 | −0.844 | 14.220 | 26.082 | 1.842 |

关键事实：

1. **开爪/释放瞬态是局部非刚体运动。** 1944 附着解除时 `holding/attached/enabled` 全 false；开合量从 0 在 1949 左右到 80 mm；EE z 在 1953 前保持约 46.8 mm。质心在 1948 达到约 1.236 mm 后回落到 0.848 mm；P95 增至 13.8 mm、最大 25.6 mm、刚体 RMS 1.89 mm。该瞬态发生在退让指令（1954）之前，并在 10 步预退让等待中继续演化/部分回落。
2. **退让阶段是近刚体平移/转动。** 1955–2097 的 2.37 s 内质心 2.277 mm、旋转 −0.804°、P95 4.887 mm、刚体 RMS 仅 0.094 mm；来源是整块布的平移/转动，叠加释放瞬态残留的局部形变（相对锚点的 P95 仍约 14 mm）。
3. **正式窗口延续刚体运动。** 210–330 窗口的质心 2.043 mm、P95 4.414 mm、刚体 RMS 0.0011 mm，超 1 mm/3 mm；与第 2 步一致，是退让后的整体滑移/转动。
4. **D1 的方向**：释放瞬态在退让前已发生，D1 延迟退让应延长开爪后的等待并逐物理步记录瞬态是否继续/回落；D2 再改变脱离路径。当前数据支持先做 D1，但不能据此把瞬态唯一归因于机器人接触。

## 接触与距离

- 接触通道 0 事件；EE 到最近顶点：锚点 3.8 mm、释放后 14.7 mm、released 21.1 mm、退让结束 166.0 mm。EE 距离是几何证据，不是接触力/冲量；手指 link 距离不可用。
- 开合量来自 finger joint 位置求和（joint indices 7/8），不是标定指尖间距；`release_diag.json` 的 `dof_names` 为 null（timeline state 行有名称，不影响开合量派生），后续若需按名称解释关节应在新诊断版本补齐。
- 窗口内 EE 距布料约 166 mm，提示机器人本体远离，但不能据此认定无接触；释放/开爪阶段的 finger-link 距离不可用，只有 EE 距离。

## 结论与下一步

- 第 3 项目标“区分释放、开爪和退让阶段”已用 v1.1 数据实现：开爪/释放（1944–1953）是局部瞬态，退让（1955–2097）是近刚体运动。
- v1 的 `complete=False` 已定位为上述两个审计/接口问题；v1.1 已重跑并得到 `complete=True` 的干净记录。v1.1 与 v1、RC2 4202 single 的物理数组/动作目标逐位相同，见 [v1_1_compare.md](v1_1_compare.md)；因此**不需要登记新的物理版本或重建 baseline**。
- 仍缺：finger-link 距离全 NaN（只有 EE 距离代理）；接触通道 0 事件且未独立验证；`release_diag.json` 的 `dof_names` 为 null（timeline state 行有名称，开合量不受影响）。这些限制不改变“开爪瞬态 → 退让近刚体运动”的分段结论。
- 下一步可提出 D1（延迟退让），但必须先登记延迟长度、12 动作预算和对照方式，并得到明确指令后才能运行；D0 baseline 已完成并逐位复现。不得以诊断 run 冒充 RC2、D1 或正式成功。正式 Stage 4 成功仍为 0。

## 产物

- [analysis.md](analysis.md)：完整分段表、事件、图说明。
- [v1_1_compare.md](v1_1_compare.md)：v1.1 与 v1、RC2 4202 single 的逐位比较与剩余证据缺口。
- [release_diag_analysis.json](release_diag_analysis.json)、[release_diag_segments.csv](release_diag_segments.csv)、[release_diag_events.csv](release_diag_events.csv)。
- [release_diag_4202_single.png](release_diag_4202_single.png)：质心、P95、开合量/EE 高度、EE 距离四联图。
- 分析脚本：[analyze_a5_rc2_release_diag.py](../../analyze_a5_rc2_release_diag.py)。
