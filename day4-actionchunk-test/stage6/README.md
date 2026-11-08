# Stage 6 最低开发验收归档

状态：**Stage 6 最低开发验收完成**（最低开发评估已执行；不是 Stage 6 成功验收通过）。

## 结果

| 档 | learned accepted | random accepted |
|---|---:|---:|
| L1 flat | 2/5 | 0/5 |
| L2 perturbed | 0/5 | 未运行 |
| L3 crumpled | 0/5 | 未运行 |
| 合计 | **2/15** | **0/5** |

- L1：6122、6151 accepted；6120 prepared-region；6121 waypoint timeout；6148 geometry rejected。
- L2：0/5；grasp-region 1、prepared-region 3、terminal held check 1。
- L3：0/5；grasp-region 2、prepared-region 3。
- L2/L3 无完整 331 帧，几何/稳定性指标不可用。
- checkpoint 重载：`BCPolicy` 新 checkpoint/stats 加载通过（`OLD_LOAD_OK legacy`、
  `NEW_LOAD_OK identity`）；L1 precheck 与 budget500 均完成真实 torch 前向。
- 成功/失败视频：L1 [6122](../../../stage6_l1_dev_20261108/videos/l1dev-learned-6122.mp4)、
  [6151](../../../stage6_l1_dev_20261108/videos/l1dev-learned-6151.mp4)；
  L1 失败 [6120](../../../stage6_l1_dev_20261108/videos/l1dev-learned-6120.mp4)、
  [6121](../../../stage6_l1_dev_20261108/videos/l1dev-learned-6121.mp4)、
  [6148](../../../stage6_l1_dev_20261108/videos/l1dev-learned-6148.mp4)；
  L2/L3 代表失败视频见 [L2/L3 结果](STAGE6_L2L3_DEV_RESULT.md)。
- 这是 5 个固定初态/档的开发评估；缩减数据、小样本，不作统计显著性声明，不宣称 Stage 6 自动通过。

## 初态来源

- L2 4210–4214：最终清单无 perturbed val；这些初态**曾用于 Stage 4**，未用于 Stage 5 模型训练，不称全新 held-out。
- L3 6504/6507：已有 final val；4310–4312 **曾用于 Stage 4**，未用于 Stage 5 模型训练。
- 未选 train；test `6300, 6301, 6516, 6517` 保留。
- 全量初始哈希、task、strips 记录在 L2/L3 manifest。

## 已知差异

专家 `a5_recovery.py` 在 recovery release 后执行 `_settle(240)` + 120-step hold；
当前 learned runner 只有初始 `_settle(30)`，未临时加入专家等待/补救。
L2/L3 失败不单独归因于数据量：region 拒绝、4211 terminal held check 失败和该 settle/hold
差异并列保留。

## 文件

- [L1 结果](STAGE6_L1_DEV_RESULT.md)
- [L2/L3 结果](STAGE6_L2L3_DEV_RESULT.md)
- [Stage 6 交接日报](STAGE6_HANDOFF.md)
- [H4 离线报告](STAGE7_H4_OFFLINE.md)
- [H4 L1 6120 开发试跑](STAGE7_H4_L1DEV_RESULT.md)
- [6120 首例结果](STAGE6_6120_SINGLE_RESULT.md)
- [holdingfix 报告](STAGE6_HOLDINGFIX_REPORT.md)

本地结果/视频：`stage6_l1_dev_20261108/`、`stage6_l2l3_dev_20261108/`。

## 限制

- 开发评估，不是独立 test；L2/L3 缩减数据探索性。
- 只有 L1 2/15 accepted；不能称为 Stage 6 通过。
- 旧模型 6120 未并入当前模型分母；当前模型 6120 是 recheck 失败。
- 本轮不追加采集、不训练、不重跑已有结果、不自动 rollout。
