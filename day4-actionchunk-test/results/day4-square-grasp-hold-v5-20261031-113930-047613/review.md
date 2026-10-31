# Square grasp-hold v5 审查

## 结论

短程抓取 held gate 与接触正控均通过：`passed=true`、`errors=[]`、`formal_day4_success=false`。本测试不含折叠，正式成功仍为 0。

## 失败修正

首次运行 `day4-square-grasp-hold-v5-20261031-112822-203913` 在 `BlockContactRecorderV2.__init__` 因 `verified['attachment_bodies']` 抛 `KeyError`，发生在任何公共动作之前（`public_action_count=0`），不计实验数据。根因是记录器第 63 行键名与第 46 行字典不一致；已改为 `verified['blocks']`，同步更新 `square-grasp-hold-v5-files.json` 哈希并重新上传。修复后远端 `py_compile` 与 21 文件预检通过。

## 关键结果

| 项目 | 结果 |
|---|---|
| 公共动作 | 4 个，全部 checks 通过 |
| 保持位置误差 | 0.473 mm |
| 保持末臂速 | 0.0086 rad/s |
| 姿态到达 | true |
| 锚点最大间隙 | 1.36 mm |
| 释放后 | holding=false，三个附件全部 disabled |
| 接触事件 | callback 751，event 2609；block_ground 2253，robot_ground 356，robot_block 0 |
| 力通道 | 150 次采样，14 次正（close 2、held 12），最大 287.58 N |
| 诊断 | `block_ground_events_recorded` |

## 与 v4 的一致性

4 个动作矩阵、物理步数 `[462, 608, 649, 731]`、`held_check`、`pose_contract`、slot 事件及线性路径与 v4 完全相同；视频同为 255 帧。v5 只改变接触诊断，未扰动控制路径。

## 完整性

- 远端/本地 60 个文件 SHA256 全部一致，无缺失或多余
- 视频远端解码 255 帧、640×480；本地字节一致
- 20 份源码清单与本地当前文件一致，记录器哈希 `91676938…`

## 边界与判读

1. `block_ground` 从 initial_settle 第 12 步起就存在（辅助块本就压在地面），证明的是接触记录通道有效，不是抓取本身。抓取证据是 held gate、附件激活位移（最大 1.36 mm、跟踪均值 0.356 mm）和释放状态。
2. `robot_block=0` 不能独立证明机械隔离：`attach_group` 与 `robot_group` 本就互相过滤；布料粒子接触未认证。
3. 力最大值 287.58 N 出现在保持阶段 `attach_2/block` 的 z 向。辅助块中心 z 仍为 15 mm、目标 10.207 mm，块被地面挡住；预登记只用 `>1e-6` 判断通道有效，这不是夹持力阈值。
4. 第 585 步起出现左右指尖-地面接触（各 178 次），持续到释放。预登记门槛未包含此项，但 L1 完整路径设计时应保留观察。

## 预登记判读

事件正控 `block_ground > 0` 满足，独立力通道同时为正，按 v4 预登记可进入第 1 步解锁审查；但保留上述碰撞组过滤限制。本轮有效运行一次，符合“本轮只运行一次”。

## 下一步

第 2 步接回 L1 对折。先解决完整路径末段约 3.15 rad 的 IK 分支跳变，再验证释放、退让、静置后的折叠保持；不延长保持、不改门槛、不调 RMP 增益。
