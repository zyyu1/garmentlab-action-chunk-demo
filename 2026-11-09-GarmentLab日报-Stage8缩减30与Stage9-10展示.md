# 2026-11-09 GarmentLab 日报 · Stage 8 缩减 30 例、Stage 9 展示、Stage 10 架构

**结论：Stage 8 缩减版 30 例完成（single 0/15、H4 2/15）；Stage 9 展示材料完成；原 120 例仍有 90 例未执行。**

## 1. Stage 8

### 冻结身份

| 项 | 值 |
|---|---|
| 父 manifest（60 seeds / 120 cases） | `ae1b1653…`，保留未改 |
| 缩减 manifest（15 seeds / 30 cases） | `14532f7a…` |
| single | `ade60131…`，2000 updates |
| H4 | `ff8c6945…`，500 updates，execute_k=4 |

- 60/60 初态补齐并冻结；缩减清单逐 seed 继承父 manifest 的文件与哈希。
- dry run 4 例配对：H4 2/2 accepted，single 2/2 execution_error（仅接口验证，不计正式成绩）。

### 缩减 30 例结果（2026-11-09 02:49 UTC 启动，串行，无重试）

| 档 | single | H4 |
|---|---:|---:|
| L1 flat | 0/5 | **2/5** |
| L2 perturbed | 0/5 | 0/5 |
| L3 crumpled | 0/5 | 0/5 |
| 合计 | **0/15** | **2/15** |

- H4 成功：**4111、4113**；4113 的 single 为完整 rejected（7 actions、331 帧，几何可用）。
- 其余多为 execution_error / incomplete（动作预算内未达终端条件）。
- 输出独立目录，未混入 dry run 或原 120 例；`CASE_OK 30/30`、`BATCH_COMPLETE cases=30`。

## 2. Stage 9 展示成果

- 2 页报告 `STAGE9_REPORT.pdf`
- 分档成功率图 `fig1_success_rate.png`（标注成功数/5）
- 失败类型分布 `fig2_failure_types.png`
- 60 秒中英双语字幕视频 `stage9_showcase_bilingual.mp4`
- `raw_results.csv`（30 行）、`forward_timings.csv`（99 次 forward）
- 索引：[Stage 9 README](day4-actionchunk-test/stage9/README.md)

## 3. Stage 10

- Stage 10 架构与可移植 showcase 进入仓库；README 完成英文化与架构说明（v9.1.5）。
- 版本序列：v9.1.0（Stage 9 报告 + Stage 10 架构）→ v9.1.1（60 秒 demo）→ v9.1.2（motivation）→ v9.1.3（English-only showcase）→ v9.1.4（demo 描述）→ v9.1.5（英文 README 与架构）。

## 4. 状态与限制

- 原 120 例评估仅完成 30 例（缩减版），**90 例未执行**；不得把 30 例称为完整 Stage 8。
- single 在 30 例中 0 成功；H4 2 例成功，样本小，不作泛化结论。
- 未重训、未改阈值、未追加 rollout。

## 5. 证据

- [Stage 8 缩减 30 例交接](day4-actionchunk-test/stage8/STAGE8_REDUCED30_HANDOFF.md)
- [Stage 8 seed map](day4-actionchunk-test/stage8/STAGE8_REDUCED30_SEED_MAP.md)
- [Stage 9 展示索引](day4-actionchunk-test/stage9/README.md)
- [Stage 8 README](day4-actionchunk-test/stage8/README.md)
