# Recovery + half-fold review

Development runs only; no frozen formal success classification.

| Run | Seed/edge | Actions | Crossed | Extent XY (m) | zP95 (m) | All checks |
|---|---|---:|---:|---|---:|---|
| day4-recovery-fold-20261102-113247-548209 | 4300/left | 12 | 0.000 | [0.45771822333335876, 0.45770876109600067] | 0.00990 | True |
| day4-recovery-fold-20261102-114705-003675 | 4300/right | 12 | 1.000 | [0.2446233555674553, 0.42751845717430115] | 0.06908 | True |
| day4-recovery-fold-20261102-115933-089864 | 4200/left | 12 | 0.000 | [0.4423837661743164, 0.4423453211784363] | 0.00990 | True |

Final sampling follows OPEN, 30 release ticks and 180 settle steps. These runs do not include a separate retreat or a second retention sample. Geometric overlap is a diagnostic proxy, not certified triangle overlap or material quality.

See audit.json for all checks, file hashes and failure reasons.

## 2026-11-02 自动接续结果：L3 right 保持，L2 recovered-yaw left 回弹

本轮通过 SSH 等待正在运行的 L3 right 结束，再执行一次 L2 left；两组均已退出，未追加其他 GPU 实验。完整结果均下载至本仓库 `day4-actionchunk-test/results/`，与远端逐文件 SHA256 一致。

| 开发尝试 | 结果目录后缀 | crossed | 释放静置后 XY extent (m) | z_p95 (m) | 动作 |
|---|---|---:|---|---:|---:|
| L3 4300 left（已运行对照） | 113247-548209 | 0.0 | 0.458×0.458 | 0.00990 | 12 |
| L3 4300 right fallback | 114705-003675 | 1.0 | 0.245×0.428 | 0.06908 | 12 |
| L2 4200 left recovered-yaw 重跑 | 115933-089864 | 0.0 | 0.442×0.442 | 0.00990 | 12 |

三组 441 顶点快照、5+7 动作、逐动作状态、60步保持记录和最终 OPEN 未持布/未附着记录核对通过。L3 right 的截图及材料分半投影支持半折候选；两个 left 最终网格为平铺，不能按动作完成认定折叠成功。9/10/9 份原始结果文件哈希核对通过。失败例的 final.png 未生成（脚本在几何门槛失败后进入 finally），但 final.npz、result.json、hold_trace 和 runner.log 均保留。另有 112937-225297 未写 result.json 的未完成目录，原因未判定，单独记录。

L2 新旧对照：旧成功例 103502-594762 与新失败例的 recovered.npz 逐字节相同；5个 recovery 目标相同；fold yaw 改变 0.002499711 rad（约0.143°），place XYZ 改变约1.000 mm。结果由 crossed=1 变为0，说明候选敏感，不能宣称 recovered-yaw 修正已普遍通过，也不据此断定单一物理根因。

审查产物：`day4-actionchunk-test/results/RECOVERY_FOLD_REVIEW_20261102/` 下的 `review.md`、`audit.json`、`recovery_fold_comparison.png`、`transfer_verification.json`、`L2_old_vs_recovered_yaw.json`、`development_attempts.json`；脚本 `day4-actionchunk-test/review_recovery_fold_nov2.py`。

限制：本组合脚本在 OPEN 后额外30个release tick和180个settle步取样，未单独退让、未保存第二个延迟保持快照。不得将本轮算作退让后保持或正式批次验收。正式成功仍为0，评价未冻结。下一收敛点为处理 L2 的 yaw-aware 回弹与最终统一路径选择，再补齐 L1 yaw-aware及评价冻结；不启动参数网格、翻腕或完整三阶段折衣。

