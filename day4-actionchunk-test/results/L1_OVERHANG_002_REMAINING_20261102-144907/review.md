# L1 overhang 0.02: remaining three requested cases

Development runs only. Full downloads were verified against remote SHA256 before each next run.

| Seed | Run | Runner passed | Actions | Crossed | Alignment (mm) | IoU proxy | zP95 (mm) | Checks |
|---|---|---|---:|---:|---:|---:|---:|---|
| 4101 | day4-l1-xfold-yaw-aware-20261102-224914-136557 | True | 7 | 1.000 | 13.823 | 0.365 | 67.657 | True |
| 4106 | day4-l1-xfold-yaw-aware-20261102-225757-935709 | True | 7 | 1.000 | 13.824 | 0.377 | 67.527 | True |
| 4103 | day4-l1-xfold-yaw-aware-20261102-230743-527418 | True | 7 | 1.000 | 13.811 | 0.370 | 67.468 | True |

Snapshots cover hold end, release, 30 release ticks, and 180 settle steps. No separate retreat or later retention snapshot. This review does not freeze an acceptance threshold or count formal successes.

## 2026-11-02 L1 过折 0.02：最后三例已执行并逐例下载

按用户指定顺序 4101 → 4106 → 4103，各执行一次 `L1_XFOLD_OVERHANG=0.02`；每例完成后下载完整目录并核对 SHA256，再启动下一例。三例 runner_exit=0、passed=true、errors=[]，各7个公开动作，总计57份原始文件哈希一致。未追加重试或其他GPU实验，三例进程均已结束。

| seed | 完整运行目录 | crossed | alignment (mm) | IoU代理 | z_p95 (mm) |
|---|---|---:|---:|---:|---:|
| 4101 | `day4-l1-xfold-yaw-aware-20261102-224914-136557` | 1.0 | 13.823 | 0.3646 | 67.657 |
| 4106 | `day4-l1-xfold-yaw-aware-20261102-225757-935709` | 1.0 | 13.824 | 0.3766 | 67.527 |
| 4103 | `day4-l1-xfold-yaw-aware-20261102-230743-527418` | 1.0 | 13.811 | 0.3700 | 67.468 |

独立重算与日志一致：seed/overhang、441顶点、动作状态、60步保持、最终OPEN未附着及释放后几何检查全部通过。05_release_stationary→06_final_3s 平均顶点位移：4101约0.186mm、4106约0.223mm、4103约0.181mm。阶段图及三张最终PNG已视觉检查，未摊平；仍存在拱形/偏置覆盖和机器人遮挡，不能用passed替代正式折叠质量验收。

本地overhang=0.02的结果现已覆盖seeds4100–4109，10例runner均通过且crossed=1.0；覆盖CSV记录各结果JSON哈希。该覆盖统计不证明正式统一配置/阈值已经冻结，也不等同正式批次成功。

本轮汇总位于 `day4-actionchunk-test/results/L1_OVERHANG_002_REMAINING_20261102-144907/`，含 `batch.json`、每例SSH完整日志/下载哈希、`independent_audit.json`、`review.md`、`l1_overhang_comparison.png` 和 `l1_overhang_002_development_coverage.csv`。完整原始目录位于同级results目录。

限制：本7动作runner在OPEN后30个release tick和180个settle步取样，没有独立退让或3秒后的第二保持样本；本轮为开发验证，正式成功仍为0。下一步需统一L1过折与L2/L3折叠定义和评价口径，再冻结正式评价；不自动启动额外实验。

