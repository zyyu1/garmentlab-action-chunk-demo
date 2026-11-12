# v3 控制时序诊断结论与 v4 静止保持候选

## v4 运行结果（20261031-104528-426384）

已下载并审查。held gate 通过：末端位置误差 0.474 mm、保持末臂速 0.0086 rad/s、姿态到达、锚点间隙 1.36 mm；60 步内末端漂移 0.003 mm、姿态漂移 0.0005°。保持阶段只有 60 次显式 joint_indices 0–6 的 apply_action（位置目标+零速度），controller.forward 和 controller_output 均为 0；全轨迹无 Python 层位姿/关节设置调用。00_initial、01_before_close、02_grasp 与 v3 逐顶点/逐位姿相同，03_held 起才出现差异（v3 保持末端漂移 19.12 mm）。release 动作步数 731（v3 753），原因是保持结束位姿稳定；公共动作仍为 4。

但接触通道正控为 0（callback_count 0、event_count 0、block_ground 0），而辅助块中心 z 恒为 15.000 mm、目标 10.207 mm，块被地面持续挡住。按预登记规则通道无效，不能据此判定无 robot_block 接触；且 robot_group 与 attach_group 本就互相过滤，robot_block 记录不能独立证明机械隔离。因此第 1 步未解锁，不进入 L1；正式成功 0。

审查：`results/day4-square-grasp-hold-20261031-104528-426384/review.md`、`independent_audit.json`、`hold_v3_v4.png`；本地脚本 `review_square_grasp_hold_v4.py`。下一步先做有效接触正控，不延长保持、不改阈值、不调 RMP 增益；修复候选见 [SQUARE_GRASP_HOLD_V5.md](SQUARE_GRASP_HOLD_V5.md)。

## v3 结果已完整下载

目录 `results/day4-square-grasp-pose-20261031-093041-511232`。动作、脚本、物理步数与 v2 完全一致（approach 462、descend 608、close 649、release 753），因此这是同一确定性运行的补充记录，不是新的成功候选。正式成功 0。

`control_trace.jsonl` 共 3466 行：1546 条 before/after 状态、633 次 controller.forward、633 次 controller_output、653 次 apply_action，另有 20 次夹爪开合动作。未观察到任何 Python 层 `set_world_pose`、`set_local_pose`、`set_joint_positions` 调用；原生 PhysX 调用仍不在覆盖范围。

## 判读：控制器输出先发散，实际关节滞后跟随

保持阶段第 650–689 步位置误差 0.44–0.73 mm、最大臂速 0.03–0.06 rad/s。第 690 步 RMP 输出关节 7 目标先增加 0.0028 rad；第 691 步输出跳变为关节 5 +0.0119 rad、关节 7 −0.0308 rad；随后实际关节在第 691–692 步出现 0.60/2.24/4.40 rad/s 响应。逐帧用 URDF FK 复核：

- 发散方向是末端绕世界 Z 轴偏航，最终约 10.7°，同时位置漂移 19 mm；不是滚转或俯仰。
- 6D 雅可比条件数全程约 11.2–11.4，腕部不在运动学奇异点；关节限位余量充足。
- 控制器输出的位姿误差从 0.3° 主动增大到约 10°，即控制器在远离而非靠近固定目标。
- 释放后（附件关闭、夹爪打开）同一 RMP 在另一关节构型下保持约 45 步稳定，速度衰减到 0.03 rad/s，说明不是所有静止保持都会发散。

结论：保持阶段失稳的直接来源是 RMP 在固定目标处的输出发散；但附件启用/夹爪闭合与释放后的稳定性差异，仍不能排除意外接触通过夹爪传力。不能只凭控制日志断定根因。

## 未验证的可疑点

1. 3 cm 辅助块中心位于闭合手指内部（URDF 网格与块体积重叠），依赖 robot↔attach 碰撞过滤；该过滤只有 USD 关系静态声明，尚未有运行时接触证据。
2. 辅助块中心 z≈0.015 m 时底面正好在地面，而块目标 z≈0.010 m，保持阶段每步都向下饱和速度指令 0.3 m/s，块实际被地面挡住，形成持续接触。
3. 旧接触记录只订阅机器人刚体，事件 0、通道未独立验证；无事件不能判为无碰撞，也没有块-地正控。

## v4 候选（已上传并运行）

入口：`run-square-grasp-hold.sh`；输出目录前缀 `day4-square-grasp-hold-`。与 v3 相同的公共四动作（approach OPEN → descend OPEN → close CLOSE → release OPEN）、目标、路径、物理配置、60 步保持时长、30 步释放后静置及全部判据。

唯一控制改动：60 步静止保持改为关节空间位置锁定。保持开始时读取当前 7 个臂关节位置，逐步以显式 joint_indices 提交 position 目标与零速度目标，不再调用 RMP；辅助块跟随速度逻辑与 `_tick(follow=True)` 保持一致。目的为隔离并绕过已证实的 RMP 固定点发散，不改公共接口、不隐藏路径、不放宽门槛。

新增被动诊断（不改物理）：

- `square_block_contact_recorder.py`：同时对 12 个机器人刚体和 3 个辅助块启用接触报告，按 robot_block / block_ground / robot_ground / 其他分类写入 `block_contacts.jsonl`。块-地接触是内置正控；若正控仍为 0，则通道无效。
- 启动时输出 `collision_filter_audit.json`：碰撞组 filteredGroups、colliders includes/excludes、三个块路径与 collision enabled 状态。
- `hold_trace.jsonl`：保持阶段每步末端位姿、关节位置/速度、块实际位置/目标、持布状态与累计锚点误差。

通过条件保持 v2/v3 原值：位置误差 <10 mm、最大臂速 <0.1 rad/s、姿态到达、锚点误差 ≤10 mm，释放后附件全部 disabled。`passed=True` 仍只代表四动作诊断通过，不是折叠成功。

## 判读与停止规则

- 若 held gate 通过且 robot_block 接触为 0，则第 1 步解锁；进入 L1 折叠接回前仍需保留该接触证据。
- 若 held gate 通过但出现 robot_block 接触，不得视为机械隔离成立；先修正碰撞过滤或块-地接触，再进入折叠。
- 若关节锁定后仍不通过，说明存在通过夹爪传入的持续外力或关节驱动问题；停止本候选，围绕接触/驱动证据修正，不延长保持或放宽阈值。
- 若块-地正控为 0，接触通道记无效，不能据此判定无碰撞；需要另做有效正控。
- 本轮只允许一次运行；不扫描保持时长、不调 RMP 增益、不改块尺寸或质量。

已上传 5 份新文件，远端 20 文件 SHA256 全部一致，Python/Bash 语法通过。已由用户运行一次，结果见本节顶部；正式成功 0。

运行命令：

```bash
bash <remote-root>/run-square-grasp-hold.sh
```
