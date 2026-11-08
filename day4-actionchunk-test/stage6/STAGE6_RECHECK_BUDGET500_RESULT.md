# Stage 6 L1 开发复验结果（budget500 best_val）

purpose：`development_recheck_new_checkpoint`；seed=6120；flat/val；**不计独立泛化测试**。

本轮只执行一次，无自动重试；未重训、未切换 last.pt、未追加采集、未运行其余 19 例。

## 1. 模型与初态身份

| 项 | 值 |
|---|---|
| source checkpoint | `/root/autodl-tmp/stage5-trial/holdingfix-20261108/diagnostics/budget500/best_val.pt` |
| checkpoint sha256 | `ade6013141cfa3b114fe6583602da4b14486b96d736ffe5bbfd104cc3e517208` |
| epoch / val total | 498 / `0.024020773073634115` |
| runtime bind | `.../budget500/runtime_recheck/best.pt`（字节相同，hash `ade60131…`） |
| stats | `.../holdingfix-20261108/data/stats.json` |
| stats sha256 | `cbc4d711b2341b7ab786ca345ccb490bb32de1ebf93fb1eacc59de22d61a9ae9` |
| holding normalization | identity，index 1339，mean=0，std=1 |
| runner | `562386eec41826c818febbf930c7107f39b9d2ebafcc92de4b45be76c5205a7d` |
| step_hook | `50aca4767d965871df80df06a233b438c17a45b6b88cb21275bd6eb2f7eb9b85` |
| 初态 result / geometry | `21f9f754…` / `e2725e24…` |
| torch | 2.2.2+cu121，cuda available |

`BCPolicy` 实际加载了新 checkpoint/stats；`holding` 输入保持原始 0/1。
runner 的旧 checkpoint 身份检查用 `--skip-identity-check` 显式绕过；precheck 已独立核对
新 checkpoint/stats 完整哈希，未使用旧 stats。

## 2. 实际命令与退出码

wrapper：

```bash
bash /root/autodl-tmp/stage5-trial/stage6/run_6120_recheck_budget500.sh
```

runner 实际命令：

```bash
/root/autodl-tmp/envs/isaac40/bin/python -u \
  /root/autodl-tmp/stage5-trial/stage6/a5_bc_single.py \
  --initial-dir /root/autodl-tmp/day4-square-initial-20261107-070155-602415 \
  --checkpoint /root/autodl-tmp/stage5-trial/holdingfix-20261108/diagnostics/budget500/runtime_recheck/best.pt \
  --stats /root/autodl-tmp/stage5-trial/holdingfix-20261108/diagnostics/budget500/runtime_recheck/stats.json \
  --app-dir /root/autodl-tmp/stage5-trial/app \
  --repo-root /root/autodl-tmp/garmentlab-action-chunk-demo \
  --out-root /root/autodl-tmp/stage6_runs/results \
  --label day4-a5-bc-recheck-budget500 \
  --skip-identity-check
```

| 项 | 值 |
|---|---|
| process_exit_code | **0** |
| effective_exit_code | **3** |
| shell exit | **3** |
| attempt | `/root/autodl-tmp/stage6_runs/attempts/6120-recheck-budget500-20261108-190259` |
| result | `/root/autodl-tmp/stage6_runs/results/day4-a5-bc-recheck-budget500-20261109-030302-075279` |
| automatic_retry | false |

## 3. 预测/执行动作与终止原因

共 **2 次预测，1 个动作执行**。

| prediction index | label | command | 是否执行 | 终止/结果 |
|---:|---|---:|---|---|
| 0 | `bc_initial_open_000` | 0 OPEN | 是，1 step | 正常返回；holding/attached=false；`not_done=true` |
| 1 | `bc_grasp_01` | 1 CLOSE | **否** | Backend `choose_unused_region` 抛出 `RuntimeError('CLOSE target is outside unused prepared regions')` |

第一个失败动作是**第二次预测的 CLOSE**（1-based action 2）；失败发生在 CLOSE 执行前的
prepared-region 校验，**没有发生 CLOSE step、没有抓取**。
`action_count=1`，budget used `1/7`。

action 0 的模型 target 原样执行：

`[-0.2051526918, -0.4513928849, 0.1639995349]`，yaw `0.0784358126`，gripper 0；
`target_override=false`，`model_target_preserved=true`。

## 4. 第二次预测的 CLOSE 目标与 prepared-region

| 项 | 值 |
|---|---|
| CLOSE prediction xyz | `[-0.2299329018, -0.4553018878, 0.0150068478]` |
| yaw / gripper | `0.0907527441` / `1` |
| pre-CLOSE observation | sim `6.3333336636 s`，absolute_step `380`，holding=false |
| nearest region | left_210（pick 210） |
| nearest distance | **`0.040755 m`** |
| Backend threshold | `0.03 m`（未改） |
| within threshold | **否** |
| 抓取成功 | **否**（异常发生在执行前；holding 仍 false） |

距离按运行保存的 `bc_observations.npz` 第 2 条 pre-CLOSE 顶点、region picks
210/230/10 与同一 CLOSE target 计算；Backend 也在该次调用抛出越界异常。
这是 prepared-region 距离，不是“到专家 target 的误差”。

与首例旧模型同例对照：

| 项 | 旧模型首例 | 本次 budget500 |
|---|---|---|
| CLOSE target xyz | `[-0.132028, -0.442083, 0.037617]` | `[-0.229933, -0.455302, 0.015007]` |
| nearest left_210 距离 | `0.064629 m` | **`0.040755 m`** |
| within 0.03 m | 否 | **否** |
| 抓取 | 否 | 否 |
| 结果 | execution_error | execution_error |

CLOSE 目标更接近 region（约缩短 `0.0239 m`），但仍未进入 0.03 m，仍是同一类
“CLOSE target 不可执行”失败；**没有产生可执行的闭环改善**。

## 5. 折叠、释放、退让与评价窗口

均**未发生**：

- 无抓取，`grasp_events=0`，holding/attached 始终 false；
- 无终端 release/retreat；`terminal_release=null`；
- 无 `success_trace.npz`、`success_meta.json`、`final.npz`；
- 无 331 帧评价窗口，无 fold accepted/rejected 结论；
- 仅有 1 帧 `partial_trace.npz`（失败前状态），不凑窗口。

## 6. bc-verdict / 物理检查 / 证据

`bc-verdict.json`：

- `status=execution_error`，`success=false`；
- `adapter.status=incomplete`，`accepted=false`；
  `adapter.error="missing success_meta.json or success_trace.npz"`；
- `terminal_ok=false`、`trace_ok=false`、`clock_ok=false`、`evidence_ok=false`；
- `step_hook_ok=true`、`no_expert_actions=true`、`budget_ok=true`、
  `no_runtime_error=false`；
- 无 accepted/rejected；不是几何 rejected。

`evidence_checks`：采集/时间/视频/动作边界等为 true；因未到终端，
`retention_samples`、`retention_timing`、`retention_detached`、`retreat_moved`、
`retreat_public_action` 为 false；`terminal_saved=true`。

证据/视频：

- result：`.../day4-a5-bc-recheck-budget500-20261109-030302-075279`
- `result.json` `a877e650…`
- `bc-verdict.json` `757b1ef8…`
- `failure.json` `22ea68bf…`
- `bc_observations.npz` `49ced0e8…`
- `partial_trace.npz` `b50942cc…`
- step_hook `eb687515…` / `c4bf0a25…`
- video：`evidence/episode.mp4`，`170517 bytes`，sha256 **`ebde61a5…`**
  （`evidence_checks.video_decodes=true`）
- evidence：`evidence/summary.json` `291988f0…`，`evidence/manifest.json` `44f6ecb9…`

本地下载：`E:\learning\project\stage6_recheck_budget500_20261108\`。

## 7. 结论：实际闭环行为是否改善

**没有达到可执行的闭环改善。**

- 相同初态、相同 L1 预算和阈值；
- 新模型仍然在第二次预测的 CLOSE 前失败：prepared-region 距离
  `0.040755 m > 0.03 m`，无抓取、无终端、无 331；
- CLOSE 目标比旧模型更接近 region（`0.064629 → 0.040755 m`），但仍是同一失败类；
- 因此本轮回答是：**数值上更接近，但没有形成可执行闭环行为改善**。

首个失败动作是第二次预测的 CLOSE target 校验失败；本轮不推断其机制，只登记该事实。
