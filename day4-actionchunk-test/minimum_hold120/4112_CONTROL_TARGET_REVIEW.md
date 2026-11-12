# 4112 arc135 末段控制链只读审查

**范围：** 静态代码追踪 + 已有 `arc135_ticks.jsonl` / `arc135_summary.json` / `result.json` 复算；未启动 4112、4100 或其他 seed，未改冻结候选/回执/控制/阈值。

## 1. 身份与加载路径

| 项目 | 值 |
|---|---|
| 冻结候选 manifest | `40858efc1a5840ab2bf51e025f823382e8586bc037fbe41bf1d1de5b21dee86a`（63 项） |
| 诊断 overlay | `<remote-root>/stage4-4112-diag/app`（冻结 app 的逐文件同哈希副本） |
| 诊断启动 | `nohup python diagnose_arc135.py`（runpy 加载 `app/a5_l1.py`，未走父 `a5_entry.py run`） |
| 父回执 SHA256 | `9042e88ed8b4d082917151023705276230c1a4ba5c8e65b3c602337fa68ab66a` |
| 子回执 SHA256 | `9042e88e…`（overlay 内副本，内容同父回执） |
| 初态 | `day4-square-initial-20261105-232137-703257`；`result.json` `8a092d8a…`，geometry `a90de233…` |

- overlay 的 63 项 app manifest 通过 `a5_entry.preflight`；`a5_l1.py` 自身字节哈希检查通过。
- 观测包装器只在 `SquareProbeControl.robot_goto_position` 外层 patch；没有改动 app 文件、控制调用顺序、目标、步进、120 tick 或阈值。
- overlay gate 0；冻结 app 直接 gate 1（无 app 内 receipt），故诊断使用 overlay 的 receipt 副本，父/子回执内容一致。

## 2. 目标交接链（源码行号）

| 阶段 | 下发命令 | 控制器目标 | 判定目标 | 证据 |
|---|---|---|---|---|
| 第 5 公共动作 arc135 | `CartesianAction(target_pose=[x,y,z,yaw], gripper_command=2)` | — | — | `a5_l1.py:116-120`, `314-319` |
| backend `_execute_single` | `control.move([target],[orientation],[True])` | target xyz | — | `square_pose_backend.py:17-32` |
| 7 个线性子段 | `active.robot_goto_position([point],[orientation],True,240)` ×7 | 每个 `point` | — | `square_probe_control.py:16-25` |
| 第 7 子段（最后） | `_drive(point,ori,follow=True)` → `_tick(point)` → `robot.move(point,fold_orientation(ori))` | `point` | — | `square_probe_control.py:25`; `hem_prepared_grasp_control.py:133-175` |
| 最终 120 tick | 每 tick `active._tick(target,ori,follow=True)` → `robot.move(target,fold_orientation(ori))` + `world.step()` | **target** | **target** | `square_probe_control.py:26-39`; `hem_prepared_grasp_control.py:133-148` |
| 收敛判定 | `norm(ee-target)<.01`；`max(abs(vel[:7]))<.1`；holding block `<.005`；连续 6 | target | target | `square_probe_control.py:27-39` |

### 关键值

- 公共动作目标：`[0.15437224507331848, -0.4311170279979706, 0.17036335170269012]` m，yaw `0.03721895441412926` rad。
- 第 7 子段目标：`[0.15437224507331845, -0.4311170279979706, 0.17036335170269012]`（`short_segments` 末点）。
- 两者最大差：**2.8×10⁻¹⁷ m**（仅 float 舍入）；判定目标与控制器目标一致。
- 坐标系：`target_pose[:3]` 为世界/right_gripper 位置（米），`target_pose[3]` 为 yaw（弧度）；`orientation_euler` 转四元数，`fold_orientation` 只调整姿态；`short_segments` 做世界 XYZ 线性插值（步长 ≤25 mm）。
- `probe_subtarget` 只是诊断字段；源码中没有读取它来驱动控制。控制器没有另存“子段目标”变量；每 tick 把 `target` 重新交给 `robot.move`。

### 窗口内行为

- 不是“只推进仿真”：每个 tick 都调用 `robot.move(target, ...)`，再 `world.step()`；同时 holding 时设置 block 跟随速度。
- 进入窗口时没有清除/覆盖 target：`target` 来自 `_args`，`consecutive=0` 重置；`robot.move` 每 tick 用同一个 target 覆盖 RMP 目标。
- 控制目标与判定目标相同；末段目标与动作目标只差浮点舍入。

## 3. 已有证据复算

有效诊断 120 个判定 tick（segment 6，最后子段之后）：

| 指标 | 值 |
|---|---:|
| 速度超限 | **118 / 120** |
| 位置超限 | **110 / 120** |
| block 超限 | **0 / 120** |
| 最长连续通过 | **0** |
| 仅速度失败 | **10 tick（tick 0–9）** |
| 位置+速度失败 | **108 tick** |
| 仅位置失败（速度达标） | **2 tick** |
| tick 0 | err **3.541 mm**；关节速度 max **0.252865 rad/s**；block **1.146 mm**；pos pass / vel fail / block pass |
| tick 10 | err **10.552 mm**；位置首次越界 |
| 末态 | err **57.211 mm**；关节速度 **0.157776 rad/s**；block **1.655 mm**；consecutive 0 |
| 全程 min err / max vel / max block | 3.285 mm / 0.351733 rad/s / 1.655 mm |

- 报告口径成立：**118/120 速度超限，另 2 tick 速度达标但位置超限；tick 0–9 仅速度失败，连续通过计数从未启动。**
- 首次打断连续计数的条件是**关节速度**（tick 0）；tick 10 后位置也失败，但计数此前从未 >0。
- 源码可解释“接近目标后越界”：窗口固定 target、每 tick 重新下发 RMP 目标，没有制动/减速；但源码本身不能解释为何关节速度不衰减。控制层原因仍只能由运行时证据支持。

## 4. 结论

**目标交接一致，未发现源码级目标错配。** 第 7 子段末点与最终 120 tick 判定 target 的最大差为 2.8×10⁻¹⁷ m；`probe_subtarget` 不参与控制；窗口每 tick 继续下发同一 target。失败不是“控制器保留了旧子段目标”。

**观测到的失败条件：** 关节速度从 tick 0 起超 0.1 rad/s（0.2529，最高 0.3517），位置在 tick 0–9 通过后于 tick 10 越界；block 误差全程 ≤1.655 mm，合格。最可能为速度未衰减/过冲，而非目标交接错误。

**若需进一步定位控制层原因，最少运行时字段（下一次诊断，不本轮执行）：**

| 字段 | 读取点 |
|---|---|
| 最后一次 `robot.move` 的 target/orientation | `hem_prepared_grasp_control.py:137` |
| RMP `forward` 输出的 joint target / 实际 applied action | `MyFranka.py:262-273` |
| 每 tick 实际关节位置、关节速度 | `square_probe_control.py:30-32`（已有速度；补位置） |
| 控制器实际 EE target / EE actual / 误差 | `square_probe_control.py:29-32` |
| block target / block actual / 误差 | `square_probe_control.py:33-34` |
| 窗口 target 与最后段 target 的差 | `square_probe_control.py:25-32` |

- 4100 仅在需要确认“速度衰减差异”时作为对照；不因本次目标一致性结论而重跑。

## 5. 判定

- 目标交接：**一致**；无需为“目标交接”做最小修正。
- 若下一步要修正，应针对速度/过冲控制，而不是 target 变量；需先取得 RMP 输出/关节位置/速度字段。
- 本轮停止在审查阶段；未启动仿真，未修改冻结候选、回执、控制或阈值。
