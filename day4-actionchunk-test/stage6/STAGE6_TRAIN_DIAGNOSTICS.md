# Stage 6 最小离线拟合诊断（holdingfix 固定版）

日期：2026-11-08。**不启动 Isaac、不追加采集、不运行 6120/其余 19 例、不重训 H4、不扫参。**
只使用 **train** 做分组诊断；6120 仍是已使用的 val 调试例，不作为唯一放行门槛。

固定版本：

- dataset `1ed533e8…`；stats `cbc4d711…`；正式 single checkpoint `ce7ee2aa…`
- 本轮未改数据、stats、正式 checkpoint 或现有报告；小样本诊断模型独立目录保存。
- 所有下表的 XYZ 误差是**到专家动作目标的欧氏误差**；不是 Backend prepared-region
  距离，`<0.03 m` 也不等于 prepared-region 检查通过，两者分开。

## A. train by level × true command

| level | command | n | XYZ 欧氏 mean (m) | median (m) | P95 (m) | 夹爪 acc |
|---|---:|---:|---:|---:|---:|---:|
| crumpled | 0 | 24 | 0.116174 | 0.080433 | 0.288535 | 0.7917 |
| crumpled | 1 | 12 | 0.100534 | 0.091713 | 0.208934 | 0.9167 |
| crumpled | 2 | 36 | 0.091365 | 0.036135 | 0.287642 | 1.0000 |
| flat | 0 | 62 | 0.023347 | 0.019169 | 0.049536 | 1.0000 |
| flat | 1 | 31 | 0.078568 | 0.065081 | 0.175347 | 1.0000 |
| flat | 2 | 124 | 0.032606 | 0.020950 | 0.090468 | 1.0000 |
| perturbed | 0 | 32 | 0.082292 | 0.050116 | 0.227196 | 1.0000 |
| perturbed | 1 | 16 | 0.098492 | 0.071244 | 0.209667 | 1.0000 |
| perturbed | 2 | 48 | 0.037116 | 0.026504 | 0.115099 | 1.0000 |

共 385 个 train 样本。flat 最好；crumpled 的 command 0 夹爪准确率最低
（0.7917），整体误差也最大。

## B. train CLOSE by true action label

| label | n | XYZ 欧氏 mean (m) | median (m) | P95 (m) | 夹爪 acc |
|---|---:|---:|---:|---:|---:|
| L1_grasp | 31 | 0.078568 | 0.065081 | 0.175347 | 1.0000 |
| L2_recovery_grasp | 8 | 0.043685 | 0.045734 | 0.057636 | 1.0000 |
| L2_fold_grasp | 8 | **0.153300** | 0.145370 | 0.215609 | 1.0000 |
| L3_recovery_grasp | 6 | 0.064244 | 0.062784 | 0.098750 | 1.0000 |
| L3_fold_grasp | 6 | **0.136824** | 0.130502 | 0.213392 | **0.8333** |

分类只用 `level + phase + true command` 作为分析标签，未进入模型输入。
最明显的误差集中在 **L2/L3 fold CLOSE**，不是所有 CLOSE 平均地差。

## C. CLOSE 预测夹爪类别分布

| label | n | pred 0 | pred 1 | pred 2 |
|---|---:|---:|---:|---:|
| L1_grasp | 31 | 0 | 31 | 0 |
| L2_recovery_grasp | 8 | 0 | 8 | 0 |
| L2_fold_grasp | 8 | 0 | 8 | 0 |
| L3_recovery_grasp | 6 | 0 | 6 | 0 |
| L3_fold_grasp | 6 | **1** | 5 | 0 |

L3 fold 的 1 个样本被预测为 OPEN，与 B 中该组夹爪 acc 0.8333 对应。

## D. 10 条 flat train 轨迹的小样本拟合

固定选择：flat、train、按 seed 升序前 10 条完整轨迹：

`6114, 6118, 6119, 6124, 6125, 6126, 6127, 6130, 6132, 6134`

共 70 个动作。使用 holdingfix 数据、全 train stats、同一 `BCNet(1340,512,single)`；
从头初始化，seed=0；AdamW lr=1e-3、wd=1e-4、batch=128；loss 仍为
`MSE(cont_norm) + CE(gripper)`；**固定 500 epochs，无 val/早停，不评估 test**。

| epoch | train total | 子集 XYZ 欧氏 mean (m) | 子集 CLOSE 欧氏 mean (m) | 夹爪 acc |
|---:|---:|---:|---:|---:|
| 1 | 2.191908 | 0.468346 | 0.522112 | 0.657143 |
| 10 | 0.642171 | 0.083928 | 0.085365 | 0.785714 |
| 50 | 0.137694 | 0.023803 | 0.054639 | 1.000000 |
| 100 | 0.003353 | 0.004573 | 0.005228 | 1.000000 |
| 200 | 0.000570 | 0.001943 | 0.002043 | 1.000000 |
| 300 | 0.000937 | 0.002402 | 0.004679 | 1.000000 |
| 400 | 0.000160 | 0.000782 | 0.000913 | 1.000000 |
| 500 | **0.000097** | **0.000582** | **0.000665** | **1.000000** |

最终 70 条：

- 全动作：坐标 MAE `0.000285 m`，欧氏 mean `0.000582 m`、median `0.000514 m`、
  P95 `0.001064 m`，夹爪 acc 1.0；
- CLOSE（10 条）：欧氏 mean `0.000665 m`、median `0.000587 m`、
  P95 `0.001430 m`，夹爪 acc 1.0；
- 逐动作位置误差：

| action index | phase | n | mean (m) | median (m) | max (m) | 夹爪 acc |
|---:|---|---:|---:|---:|---:|---:|
| 0 | APPROACH | 10 | 0.000598 | 0.000464 | 0.001504 | 1.0 |
| 1 | GRASP | 10 | 0.000665 | 0.000587 | 0.001715 | 1.0 |
| 2 | LIFT | 10 | 0.000497 | 0.000461 | 0.001010 | 1.0 |
| 3 | TRANSFER | 10 | 0.000296 | 0.000286 | 0.000446 | 1.0 |
| 4 | TRANSFER | 10 | 0.000705 | 0.000705 | 0.001041 | 1.0 |
| 5 | PLACE | 10 | 0.000579 | 0.000559 | 0.000937 | 1.0 |
| 6 | RELEASE | 10 | 0.000731 | 0.000759 | 0.001308 | 1.0 |

结论：**同一网络、同一输入字段/归一化/损失能够记忆这 10 条 flat train 轨迹**；
这不是泛化或闭环成功，也不能推出 L2/L3 fold 同样可拟合。

## E. 证据支持的下一步

小样本拟合良好，说明全数据误差不是“训练实现/损失完全无法拟合”。第 B 表显示
误差主要集中在 **L2/L3 fold CLOSE**（15.33/13.68 cm），而 L2/L3 recovery
为 4.37/6.42 cm；第 C 表 L3 fold 还有 1 个夹爪误判。这是最小的可疑点。

**下一步只做 train-only 的 fold CLOSE 可分性/冲突审计**：

1. 取 train 的 L2/L3 fold CLOSE（8+6 条），比较其 1340 输入与目标的
   nearest-neighbor / 条件目标方差；
2. 检查是否存在相似 pre-CLOSE 观测对应差异很大的 fold target（歧义），
   或 fold CLOSE 目标本身在 train 中覆盖不足；
3. 若歧义/覆盖是主因，再讨论 loss/动作表示/样本策略；若干扰小，再查优化。
   本轮不追加数据、不扩大仿真找 seed、不扫参、不重训 H4。

## F. 实际命令与产物

```bash
# 三张 train 表
<remote-root>/envs/isaac40/bin/python -u stage6/train_group_metrics.py

# 10 条 flat train 轨迹，500 epochs
<remote-root>/envs/isaac40/bin/python -u stage6/fit_flat10.py \
  --epochs 500 --batch 128 --lr 1e-3 --weight-decay 1e-4 --seed 0
```

远端：

- `<remote-root>/stage5-trial/holdingfix-20261108/diagnostics/train_tables.{json,md}`
- `<remote-root>/stage5-trial/holdingfix-20261108/diagnostics/fit_flat10/{config,curves,metrics,predictions}.json`
- `<remote-root>/stage5-trial/holdingfix-20261108/diagnostics/fit_flat10/final.pt`

本地：

- `stage6_holdingfix_20261108/holdingfix-20261108/diagnostics/`
- 报告：[STAGE6_TRAIN_DIAGNOSTICS.md](STAGE6_TRAIN_DIAGNOSTICS.md)

正式 checkpoint `ce7ee2aa…` 未替换；小样本 `final.pt` 独立保存，不是正式模型。
