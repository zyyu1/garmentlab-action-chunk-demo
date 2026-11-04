# D0 4202 确定性复现审计（2026-11-03）

对象：远端 D0 `day4-a5-rc2-recovery-20261104-042325-295743`（journal `stage4-rc2-d0-4202-XaDTIjGX`），对照既有 RC2 4202 single `day4-a5-rc2-recovery-20261104-022718-388270`。离线审计，无新增仿真。

## 结论

**97/97 项检查通过；D0 4202 在物理/状态层面逐位复现 RC2 4202 single。** 不只是“报告精度一致”：

- 12 个 action target 最大绝对差 **0.0**；commands、labels、`call_horizons` 完全相同；`code_files` 60/60 相同。
- `final.npz`、`recovered.npz`、`pre_release_hold.npz`（180×441×3）、`cloth_constructed.npz`、`success_trace.npz`（331×441×3、steps、absolute_steps、sim_time_s、holding、attachment_enabled、gripper_open）全部 `array_equal`，max|Δ|=0。
- `released/retreated/hold_3s/hold_4s/terminal` 五个 evidence 快照逐位相同。
- 归一化后的 timeline `state`/`sample` 行（2,432 行）与 `action_begin`/`action_end` 行（24 行）逐行相同；summary 的 frames 1219、observed_steps 2427、execute_calls 12、sources 哈希相同。
- verdict 的 status、criteria、stability、first/final geometry、failed frames、evidence_checks 全部相同；`success_meta` 的 absolute_step 2099、sim_time 34.983335、pick 230、yaw 0.10795666、upward 0.14602046 全部相同。
- 稳定性拒绝为质心 **2.042884 mm**、P95 **4.414119 mm**；geometry 全过、held 通过、released_continuously 通过、no_runtime_error 通过。`runner_exit=0`；`entry-exit-code.txt=1` 是评价器有效拒绝，不是基础设施故障；journal 的 finished/started 身份一致。

## 非物理差异

`evidence/manifest.json` 只有三个文件哈希不同：

| 文件 | 原因 | 是否物理差异 |
|---|---|---|
| `summary.json` | 含 UTC/单调时钟与样本时间戳 | 否；物理字段、frames、sources 哈希相同 |
| `timeline.jsonl` | 含 UTC/`monotonic_ns` | 否；归一化 state/sample/action 行逐行相同 |
| `episode.mp4` | 视频编码/背景，非物理状态 | 否；本地未解码（cv2 不可用），remote `video_and_samples` 已通过 |

因此不能写“视频逐帧相同”；能写的是：状态、动作、布料几何、样本快照和评价指标逐位相同，视频文件哈希不同且未在本地做帧级对比。

## 边界

- 这是 **RC2 基线 D0**，不是 `a5-rc2-drift-diag-v1`；没有 `release_diag` 逐物理步数据。释放/开爪/退让记录仍待诊断版 4202 run。
- D0 复现只证明该失败是确定性的；不能据此确定漂移原因。
- 正式 Stage 4 成功仍为 0；本审计不升级正式成功。

## 产物

- [audit.json](audit.json)：97 项检查、failed=[]、max diff 与 evidence manifest 差异。
- 审计脚本：[audit_a5_rc2_d0_repro.py](../../audit_a5_rc2_d0_repro.py)。

## 下一步

4302 D0 使用同一 RC2 app 与 4302 初态、新的 journal；下载后可用同一脚本对照 `A5_RC2_AUDIT_20261103T194913Z/day4-a5-rc2-recovery-20261104-025702-598075`。若确定性成立，预期动作目标 0 差、终态/轨迹顶点 0 差、稳定性仍为质心约 1.910233 mm、P95 约 4.123147 mm。

**2026-11-03 更新：4302 D0 已完成并 97/97 通过**，见 [D0 4302 审计](../D0_4302_REPRO_AUDIT_20261103/review.md)。两例 D0 baseline 均确定性复现。
