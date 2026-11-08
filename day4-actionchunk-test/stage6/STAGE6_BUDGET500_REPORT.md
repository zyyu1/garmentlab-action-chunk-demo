# Stage 6 全量训练预算对照（500 epochs）

日期：2026-11-08。只改变训练预算；**不启动 Isaac、不追加采集、不重训 H4、不扫参、不评估 test、不启动 rollout**。

固定：

- holdingfix 数据 `1ed533e8…`、stats `cbc4d711…`、70 episodes、seed 划分不变；
- 只用 385 个 train 样本更新模型；val 用于按既定总 loss 选模型；
- BCNet 1340→512→512（GELU+LayerNorm），holding 原始 0/1；
- `MSE(cont_norm) + CE(gripper)`；AdamW lr=1e-3、wd=1e-4、batch=128、seed=0；
- 从头初始化，固定 500 epochs，关闭早停；未加 phase/专家标签/目标信息作为输入。

实际 optimizer 更新：**2000 次**（4 batches/epoch × 500；与 `ceil(385/128)=3` 对应的实际 4 个 batch 一致）。

## 检查点曲线

| epoch | updates | train total | val total | train 全动作 XYZ 欧氏 mean (m) | L1 mean/P95/acc | L2/L3 recovery mean/P95/acc | L2/L3 fold mean/P95/acc |
|---:|---:|---:|---:|---:|---|---|---|
| 100 | 400 | 0.488915 | 0.440076 | 0.087158 | 0.070474/0.171999/1.000 | 0.072080/0.164813/0.786 | 0.302601/0.423618/1.000 |
| 200 | 800 | 0.046249 | 0.110979 | 0.027569 | 0.027984/0.069550/1.000 | 0.022500/0.041367/1.000 | 0.036420/0.078851/1.000 |
| 300 | 1200 | 0.184534 | 0.225221 | 0.052575 | 0.048700/0.078932/1.000 | 0.052592/0.078597/1.000 | 0.076597/0.126269/1.000 |
| 400 | 1600 | 0.056554 | 0.040695 | 0.026522 | 0.033733/0.060144/1.000 | 0.022067/0.046836/1.000 | 0.041999/0.084050/1.000 |
| 500 | 2000 | 0.012305 | 0.025453 | 0.017708 | 0.019392/0.057628/1.000 | 0.015434/0.025956/1.000 | 0.028800/0.057565/1.000 |

曲线在 100–300 间有非单调波动；总体训练/验证均明显下降。完整 500 点 train/val 曲线在
`budget500/curves.json`。

## best_val 与 last

best_val 按**总 val loss**选择；last 固定为 epoch 500。两者都在同一 train 上评估。

| checkpoint | epoch | updates | train total | val total | train 全动作欧氏 mean (m) | L1 mean/P95/acc | recovery mean/P95/acc | fold mean/P95/acc |
|---|---:|---:|---:|---:|---:|---|---|---|
| best_val | 498 | 1992 | 0.013997 | **0.024021** | **0.016405** | 0.016624/0.037323/1.000 | 0.020973/0.033058/1.000 | 0.035712/0.075473/1.000 |
| last | 500 | 2000 | **0.012305** | 0.025453 | 0.017708 | 0.019392/0.057628/1.000 | 0.015434/0.025956/1.000 | 0.028800/0.057565/1.000 |

- best_val 的 val loss 更低，train 欧氏/大部分分组也略好；last 的 train total 略低。
- 两者夹爪 acc 均为 1.0。
- 相对 100 epochs 附近：train 全动作从 `0.0872` 降到 `0.0164`，val loss 从
  `0.4401` 降到 `0.0240`；**train 与 val 同时改善**。
- 但 best_val 的 train 全动作仍 `0.0164 m`，L2/L3 fold 仍 `0.0357 m`
  （P95 `0.0755 m`），并非零误差。

## 判读

训练误差和 val 同时显著改善，**支持“训练预算不足是贡献因素”**；保留
`best_val.pt` 作为候选（epoch 498，val total `0.024021`）。
这不等于全数据已拟合充分：fold CLOSE 仍是最大项，train 误差也未到零。
因此不能据此自动启动 rollout，也不能用 6120 调参或作为唯一门槛。

## 产物与命令

```bash
/root/autodl-tmp/envs/isaac40/bin/python -u stage6/train_budget500.py
```

固定参数：`--epochs 500 --batch 128 --lr 1e-3 --weight-decay 1e-4 --seed 0`。

远端：

- `/root/autodl-tmp/stage5-trial/holdingfix-20261108/diagnostics/budget500/best_val.pt`
  （sha256 `ade60131…`）
- `.../budget500/last.pt`（sha256 `81e98dd9…`）
- `.../budget500/curves.json`
- `.../budget500/checkpoint_metrics.json`
- `.../budget500/best_val_metrics.json`
- `.../budget500/last_metrics.json`
- `.../budget500/report.json`、`report.md`

本地：

- [STAGE6_BUDGET500_REPORT.md](STAGE6_BUDGET500_REPORT.md)
- [budget500/curves.json](stage6_holdingfix_20261108/holdingfix-20261108/diagnostics/budget500/curves.json)
- [budget500/checkpoint_metrics.json](stage6_holdingfix_20261108/holdingfix-20261108/diagnostics/budget500/checkpoint_metrics.json)
- [budget500/best_val_metrics.json](stage6_holdingfix_20261108/holdingfix-20261108/diagnostics/budget500/best_val_metrics.json)
- [budget500/last_metrics.json](stage6_holdingfix_20261108/holdingfix-20261108/diagnostics/budget500/last_metrics.json)
- [budget500/best_val.pt](stage6_holdingfix_20261108/holdingfix-20261108/diagnostics/budget500/best_val.pt)
- [budget500/last.pt](stage6_holdingfix_20261108/holdingfix-20261108/diagnostics/budget500/last.pt)

正式 checkpoint `ce7ee2aa…`、flat10 诊断 `74eaf979…` 均未覆盖；test 未评估；无 rollout。
