# Stage 8 缩减版 30 例交接日报

日期：2026-11-09。**在这里暂停：30 例已运行完成，无同批活跃进程。**

**状态：Stage 8 缩减版 30 例评估完成；Stage 9 展示成果已整理；原 120 例评估尚有 90 例未执行。**

## 1. 身份与清单

| 项 | 值 |
|---|---|
| 父 manifest | `/root/autodl-tmp/stage8_frozen/STAGE8_FROZEN_MANIFEST.json` |
| 父 file sha256 | `ae1b165376e1b6adc88288fdc3e2e9388ba23c1df74f7377d694f4a2c4dfc030` |
| 父 core sha256 | `364c9b7e1bdfc7c1a107508dae0ee1192eaff021d8de4e7dd5d71116527d7dce` |
| 缩减 manifest | `/root/autodl-tmp/stage8_frozen/STAGE8_REDUCED30_MANIFEST.json` |
| 缩减 file sha256 | `14532f7a5a7f77ef4f1f1396216bf30aeb04b0e126f5e6c80563eb146cad396f` |
| 缩减 core sha256 | `2c70026aa5ed0340ada5e07659f5c849dfc7d84341fe0783812c0f2428a1789e` |
| 规模 | **15 seeds / 30 cases** |
| single | `ade60131…` + stats `cbc4d711…`，2000 updates |
| H4 | `ff8c6945…` + stats `fe5df5c4…`，500 updates，execute_k=4 |
| 初态 | 全部继承父 manifest 的同一文件和哈希 |

父 120 例 manifest 未覆盖、未修改。缩减清单见
[STAGE8_REDUCED30_MANIFEST.json](../../stage8_frozen/STAGE8_REDUCED30_MANIFEST.json)；
逐 seed 历史见 [SEED_MAP](STAGE8_REDUCED30_SEED_MAP.md)。

## 2. 执行

- 实际命令：`/root/autodl-tmp/stage8_reduced30/run_reduced30.sh`
- 启动 UTC：`2026-11-09T02:49:22Z`
- 输出 root：`/root/autodl-tmp/stage8_reduced30`
- 结果/attempt/CSV 均独立，未混入 dry run 或原 120 例目录。
- 串行执行；每个 policy/seed 一次；无自动重试、无换 seed。
- 正常策略失败继续；没有身份/基础设施/观测/导出异常导致批次暂停。
- 最后日志：`CASE_OK 30/30 ...`、`BATCH_COMPLETE cases=30`。

## 3. 结果

| 档 | single success | H4 success |
|---|---:|---:|
| L1 flat | 0/5 | **2/5** |
| L2 perturbed | 0/5 | 0/5 |
| L3 crumpled | 0/5 | 0/5 |
| 合计 | **0/15** | **2/15** |

H4 成功：**4111、4113**。  
single 无 accepted；4113 为完整 `rejected`（7 actions、331 帧，几何可用）。

### 逐 seed 配对

| 档 | seed | single | H4 | actions single/H4 |
|---|---:|---|---|---:|
| flat | 4110 | execution_error | execution_error | 1/4 |
| flat | 4111 | execution_error | **accepted** | 1/7 |
| flat | 4112 | execution_error | execution_error | 1/4 |
| flat | 4113 | rejected | **accepted** | 7/7 |
| flat | 4114 | execution_error | execution_error | 2/2 |
| perturbed | 4215 | execution_error | execution_error | 1/1 |
| perturbed | 4216 | execution_error | incomplete | 6/12 |
| perturbed | 4217 | incomplete | incomplete | 12/12 |
| perturbed | 4218 | execution_error | incomplete | 1/12 |
| perturbed | 4219 | execution_error | incomplete | 6/12 |
| crumpled | 4313 | execution_error | execution_error | 1/1 |
| crumpled | 4314 | incomplete | execution_error | 12/0 |
| crumpled | 4315 | execution_error | execution_error | 6/0 |
| crumpled | 4316 | execution_error | incomplete | 0/12 |
| crumpled | 4317 | execution_error | execution_error | 1/1 |

## 4. 失败分类

状态计数：**accepted 2、rejected 1、incomplete 7、execution_error 20**。

| 类别 | 次数 | 说明 |
|---|---:|---|
| `Grasp is outside the preselected cloth region` | 4 | single 3、H4 1 |
| `CLOSE target is outside unused prepared regions` | 9 | single 7、H4 2 |
| `Square waypoint velocity/position did not converge` | 6 | single 1、H4 5 |
| `Release before another CLOSE` | 1 | single 4114 |
| 完整 rejected（无 error） | 1 | single 4113 |
| incomplete（12 actions，未到 terminal/331） | 7 | single 2、H4 5；H4 均见 pre-release held check failed |

- 0-action execution_error 的 evidence audit 出现
  `non-BC action label` / `action count outside BC budget` 的 fail-closed 警告；
  对应 result 没有实际执行动作，**不能据此认定专家动作注入**。
- 所有失败均保留 result/attempt/partial trace/video；没有补跑。

## 5. 计时、几何与视频

### Forward timing（同 RTX 3090、CUDA 同步、仅 model forward）

| policy | cases | forward calls | first mean ms | subsequent median ms | subsequent P95 ms |
|---|---:|---:|---:|---:|---:|
| single | 15 | 70 | 26.369 | 1.168 | 1.849 |
| H4 | 15 | 29 | 27.493 | 1.303 | 1.509 |

first 单独统计；每 policy 仅 15 例，P95 只作描述，不宣称稳定延迟优势。
H4 call 数少主要来自失败/截断，不能单独解释为效率优势。

### 完整 331 窗口

- 3/30 有完整窗口：single 4113（rejected）、H4 4111、H4 4113。
- 其余 27 例无完整窗口，几何/稳定性 **不可用**，CSV 标记
  `unavailable: no complete 331-frame window`，未填 0。

### 代表视频（取自现有 30 例，不另跑）

- [H4 4111 success](../../../stage8_reduced30_20261109/videos/H4_flat_4111_success.mp4)
- [H4 4113 success](../../../stage8_reduced30_20261109/videos/H4_flat_4113_success.mp4)
- [single 4110 failure](../../../stage8_reduced30_20261109/videos/single_flat_4110_failure.mp4)
- [H4 4215 failure](../../../stage8_reduced30_20261109/videos/H4_perturbed_4215_failure.mp4)
- [H4 4313 failure](../../../stage8_reduced30_20261109/videos/H4_crumpled_4313_failure.mp4)

远端 30 个结果目录均有 `evidence/episode.mp4`。

## 6. 产物与复现

| 文件 | 内容 |
|---|---|
| `raw_results.csv` | 30 行数据（header 另计） |
| `forward_timings.csv` | 99 次 forward 调用（header 另计） |
| `summary.json` / `summary.md` | 成功率、配对、失败、计时、视频索引 |
| `run_reduced30.sh` | 实际启动脚本 |
| `batch.log` | `CASE_OK ...` 与 `BATCH_COMPLETE cases=30` |
| `started_utc.txt` | `2026-11-09T02:49:22Z` |
| `results/` | 30 个结果目录 |
| `attempts/` | 30 个 batch attempt 日志 |

本地副本：`stage8_reduced30_20261109/`（CSV、summary、脚本、5 个代表视频）。  
远端：`/root/autodl-tmp/stage8_reduced30/`。

本地：[raw_results.csv](../../../stage8_reduced30_20261109/raw_results.csv) ·
[forward_timings.csv](../../../stage8_reduced30_20261109/forward_timings.csv) ·
[summary.json](../../../stage8_reduced30_20261109/summary.json) ·
[summary.md](../../../stage8_reduced30_20261109/summary.md)。

复现：使用同一缩减 manifest 重跑批次；不要改动 seed/checkpoint/stats/execute_k。
本批已结束，未保留活跃进程；如需补齐剩余 90 例，应派生父 manifest 的补集清单，
沿用同一协议，**不要重跑本 30 例**。

```bash
bash /root/autodl-tmp/stage8_reduced30/run_reduced30.sh
# 只应在明确要求复现/续跑时使用；不得覆盖已有 reduced30 目录
```

## 7. 磁盘与限制

- 磁盘：50G 总，**12G 可用**；本批约 **205 MB**。
- 未扩容、未删除历史证据、未重训、未追加演示采集。
- **限制**：
  - 缩减版仅 15 seeds、30 episodes，不是正式 120 例子集之外的统计样本；
    H4 2/15、single 0/15 只作描述，不能宣称 H4 泛化优势或统计显著性。
  - 初态中 4110–4114、4215、4313–4316 曾用于 Stage 4 专家，因此不是全新独立 test；
    它们未进入 Stage 5 train/val，也未用于 Stage 6/7 策略调试。
  - 27/30 无完整 331 帧，物理几何/稳定性指标不可用。
  - H4 成功均在 L1；L2/L3 均为 0/5。
  - 0-action 失败的 audit 警告已保留，未据此推断动作注入。

## 8. 剩余工作

- 原 120 例计划保留；**剩余 90 例未执行**（父 manifest 120 − 本缩减 30）。
- 若继续，必须使用同一父 manifest、同一 seed/初态、同一 checkpoint/stats、
  同一 Backend/预算/终端/331 帧/计时协议；H4 仍 execute_k=4。
- 不自动执行剩余 90 例，不重训、不扩采、不扩容。

**暂停点：本批已完成并归档；等待接手者决定是否补齐剩余 90 例。**
