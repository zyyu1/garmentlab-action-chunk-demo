# Stage 5 缩减版登记（2026-11-07 批准）

**原计划保留：** 每档 50、合计 150 条有效演示的 Stage 5 要求仍登记在案（`STAGE5_FORMAL_POOL_REGISTRATION.md`、`STAGE5_DEMO_LAYER_20261106.md`），本文件不删除、不覆盖原计划。

**本缩减版：**

| 档 | 有效演示目标 | 定位 |
|---|---:|---|
| L1 flat | **50** | 主实验 |
| L2 perturbed | **10** | 探索性验证 |
| L3 crumpled | **10** | 探索性验证 |
| 合计 | **70** | — |

- 完成后标记 **“Stage 5 缩减版完成”**；**不声称**满足原 150 条要求，后续可在演示可展示后再增补实验。
- 质量、观测、导出与 split 门槛**不变**：只有通过 `_valid_obs` + 动作对齐 + single-step/H=4 导出的 accepted 轨迹才计入；split 仍按 `sha256('stage5-split-v1-<seed>')` 70/15/15，single/H4 共用。
- 采集顺序、每 seed 一次、每档最多 120 个登记 seed、正常拒绝/waypoint 超时保留继续、异常暂停等规则不变。
- 未改：冻结候选 `40858efc…`、物理、控制、评价阈值、观测与导出代码。

## 完成后的交付核对

1. 每档有效演示清单与总数（目标 50/10/10）。
2. 每档 train/val/test 实际数量；小样本导致某 split 为空时如实报告，不挪 seed。
3. single-step / H=4 导出：条数、形状、mask 规则、无跨 episode。
4. 证据路径与账本（全部尝试、失败分类）。
5. 不启动训练、不增加诊断仿真。

## 状态（2026-11-08 更新）

- **已完成**：flat 50、perturbed 10、crumpled 10 全部 `stop=target`（70 条有效演示）。
- 归档与 BC 训练结果见 `results/STAGE5_REDUCED_50_10_10/README.md`；数据集 sha256 `b756bc8d…`。
- 历史：自 2026-11-07 04:2x UTC 起生效；切换时未中断运行中的 episode，已启动 seed 未重跑。
