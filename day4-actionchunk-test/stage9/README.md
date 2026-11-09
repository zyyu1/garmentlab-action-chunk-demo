# Stage 9 展示成果

**Stage 8 缩减版评估完成；Stage 9 展示成果已整理；原 120 例评估尚有 90 例未执行。**

本目录是成果索引；实际可打开文件在
`E:\learning\project\stage9_showcase_20261109\`。

## 成果

| 文件 | 说明 |
|---|---|
| `STAGE9_REPORT.pdf` | 2 页报告 |
| `fig1_success_rate.png` | 分档成功率，标注成功数/5 |
| `fig2_failure_types.png` | 两策略失败类型分布 |
| `stage9_showcase_bilingual.mp4` | 60 秒中英双语字幕展示视频 |
| `raw_results.csv` | 30 行结果 |
| `forward_timings.csv` | 99 次 forward |
| `STAGE8_REDUCED30_MANIFEST.json` | 15 seeds / 30 cases，父哈希绑定 |
| `STAGE8_FROZEN_MANIFEST.json` | 原 60 seeds / 120 cases，保留未改 |
| `run_reduced30.sh` | 实际启动脚本 |
| `README.md` | 成果目录打开说明 |

## 固定结果

| 档 | single | H4 |
|---|---:|---:|
| L1 flat | 0/5 | **2/5** |
| L2 perturbed | 0/5 | 0/5 |
| L3 crumpled | 0/5 | 0/5 |
| 合计 | **0/15** | **2/15** |

H4 成功：4111、4113。27/30 无完整 331 帧；几何/稳定性 unavailable，未填 0。

## 状态

- 原 120 例计划保留；剩余 **90** 例未执行。
- 不补跑、不重训、不追加采集。
- Stage 6/7 只作开发背景，不合并分母。
- 报告称 single-step **MLP 行为克隆** 与 **H4 动作分块**，不称 ACT Transformer。
