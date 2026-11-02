# 第 5 步 10 循环 Backend reset / 重抓取审查（开发）

## 结论

第 5 步开发完成标准满足：

- **同一 episode 可重抓取**：第 2 循环完成短程抓取→保持→释放，再用同一 `left_sleeve` 槽位重抓取→抬升→释放；`reuse_count=2`，重抓取激活文件最大顶点位移 1.2718 mm。
- **连续 10 次 reset/rollout 无状态残留或保存错误**：10 个循环全部 `json_save_ok=true`，每循环 reset 后三槽均为 released/disabled/unused、约束存在且路径唯一、布料 0.4×0.4 平铺、保存的 JSON/NPZ/PNG 全部读回成功；`ERRORS=[]`、`RESULT_VERIFIED True`。

正式折叠成功仍为 0；本结果是开发整合验证，不是正式 Day4 验收。

## 运行

- 远端目录：`day4-prepared-square-backend-reset-20261101-080713-870146`。
- `passed=true`、`cycle_count=10`、`errors=[]`、`PREPARED_SQUARE_BACKEND_RESET_RESULT_VERIFIED True`。
- settings：cycles=10、fold_cycles=1、regrasp_cycle=2、seed=5100、`apply_difficulty=False`。

| cycle | rollout | actions | save | yaw err rad | held pos mm | held speed rad/s | anchor mm | hold steps | reuse | fold IoU |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | fold | 9 | true | — | 0.474 | 0.000915 | 2.034 | 60 | — | 0.6971 |
| 2 | short+regrasp | 10 | true | 0.000191 | 4.093 | 0.003331 | 1.427 | 60 | 2 | — |
| 3–10 | short | 6 each | true | 0.000191 | 4.093 | 0.003331 | 1.427 | 60 | — | — |

每个循环的 reset 检查全部通过：

- `all_slots_released`、`not_holding`、`not_enabled`、`constraints_exist`、`paths_distinct_and_valid`：true。
- 布料 xy extent `[0.4000, 0.4000] m`、中心 `[~0, -0.450] m`、`z_p95=0.0099 m`、有限值检查 true。
- 机器人 reset 后最大臂关节速度 0.00119 rad/s；stage PNG 480×640 可解码；`reset.json`、`reset_state.npz` 保存并读回。
- 每循环结束三槽 `used=[false,false,false]`、`enabled=[false,false,false]`。

## 各项验证

- **yaw**：approach 命令 yaw=0.3；实际末端姿态与 `Rz(0.3)Rx(pi)` 误差 1.906e-4 rad。
- **保持**：静止 HOLD 执行 60 步关节空间保持（`joint_position_hold; RMP not called at fixed target`）；短程循环 held gate 位置 4.093 mm、末臂速 0.003331 rad/s、锚点 1.427 mm，均通过。
- **完整折叠（正式 Backend）**：第 1 循环 9 个公共动作；IoU 0.6971、crossed fraction 1.0、对称对齐 5.350 mm、反射目标误差 13.62 mm、`cloth_z_p95=69.39 mm`；held gate 位置 0.474 mm、末臂速 0.000915 rad/s、锚点 2.034 mm。与第 3/4 步 x 向候选（IoU 0.6617、对齐 6.358 mm、z_p95 68.66 mm）可比，折叠层仍略抬。
- **重抓取**：第 2 循环同一槽位第二次 CLOSE 的激活文件 `cycle_02/activation_left_sleeve.npz`：最大顶点位移 1.2718 mm、跟踪区均值 0.332 mm；`reuse_count=2`。`result.json` 里的 `activation_record` 为 null，是因为测试在 release 后读取、`enable_regrasp()` 已清除记录；实际激活证据在 npz 和 `ENABLE_DISPLACEMENT` 日志中。该字段是报告顺序问题，不是激活失败。
- **保存**：10 个 `cycle.json`、10 个 `reset.json`、10 个 `reset_state.npz`、10 张 `reset.png` 及 `activation_left_sleeve.npz` 均存在并可读回。

## 限制

- 10 循环中只有 1 次完整折叠，其余为短程生命周期 rollout；完整折叠重复性已由第 3/4 步两例验证。若要 10 次完整折叠，可把 `--fold-cycles 10`（运行时间显著增加）。
- 本测试 `apply_difficulty=False`；L1 的 ±10° yaw / 平移与当前世界轴 x 折线的对齐尚未解决，留到第 6 步。
- recovery 未接入；折叠 9 动作 + 一次 recovery 5 动作超过 12，动作预算组合留到第 6 步。
- 接触诊断关闭；折叠层抬高、固定半片拖拽等既有质量限制仍存在。
- 正式成功仍为 0；本结果不计入正式批次。

## 下一步

第 6 步：三档难度（L1/L2/L3）、L2/L3 角点 lift/drop、每档 10 张初态图、参数化 recovery，以及 ≤12 高层动作预算的组合验证。
