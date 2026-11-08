# Stage 7 最低开发验收归档

状态：**Stage 7 最低开发验收完成**（开发评估执行完成；不是 H4 泛化或统计结论）。

## 固定候选

| 项 | single | H4 |
|---|---|---|
| checkpoint | `ade60131…`（budget500 best_val） | `ff8c6945…`（epoch 389 best_val） |
| stats | `cbc4d711…` | `fe5df5c4…` |
| 归一化 | — | 与 single 的 obs_mean/obs_std/cont_mean/cont_std **逐元素相同** |
| optimizer updates | 2000 | 500 |
| 主执行口径 | 每动作单步 | **execute_k=4** |

single 与 H4 的 stats 哈希不同仅因 H4 计数元数据；归一化数组无差异。
训练预算不同（2000 vs 500 updates），不称计算预算相同，也不为凑相同预算重训。

## 检查与结果

- H4 数据：160 chunks / 590 valid / 50 padding；chunk indexing、gripper、padding 通过；
  不跨 episode、不用未来观测；holding 0/1。
- `execute_k=1/2/4` 调度离线通过：预算截断、失败停止、terminal 丢弃、chunk 内不重新预测。
- H4 6120 单次开发试跑：**accepted**，7 actions、2 policy calls、331 帧；
  第一块 4 个、第二块剩余 3 个；第二块第 4 个 CLOSE 因 terminal discarded。
- 全部 action `target_override=false`；无专家动作、无区域吸附。
- Terminal physical：upward `0.148718 m`，held OK，geometry/stable 全通过。

结果/视频：[H4 L1 结果](../stage6/STAGE7_H4_L1DEV_RESULT.md)、
[H4 离线报告](../stage6/STAGE7_H4_OFFLINE.md)、
[H4 offline check](../../../stage6_h4fix_20261108/h4fix-20261108/diagnostics/h4_l1_offline_check.json)。

## 限定

- 仅 6120 一个开发例；不证明泛化、统计优势或稳定延迟收益。
- H4 raw inference 只有 2 次（6.776/3.497 ms），不构成稳定 P95；single 无同口径计时，
  不比较。
- **原 result 的 `mode='single'` 不改写**；汇总显式使用
  `policy.kind=h4_chunk`、`execute_k=4` 识别实际策略。
- 未启动 H4 扩批 rollout；Stage 8 比较必须重新使用同一初态/Backend/预算/终端规则。
