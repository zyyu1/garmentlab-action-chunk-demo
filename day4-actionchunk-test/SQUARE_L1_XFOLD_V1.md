# x 向中心对折 L1 候选 v1（待运行）

状态：开发候选，只验证第 3/4 步完整对折；不计正式成功。已用相同配置独立运行两次并通过视频/阶段图视觉审查：`day4-square-l1-xfold-v1-20261101-062602-150760` 和 `day4-square-l1-xfold-v1-20261101-065314-576894`，审查记录见各自目录下的 [review.md](results/day4-square-l1-xfold-v1-20261101-062602-150760/review.md) 与 [review.md](results/day4-square-l1-xfold-v1-20261101-065314-576894/review.md)。

## 路线改动依据

原 y 向候选从 v5 实际抓取关节 `[0.151, 0.799, -0.156, -1.768, 0.202, 2.550, 2.230]` 连续跟踪到 place 第 15 个子目标（y=-0.277, z=0.097）时，IK 解在关节限位处被阻断；最终点 y=-0.25, z=0.033 在实际分支上不可连续到达。离线 3.15 rad 跳变不是单纯求解器分支选择问题。

改用同一方巾的 x 向中心对折：左边缘中点抓取，绕 x=0 折到右边缘。使用已预建的 `left_sleeve` 槽位（`slots[1]`），不新增动作通道。离线用 v5 实际初态几何和 8 个不同 descend 分支连续跟踪到最终点，8/8 全部完成，最大相邻关节变化 ≤0.100 rad；最好分支最小关节余量 0.620 rad，其余分支 0.0001–0.261 rad。v5 实际初态几何：pick=(-0.200, -0.450, 0.0099)，折线 x=7.45e-9，目标=(+0.200, -0.450, 0.0299)。报告：`frame_audit/xfold_path_continuity.json`。

## 单一改动范围

- 新增 `square_edge_fold_geometry.py`：x 向 `edge_plan` 与 4 个圆弧目标。
- 新增 `square_edge_control.py`：只把 `left_sleeve` 槽位改为单点手写锚点，并保留 `SquareProxyGroundControl` 的辅助块—默认地面配对过滤。
- 新增运行入口 `day4-square-l1-xfold-v1.py` / `run-square-l1-xfold-v1.sh`。
- 公共 5 维动作、9 个高层动作、25 mm 内部线段、物理配置、方块过滤、60 步保持、释放/退让/静置与 v6 相同；不修改 held gate 阈值，不新增 yaw/pitch 侧通道。
- 原 `hem` 槽位与其单点锚点保留但本候选不使用。

## 预登记判读

- 过程通过：9 个公共动作全部完成且状态一致；只在 `left_sleeve` 槽位使用一次；释放后三槽均 disabled、不 holding；块路径保留、释放漂移 <1 mm。
- held gate 沿用 v6：末端位置误差 <10 mm、末臂速 <0.1 rad/s、姿态到达、最大锚点间隙 ≤10 mm。
- 折叠判读：保存释放、退让、静置 3 s 和再 1 s 快照；报告 `fold_metrics`/`retention_metrics`、`moving_half_crossed_fraction`、`particle_occupancy_iou`、固定半片漂移、释放后回弹和块漂移。本开发候选不冻结 success 阈值，成功/失败交由完整结果和视频审查；`fold_success_accepted=False`。
- 路径连续性：离线已通过；运行时记录每 5 物理步关节位置，报告最大相邻关节变化和最大关节速度，仅作诊断，不替代离线检查。
- 只运行一次；失败保存并审查，不自动调阈值、扫描参数或重跑。

## 运行

```bash
bash /root/autodl-tmp/run-square-l1-xfold-v1.sh
```

运行结束后用日志末尾的 `DOWNLOAD_DIR` 手动下载，例如：

```powershell
scp -P 22895 -r root@connect.nmb1.seetacloud.com:/root/autodl-tmp/day4-square-l1-xfold-v1-<时间戳> "E:\learning\project\thesis\day4-actionchunk-test\results"
```

完整结果由用户手动下载。正式成功仍为 0。

## 本次运行结果（视觉审查通过）

远端 `day4-square-l1-xfold-v1-20261101-062602-150760`：`passed=true`、`errors=[]`，9 个公共动作全部状态一致，视频 606 帧、13 张阶段图，退出码 0。

| 检查 | 结果 |
| --- | --- |
| held gate 位置误差 | 0.5033 mm，通过 |
| 保持末臂速 | 0.000916 rad/s，通过 |
| 姿态到达 / 最大锚点间隙 | true / 1.9907 mm，通过 |
| 全生命周期 | 仅 left_sleeve 使用；全部禁用；不 holding；路径保留；块漂移 0 |
| moving half crossed fraction | 1.0 |
| 投影 IoU / 对称对齐 / 反射目标误差 | 0.6617 / 6.358 mm / 5.685 mm |
| 静置 4 s 保持 | 对齐 6.258 mm、IoU 0.6519、反射误差 5.717 mm、3→4 s 漂移 0.860 mm |
| 固定半片质心位移 | [-10.77, -0.51, +4.32] mm |
| 折叠各阶段相邻 5 步关节变化 / 最大速度 | ≤0.0206 rad / ≤0.257 rad/s；无跳变 |
| approach 初始大运动 | 0.2336 rad / 2.865 rad/s（非折叠段） |
| `cloth_z_p95` | 68.66 mm |

视觉判读：折叠前后投影由完整方巾变为右半幅，左半覆盖在右半上；释放、退让、静置 3 s/4 s 后形状保持，无整件搬移、翻转或持续滑动。折叠层左侧略抬/卷曲（垂直间隙中位数 22.1 mm、p90 56.8 mm），固定半片被拖拽约 1.1 cm；不冻结正式高度/重叠阈值。第 3 步开发判据满足，建议第 4 步独立重复。`fold_success_accepted=False`。

## 第 4 步独立重复

第二次运行：`day4-square-l1-xfold-v1-20261101-065314-576894`，`passed=true`、`errors=[]`、9 个公共动作，步数与第一次完全相同（469/616/657/813/961/1119/1293/1375/1550）。`result.json`、`hold_trace.jsonl`、`state_trace.json`、`postcross_trace.npz`、`00_initial.npz`、`10_final_3s.npz` 的 SHA256 与第一次逐字节相同；物理轨迹和全部指标一致。

`episode.mp4` 文件哈希不同，解码 606 帧的全图平均绝对差约 20.9 灰度级；阶段图显示第一次背景为蓝色网格、第二次为浅灰无网格，机器人位姿和布料折叠形状相同。该差异与缺失房间纹理的渲染回退一致，不改变物理状态。视觉上第二次同样是完整方巾折成右半幅、左半覆盖右半、释放/退让/静置后保持。

判读：两次开发运行均完成真正对折，第 4 步完成；同配置得到逐字节相同的物理轨迹，证明路径可重复，但不证明对种子/初态扰动/难度变化的鲁棒性。不认定为正式成功。

## 首次运行失败（已修正）

远端 `day4-square-l1-xfold-v1-20261101-062036-672015` 在初始化阶段失败：
`AttributeError('Control' object has no attribute 'rest_world')`。原因是 `square_edge_control.py` 在 `initialize` 中误用 `slot.rest_world`；`PreparedRegion` 没有该属性，应使用控制器的 `self.rest_world`。该次没有产生任何公共动作，不计折叠尝试。

已修正并重新上传 `square_edge_control.py`（新 SHA256 `6f16c10f…`）与清单（`2dcc98a8…`）；远端 24/24 预检、`py_compile` 和 `bash -n` 通过。其余候选逻辑未改。

## 上传状态

远端 `/root/autodl-tmp/` 已上传 4 个新文件及 `square-l1-xfold-v1-files.json`（24 项清单）。远端 SHA256 与本地一致：runner `51b6086e…`、run script `03617c0c…`、edge geometry `a27d32c7…`、edge control `6f16c10f…`。清单 24/24 预检通过。首次运行失败已由上述修正覆盖，尚未取得有效折叠运行。
