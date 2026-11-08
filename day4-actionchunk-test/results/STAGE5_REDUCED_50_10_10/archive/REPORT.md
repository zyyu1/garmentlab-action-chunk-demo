# Stage 5 缩减版 50/10/10 — 最终报告

**状态：Stage 5 缩减版 50/10/10 完成；single/H4 离线训练完成；闭环 rollout 未执行，L2/L3 为探索性结果。**

## 1. 采集与尝试分类

| 项 | 数值 |
|---|---:|
| 有效演示 | **70**（flat 50 / perturbed 10 / crumpled 10） |
| 启动 episode（started） | **117** |
| accepted | 79 |
| incomplete（waypoint 超时） | 29 |
| rejected | 7 |
| 启动后中断 | 2（6117、6131，未重跑） |

等式：**117 started = 79 accepted + 29 incomplete + 7 rejected + 2 interrupted**。

- 其中 **9 个 accepted 缺动作前观测**（6103/6106/6107/6110/6111/6112/6113/6115/6116），保留在账本但不收录。
- **2 次初态生成错误**（6101、6300）另列，不计入 episode 次数；修复后重试成功。
- 原始账本未改写；6117、6131 未重跑。

## 2. 切分与样本

| 档 | 有效演示 | train / val / test（episode） |
|---|---:|---:|
| flat | 50 | 31 / 10 / 9 |
| perturbed | 10 | 8 / **0** / 2 |
| crumpled | 10 | 6 / 2 / 2 |
| 合计 | **70** | **45 / 12 / 13** |

- single-step **590** 条；H=4 **160** 块，共 **640 个位置**（mask 有效 **590**、padding **50**；其中 test 为 120 位置、111 有效、9 padding）。
- 输入 **1340** 维；数据集 sha256 `b756bc8d4bbbe5a4aa1c010e0b152ab347312b9c348bfe9910521a1a793650cb`。
- **限制**：perturbed 的 val=0（未挪 seed 凑数）。

## 3. 指标口径

- **single**：111 个真实动作（test 行）。
- **H4**：30 块、120 个位置，其中 111 有效、9 padding；按 **episode/动作索引**核对，111 个有效位置与 single 的 111 个真实动作**一一对应**（`same_actions=true`），9 个 padding 不对应真实动作。
- **XYZ MAE**：逐坐标平均（mean |dx|, |dy|, |dz|）；另报告欧氏距离 MAE 作为补充。
- **yaw**：周期角差 `|wrap(Δyaw)|`（wrap 到 [-π, π]）。
- **夹爪准确率**：三分类 argmax 准确率，H4 排除 padding。
- 现有训练指标已按**有效动作**平均（mask 加权，除以有效元素数）；本次补算确认一致，并补充欧氏距离与 H4 块平均对照。

## 4. 测试指标（固定测试集，未调参、未换模型）

| 模型 | XYZ MAE（逐坐标） | XYZ 欧氏 MAE | yaw MAE | 夹爪准确率 | 有效动作 |
|---|---:|---:|---:|---:|---:|
| single | 0.03010 m | 0.06603 m | 0.02470 rad | 0.9640 | 111 |
| H4（有效动作加权） | 0.00777 m | 0.01590 m | 0.00933 rad | 0.9820 | 111 |
| H4（块平均，对照） | 0.00729 m | — | 0.00874 rad | 0.9833 | 30 块 |

分档 test（single / H4，xyz 逐坐标 / yaw / 夹爪 acc）：

| 档 | single | H4 |
|---|---|---|
| flat | 0.0190 m / 0.0178 rad / 1.000 | 0.0020 m / 0.0022 rad / 1.000 |
| perturbed | 0.0342 m / 0.0275 rad / 1.000 | 0.0054 m / 0.0074 rad / 1.000 |
| crumpled | 0.0551 m / 0.0401 rad / 0.833 | 0.0252 m / 0.0299 rad / 0.917 |

## 5. 训练配置

MLP 512→512（GELU+LayerNorm）；single 连续头 (4)+夹爪 (3)；H4 连续 (4,4)+夹爪 (4,3)。连续维标准化 MSE + 夹爪 CE，H4 两项按 mask 排除 padding。AdamW lr=1e-3、wd=1e-4，batch=128，最多 100 epoch，早停 15，seed=0；按验证总损失选最佳 checkpoint。

## 6. 交付文件

- `episodes.jsonl`：70 条 episode 清单（level/seed/split/result_dir/obs_dir/exports 路径与 npz sha256）。
- `identity.json`：数据集身份、账本哈希。
- `stats.json`：train-only 统计量；`config.json`：训练配置；`summary.json`：汇总指标。
- `runs/single/`、`runs/h4/`：`best.pt`、`metrics.json`、`curves.json`。
- `report_metrics.json`：覆盖核对、逐坐标/欧氏、周期 yaw、块平均对照。

本地与远端哈希一致：`dataset_single.npz` ae263a6a…、`dataset_h4.npz` 75e6831c…、`stats.json` 8f1788d1…、`best.pt` 5bff9e67…（single）/ 93d4fca4…（h4）。
