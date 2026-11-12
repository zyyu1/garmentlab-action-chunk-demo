# Stage 7 H4 L1 开发试跑（seed 6120）

日期：2026-11-08。**Stage 7 最低开发验收完成**（一个开发例；不是泛化/统计结论）。
**一次开发试跑；不重训、不采集、不重跑 single、不扩展其他 seed、未启动 H4 扩批 rollout。**

## 1. 固定身份

| 项 | 值 |
|---|---|
| H4 checkpoint | `.../h4fix-20261108/runs/h4_budget500/best_val.pt` |
| H4 checkpoint sha256 | `ff8c694516eb8940e089aeb0a380daab6da0d84e9ab53aeaa6cd302c9a6c21d5` |
| H4 stats | `.../h4fix-20261108/stats.json` |
| H4 stats sha256 | `fe5df5c45fb29f0c96d38a7d6cae8b8f19464c51884ae6631bdaa3dc16d553fb` |
| single 对照 | budget500 `ade60131…` 的 6120 recheck；未重跑 |
| 初态 | `<remote-root>/day4-square-initial-20261107-070155-602415` |
| 初态 result / geometry | `21f9f754…` / `e2725e24…` |
| H4 runner | `488711adb25f1258bf9b11df7b9f0db9d4596215391f9429490cfc5e129f6be2` |
| H4 policy / scheduler | `4c96c29d…` / `27b895f2…` |

### stats 差异核对

single stats `cbc4d711…` 与 H4 stats `fe5df5c4…` 的哈希不同，但四组归一化数组
**逐元素完全相同**：

| 数组 | equal | max abs diff |
|---|---|---|
| `obs_mean` | true | 0.0 |
| `obs_std` | true | 0.0 |
| `cont_mean` | true | 0.0 |
| `cont_std` | true | 0.0 |

差异仅来自 H4 计数/元数据（`h4_chunks` 等）；没有静默混用不同归一化。

## 2. 离线检查

`check_h4_l1_offline.py` 使用真实 torch：

- H4 输出连续 `[1,4,4]`、夹爪 logits `[1,4,3]`，finite；
- 4 个动作反归一化，gripper 合法；
- execute_k=1/2/4 调度：
  - k=4：2 calls、7 executed、1 discarded（第二块预测 4、预算只剩 3）；
  - k=1：7 calls、7 executed、21 discarded；
  - k=2：4 calls、7 executed、9 discarded；
- action failure 在 chunk 内第 2 项后停止并丢弃余项；
- terminal 在 chunk 内第 3 项后停止并丢弃余项；
- 无 Isaac 启动，未评估 test。

结果：[h4_l1_offline_check.json](stage6_h4fix_20261108/h4fix-20261108/diagnostics/h4_l1_offline_check.json)。

## 3. 实际试跑

命令：

```bash
<remote-root>/envs/isaac40/bin/python -u stage6/a5_bc_single.py \
  --initial-dir <remote-root>/day4-square-initial-20261107-070155-602415 \
  --checkpoint .../h4fix-20261108/runs/h4_budget500/best_val.pt \
  --stats .../h4fix-20261108/stats.json \
  --app-dir <remote-root>/stage5-trial/app \
  --repo-root <remote-root>/garmentlab-action-chunk-demo \
  --out-root <remote-root>/stage6_runs/results \
  --label day4-a5-h4-l1dev-6120 \
  --policy h4 --execute-k 4 --skip-identity-check
```

| 项 | 值 |
|---|---|
| process_exit_code | 0 |
| effective_exit_code | 0 |
| attempt | `<remote-root>/stage6_runs/attempts/h4-l1dev-6120-20261108-223301` |
| result | `<remote-root>/stage6_runs/results/day4-a5-h4-l1dev-6120-20261109-063303-357071` |
| status | **accepted** |
| action_count | **7 / 7** |
| policy calls | **2** |
| actual actions / discarded | **7 / 1** |

`result.policy.kind=h4_chunk`；继承自 single 模板的 `mode='single'` 字段是旧模板字段，
不代表实际策略；实际 checkpoint/stats/H4Policy/H4 scheduler 身份以本表哈希为准。

### Policy calls

| call | start action | inference ms | remaining | predicted | executed | discarded | stop |
|---:|---:|---:|---:|---|---|---|---|
| 0 | 0 | 6.7761 | 7 | 4 | 0,1,2,3 | — | — |
| 1 | 4 | 3.4973 | 3 | 4 | 4,5,6 | chunk 3 (`CLOSE`) | terminal_stop |

- 第一块执行 4 个；第二块最多剩余 3 个。
- 第二块第 4 个预测 `[0.02493,-0.43587,0.03534]` / yaw `0.09121` / CLOSE 因终端停止被
  **discarded**，未执行。
- chunk 内没有重新预测；动作顺序与预测顺序一致。
- 推理计时只包含 H4 模型 forward，不包含 Isaac 执行/视频写入；2 次样本不构成稳定 P95。

### 动作

| # | label | command | holding after | target xyz / yaw |
|---:|---|---:|---|---|
| 0 | bc_initial_open_000 | OPEN | false | `[-0.188101,-0.449028,0.160812] / 0.084337` |
| 1 | bc_grasp_01 | CLOSE | true | `[-0.191506,-0.448970,0.013041] / 0.087180` |
| 2 | bc_hold_002 | HOLD | true | `[-0.132011,-0.444699,0.160862] / 0.085763` |
| 3 | bc_hold_003 | HOLD | true | `[0.010324,-0.432402,0.224130] / 0.086250` |
| 4 | bc_hold_004 | HOLD | true | `[0.149562,-0.419850,0.170740] / 0.089270` |
| 5 | bc_hold_005 | HOLD | true | `[0.228247,-0.412339,0.033789] / 0.089635` |
| 6 | bc_release_open | OPEN | false | `[0.227395,-0.412063,0.184929] / 0.090090` |

- 全部 `target_override=false`、`model_target_preserved=true`。
- 无专家补抓/补释放/区域吸附。

## 4. 终端与原评价

- grasp_count=1、intermediate_release_count=0；
- fold slot / reference OK；held check：
  position error `0.000233 m`、arm speed `0.095837 rad/s`、anchor gap
  `0.001994 m`、orientation reached；
- upward displacement `0.148718 m`；
- terminal target 与 expert `released EE+0.15` 距离 `0.001227 m`（atol 0.002），
  但该关系仍只作一致性记录，不是 BC 门槛；
- **331 帧完成**，release_clock absolute_step 1440；
- geometry/stability 全部通过：
  centroid drift max `1.166e-4 m`、vertex drift p95 max `1.601e-4 m`、
  vertex speed p95 max `2.323e-3 m/s`；
- `bc-verdict=accepted`、`success=true`、physics held/released/geometry/stable 全 true。

证据：

- `result.json` `a2c92cc5…`
- `bc-verdict.json` `4b802f4a…`
- `success_trace.npz` 331 帧
- `final.npz`、`success_meta.json`、`step_hook.npz`
- video `evidence/episode.mp4`，682072 bytes，sha256 `3b4d8781…`

## 5. 与 single 6120 对照

| 项 | single budget500 `ade60131…` | H4 `ff8c6945…` |
|---|---|---|
| result | `day4-a5-bc-recheck-budget500-20261109-030302-075279` | `day4-a5-h4-l1dev-6120-20261109-063303-357071` |
| status | execution_error | **accepted** |
| action_count | 1 | **7** |
| 抓取 | 无 | **有**（grasp_count=1） |
| 释放/退让 | 无 | **完成**（upward 0.1487 m） |
| 331 帧 | 无 | **完成** |
| 首个失败 | 第二次预测 CLOSE 超出 prepared region | — |

- single 的 CLOSE 目标距离 `0.040755 m > 0.03`；H4 首次 CLOSE 在
  `PREPARED_GRASP_REGION_DISTANCE 0.002077 m`，抓取成功。
- single 没有同口径 H4/single 推理计时；**不可比较**。不为补计时重跑 single。
- 这不是泛化或统计结论：仅 6120 一个开发例。

## 6. 边界

- 只跑一次；无自动重试、无其他 seed、无 L2/L3、无 H4 扩批 rollout。
- H4 成功仅代表该开发例；不能据此宣称 H4 优于 single 或 Stage 7 通过。
- single/H4 必须继续使用相同 Backend、预算、终端规则；后续才比较动作分块影响。
