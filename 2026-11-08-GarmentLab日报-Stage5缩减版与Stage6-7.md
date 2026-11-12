# 2026-11-08 GarmentLab 日报 · Stage 5 缩减版 50/10/10、离线训练、Stage 6/7 开发验收

**结论：Stage 5 缩减版 50/10/10 完成并训练出 single/H4 两个 checkpoint；Stage 6 最低开发评估与 Stage 7 离线 H4 完成（均为开发结论，非泛化）。**

## 1. Stage 5 缩减版完成

| 档 | 有效演示 | stop | episodes train/val/test |
|---|---:|---|---:|
| flat | 50 | target | 31 / 10 / 9 |
| perturbed | 10 | target | 8 / **0** / 2 |
| crumpled | 10 | target | 6 / 2 / 2 |
| 合计 | **70** | — | **45 / 12 / 13** |

- 尝试：**117 started = 79 accepted + 29 incomplete + 7 rejected + 2 interrupted**（6117、6131）。
- 9 条 accepted 缺观测不收录；6101、6300 初态错误另列；原始账本未改写。
- single-step **590**、H=4 **160**（640 位置：590 有效 / 50 padding）；输入 1340 维。
- 数据集 sha256 `b756bc8d4bbbe5a4aa1c010e0b152ab347312b9c348bfe9910521a1a793650cb`。
- 限制：perturbed val=0，未挪 seed。

## 2. 离线 BC 训练（固定超参，未扫参）

MLP 512→512 + single 连续(4)/夹爪(3)；H4 连续(4,4)/夹爪(4,3)；MSE+CE，AdamW 1e-3/1e-4，batch 128，≤100 epoch，早停 15。

| 模型 | test XYZ（逐坐标） | yaw | 夹爪 acc |
|---|---:|---:|---:|
| single | 0.0301 m | 0.0247 rad | 0.964 |
| H4（有效动作加权） | 0.0078 m | 0.0093 rad | 0.982 |

- checkpoint `best.pt`、`metrics.json`、`curves.json` 已归档。

## 3. Stage 6 最低开发评估

- 15 个 learned（L1/L2/L3 各 5）+ L1 5 个 random；同初态、同预算、同后端。
- 结果：L1 learned **2/5**（6122、6151），L1 random **0/5**，L2 **0/5**，L3 **0/5**；合计 **2/15**。
- L2/L3 无完整 331 帧；L2 4211 到 12 动作但 held check 失败。
- 初态 4210–4214、4310–4312 曾用于 Stage 4、未用于 Stage 5 训练，不称全新 held-out；test `6300,6301,6516,6517` 保留。

## 4. Stage 7 离线 H4

- 数据核对：160 chunks / 590 valid / 50 padding；chunk indexing、gripper、padding、不跨 episode 通过。
- 500 epochs best_val epoch 389，val total `0.004146`，checkpoint `ff8c6945…`。
- L1 6120 H4 dev 一次 accepted（7 actions、331 帧）→ **Stage 7 最低开发验收完成**；未扩批 rollout。

## 5. 证据

- [Stage 5 归档](day4-actionchunk-test/results/STAGE5_REDUCED_50_10_10/README.md)
- [Stage 6 Tracker](day4-actionchunk-test/stage6/STAGE6_TRACKER.md)、[L1 结果](day4-actionchunk-test/stage6/STAGE6_L1_DEV_RESULT.md)、[L2/L3 结果](day4-actionchunk-test/stage6/STAGE6_L2L3_DEV_RESULT.md)
- [Stage 7 归档](day4-actionchunk-test/stage7/README.md)、[H4 离线](day4-actionchunk-test/stage6/STAGE7_H4_OFFLINE.md)
