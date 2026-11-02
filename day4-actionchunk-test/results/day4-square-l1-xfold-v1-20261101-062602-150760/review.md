# x 向 L1 首例视觉审查（开发候选）

## 结论

第 3 步开发判据初步满足：**路径连续；释放、机械臂退让、静置 3 s/4 s 后两半仍保持重叠**。不认定为正式 Day4 成功，`fold_success_accepted=False`；建议用同一配置独立重复一次（第 4 步）。

首次运行 `day4-square-l1-xfold-v1-20261101-062036-672015` 在初始化阶段因 `slot.rest_world` 属性错误失败，没有公共动作，不计入本审查。有效运行为 `day4-square-l1-xfold-v1-20261101-062602-150760`。

## 运行与产物

- 远端/本地目录：`day4-square-l1-xfold-v1-20261101-062602-150760`。
- `result.json`：`passed=true`、`errors=[]`、`formal_day4_success=false`、`fold_success_accepted=false`。
- 9 个公共动作全部 `executed_one=True`、`not_done=True`、holding/附件计数一致：approach、descend、close、arc45、arc90、arc135、place、release、retreat。
- 视频 606 帧、13 张阶段图、0 帧错误；`PYTHON_EXIT=0`、`TEE_EXIT=0`，视频可解码。
- 阶段图：`00_initial`、`01_before_close`、`02_grasp`、`03_arc45/90/135/place`、`06_supported_place`、`07_released`、`08_release_stationary`、`09_retreated`、`10_final_3s`、`11_retention_4s`。

## 指标

| 检查 | 结果 | 判读 |
| --- | --- | --- |
| held gate 位置误差 | 0.5033 mm | 通过（<10 mm） |
| 保持末臂速 | 0.000916 rad/s | 通过（<0.1 rad/s） |
| 姿态到达 | true | 通过 |
| 最大锚点间隙 | 1.9907 mm | 通过（≤10 mm） |
| moving half crossed fraction | 1.0 | 左半全部越过折线 |
| 投影 IoU | 0.6617 | 两半投影重叠 |
| 对称对齐 / 反射目标误差 | 6.358 / 5.685 mm | 投影位置一致 |
| 固定半片质心位移 | [-10.77, -0.51, +4.32] mm | 非整件搬移，但被拖拽约 1.1 cm |
| 释放后 30 步 | 三槽 disabled、不 holding、块漂移 0 | 通过 |
| 3→4 s 源半片漂移 | 0.860 mm | 无持续滑动/回弹 |
| 静置 4 s 保持 | 对齐 6.258 mm、IoU 0.6519、反射误差 5.717 mm | 重叠保持 |
| `cloth_z_p95` | 68.66 mm | 折叠层明显抬高，需注意 |
| source→fixed 垂直间隙 | 中位数 22.1 mm、p90 56.8 mm | 折叠层未完全压平 |

接触诊断：`force_only_positive_control`。事件通道因本轮主动过滤块—地正控而标记无效；块净力 356 次采样中 1 次为正、最大 8.81 N；事件计数 `robot_ground=482`、`block_other=139`。该通道不作为第 3 步门槛，也不据此宣称无碰撞或接触力已量化。

## 路径连续性（运行时，每 5 物理步采样）

| 阶段 | 最大相邻关节变化 rad | 最大臂关节速度 rad/s |
| --- | ---: | ---: |
| approach | 0.2336 | 2.8647 |
| descend | 0.0205 | 0.2570 |
| close | 0.0059 | 0.0716 |
| arc45 | 0.0206 | 0.2573 |
| arc90 | 0.0188 | 0.2408 |
| arc135 | 0.0173 | 0.2079 |
| place | 0.0205 | 0.2555 |
| place_hold | 0.0000 | 0.0009 |
| release | 0.0074 | 0.0901 |
| released_stationary | 0.0069 | 0.0813 |
| retreat | 0.0204 | 0.2531 |
| settle_3s / retention_4s | 0.0000 | 0.0518 / 0.0516 |

approach 的 2.865 rad/s 是初始化后从 home 到接近位姿的大幅运动，不属于折叠段。折叠四段及退让均 ≤0.0206 rad/5 步、≤0.257 rad/s，无 3.15 rad 跳变。该表为 5 步诊断采样，不是新的验收阈值。

## 视觉判读

- `00_initial`：完整 40 cm 方巾平铺，机器人位于中心上方。
- `02_grasp`：夹爪在左边缘中点闭合，布料仍为完整方巾。
- `03_arc45/90/135`：左半被抬起并越过 x=0 折线，投影逐渐变为右半幅。
- `03_place` / `06_supported_place`：夹爪到达右边缘，左半覆盖在右半上；布料投影只剩右半幅。
- `07_released` / `08_release_stationary`：释放后形状保持，未见整件跳移或明显回弹。
- `09_retreated` / `10_final_3s` / `11_retention_4s`：退让和静置后投影不变，两半保持重叠。

限制：相机为正上方视角，层间高度只由几何指标给出；折叠层左侧边缘略抬/卷曲（`cloth_z_p95` 68.66 mm），不是完全压平的理想对折。固定半片被拖拽约 1.1 cm，但远小于 20 cm 的整件搬移。该结果足以支持“第 3 步开发候选通过”，不足以冻结正式重叠/高度阈值。

## 下一步

1. 用完全相同配置独立重复一次（第 4 步），保存状态和视频；两次均为开发候选，不计正式成功。
2. 重复通过后再进入第 5 步：正式 Backend 整合、附件清理、同 episode 重抓取、连续 10 次 reset/rollout。
