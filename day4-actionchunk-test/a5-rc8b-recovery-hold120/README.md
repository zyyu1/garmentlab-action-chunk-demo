# a5-rc8b-recovery-hold120：recovery 后固定保持 120 步（已完成：accepted，待审查后扩展）

**唯一干预：** 在 recovery 的 `rec_release` 与正常 240 步 settle 完成后、重新观测并计算 fold pick/yaw 之前，精确增加 **120 个物理步（dt=1/60 s，共 2.0 s）**。保持当前机器人控制目标；不新增移动/开爪/闭爪，不修改布料位置，不清零速度，不换材料。等待结束后重新观测，再调用原 expert 计算 fold。

**结果：accepted 0.2374 / 0.3484 mm**、stationary 6.69 mm、无几何失败（new 7.4809/11.5382、first 249；old 0.2642/0.3792）。保持 2.0 s 内运动已接近零（质心 ~0.0001 mm/s、粒子 P95 ~0.007 mm/s、EE 漂移 0、附件全关），不是“运动衰减”；额外静态步改变下游 fold，机制未隔离。作为**候选衔接改进**，审查后再决定是否扩展。详见 [hold120 审查](../results/RC8B_L2_DIAG_20261105/hold120_review.md)。

**审计异常：** entry exit 0；runner exit 3 是 audit 打印 `KeyError: recovery_hold`（结果 JSON 已完整写出）；修正 audit 后对同一结果复审计 exit 0，**未重跑仿真**。因此本 run 不标成干净完成。

## 1. 身份

| 项目 | 值 |
|---|---|
| 父版本 | rc8b（manifest `cce573dd…`） |
| 新 manifest | `b61fd56e…`（63 项；**60 项与 rc8b 相同**） |
| 变化 | `a5_recovery.py`（仅新增 hold 函数与 6 行调用/事件）、登记 JSON、runner |
| 初态 | rc8b 新 4202 `…015817-115841`（result `1eef6c83…`、geometry `13b56808…`）；**不使用** l2pose/l2patch9/旧 pfs=0 |
| 协议 | L2 初态生成与 rollout 均为 pfs=1 |
| 范围锁 | 仅 4202 single；新账本 `a5-rc8b-recovery-hold120-runs` |
| 评价 | release_retreat 完成仍为 step 0；原采样窗口/评价器/阈值 |

## 2. 保持与记录

- 121 帧：等待开始前一帧 + 120 步后每步；`recovery_hold_trace.npz` + metadata。
- 每步核对 holding=false、逻辑附件关闭、command holding=false、所有附件槽关闭、步数 +1、dt=1/60；异常保存部分记录并停止。
- 速度用世界顶点位置有限差分：120 个有效区间，不为首帧填零；raw readback 若保留标 unvalidated。
- 事件：`recovery_retreat_end`、`recovery_hold_begin`、`recovery_hold_end`、`fold_observation`；不伪造动作结束时间。
- 等待结束重新观测后计算 fold；不缓存等待前 pick/yaw。

## 3. 边界

- 只跑一次 4202 single；无重试、不扩批、不扫摩擦、不扩展 seed、不重跑七例、不冻结、不跑 held-out。
- 不继承 D1 的释放后等待或 D2-C preopen；保留所有旧候选/初态/结果/锁。
- 诊断通过不计入正式 Stage 4 成功。
