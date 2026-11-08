# Stage 5 缩减版 50/10/10 — 采集、离线核对与 BC 训练结果

日期：2026-11-08。**状态：Stage 5 缩减版 50/10/10 完成；single/H4 离线训练完成；闭环 rollout 未执行，L2/L3 为探索性结果。**（原 150 条计划保留在案，本结果不声称满足原计划。）

## 0. 尝试分类与指标口径

- **117 started = 79 accepted + 29 incomplete（waypoint 超时）+ 7 rejected + 2 interrupted（6117、6131）**。
- 9 个 accepted 缺动作前观测，保留但不收录；2 次初态生成错误（6101、6300）另列，不计入 episode；原始账本未改写。
- 指标口径：
  - single：111 个 test 真实动作；H4：30 块×4=120 位置，其中 111 有效、9 padding；两者按 (episode, 动作索引) 一一对应（`same_actions=true`）。
  - XYZ MAE 为**逐坐标**平均（另附欧氏距离 MAE）；yaw 为周期角差 `|wrap(Δ)|`；夹爪准确率为三分类 argmax，H4 排除 padding。
  - 已有训练指标按**有效动作加权**（mask 加权/有效元素数），补算结果一致；另附 H4 块平均对照。

## 1. 有效演示与切分

| 档 | 有效演示 | train / val / test（episode） |
|---|---:|---:|
| flat | 50 | 31 / 10 / 9 |
| perturbed | 10 | 8 / **0** / 2 |
| crumpled | 10 | 6 / 2 / 2 |
| 合计 | **70** | **45 / 12 / 13** |

- single-step **590** 条；H=4 **160** 块（mask 有效 590/640，尾部填充按 mask 排除）。
- 观测输入 **1340** 维：vertices 1323 + ee_position 3 + ee_quat_wxyz 4 + joints 9 + holding 1；phase 仅元数据。
- 数据集身份 sha256：`b756bc8d4bbbe5a4aa1c010e0b152ab347312b9c348bfe9910521a1a793650cb`
- **空 split 如实报告**：perturbed 的 val 为 0（未挪动 seed 凑数）；全库 val 由 flat 10 + crumpled 2 组成。

## 2. 训练（固定配置，未扫参）

- 主干 MLP 512→512（GELU+LayerNorm）；single 连续头 (4) + 夹爪 logits (3)；H4 连续头 (4,4) + 夹爪 logits (4,3)。
- 损失：连续维标准化 MSE（dims 0–3）+ 夹爪 CE（3 类）；H4 两项均按 mask 排除 padding。
- AdamW lr=1e-3、wd=1e-4，batch=128，最多 100 epoch，早停 15，seed=0；按验证总损失选最佳 checkpoint。

| 模型 | test xyz MAE（逐坐标） | 欧氏 MAE | test yaw MAE | 夹爪准确率 | test cont MSE | test grip CE |
|---|---:|---:|---:|---:|---:|---:|
| single | 0.03010 m | 0.06603 m | 0.02470 rad | 0.9640 | 0.1882 | 0.1985 |
| H=4（有效动作加权） | 0.00777 m | 0.01590 m | 0.00933 rad | 0.9820 | 0.0396 | 0.0410 |
| H=4（块平均，对照） | 0.00729 m | — | 0.00874 rad | 0.9833 | — | — |

注意：H4 test 为 30 块 / 120 位置（111 有效、9 padding）；single 为 111 个真实动作；H4 的 111 个有效位置与 single 逐动作一一对应，但块级与步级数值不宜直接横比。

## 3. 文件

| 路径 | 内容 |
|---|---|
| `archive/episodes.jsonl` | 70 条 episode：level/seed/split/result_dir/obs_dir/exports 路径与 npz sha256 |
| `archive/identity.json` | 数据集身份、账本哈希、分档/切分计数 |
| `archive/stats.json` | train-only 统计量（obs 1340 维、连续动作 4 维） |
| `archive/config.json` | 训练与数据配置 |
| `archive/summary.json` | 汇总（含两模型 metrics） |
| `archive/REPORT.md` | 服务端生成的归档摘要 |
| `runs/single/`、`runs/h4/` | `best.pt`、`metrics.json`、`curves.json` |
| `dataset/` | `dataset_single.npz`、`dataset_h4.npz`、`stats.json` |

## 4. 采集账本（全部尝试保留）

- started 117、accepted 79（其中 9 条历史缺观测不收录）、incomplete 29、rejected 7、infra error 2（6101/6300 初态，均已修复重试成功）。
- 6117（中断）、6131（挂起）未重跑；6300 首败记录保留并已补修复说明。
- 三个档 `summary.json` 均为 `stop=target`。

## 5. 未启动项

- 未启动仿真 rollout，未扫参，未使用 65 条冒烟产物作为最终训练数据。
