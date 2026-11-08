# Stage 7 离线部分：修正版 H=4 数据与训练

日期：2026-11-08。**只做离线数据重建、拟合检查和训练；未启动 Isaac、未追加采集、未修改 single checkpoint、未启动 H4 rollout。**

## 1. H4 数据身份

| 项 | 值 |
|---|---|
| 新 H4 数据 | `/root/autodl-tmp/stage5-trial/holdingfix-20261108/h4fix-20261108/dataset_h4.npz` |
| 新 H4 sha256 | `e17364992c97010589d513b249c93033d3320c145e17895d097a5cc9fd6e6051` |
| 新 stats | `.../h4fix-20261108/stats.json` |
| 新 stats sha256 | `fe5df5c45fb29f0c96d38a7d6cae8b8f19464c51884ae6631bdaa3dc16d553fb` |
| 来源 single | `.../holdingfix-20261108/data/dataset_single.npz` `1ed533e8…` |
| 旧 H4 数据 | `/root/autodl-tmp/stage5-trial/training/final/dataset_h4.npz` `75e6831c…`（保留） |
| 旧 H4 checkpoint | `.../training/runs/h4/best.pt` `93d4fca4…`（保留） |
| single checkpoint | `.../runs/single/best.pt` `ce7ee2aa…`（未修改） |

数据构造：

- 同一 70 episodes、seed/split、train-only stats；
- 每块输入只取起始动作前的 1340 维观测；
- 目标最多 4 个后续动作；padding 不参与损失；
- 不跨 episode、不使用未来观测；
- holding 取修正版 single 的 chunk-start 值，保持 0/1。

## 2. 数据核对

`h4_data_check.json`：

| 项 | 值 |
|---|---:|
| chunks | **160** |
| valid actions | **590** |
| padding | **50** |
| chunks by level | flat 100 / perturbed 30 / crumpled 30 |
| valid by level | flat 350 / perturbed 120 / crumpled 120 |
| chunks by split | train 104 / val 26 / test 30 |
| valid by split | train 385 / val 94 / test 111 |
| max start-observation diff vs single | **0.0** |
| max action diff vs single | **0.0** |
| no cross-episode | true |
| no future observation | true |
| old structural fields equal | action/mask/start/seed/level/split/phase 全 true |
| holding true / false chunk starts | 90 / 70 |

`stats.json` 同步为 h4_chunks=160、mask_ones=590、mask_total=640；
单步 stats 仍为 385/94/111，holding identity（index 1339，mean=0，std=1）。

## 3. 小样本 H4 拟合检查

固定 10 条 flat/train 轨迹：6114, 6118, 6119, 6124, 6125, 6126, 6127,
6130, 6132, 6134。

- 20 chunks、70 valid actions、10 padding；
- `BCNet(1340,512,h4)`，500 epochs，seed=0，AdamW lr=1e-3/wd=1e-4，batch=128；
- 两项损失均使用已有 `masked_cont_mse` / `masked_ce`，padding 不参与；
- 无 val、无 test、无 rollout。

| 项 | 值 |
|---|---:|
| initial train total | 2.406883 |
| final train total | **4.0671e-5** |
| final masked cont MSE | 2.9315e-6 |
| final masked grip CE | 3.7739e-5 |
| XYZ coord MAE | 0.000105 m |
| XYZ Euclidean mean | **0.000214 m** |
| XYZ Euclidean median / P95 | 0.000158 / 0.000532 m |
| gripper accuracy | **1.0** |

结论：H4 数据管线、masked losses 和架构可以记忆这 10 条轨迹；仅作管线诊断，不是泛化或 rollout 结果。

## 4. 全量 H4 固定训练

- 同 single encoder（BCNet trunk 512→512）、AdamW lr=1e-3、wd=1e-4、batch=128、seed=0；
- 500 epochs，无早停；按总 val loss 选 best_val；
- train chunks 104、val chunks 26；test **未评估**；
- 实际 optimizer updates：**500**（104 chunks/batch 128 = 1 batch/epoch）。

### 曲线

| epoch | updates | train total | val total | val cont | val grip |
|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 2.591223 | 1.010263 | 0.677800 | 0.332463 |
| 50 | 50 | 0.008950 | 0.024099 | 0.019749 | 0.004351 |
| 100 | 100 | 0.001302 | 0.006914 | 0.005520 | 0.001393 |
| 150 | 150 | 0.000540 | 0.005008 | 0.004303 | 0.000705 |
| 200 | 200 | 0.000331 | 0.004602 | 0.004133 | 0.000469 |
| 250 | 250 | 0.000230 | 0.004404 | 0.004071 | 0.000333 |
| 300 | 300 | 0.000171 | 0.004282 | 0.004032 | 0.000250 |
| 350 | 350 | 0.000133 | 0.004199 | 0.004004 | 0.000195 |
| **389** | **389** | **0.000113** | **0.004146** | **0.003982** | **0.000164** |
| 400 | 400 | 0.005836 | 0.008346 | 0.008155 | 0.000191 |
| 450 | 450 | 0.000104 | 0.004262 | 0.004078 | 0.000184 |
| 500 | 500 | 0.000077 | 0.004154 | 0.004029 | 0.000125 |

**best_val：epoch 389，val total `0.0041460914`**。

| checkpoint | train masked cont/CE/total | val masked cont/CE/total | train XYZ Euclid mean | val XYZ Euclid mean | val grip acc |
|---|---|---|---:|---:|---:|
| best_val (389) | 2.04e-5 / 9.36e-5 / 1.14e-4 | 0.003982 / 0.000164 / **0.004146** | 0.000664 m | 0.004808 m | **1.0** |
| last (500) | 1.11e-5 / 6.52e-5 / 7.63e-5 | 0.004029 / 0.000125 / 0.004154 | 0.000481 m | 0.004678 m | **1.0** |

### best_val 身份与重载

| 项 | 值 |
|---|---|
| `best_val.pt` sha256 | `ff8c694516eb8940e089aeb0a380daab6da0d84e9ab53aeaa6cd302c9a6c21d5` |
| `last.pt` sha256 | `88387edf2792227272ef542ba2c3b847ab909b1389a32c4f0687efbd37409afd` |
| reload | `state_loaded=true`, epoch 389, mode h4, in_dim 1340, hidden 512 |
| reload output | shape `[26,4,4]`, finite=true |
| reload val cont/grip | `0.0039819204` / `0.0001641710`（与 best_val 一致） |

## 5. 产物与命令

```bash
/root/autodl-tmp/envs/isaac40/bin/python stage6/rebuild_h4_data.py

/root/autodl-tmp/envs/isaac40/bin/python stage6/fit_h4_flat10.py \
  --epochs 500 --batch 128 --lr 1e-3 --weight-decay 1e-4 --seed 0

/root/autodl-tmp/envs/isaac40/bin/python stage6/train_h4_budget500.py
```

远端：

- `holdingfix-20261108/h4fix-20261108/{dataset_h4.npz,dataset_single.npz,stats.json,config.json,dataset_identity.json,h4_data_check.json}`
- `.../diagnostics/fit_h4_flat10/{final.pt,curves.json,metrics.json,config.json}`
- `.../runs/h4_budget500/{best_val.pt,last.pt,curves.json,best_val_metrics.json,last_metrics.json,reload_check.json}`

本地：

- `stage6_h4fix_20261108/h4fix-20261108/`
- [STAGE7_H4_OFFLINE.md](STAGE7_H4_OFFLINE.md)

## 6. 边界

- 只做离线数据/训练；**未启动 H4 rollout**。
- 未使用 test 选择模型；不宣称 H4 闭环成功。
- 旧 H4 数据/checkpoint、single checkpoint 均保留。
- 后续 H4 rollout 必须沿用 single 的 Backend、预算和终端规则，再比较动作分块影响。
