# Stage 6 holding 修复与 single BC 离线重训报告

日期：2026-11-08。**只做离线数据修复、单次 single 重训与离线评估；未启动 Isaac 仿真、未重跑 6120、未运行其余 19 例、未追加采集、未扫参、未重训 H=4。**

## 1. 结论摘要

- 历史 holding 恢复：**590/590 动作、70/70 episode 全部对齐成功**；无缺失/歧义。
- 新数据版本：`<remote-root>/stage5-trial/holdingfix-20261108/`；
  原数据集/stats/checkpoint 全部保留。
- holding 归一化：**identity**（mean=0、scale=1），不参与均值方差标准化；其余统计仍只来自 train。
- single 固定配置重训一次：`best_val=0.3119828`，93 epochs；test 坐标 MAE `0.0279849 m`，
  欧氏 MAE `0.0622569 m`，夹爪 accuracy `0.954955`。
- CLOSE 欧氏误差仍偏高：train/val/test mean `0.088439 / 0.126007 / 0.098268 m`；
  比旧模型改善，但仍不足以让 6120 进入 prepared region。
- 6120 新预测：`[-0.151346, -0.447819, 0.024252]`、yaw `0.116103`、gripper 1；
  欧氏误差 `0.040207 m`，到 left_210 `0.041263 m` > 0.03 m；
  **仍不满足 prepared-region 条件，不启动 rollout。**

## 2. holding 恢复覆盖与来源

输出：

- `holdingfix-20261108/recovery/holding_recovery.jsonl`
- `holdingfix-20261108/recovery/holding_recovery_summary.json`
- `holdingfix-20261108/recovery/holding_validation.json`
- `holdingfix-20261108/recovery/episode_reports.json`

| 项 | 结果 |
|---|---:|
| episodes expected / checked | 70 / 70 |
| actions expected / checked | 590 / 590 |
| actions ok | **590** |
| missing / ambiguous | **0 / 0** |
| primary source `state` | 160 |
| primary source `action_end` | 430 |
| saved JSON holding used | **0** |

对齐规则：

- call 1：`action_begin` 前最后一个 `state`，要求与 begin 同 step/time；
- call c>1：正常情况下取上一个 `action_end`；若上一动作与本次之间存在
  settle/hold（L2/L3 call 6、call 12），取 `action_begin` 前最后一个
  `state`，并 cross-check 上一 `action_end` holding、`result.json` 上一动作
  post-holding。
- 每次均记录 timeline 行号、kind、call_id、observed_step、sim_time、backend_step。
- 历史 saved `action_XXX_obs.json` 的 `holding=false` **只记录、未使用**。

holding 验证：

| 项 | 结果 |
|---|---:|
| holding true / false | **410 / 180** |
| command 0 (OPEN) holding true | 90 / 180 |
| command 1 (CLOSE) holding true | **0 / 90** |
| command 2 (HOLD) holding true | **320 / 320** |
| first action false | 70 / 70 |
| last action true | 70 / 70 |
| previous CLOSE → next holding true | **90 / 90** |

这说明：CLOSE 前均为未抓持；CLOSE 后下一动作均为已抓持；HOLD 均带实际抓持；
APPROACH/RELEASE 的 OPEN 分别 false/true；不是仅“整列不全零”。

## 3. 新数据版本与归一化

| 文件/身份 | SHA256 |
|---|---|
| 原 dataset | `ae263a6a400a2300951c80473782cb6962c18d3526cd777f801f8272c210cdf6` |
| 原 stats | `8f1788d11803be7e22729758cf071f68d49ec5bae80aa387a3327112fcae746a` |
| 原 single checkpoint | `5bff9e671c54b5240b93fefb5c67507987553153bad4b5ca0a5bb92d20e48ad6` |
| 新 dataset | `1ed533e81c547b8d718950e08c3fb66cc50f0b36261cc77c91090f112d3f8c15` |
| 新 stats | `cbc4d711b2341b7ab786ca345ccb490bb32de1ebf93fb1eacc59de22d61a9ae9` |
| 新 single checkpoint | `ce7ee2aa716006d2e697e8d810248474dc365ad3771918bf4083da2b9796e938` |
| holding recovery JSONL | `e976fcb9714a22d9d8a1f3cc6edd03d1ae28f6d667508fe82a40f89ac3f5e374` |
| final episodes.jsonl | `33eb52dfd52292e558eeef516ea218053c6e4a2702b66a9cde27c6dcbcce9a00` |

- 70 episodes、590 samples、train/val/test = **385/94/111** 保持不变。
- seed/level/split/action/obs 其余数组全部与旧数据一致；仅 `obs_holding` 更新。
- `stats`: holding index 1339，mean=0，std=1；其余 obs 统计仅来自 train；
  `cont_mean/std` 仅来自 train 动作。
- 旧 dataset/stats/checkpoint 未覆盖；新 checkpoint 只配新 stats。

## 4. 固定配置重训（single 一次）

```bash
<remote-root>/envs/isaac40/bin/python -u training/train_bc.py \
  --dataset holdingfix-20261108/data --mode single \
  --out holdingfix-20261108/runs/single \
  --epochs 100 --batch 128 --lr 1e-3 --seed 0
```

- 架构：MLP 512→512（GELU+LayerNorm）；single 连续头 4 + 夹爪 3。
- AdamW lr=1e-3、wd=1e-4、batch=128、最多 100 epoch、早停 15、seed=0；
  按验证总损失选择 best；test 不参与选择。
- 实际 93 epochs；`best_val=0.31198276579380035`；device=cuda。
- 产物：`holdingfix-20261108/runs/single/{best.pt,metrics.json,curves.json}`。

## 5. 输入一致性

同一批 590 条观测，比较 `train_bc.obs_matrix` + 新 stats 与
`BCPolicy.build_obs` + 新 stats：

| 项 | 结果 |
|---|---:|
| n | 590 |
| raw max abs diff | `2.9759e-8` |
| raw allclose 1e-6 | true |
| normalized max abs diff | `5.3771e-7` |
| normalized allclose 1e-6 | true |
| holding normalized unique | `[0.0, 1.0]`（两条路径相同） |
| raw holding true/false | 410 / 180 |

holding 没有被标准化；其余字段顺序与训练矩阵一致。

## 6. 全动作指标（新模型，590 条）

**坐标 MAE** = 每样本 `(|dx|+|dy|+|dz|)/3` 再平均；
**欧氏 MAE** = 每样本 `sqrt(dx²+dy²+dz²)` 再平均。两者不可混用。

| split | n | 坐标 MAE (m) | 欧氏 MAE (m) | 欧氏 median (m) | yaw MAE (rad) | 夹爪 acc |
|---|---:|---:|---:|---:|---:|---:|
| train | 385 | 0.024469 | 0.055067 | 0.028600 | 0.021431 | 0.984416 |
| val | 94 | 0.027665 | 0.066976 | 0.030962 | 0.021008 | 0.957447 |
| test | 111 | 0.027985 | 0.062257 | 0.035670 | 0.025067 | 0.954955 |
| all | 590 | 0.025640 | 0.058317 | — | 0.022048 | 0.974576 |

- normalized cont MSE `0.136675`；grip CE `0.118898`（all）。
- 旧模型参考（旧 stats/ckpt，坐标 MAE）：test `0.030100`、yaw `0.024704`、
  grip acc `0.963964`、cont MSE `0.188213`、grip CE `0.198478`；
  旧模型全动作欧氏未在同一脚本重算，不与新欧氏直接横比。

## 7. CLOSE 分 split 欧氏误差（新模型）

| split | n | 欧氏 mean (m) | median (m) | P95 (m) | 坐标 MAE (m) | yaw MAE (rad) | 夹爪 acc |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 59 | 0.088439 | 0.073023 | 0.209502 | 0.036648 | 0.024224 | 0.983051 |
| val | 14 | 0.126007 | 0.123480 | 0.257072 | 0.049122 | 0.021088 | 0.928571 |
| test | 17 | 0.098268 | 0.061304 | 0.252527 | 0.042790 | 0.030792 | 0.882353 |

旧模型 CLOSE 欧氏参考：train `0.100732`、val `0.134008`、test `0.112092`。
新模型有改善，但 CLOSE 仍是最大误差项，远高于全动作欧氏均值。

## 8. 6120 新模型（val 调试，不是独立泛化）

输入：6120 保存的专家 `action_002_obs`（执行前观测），holding=false；
实际 prepared region 使用该观测的实际 vertices，阈值仍为 `0.03 m`。

| 项 | 值 |
|---|---|
| 新预测 xyz | `[-0.1513461899, -0.4478187518, 0.0242520389]` |
| 新预测 yaw | `0.1161026416` |
| 新预测 gripper | `1`（与专家 command 1 一致） |
| 专家 target | `[-0.1900197715, -0.4488316178, 0.0133000202]` |
| 欧氏误差 | `0.040207 m`（旧模型 `0.063810 m`） |
| 最近 region | left_210 |
| 最近距离 | `0.041263 m`（旧 `0.065246 m`） |
| within 0.03 m | **否** |

结论：holding 修复后 6120 的 CLOSE 误差从 6.38 cm 降到 4.02 cm，方向正确，
但仍超出 prepared region 阈值；**不启动下一次单例**。

## 9. 未来采集修复（未运行）

- `stage5_collect/trial/sitecustomize.py`：`_snap` 改为调用
  `evidence.state()` 读取同一时刻 holding；缺失或非 bool 直接 raise，
  不再静默 false；同时记录 attached/enabled_slots/logical/command state。
- 远端 `app/sitecustomize.py` 同步修复，保留原有 demo 授权；
  原文件备份为 `app/sitecustomize.py.original-20261108`。
- `training/build_dataset.py`：`holding_for` 要求 JSON 中存在 `holding` 且为 bool，
  缺失/类型错误直接退出。
- 未修改冻结仿真文件、控制、物理或阈值；`a5-manifest.json` 不含
  `sitecustomize.py`，冻结候选 manifest 未变。

## 10. 产物位置

远端：

- `stage5-trial/holdingfix-20261108/data/dataset_single.npz`
- `stage5-trial/holdingfix-20261108/data/stats.json`
- `stage5-trial/holdingfix-20261108/runs/single/best.pt`
- `stage5-trial/holdingfix-20261108/recovery/`
- `stage5-trial/holdingfix-20261108/report/offline_metrics.json`

本地：

- `stage6_holdingfix_20261108/holdingfix-20261108/`（数据、stats、checkpoint、恢复记录、报告）
- `stage6_6120_single_20261108/`（首例原始证据、posthoc、旧模型对照）

## 11. 下一步建议

1. **暂不启动 6120 或 19 例**：新模型 6120 最近距离仍 `0.041263 m > 0.03 m`。
2. 下一轮只做离线 CLOSE 拟合诊断：按 command/phase/level 检查 CLOSE 误差，
   确认是否还需要动作表示/损失/样本层面的修复；不扫参、不重训 H=4。
3. 若继续改进，保持新数据版本、旧数据/旧 stats/旧 checkpoint 不变；
   新模型仍只配新 stats。
4. 只有 6120 的离线 CLOSE 距离进入 0.03 m 内，才讨论新的单例 rollout。
