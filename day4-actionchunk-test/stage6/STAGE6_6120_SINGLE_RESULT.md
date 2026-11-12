# Stage 6 首例 6120 single 实际结果（2026-11-08）

**结论：入口跑通到第 1 个公共动作；第 2 个动作的 BC CLOSE 目标被 Backend 拒绝，
episode 在任何抓取/终端释放之前以 `execution_error` 结束。没有启动 331 帧评价窗口，
因此没有 accepted/rejected 的折叠判据结果。未重跑，未启动其余 19 例。**

## 1. Run identity

| 项 | 值 |
|---|---|
| seed / level / split | 6120 / flat / val |
| execution | single，L1 budget 7 |
| result dir | `<remote-root>/stage6_runs/results/day4-a5-bc-single-20261109-015433-798440` |
| attempt dir | `<remote-root>/stage6_runs/attempts/6120-single-20261108-175431` |
| runner | `<remote-root>/envs/isaac40/bin/python -u stage6/a5_bc_single.py ...` |
| process exit code | 0（`SimulationApp.close()` 先于最终 print；见 §5） |
| effective exit code | 3（`bc-verdict.status=execution_error`） |
| 自动重试 | 无 |

实际命令（started.json 记录）：

```bash
<remote-root>/envs/isaac40/bin/python -u <remote-root>/stage5-trial/stage6/a5_bc_single.py \
  --initial-dir <remote-root>/day4-square-initial-20261107-070155-602415 \
  --checkpoint <remote-root>/stage5-trial/training/runs/single/best.pt \
  --stats <remote-root>/stage5-trial/training/final/stats.json \
  --app-dir <remote-root>/stage5-trial/app \
  --repo-root <remote-root>/garmentlab-action-chunk-demo \
  --out-root <remote-root>/stage6_runs/results \
  --label day4-a5-bc-single
```

## 2. 初态 / checkpoint / stats 身份

| 文件 | SHA256 |
|---|---|
| initial `result.json` | `21f9f754d1e00726c29c86190f8c31ef016f116ea96815f2e7788f9dd16e83bc` |
| initial `initial_geometry.npz` | `e2725e24a0dc74541f3efc0ae7080e33c2d759e9f3e6c10e4bf92c1aa24507fa` |
| `best.pt` | `5bff9e671c54b5240b93fefb5c67507987553153bad4b5ca0a5bb92d20e48ad6` |
| `stats.json` | `8f1788d11803be7e22729758cf071f68d49ec5bae80aa387a3327112fcae746a` |

初态核验：`level=flat`、`seed=6120`、`task=A_l1_overfold`、
`particle_friction_scale_expected=0.0`、材料 readback friction≈0.3 / pfs=0.0、
`initial_geometry.npz` 的 `settled` 形状 `(441,3)` 且有限。
最终 `episodes.jsonl` 中 6120 为 `flat/val`，result_dir/obs_dir 与上述一致。

## 3. 真实 torch 前向（不是假 torch 测试）

- 解释器：`<remote-root>/envs/isaac40/bin/python`，Python 3.10.8。
- torch：`2.2.2+cu121`，CUDA available=true；BCPolicy 推理 device=cpu。
- 输入：6120 的 `action_001_obs.npz`，`obs_shape=(1340,)`，`obs_finite=true`，
  `holding=false`。
- 输出：`xyz=[-0.18011859072564107, -0.4375714555321282, 0.16165882945249477]`，
  `yaw=0.07461045391484378`，`gripper=0`；全部有限，夹爪映射 0 合法。
- 对照：专家 action_001 target `[-0.19001977145671844, -0.44883161783218384,
  0.1599000245332718, 0.0859541967511177]`，command 0。

结果文件：`<remote-root>/stage6_6120_real_check.json`。

## 4. 实际公共动作

| action | 来源 | command | 目标（model，未覆盖） | 实际执行 | 结果 |
|---:|---|---:|---|---|---|
| 0 | BC | 0 OPEN | `[-0.18011859, -0.43757146, 0.16165883]` yaw 0.07461045 | 同一 target，step 358，EE `[-0.17954874, -0.43699404, 0.16482204]` | 成功，`target_override=false` |
| 1 | BC | 1 CLOSE | `[-0.13202764, -0.44208298, 0.03761742]` yaw 0.11356681 | **未执行** | Backend `choose_unused_region` 拒绝：`CLOSE target is outside unused prepared regions` |

- 公共动作执行数：**1**（预算 7）。
- 是否有目标覆盖：**无**。已执行 action 的 `target_override=false`、
  `model_target_preserved=true`；action 0 的 `target_pose[:3]` 与 BCPolicy 输出逐值相同。
- action 1 的预测记录在 `runner.log`（`BC_PREDICT 1`），因 Backend 在
  `control.grasp` 前抛错，未进入 `result.actions`。
- 离线距离复核（`posthoc_review/close_target_distance.json`）：
  - policy CLOSE target 到最近未使用 prepared region（left_210, 初态 `[-0.1900,-0.4488,0.0099]`）
    的距离 **0.0646 m**，超过 Backend `max_distance=.03 m`；
  - 专家 action_002 CLOSE target `[-0.19001977,-0.44883162,0.01330002]`
    到同一 region 的距离 **0.0034 m**；
  - policy 与专家 CLOSE target 相差 **0.0632 m**。
  因此这不是阈值误伤，而是 BC 第二个动作的目标误差/闭环分布偏移。

## 5. 终端 / 评价窗口

- `grasp_events=0`，`holding/attachment` 始终 false；action 0 是 initial OPEN，
  没有抓取，也没有 release transition。
- **没有终端 OPEN**，没有 `release_clock`，没有 `success_trace.npz` 或
  `success_meta.json`；未启动 331 帧窗口。
- `bc-verdict.json`：`status=execution_error`，`success=false`，
  `adapter.status=incomplete`，`terminal_ok=false`，`trace_ok=false`，
  `clock_ok=false`，`evidence_ok=false`，`step_hook_ok=true`，
  `no_expert_actions=true`，`budget_ok=true`，`no_runtime_error=false`。
- `failure.json` 的错误：`RuntimeError('CLOSE target is outside unused prepared regions')`。
- 这不是“几何 rejected”，也没有有效的 331 帧原判据；不能写成 accepted 或 rejected。

## 6. 证据实际保存

| 文件 | 状态 |
|---|---|
| `result.json` | 有（action 0、prediction、errors、budget、fold_reference、verdict） |
| `bc-verdict.json` | 有，execution_error |
| `failure.json` | 有 |
| `step_hook.npz` / `.json` | 有；358 records / 358 calls，step 3..360，无 observation errors |
| `evidence/episode.mp4` | 有；181 frames，observed_steps=358，video decodes |
| `evidence/summary.json` / `manifest.json` / `timeline.jsonl` | 有 |
| `fold_initial.npz` | 有（L1 pick_index=210，yaw=0.0859541941） |
| `pfs1_stages/initial_loaded.npz` | 有 |
| `success_trace.npz` / `success_meta.json` | **无**（未到终端） |
| `bc_observations.npz` | **首例缺失**（见 §7；已修代码，未重跑） |
| `partial_trace.npz` | **首例缺失**（失败发生在终端前；已修代码，未重跑） |

`evidence_checks` 除 retention 系列（released/retreated/hold_3s/hold_4s）外全部 true；
retention false 是因为没有 terminal OPEN。

## 7. 首例暴露的 runner 证据/日志缺口（已修，未重跑）

1. **obs_rows 丢失**：`_run_policy` 内局部 `obs_rows` 在 action 1 抛错时没有返回，
   `_finalize` 收到空列表，故没有 `bc_observations.npz`。
   修复：`main` 创建 `obs_rows` 并传入 `_run_policy(..., obs_rows=...)`，异常时仍保留。
2. **pre-terminal 失败没有 partial trace**：`_save_partial_trace` 只在终端路径调用。
   修复：`main` 的 except 在无 `success_trace/partial_trace` 且已有 initial 时保存
   一帧 partial trace，并记录原因。
3. **`DOWNLOAD_DIR` 未打印**：print 在 `backend.stop()`/`SimulationApp.close()` 之后，
   close 抢先终止进程；attempt 的 `finished.json` 因此 result_dir=null。
   修复：`RESULT_FILE`/`DOWNLOAD_DIR`/`BC_VERDICT` 在 close 前打印；run script 增加
   按时间戳回退查找 result dir；attempt 增加 `effective_exit_code`。
4. **首例 attempt 记录已修复**：`finished.original.json` 保留原文件；
   `finished.json` 以已知 result dir / bc-verdict 重建，标注
   `record_repaired_after_run=true`。

首例结果目录另存派生复核（不冒充 runner 原始产物）：
`posthoc_review/policy_decisions.json` 从 runner.log 解析两次预测；
`posthoc_review/failure_snapshot.npz` 取 StepHook 最后一帧，明确标注
`source=posthoc_step_hook_last_frame`。原始 result 目录未被改写。

## 8. 分类

- **入口正常**：初始化、材料、BCPolicy/真实 torch、StepHook、相机/视频、action 0
  执行、失败保存均跑通；step_hook 计数一致，evidence 基础检查通过。
- **策略失败**：BC 的第二个动作（CLOSE）输出目标落在 prepared region 之外，
  固定 Backend 拒绝。这是闭环策略输出不可执行，不是评价器把有效折叠判失败。
- **证据/接口异常（首例代码）**：`bc_observations.npz`、`partial_trace.npz`、
  `DOWNLOAD_DIR`/finished result_dir 缺失；已修代码，但按“仅运行一次”未重跑。
- **没有 accepted/rejected 结论**：未进入终端释放/退让，未产生 331 帧，不能判折叠成功或失败。

## 9. 服务器/磁盘

- 数据盘：50G，已用 39G，可用 12G；首例结果 1.9M。单例预计 30–65M，
  20 例约 0.8–1.1G，当前剩余空间不需要扩容；若后续保留大量 step_hook/视频，
  再按 `df -h <remote-root>` 和 `du -sh` 判断。
- 本次未启动剩余 19 例，未修改物理、阈值、采样或原评价窗口。

## 10. 后续离线定位（2026-11-08，未重跑）

- 真实 torch 在**专家 action_002 观测**上同样预测错误 CLOSE：
  XYZ L2 `0.063810 m`；闭环观测实际输出误差 `0.063245 m`；两者几乎相同。
- 训练集 59 个 CLOSE 样本 mean XYZ L2 `0.100732 m`，说明 CLOSE 在训练集上就
  欠拟合；6120 的 6.38 cm 不是单例异常。
- 全部 590 条演示 `obs_holding=0.0`；源码为
  `sitecustomize._snap` 从 `action_begin` 的 `row.get('holding')` 取值，而
  `episode_evidence.execute` 的 `action_begin` 不携带 holding（恒 false）。
  stats holding std=1e-6；推理 holding=1 会归一化成 `1e6`。
- 标签对齐、字段顺序（float32 cast 差 2.95e-8）、归一化 z≤1.50 未发现错误。
- B 的完整 1340 维输入仍不可恢复（`bc_observations.npz` 缺失、StepHook 无
  joints）；未用专家值补、未追加仿真。
- 终端判据已把 `target == released EE+[0,0,0.15]` 改为
  `expert_target_consistency` 登记字段，不再作为 BC 成功门槛；保留 actual
  upward≥1cm、detach/open、held、331 帧、geometry/stability。

详见 `STAGE6_6120_CLOSE_DIAGNOSIS.md`、`STAGE6_TERMINAL_CRITERIA.md`、
`STAGE6_RUN_IDENTITY.json`。
