# v1.1 干净记录与 v1、RC2 4202 single 的逐项比较

对象：

- v1.1：`day4-a5-rc2-drift-diag-20261104-053151-197013`，`a5-rc2-drift-diag-v1` 的 v1.1 审计修复版。
- v1：`day4-a5-rc2-drift-diag-20261104-050739-915052`。
- RC2：`A5_RC2_AUDIT_20261103T194913Z/day4-a5-rc2-recovery-20261104-022718-388270`（4202 single）。

比较为离线读取，无新增仿真，不修改任何已有结果目录。

## 1. 结论

1. **v1.1 是干净的诊断记录。** `DIAG_ASSESS complete=True`，全部 25 项诊断检查为 true；`evidence.evidence_complete=True`，18 项证据检查全为 true；1219 帧解码、12 个公开动作。
2. **v1.1 与 v1 的物理数据逐位相同。** `release_diag.npz` 的全部数组（顶点、EE 位姿、四元数、9 关节、开合量、附着/持握状态、槽位、命令状态、sim time、observed/backend step、call id、EE 距离、采样标签、phase）数值相等；唯一例外是全为 NaN 的 `finger_min_vertex_distance_mm`，两边 157/157 NaN 且掩码相同。`result.json` 的 12 个动作目标最大差 0；`final.npz`、`recovered.npz`、`pre_release_hold.npz`、`cloth_constructed.npz`、`success_trace.npz` 和五个证据快照逐位相同；2427 条 state、1219 条 frame、12 组 action 行相同。v1 与 v1.1 的唯一数据差异是审计产物：v1 在 1943 多一条 `state` 锚点，v1.1 改为 `release_anchor`；锚点内容除 `kind` 外相同。两边 `code_files` 的差异只有 v1.1 修改的三个诊断文件（配置、assessor、release_diag），60 项基础文件不变。
3. **v1.1 与 RC2 4202 single 的物理轨迹逐位相同。** 12 个动作目标最大差 0；动作标签、命令、call horizon、fold/held/recovery 指标、initial_case 完全相等；`success_trace.npz`、`final.npz`、`recovered.npz`、`pre_release_hold.npz`、`cloth_constructed.npz` 和 released/retreated/hold_3s/hold_4s/terminal 快照逐位相同；`success_meta` 的 seed/level/edge/width/overhang/floor/action_count/recovery_count/held/errors/initial_hashes/absolute_step/sim_time/dt/pick/yaw/upward 全部相等（absolute_step=2099，sim_time=34.983335157856345 s，pick_index=230）。
4. **质量结论未变。** v1.1 的 `quality` 与 RC2 的 `criteria` 字典逐项相等：`status=rejected`、`success=false`、`stable=false`；质心 2.042884 mm > 1 mm，顶点 P95 4.414119 mm > 3 mm；几何全过、held 通过、释放连续。正式 Stage 4 成功仍为 0。
5. **没有发生物理步进、控制频率或动作目标改变。** 因此不需要登记新的物理版本或重建 baseline；v1.1 只是观测/审计修正。RC2 原始目录未被覆盖。

## 2. v1.1 与 v1 的差异清单

| 项目 | v1 | v1.1 | 判定 |
|---|---|---|---|
| `complete_diagnostic` | false | **true** | 审计修复 |
| 失败检查 | `release_diag_action_target` | 无 | float32 比较修复 |
| `evidence.continuous_steps` | false | **true** | 锚点 `release_anchor` 修复 |
| 1943 锚点行 | 额外 `state` 行 | `release_anchor` 行 | 内容除 kind 外相同 |
| release_diag 数组 | 157 行 | 157 行 | 全部逐位相同 |
| 动作目标 | 12 个 | 12 个 | 最大差 0 |
| state / frame / action 行 | 2427+1 / 1219 / 12+12 | 2427 / 1219 / 12+12 | 去掉 v1 锚点后相同 |
| `code_files` | 66 项 | 66 项 | 仅 3 个诊断文件 hash 改变 |
| summary sources | 66 项 | 66 项 | 仅同 3 个诊断文件 hash 改变 |
| 质量 | rejected（stable） | rejected（stable） | 相同 |

`finger_min_vertex_distance_mm` 在 v1 和 v1.1 中均为 157/157 个 NaN，NaN 掩码完全一致；这不是数组差异，而是手指 link 距离不可用。

## 3. v1.1 与 RC2 4202 single 的差异清单

| 项目 | RC2 4202 single | v1.1 | 判定 |
|---|---|---|---|
| 动作目标 | 12 个 | 12 个 | 最大差 0 |
| 动作标签/命令/horizon | 12 | 12 | 相同 |
| fold/held/recovery/initial_case | — | — | 完全相同 |
| success_trace | 331 帧 | 331 帧 | 全部数组逐位相同 |
| final/recovered/pre_release_hold/cloth_constructed | — | — | 逐位相同 |
| 五个证据快照 | — | — | 逐位相同 |
| success_meta 物理字段 | — | — | 相同（含 initial_hashes、absolute_step、sim_time、dt、pick、yaw、upward） |
| quality vs criteria | `criteria` | `quality` | 两个字典逐项相等 |
| manifest | `39dc5055…`（60 项） | `13c1f20a…`（66 项） | 诊断 manifest，预期不同 |
| protocol | `stage4-a5-rc2` | `stage4-a5-rc2-drift-diag-v1` | 预期不同 |
| `code_files` 基础 60 项 | 60 | 60/60 相同 + 6 诊断项 | 基础身份不变 |
| 质量 | rejected（stable） | rejected（stable） | 相同 |

RC2 的 `development_pass=true`、`status=rejected`、`success=false`、`runner_exit=0`；v1.1 的 `formal_stage4_success=false`、`quality.status=rejected`、`quality.success=false`。两者含义一致：执行成功、开发质量判据的稳定性项失败。

## 4. 仍然缺失或不可用的证据

1. **手指 link 距离不可用。** `finger_link_names=[]`，`finger_min_vertex_distance_mm` 157 行全部 NaN。当前只有 EE 到最近布料顶点的几何距离；EE 距离 3.8 → 14.7 → 21.1 → 166.0 mm，是距离证据，不是接触力/冲量。
2. **接触通道零事件。** `ContactRecorder` subscription 已创建，但 callback=0、event=0；`diagnosis=configured_no_events_channel_not_independently_validated`。**不得写成“无接触”或“无碰撞”**；该通道本身未独立验证，也不是布料粒子接触认证。
3. **release_diag.json 的 `dof_names` 为 null。** 9 个关节名称在 evidence timeline 的 state 行中可见，但未写入 release_diag 的 JSON/npz；开合量仍可由 finger joint indices 7/8 派生，不影响本轮结论。若后续需要按名称解释每个关节，应在下一个诊断版本补齐。
4. **没有真实接触力/冲量。** 释放瞬态的非刚体形变只能归因于“释放/开爪窗口内的局部演化”，不能唯一归因于机器人接触。

## 5. 对下一步的含义

- v1.1 的释放/开爪/退让轨迹可以作为 D1 的干净对照基线；分段结论沿用 `analysis.md`（v1 与 v1.1 物理数组逐位相同）。
- D1（延迟退让）仍需单独登记延迟长度与 12 动作预算，不能直接以本诊断 run 冒充 D1 或 RC2。
- 正式批次、held-out、正式 Stage 4 成功仍全部暂停/为 0。
- 若 D1 只改变退让时序而保持动作目标序列其余部分不变，应复用本报告的物理身份检查；若改变动作目标或物理步进，则必须登记新版本并重建 baseline。

## 6. 复现命令

```powershell
cd E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test
python -I analyze_a5_rc2_release_diag.py --diag-dir E:\learning\project\thesis\day4-actionchunk-test\results\day4-a5-rc2-drift-diag-20261104-053151-197013 --out results\STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103
```

本报告的比较逻辑使用 `numpy.array_equal` 对全部数值数组逐位比较；时间戳/UTC/monotonic 字段不参与物理身份判断。NaN 数组额外比较 NaN 掩码，避免把“双方全为 NaN”误判为差异。
