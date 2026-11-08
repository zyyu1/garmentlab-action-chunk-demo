# Stage 6 终端退让判据核对（源码依据与修改）

日期：2026-11-08。只做离线核对；不启动仿真、不重训、不重跑 6120。

## 1. 原冻结实现逐项

### 1.1 专家生成目标

`a5-rc8b-recovery-hold120-rc7-r2/app/a5-candidate.json` 第 73 行：

> `"release_action": "public OPEN target = measured EE + [0,0,0.15] m; existing ungrasp before move"`

`a5-rc8b-recovery-hold120-rc7-r2/app/a5_capture.py` 第 20-22 行：

```python
start_ee = np.array(backend._env.robots[0].get_cur_ee_pos()[0], dtype=float)
target = start_ee + [0., 0., .15]
```

因此 `released EE + [0,0,0.15]` 首先是**专家释放动作的目标生成公式**。

### 1.2 原协议实际检查的退让方向/位移/解除附着

`a5_capture.py` 的 `release_window`：

| 检查 | 源码位置 | 内容 |
|---|---|---|
| 释放前已 detached | 第 23-30 行 | `measure_detachment` 要求 `backend._holding` 为 false、所有 slot `attachment_enabled()` 为 false、`_gripper_state == 0`，并把参数 target 与 `start_ee+[0,0,.15]` 比较 |
| 实际向上位移 | 第 65-68 行 | `retreated.ee_m - released.ee_m`，`delta[2] < .01` 直接 `raise` |
| 释放动作目标身份 | 第 27 行 | `np.allclose(args[0][0], target, atol=1e-6)`，是专家 release 动作的身份检查 |
| 原评价时钟 | 第 61-62、69-70 行 | `zero = world.current_time_step_index`，`start_time = world.current_time`；`release_clock = {absolute_step, sim_time_s, dt_s, pick_index, yaw_rad, upward_displacement_m}` |
| 331 帧采样 | 第 77-97 行 | `for step in range(331)`；step 0 不 step，step 1..330 调 `world.step(render=True)`；每帧检查 `tick == zero+step` 且 `time == start + step*dt`；保存 vertices/holding/attachment/gripper_open/absolute_steps/sim_time_s |
| hold 样本 | 第 96-97 行 | trace step 180 / 240 调用 `recorder.sample('hold_3s'/'hold_4s')` |
| trace 文件 | 第 99-103 行 | 331 帧写 `success_trace.npz`，否则 `partial_trace.npz`；`initial`/`local_points` 一并保存 |

`a5_capture.finish_metadata`（第 153-167 行）把 `release_clock` 合并进
`success_meta.json`（`absolute_step`、`sim_time_s`、`dt_s`、`pick_index`、
`yaw_rad`、`upward_displacement_m`）。

### 1.3 原评价器的物理检查

`a5-rc8b-recovery-hold120-rc7-r2/app/stage4_success_v1.py` 的 `evaluate`：

| 检查 | 源码位置 | 内容 |
|---|---|---|
| held | 第 113 行 | `position_error_m < held_position_max_m`、`arm_speed_rad_s < 0.1`、`anchor_gap_max_m <= 0.01`、`orientation_reached is True` |
| released_continuously | 第 114 行 | 331 帧全部 `not holding`、`not attachment_enabled`、`gripper_open` 全 true |
| geometry_entire_window | 第 116 行 | frames 210..330 全部 geometry pass |
| stable | 第 118-127 行 | 窗口内 centroid/vertex drift、vertex speed 阈值 |
| 331 帧/时钟 | 第 95-103 行 | `steps == arange(331)`、`dt_s == 1/60`、数组 shape/dtype 校验 |

`stage4_success_v1.evaluate` **没有**检查：
- 释放 target 是否等于 `released EE + [0,0,0.15]`；
- target 的向上方向；
- 退让的专家动作标签。

它只检查 detach/open 连续性、331 帧窗口、几何和稳定性。

### 1.4 `a5_entry.assess` 的专家协议身份检查

`a5_entry.py`（Stage 4/5 assess）第 102-123 行：

- 第 114-115 行 `final_open`：最后 label 必须是 `release_retreat`、command 0、call_id 一致；
- 第 116-117 行 `upward_public_target`：
  `target == released.ee_m + [0,0,.15]`（atol 0.002）**且**
  `retreated.z - released.z >= .01`；
- 第 118 行 `clock_origin`：`end[-1].sim_time_s == start_time` 且
  `retreated.sim_time_s == start_time`；
- 第 119-120 行 `absolute_clock`：`absolute_steps == meta.absolute_step + arange(331)`，
  `sim_time == start_time + arange(331)/60`；
- 第 121-123 行 `double_hold`/`terminal_matches`：hold_3s/4s 与 final 帧一致。

**结论**：`target == released EE+[0,0,0.15]` 是 `a5_entry.assess` 的
**专家释放动作身份/一致性字段**；`stage4_success_v1.evaluate` 不含该字段。
Stage 6 的 `bc_eval_adapter` 只调用 `stage4_success_v1.evaluate`，因此把 target
精确相等作为 BC 成功门槛属于额外专家协议门槛，而不是原物理判据。

实际向上位移 `>= .01 m` 则同时由 `a5_capture.release_window`（第 67-68 行）
和 `a5_entry.assess`（第 117 行）要求，属于原释放/退让协议；Stage 6 保留它。

## 2. Stage 6 修改前后

### 修改前（首例实际运行代码 `ae024ea4…`；后续证据修订 `22b8dc50…`）

`_terminal_release` 的 `terminal_ok` 要求：

```python
and terminal.get('frozen_target_ok') is True      # target == released EE + [0,0,.15]
and terminal.get('frozen_retreat_ok') is True     # actual upward >= .01
and terminal.get('detached_ok') is True
and held['accepted'] and fold_slot_ok and reference_ok
```

即把专家 target 身份也作为 BC 成功门槛。

### 修改后（当前 `562386ee…`）

`terminal_ok` 保留物理/协议要求：

- `physical_retreat_ok`：实际 `retreated.z - released.z >= .01`；
- `detached_ok`：released/retreated 的 holding/attachment 解除、gripper OPEN；
- `held`、`fold_slot_ok`、`fold_reference_ok`；
- `target_preserved`/`yaw_preserved`：Stage 6 不覆盖模型 target/yaw（完整性检查）；
- `release_clock` 与 331 帧完整；
- `bc_eval_adapter` 的 held/released/geometry/stable。

专家 target 一致性改为独立字段，不参与成功判定：

```json
"expert_target_consistency": {
  "policy_target_equals_released_ee_plus_015": false,
  "required_target": [...],
  "distance_m": ...,
  "atol_m": 0.002,
  "reasons": [...],
  "note": "expert action identity/consistency field; not a Stage 6 success gate"
}
```

- `terminal['expert_target_reasons']` 只记录专家一致性差异；
- `terminal['reasons']` 只保留物理/协议失败；
- `bc-verdict.json` 顶层增加 `expert_target_consistency` 和说明，不进入
  `success`/`reasons`；
- `frozen_target_ok`/`frozen_retreat_ok` 作为兼容别名保留，但成功门槛使用
  `physical_retreat_ok`；`frozen_target_ok` 不再参与 gate。

未改阈值：`max_distance=.03`（Backend prepared region）、`upward>=.01`、
`atol=.002`、331 帧、60 Hz、geometry/stability 阈值均未放宽。

## 3. 源码依据与冲突结论

- `a5_candidate.json` 第 73 行和 `a5_capture.py` 第 20-22 行：`+0.15` 是
  **专家 release 动作的生成公式**。
- `a5_capture.py` 第 27 行：target 精确相等是**专家 release 动作的身份检查**。
- `a5_entry.py` 第 116-117 行：target 精确相等与 actual upward 一起出现在
  **Stage 4/5 专家 assess**。
- `stage4_success_v1.py` 第 89-128 行：原物理评价器不含 target 精确相等；
  含 detach/open、331 帧、geometry、stable、held。
- 因此 Stage 6 现在：
  - **保留** actual upward displacement、detach/open、331 帧、held、geometry、
    stability；
  - **不把** target 精确相等作为 BC 成功门槛；
  - 把 target 精确相等记录为 `expert_target_consistency`，供报告/专家对照；
  - 不静默删除该关系，也不静默放宽物理阈值。

## 4. 离线核对

`check_stage6_offline.py` 新增：

```text
TERMINAL_CRITERIA_EXPERT_IDENTITY_NOT_GATE_OK
expert_target=False physical_retreat=True physical_fail_gate=True
```

含义：
- 模型 target 不等于 expert `released EE+0.15`，但实际退让 2 cm、detach/open、
  held/fold OK → `terminal_ok=True`，`expert_target_consistency=False`；
- 实际退让 0.5 cm → `terminal_ok=False`，物理门槛仍生效。
