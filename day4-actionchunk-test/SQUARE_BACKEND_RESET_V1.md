# 第 5 步：正式 Backend 整合与 reset/重抓取候选（待冒烟）

状态：第 5 步开发完成。10 循环 `080713-870146` 已通过：10 次 reset/rollout 无状态残留、无保存读回错误；第 2 循环同一 episode 重抓取通过。正式折叠成功仍为 0，不计正式验收。

## 整合内容

- `backends/prepared_square_backend.py`：正式 Backend 候选。公共动作仍为 `[x, y, z, yaw, gripper_action]`；yaw 映射为 `Rz(yaw)Rx(pi)`；抓取/移动/释放使用已验证的多槽位方巾控制；静止 HOLD 自动执行 60 步关节空间保持（`StableHold`）；OPEN 释放后调用 `enable_regrasp()` 允许同一槽位安全复用。
- `backends/garmentlab_backend.py`：增加 `_make_prepared_control(env)` 工厂钩子；默认仍为原 `PreparedGraspControl`，不改变旧路径。
- `multi_prepared_grasp_control.py`：新增 `enable_regrasp()`、`prepare_episode_reset()`、`after_scene_reset()`；释放后保留预建约束/辅助块，重抓取时重新对齐 `points1` 并重新记录激活；reset 时强制禁用/清零/清除记录并在 `world.reset()` 后复核 `points0`。
- `day4-prepared-square-backend-reset.py` / `run-prepared-square-backend-reset.sh`：step 5 测试入口。

## reset 语义

`PreparedSquareBackend.reset(seed, difficulty, apply_difficulty)`：

1. `control.prepare_episode_reset()` 强制所有槽位释放、禁用、清零、清除 used/alignment/activation。
2. `env.reset()` 执行 `world.reset()`，恢复布料和机器人初始状态。
3. 重新初始化 cloth view，`control.after_scene_reset()` 复核预建 blocks/constraints/points0，并验证辅助块—地面过滤。
4. 重置每 episode 的 step 计数器，静置 120 步。
5. 可选 difficulty；本测试使用 `apply_difficulty=False`，避免 flat 的 ±10° yaw 与当前世界轴 x 折线冲突。difficulty 下的布料局部轴对齐留到第 6 步。

## 测试设计

- 默认 10 个循环；每循环先 reset 并校验：全部槽位 released/disabled/unused、约束存在且路径唯一、布料 0.4×0.4 平铺、z_p95<30 mm、关节有限；保存 `reset.json`、`reset_state.npz`、`reset.png` 并逐项读回。
- 第 1 循环：用正式 Backend 运行完整 x 向对折 9 动作（approach、close、arc45/90/135、place、静止 hold、release、retreat），记录折叠指标。
- 第 2 循环：短程抓取→抬升→静止保持→释放，然后在**同一 episode** 重抓取同一左边缘材料点→抬升→释放；记录 `reuse_count`、激活位移和锚点间隙。
- 第 3–10 循环：短程抓取/保持/释放；每个循环保存并读回 `cycle.json`。
- 每循环校验保存可解析、无遗漏；失败保留 cycle 并停止。
- 冒烟命令（2 循环 = 1 次完整折叠 + 1 次重抓取）：

```bash
bash <remote-root>/run-prepared-square-backend-reset.sh 2
```

- 正式 10 循环：

```bash
bash <remote-root>/run-prepared-square-backend-reset.sh 10
```

## 预登记判读

- yaw：approach 用 yaw=0.3，实际末端姿态与 `Rz(0.3)Rx(pi)` 误差 <0.05 rad。
- 保持：静止 HOLD 的 60 步关节保持完成，位置误差、末臂速、姿态和锚点间隙按 v6 同口径报告。
- 重抓取：释放后 `used=False`、约束存在；重抓取成功选中同一 `left_sleeve` 槽位，激活位移/锚点间隙有记录；`reuse_count` 增加。
- reset：每循环上述状态检查通过；10 次后无 enabled/holding/used 残留、无重复约束、无保存读回错误。
- 完整折叠只在第 1 循环报告 `fold_metrics`，不作正式验收；动作数 9，未接入 recovery。

## 限制

- 10 循环中只有 1 次完整折叠，其余为短程生命周期 rollout；完整折叠的重复性已由第 3/4 步两例验证。若需要 10 次完整折叠，可把 `--fold-cycles` 设为 10（运行时间显著增加）。
- 本测试关闭 difficulty；L1 的 yaw/平移下的布料局部轴折叠尚未解决。
- 接触诊断关闭；不作为本步门槛。
- 同 episode 重抓取只测试同一 `left_sleeve` 材料点；其他槽位/不同点的 recovery 重抓取留到第 6 步。
- 折叠 9 动作 + 一次 recovery 5 动作将超过 12；动作预算与 recovery 的组合仍待第 6 步处理。

## 冒烟失败与修正

远端 `day4-prepared-square-backend-reset-20261101-072145-613587`（cycles=2）：

- 第 1 循环完整折叠通过，`json_save_ok=true`、`fold_iou=0.6971`。
- 第 2 循环 reset、重抓取 close/lift/release 通过；激活最大顶点位移 1.27 mm，`ENABLE_BLOCK_BEFORE_AFTER` 记录正常。
- 失败只发生在额外 `regrasp_retreat`：`Square waypoint velocity/position did not converge`（`SquareProbeControl` 外层 120 步收敛检查）。该退让不属于“同一 episode 可重抓取”的完成条件，下一步本来就是 reset；已从测试移除，重抓取在 release 后直接进入 reset。未修改 Backend 控制或收敛阈值。

## 冒烟通过（修正后）

远端 `day4-prepared-square-backend-reset-20261101-074938-746393`（cycles=2）：

- `CYCLE_COUNT=2`、`ERRORS=[]`、`passed=true`、`RESULT_VERIFIED True`。
- 第 1 循环完整折叠：`json_save_ok=true`、`fold_iou=0.6971214017521903`。
- 第 2 循环短程+重抓取：`json_save_ok=true`、`yaw_error_rad=0.000190633…`、重抓取激活最大顶点位移 1.27 mm、`reuse_count=3`。
- `reuse_count=3` 是跨 cycle 的累计（cycle 1 释放 1 次 + cycle 2 两次）；已改为 `prepare_episode_reset()` 清零，使每 episode 从 0 开始。该修改只影响诊断计数，不改变抓取/保持/重置行为。

## 10 循环结果

`day4-prepared-square-backend-reset-20261101-080713-870146`：`passed=true`、`cycle_count=10`、`errors=[]`、`RESULT_VERIFIED True`。

- 10 个 cycle 全部 reset 检查通过、保存并读回成功；三槽 released/disabled/unused；约束存在、路径唯一；布料 0.4×0.4、z_p95=9.9 mm；PNG 480×640。
- 第 1 循环完整折叠 9 动作：IoU 0.6971、crossed 1.0、对齐 5.350 mm、z_p95 69.39 mm；held gate 0.474 mm / 0.000915 rad/s / 2.034 mm。
- 第 2 循环同 episode 重抓取：`reuse_count=2`；激活文件最大位移 1.2718 mm；yaw 误差 1.9e-4 rad。
- 第 3–10 循环短程：held 4.093 mm、末臂速 0.003331 rad/s、锚点 1.427 mm；hold 60 步。
- 详细审查：[review.md](results/day4-prepared-square-backend-reset-20261101-080713-870146/review.md)。

## 上传状态

已上传到 `<remote-root>/` 及服务器仓库 `garmentlab-action-chunk-demo/backends/`。远端 SHA256 与本地一致：test `16bceae9…`、run `0023ed62…`、prepared backend `15a5b297…`、garmentlab_backend `def9544d…`、multi_prepared `579de3d6…`、manifest `eb73a22e…`。`py_compile`、`bash -n`、20 项清单预检通过。10 循环运行使用了上述版本。
