# Stage 8 离线执行清单

状态：**原 120 例计划保留；2026-11-09 已执行缩减版 30 例并完成。
剩余 90 例未执行。** 本文件保留原计划、资源估算和正式命令作为参考；
当前结果见 [STAGE8_REDUCED30_HANDOFF.md](STAGE8_REDUCED30_HANDOFF.md)。

## 1. 原条款与缩减方案

原计划（`Marian_Frei_GarmentLab_2024_10_stage_execution_plan.md`）：

- 冻结 configs、checkpoint selection 和 test seeds；
- 先跑 2 个 seeds dry run；
- 每个 policy × difficulty 运行 **20 episodes**；
- 两个 policy 使用相同 seeds；
- 每完成一个 difficulty 增量保存 CSV；
- 保存 representative successes/failures；
- 输出 `raw_results.csv`；
- 验收为完整 **2 × 3 × 20 = 120 episodes**。

**是否已有明确批准的 Stage 8 缩减方案：没有找到。**
Stage 5 的 `50/10/10` 是数据集划分，不自动适用于 Stage 8；本轮保留
**2 policies × 3 difficulties × 20 episodes = 120 runs / 60 unique seeds**，
不自行降低样本数。实际候选 seed 不足 60（见 §4），这是需要先解决的缺口，
不是把 20 改成 10。

## 2. 固定正式比较候选

| 项 | single | H4 |
|---|---|---|
| 选择 | budget500 `best_val` | H4 `best_val` epoch 389 |
| checkpoint | `ade6013141cfa3b114fe6583602da4b14486b96d736ffe5bbfd104cc3e517208` | `ff8c694516eb8940e089aeb0a380daab6da0d84e9ab53aeaa6cd302c9a6c21d5` |
| stats | `cbc4d711b2341b7ab786ca345ccb490bb32de1ebf93fb1eacc59de22d61a9ae9` | `fe5df5c45fb29f0c96d38a7d6cae8b8f19464c51884ae6631bdaa3dc16d553fb` |
| 归一化数组 | 基准 | 与 single 的 obs_mean/obs_std/cont_mean/cont_std **逐元素相同** |
| optimizer updates | **2000** | **500** |
| 主执行口径 | 单步 | **execute_k=4** |

- single 不是旧 `ce7ee2aa…`。
- 两个 stats 哈希不同仅因 H4 计数元数据；没有混用不同归一化。
- 训练预算不同（2000 vs 500 updates），**不称计算预算相同**，不为凑相同预算重训。
- H4 主比较只用 execute_k=4；不加入 execute_k=1/2 消融。

## 3. 必需交付物与当前状态

| 正式必需项 | 当前状态 | 尚缺 |
|---|---|---|
| 冻结 configs/checkpoint selection | 两候选固定；manifest 已写 | 无（正式启动前复核） |
| 冻结 test seeds（每档 20） | **60/60 已冻结** | 无 |
| 2 seeds dry run | **4/4 完成** | 见 [dry-run 结果](STAGE8_DRYRUN_RESULT.md) |
| 2×3×20 正式矩阵 | **0/120** | 全部 120 episodes（未启动） |
| 每 difficulty 增量 CSV | batch driver 已实现 | 正式数据尚未产生 |
| `raw_results.csv` | dry-run CSV 已产生 | 正式 120 行 |
| representative successes/failures | 规则已定 | 正式视频 |
| policy calls / latency（同 GPU、同计时边界） | CUDA 同步 instrumentation 已接入 | 正式 120 行记录 |
| 统一 Backend/预算/终端/失败/证据 | batch driver + manifest | 正式执行 |
| 独立 test 集声明 | 60 seed 冻结；6120/6121 仅 dry run | 不得称 6120 等为独立 test |

## 4. 评估初态候选择

候选规则：**不按预测或既有策略结果挑选**；按 seed 升序，先 heldout，再用
Stage 5 未进入最终 70 例的 formal/test 初态；排除 Stage 5 train/val 和
Stage 6/7 已调试 seed。Stage 4 使用仅作历史标记，因为 Stage 4 不是策略训练。

| 档 | 候选 seed（按预定顺序） | 可用 | 历史 |
|---|---|---:|---|
| flat | 4110–4119, 6100–6109 | **20/20** | 4110–4117 Stage 4 使用；4118–4119 未用；6100–6109 **均有 Stage 5 专家尝试**，未入最终 70；无 Stage 6/7 debug |
| perturbed | 4215–4229, 6300, 6301, 6305, 6310, 6311 | **20/20** | 4215 Stage 4 使用；4220–4229 本轮新生成、无专家运行；6300/6301 Stage 5 test；6305/6310/6311 Stage 5 专家尝试但未入最终 70；无 Stage 6/7 debug |
| crumpled | 4313–4319, 6500, 6501, 6503, 6506, 6509, 6510, 6511, 6512, 6513, 6514, 6515, 6518, 6519 | **20/20** | 4313–4316 Stage 4 使用；其余未用；6500 等有 Stage 5 专家尝试但未入最终 70；无 Stage 6/7 debug |

**Perturbed 补齐**：`4220–4229` 已按既定 task-scoped 协议各生成一次，
全部通过生成有效性、B_nominal、friction readback 1.0、strips、身份哈希检查；
**没有运行专家折叠**，也没有按折叠成功筛选。没有失败/替换 seed。

已调试 seed（不作为 Stage 8 全新 test）：6120、6121、6122、6148、6151（flat）；
4210–4214（perturbed）；6504、6507、4310–4312（crumpled）。

完整逐 seed 路径、初态哈希、Stage 4/5 历史见
[STAGE8_FROZEN_MANIFEST.json](../../../stage8_frozen/STAGE8_FROZEN_MANIFEST.json)；
摘要见 [SEED_INVENTORY.json](SEED_INVENTORY.json) 与
[STAGE8_SEED_AUDIT.md](STAGE8_SEED_AUDIT.md)。
两策略必须使用清单中**同一初态目录和同一哈希**；不得为某一策略换 seed 或换初态。

2 个 dry run seed `6120`、`6121`，**仅用于批次/证据/计时管线检查**，
不计入正式 20，也不称独立测试。

## 5. 统一执行口径

1. 同一 initial 文件/哈希；single 与 H4 共用。
2. 同一 Backend、初始化、观测 schema（1340）、动作 schema、L1 budget 7 / L2/L3 12、
   终端识别、331 帧评价窗口、失败保存和 evidence 规则。
3. H4 固定 execute_k=4；不做 1/2 消融。
4. 每档 20 个相同 seed，两个 policy 各 20；先完成一档再写增量 CSV；最后 `raw_results.csv`。
5. 失败即记录，不换 seed、不重试、不因中间结果调整 test 集。
6. 推理计时：同一 RTX 3090、同一进程/同一计时边界，只计 policy model forward；
   不含 Isaac 执行动作和视频写入；single/H4 都记录 call-level raw ms，再报 median/P95。
   现有 H4 2 次计时与缺失的 single 计时**不可比较**，不进入 Stage 8 结果。
7. 代表性成功/失败视频按预登记规则从结果中选取，不用来挑 seed。

## 6. 机时与存储估算

当前资源：

- GPU：RTX 3090，24576 MiB，当前 0 MiB used；
- 磁盘：50G 总，**12G 可用**；`stage6_runs/results` 130M，H4 目录 37M；
- 已有 **60/60** 个候选初态文件（含新生成 4220–4229）。

实测单例（Stage 6/7，非 Stage 8）：

- H4 L1 success：12.2 min、17.8 MB；
- single L1 success：12.9–14.4 min、17.7–18.3 MB；
- L2/L3 失败样本：4.3–11.4 min、3.3–9.2 MB。

Stage 8 估算：

- **120 runs × 约 9–14 min ≈ 19–29 h 串行**；这是按现有单例的粗略范围，
  不是承诺；2 个 dry run 另计约 0.5 h。
- 全成功存储按约 18 MB/例：**约 2.2 GB**；正式 preflight 的 120 例均值约 2.21 GB、
  最坏约 2.41 GB。12G 可用足够，但需保留余量。
- 同一 GPU 串行执行；不并行抢 GPU，避免计时污染。

## 7. 启动前必须闭合

1. **已完成**：60 个 seed 冻结；`STAGE8_FROZEN_MANIFEST.json` 120 例配对；
   每例 initial hash 已写入；两策略同一 initial。
2. **已完成**：batch driver、增量 CSV、`raw_results.csv`、forward timing CSV。
3. **已完成**：CUDA 同步 forward 计时；single/H4 同一 device/boundary。
4. **已完成**：2-seed（4 例）debug-only dry run；结果见
   [STAGE8_DRYRUN_RESULT.md](STAGE8_DRYRUN_RESULT.md)，不计入正式矩阵。
5. **未完成（按指示）**：正式 120 例未启动。

## 8. 正式批次命令（未执行）

正式 manifest：

`<remote-root>/stage8_frozen/STAGE8_FROZEN_MANIFEST.json`

启动：

```bash
cd <remote-root>/stage5-trial
<remote-root>/envs/isaac40/bin/python -u stage8/batch_run.py \
  --manifest <remote-root>/stage8_frozen/STAGE8_FROZEN_MANIFEST.json \
  --out-root <remote-root>/stage8_runs/results \
  --attempt-root <remote-root>/stage8_runs/attempts \
  --csv <remote-root>/stage8_runs/formal/raw_results.csv \
  --forward-csv <remote-root>/stage8_runs/formal/forward_timings.csv \
  --label-prefix day4-a5-stage8 \
  --policy-device cuda
```

进度：

```bash
wc -l <remote-root>/stage8_runs/formal/raw_results.csv
tail -n 3 <remote-root>/stage8_runs/formal/raw_results.csv
tail -n 20 <remote-root>/stage8_runs/attempts/day4-a5-stage8-<run_id>/runner.log
```

续跑（跳过 CSV 已有 `run_id`）：

```bash
<remote-root>/envs/isaac40/bin/python -u stage8/batch_run.py \
  --manifest <remote-root>/stage8_frozen/STAGE8_FROZEN_MANIFEST.json \
  --out-root <remote-root>/stage8_runs/results \
  --attempt-root <remote-root>/stage8_runs/attempts \
  --csv <remote-root>/stage8_runs/formal/raw_results.csv \
  --forward-csv <remote-root>/stage8_runs/formal/forward_timings.csv \
  --label-prefix day4-a5-stage8 \
  --policy-device cuda --resume
```

## 9. 本轮停止点

本轮完成 Stage 7 归档、60 初态冻结、batch/timing、4 例 dry run；
**未启动正式 120 例批次**，未训练、未追加演示采集、未删除历史证据。
