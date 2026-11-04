# D0 4302 确定性复现审计（2026-11-03）

对象：远端 D0 `day4-a5-rc2-recovery-20261104-044048-912242`（journal `stage4-rc2-d0-4302-AKnlgSH2`），对照既有 RC2 4302 single `day4-a5-rc2-recovery-20261104-025702-598075`。离线审计，无新增仿真。

## 结论

**97/97 项检查通过；D0 4302 在物理/状态层面逐位复现 RC2 4302 single。**

- 12 个 action target 最大绝对差 **0.0**；commands、labels、`call_horizons`、60 项 `code_files` 全部相同。
- `final.npz`、`recovered.npz`、`pre_release_hold.npz`（180×441×3）、`cloth_constructed.npz`、`success_trace.npz`（331×441×3、steps、absolute_steps、sim_time_s、holding、attachment_enabled、gripper_open）全部 `array_equal`，max|Δ|=0。
- `released/retreated/hold_3s/hold_4s/terminal` 五个 evidence 快照逐位相同。
- 归一化后的 timeline state/sample 行与 action_begin/action_end 行逐行相同；summary 的 frames、observed_steps、execute_calls、sources 哈希相同。
- verdict 的 status、criteria、stability、first/final geometry、failed frames、evidence_checks 全部相同；`success_meta` 的 absolute_step、sim_time、pick、yaw、upward 全部相同。
- 稳定性拒绝为质心 **1.910233 mm**、P95 **4.123147 mm**；geometry 全过、held 通过、released_continuously 通过、no_runtime_error 通过。`runner_exit=0`；`entry-exit-code.txt=1` 是评价器有效拒绝，不是基础设施故障。

## 非物理差异

`evidence/manifest.json` 只有 `summary.json`、`timeline.jsonl`、`episode.mp4` 的哈希不同：前两者含 UTC/单调时钟，后者是视频编码/背景；归一化状态行与物理字段相同。本地未解码视频（cv2 不可用）；remote `video_and_samples` 已通过。因此不能写“视频逐帧相同”。

## 两例 D0 的合并结论

- D0 4202 与 D0 4302 均为 97/97，分别逐位复现 RC2 4202 single / 4302 single。
- 两例的稳定性拒绝都在相同物理/状态下重复出现；这支持“失败是确定性的”，但仍不能解释漂移原因。
- D0 是 RC2 基线，不含 `release_diag`；释放/开爪/退让的逐物理步数据仍待 `a5-rc2-drift-diag-v1` 的 4202 run。
- 正式 Stage 4 成功仍为 0。

## 产物

- [audit.json](audit.json)：97 项检查、failed=[]、max diff 与 evidence manifest 差异。
- 审计脚本：[audit_a5_rc2_d0_repro.py](../../audit_a5_rc2_d0_repro.py)。

## 下一步

1. 运行诊断版 4202（`a5-rc2-drift-diag-v1`）补齐 `release_diag` 逐物理步数据；命令见 [README](../../a5-rc2-drift-diag/README.md)。
2. 只有拿到释放/开爪/退让逐物理步轨迹后，再进入 D1 延迟退让；D0 本身只证明基线可复现。
