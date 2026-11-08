# Stage 8 正式实验（未启动）

状态：**离线执行清单已准备；未启动任何仿真、训练或采集。**

原计划：2 policies × 3 difficulties × 20 episodes = **120 runs**，相同 seeds，
2 seeds dry run，增量 CSV、代表性视频、`raw_results.csv`。

**没有找到明确批准的 Stage 8 缩减方案**；Stage 5 的 50/10/10 不自动适用，
保留 2×3×20。当前候选初态 **50/60**：flat 20、perturbed 10、crumpled 20；
perturbed 少 10 个合规初态，不能静默凑数或改成 10。

固定候选：

- single：`ade60131…` + stats `cbc4d711…`，2000 updates；
- H4：`ff8c6945…` + stats `fe5df5c4…`，500 updates，execute_k=4；
- 两者归一化数组逐元素相同；训练预算不同，不称计算预算相同。

详见：

- [Stage 8 离线执行清单](STAGE8_OFFLINE_EXECUTION_PLAN.md)
- [候选初态摘要](SEED_INVENTORY.json)
- [完整候选初态/哈希 inventory](../../../stage8_offline_20261108/SEED_INVENTORY.json)
- [Stage 7 归档](../stage7/README.md)

**启动前缺口**：10 个 perturbed 初态；60 seed 冻结；批次/CSV/视频汇总器；
同 GPU 同边界 single/H4 计时；2-seed dry run。

本轮停止，不启动正式批次。
