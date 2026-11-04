# 源码差异：rc8b → l2pose 诊断

文件集合不变（63 项）。相对 rc8b **60 项逐字节相同**，仅 3 项变化：

| 文件 | 变化 |
|---|---|
| `a5-candidate.json` | 4202 的 initial 指向派生初态；modes 仅 `single` |
| `a5-rc2-pfs1-observation-v2.json` | 诊断登记（单例、账本、解释、边界） |
| `run-a5-rc2-pfs1-observation-v2.sh` | 单例编排、诊断预检、独立账本 |

## 未改（rollout 物理/控制/观测）

`a5_recovery.py`、`a5_capture.py`、`pfs1_observation_v2.py`、`a5_l1.py`、`a5_entry.py`、`stage4_success_v1.py`、`stage4-success-v1.json`、资产、初态 plan 与 held-out 列表。

## 诊断初态

- 只变换 `final`（旧折叠几何 → 新整体位姿）；`flat_settled` 与新旧初态逐位相同；速度不恢复、清零。
- 变换由两个初态的 441 个 `final` 顶点计算，不依据任何 rollout 结果。
- 派生初态标记为 `diagnostic-l2-pose-control-v1`，不属于正式 task-scoped 初态。
