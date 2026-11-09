# Stage 8 实验（缩减版 30 例完成；原 120 例保留）

状态：**Stage 8 缩减版 30 例评估完成；原 120 例计划保留，剩余 90 例未执行。**
60 个初态和 120 例父 manifest 已冻结；4 例 dry run 完成。

缩减版结果：single 0/15、H4 2/15（H4 成功 4111、4113）；L2/L3 均为 0/5。
见 [缩减版交接日报](STAGE8_REDUCED30_HANDOFF.md) 与
[缩减版 seed map](STAGE8_REDUCED30_SEED_MAP.md)。

dry run：H4 6120/6121 各 accepted（7 actions、2 calls、331 帧）；
single 6120/6121 各 execution_error（1 action，无 331）；接口检查通过。
两次接口修正与原始失败记录见 [dry-run 结果](STAGE8_DRYRUN_RESULT.md)。

原计划：2 policies × 3 difficulties × 20 episodes = **120 runs**，相同 seeds，
2 seeds dry run，增量 CSV、代表性视频、`raw_results.csv`。

- 60/60 初态：flat 20、perturbed 20、crumpled 20；`4220–4229` 已按 task-scoped
  协议各生成一次。
- 没有批准的缩减方案；Stage 5 的 50/10/10 不自动适用，保留 2×3×20。
- 与最终 train/val、Stage 6/7 调试 seed 无重叠；Stage 4/5 专家使用已逐 seed 标记。
- `6300/6301` 是最终 test，不是 train/val；不是全新未使用初态。
- 6120/6121 仅用于 dry run，不作为正式 test。

固定候选：

- single：`ade60131…` + stats `cbc4d711…`，2000 updates；
- H4：`ff8c6945…` + stats `fe5df5c4…`，500 updates，execute_k=4；
- 两者归一化数组逐元素相同；训练预算不同，不称计算预算相同。

文件：

- [Stage 8 缩减版交接日报](STAGE8_REDUCED30_HANDOFF.md)
- [缩减版 seed map](STAGE8_REDUCED30_SEED_MAP.md)
- [Stage 8 离线执行清单](STAGE8_OFFLINE_EXECUTION_PLAN.md)
- [配对 dry run 结果](STAGE8_DRYRUN_RESULT.md)
- [Seed 审计](STAGE8_SEED_AUDIT.md)
- [Seed 摘要](SEED_INVENTORY.json)
- [冻结父 manifest](../../../stage8_frozen/STAGE8_FROZEN_MANIFEST.json)
- [缩减 manifest](../../../stage8_frozen/STAGE8_REDUCED30_MANIFEST.json)
- [Stage 7 归档](../stage7/README.md)

**原 120 例保留，剩余 90 例未执行；本轮暂停。**
