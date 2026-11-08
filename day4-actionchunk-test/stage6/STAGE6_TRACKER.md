# Stage 6 / Stage 7 进度 Tracker（2026-11-08）

状态：**Stage 6 最低开发验收完成**；**Stage 7 离线 H4 完成，未启动 rollout**。

## Stage 6 最低开发验收

| 事项 | 状态 | 证据 |
|---|---|---|
| 15 个 learned 调试 episode（L1/L2/L3 各 5） | 已完成 | `stage6_l1_dev_20261108/`、`stage6_l2l3_dev_20261108/` |
| L1 同初态 5 个 random | 已完成 | L1 summary |
| checkpoint 重载 | 已完成 | precheck / budget500 / L1 运行 |
| 成功/失败视频 | 已保存 | 两个结果目录的 `videos/` |
| 固定初态清单 | 已完成 | 两档 manifest |
| 无重试/不换 seed | 已执行 | attempts/finished |

结果：L1 learned **2/5**、random **0/5**；L2 **0/5**、L3 **0/5**；合计 learned **2/15**。
L1 成功为 6122、6151；其余失败分类见 L1/L2/L3 报告。L2/L3 无完整 331 帧，
物理几何/稳定性指标不可用。

初态来源：L2 4210–4214、L3 4310–4312 曾用于 Stage 4，未用于 Stage 5 模型训练，
不称全新 held-out；L3 6504/6507 是已有 final val。test `6300,6301,6516,6517` 保留。

已知差异：专家 recovery 后 `_settle(240)` + 120-step hold；runner 仅 initial
`_settle(30)`，未临时加入专家等待/补救。L2/L3 失败不单独归因数据量。

## Stage 7 离线 H4

| 事项 | 状态 | 身份 |
|---|---|---|
| 修正版 H4 数据 | 完成 | `dataset_h4.npz` `e1736499…` |
| 新 H4 stats | 完成 | `fe5df5c4…` |
| 160 chunks / 590 valid / 50 padding | 核对通过 | h4_data_check |
| 10 条 flat/train 小样本拟合 | 通过 | final total `4.07e-5`，XYZ mean `0.000214 m`，grip 1.0 |
| 全量 H4 500 epochs | 完成 | best val epoch 389，val total `0.004146` |
| best_val 重载 | 通过 | `ff8c6945…`，shape `[26,4,4]`，finite |
| 旧 H4 / single | 保留 | old H4 `75e6831c…`，single `ce7ee2aa…` |
| H4 rollout | 未启动 | 等后续授权 |

## 归档限制

- Stage 6 是开发评估，不是统计显著或 Stage 6 成功验收；L2/L3 缩减数据探索性。
- 未追加采集、未重训 H4、未修改 single checkpoint、未重跑已有结果。
- 后续 H4 rollout 必须沿用 single 的 Backend、预算、终端规则，再比较动作分块影响。

## 报告

- [Stage 6 README](README.md)
- [L1 结果](STAGE6_L1_DEV_RESULT.md)
- [L2/L3 结果](STAGE6_L2L3_DEV_RESULT.md)
- [Stage 6 交接日报](STAGE6_HANDOFF.md)
- [Stage 7 H4 离线](STAGE7_H4_OFFLINE.md)
