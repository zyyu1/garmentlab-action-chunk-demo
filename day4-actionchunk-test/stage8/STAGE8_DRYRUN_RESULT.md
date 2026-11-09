# Stage 8 配对 dry run 结果

日期：2026-11-09。**4 例管线 dry run 完成；不计入正式 120 例；正式批次未启动。**

## 1. 冻结身份

| 项 | 值 |
|---|---|
| 正式 manifest | `/root/autodl-tmp/stage8_frozen/STAGE8_FROZEN_MANIFEST.json` |
| formal core sha256 | `364c9b7e1bdfc7c1a107508dae0ee1192eaff021d8de4e7dd5d71116527d7dce` |
| dry manifest | `/root/autodl-tmp/stage8_frozen/STAGE8_DRYRUN_MANIFEST.json` |
| dry core sha256 | `1e28b3a4eec4aac12634617be2755486ba57cca12908780e26a029e4f98d0c30` |
| single | `ade60131…` + stats `cbc4d711…`；2000 updates |
| H4 | `ff8c6945…` + stats `fe5df5c4…`；500 updates；execute_k=4 |
| 60-seed manifest | flat 20 / perturbed 20 / crumpled 20 |

两策略 stats 归一化数组逐元素相同；训练预算不同，不称计算预算相同。

## 2. 接口问题与修正（均保留原始失败记录）

1. **第一次启动**：manifest 的策略名 `single` 直接传给 runner，而 runner CLI 只接受
   `bc`/`h4`，argparse exit 2，无 result。
   - 保留：`/root/autodl-tmp/stage8_dryrun/`（CSV 中 `interface_error` + runner.log）。
   - 修正：batch driver 将 `single → bc`，其余策略名不变。
2. **第一次修正运行**：single 6120 完成 `execution_error`，但 runner 的 `_predict`
   重建 prediction 时丢掉了 `inference_ms`，导致 `policy_calls.inference_ms=None`。
   - 保留：`/root/autodl-tmp/stage8_dryrun_fixed/`。
   - 修正：`_predict` 保留 `inference_ms`；重新冻结 manifest（runner hash
     `e0d522ba…`），并用新的独立目录重跑 4 例。
3. **最终有效 dry run**：`/root/autodl-tmp/stage8_dryrun_final/`。未自动重试；
   上述两次是修正后的显式人工重跑，失败记录未删除。

## 3. 四例结果

| seed | policy | status | actions | calls | discarded | 331帧 | first ms | median ms | p95 ms |
|---:|---|---|---:|---:|---:|---|---:|---:|---:|
| 6120 | single | execution_error | 1 | 2 | 0 | 无 | 28.540 | 15.497 | 28.540 |
| 6120 | H4 | accepted | 7 | 2 | 1 | 有 | 32.386 | 16.733 | 32.386 |
| 6121 | single | execution_error | 1 | 2 | 0 | 无 | 18.415 | 9.915 | 18.415 |
| 6121 | H4 | accepted | 7 | 2 | 1 | 有 | 25.532 | 13.505 | 25.532 |

- single 6120：`CLOSE target is outside unused prepared regions`，无 success_trace；
  partial trace + video 可读。
- single 6121：`Manual single anchor did not follow within 10mm diagnostic bound`，
  无 success_trace；partial trace + video 可读。
- H4 6120：terminal upward `0.148717 m`，held pos `0.000233 m`，arm speed
  `0.095836 rad/s`，anchor gap `0.001931 m`，331 帧。
- H4 6121：terminal upward `0.149556 m`，held pos `0.004121 m`，arm speed
  `0.083373 rad/s`，anchor gap `0.001976 m`，331 帧。

## 4. H4 调度/预算核对

两例 H4 完全一致：

- `execute_k=4`，budget=7；
- call 0：预测 4，执行 0–3，无 discard；
- call 1：预测 4，剩余预算 3，执行 4–6；预测的第 4 项 CLOSE 因 terminal
  `discarded`，未执行；
- actual actions = 7；policy calls = 2；discarded = 1；
- chunk 内无重新预测；全部 `target_override=false`；
- 终端 action 6 为 `bc_release_open`，terminal 通过，331 帧完成。

## 5. CSV/证据一致性

`check_dryrun.py` 结果：

- raw_results.csv **4 行**；forward_timings.csv **8 行**；
- 每例 `status`/`action_count`/`policy_calls` 与 `result.json` 一致；
- 两对 seed 的 initial `result.json`/`initial_geometry.npz` 哈希完全一致；
- 所有 result 的 `policy.device=cuda`；H4 execute_k=4；
- 所有 forward `inference_ms` finite；首 call 单独记录；
- 4/4 evidence 可读（partial trace 或 331 trace + video）；
- `geometry_available=false` 的 single failure 单不填 0，标记
  `unavailable: no complete 331-frame window`。

结果文件：

- `/root/autodl-tmp/stage8_dryrun_final/raw_results.csv`
- `/root/autodl-tmp/stage8_dryrun_final/forward_timings.csv`
- `/root/autodl-tmp/stage8_dryrun_final/check.json`
- `/root/autodl-tmp/stage8_dryrun_final/results/...`

## 6. 计时边界与限制

- 同一 RTX 3090，CUDA 同步；计时仅包住 policy model forward；
  不含初始化、模型加载、Isaac 步进和视频写入。
- first call 单列；上表 median/p95 仅描述 2 次 call/例，**不是稳定延迟结论**。
- single/H4 都使用同一 device/boundary；但本 dry run 不作为策略延迟优劣比较。

## 7. 结论与边界

- 4/4 接口检查通过；H4 2/2 accepted，single 2/2 execution_error。
- dry run 只验证管线，**不计入正式 120 例**，不据此选 seed 或推广结果。
- 正式 120 例未启动；下一步只能用冻结 manifest 启动，不自动扩批。
- 当前磁盘：50G 总，**12G 可用**；`stage8_dryrun_final` 约 41 MB。
