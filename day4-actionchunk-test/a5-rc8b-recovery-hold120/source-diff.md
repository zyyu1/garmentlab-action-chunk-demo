# 源码差异：rc8b → recovery-hold120

文件集合不变（63 项）。相对 rc8b **60 项逐字节相同**，仅 3 项变化：

| 文件 | 变化 |
|---|---|
| `a5_recovery.py` | 新增 `run_recovery_hold()`；在 `rec_release` 与正常 240 步 settle 之后、重新观测之前调用；新增 4 个事件 |
| `a5-rc2-pfs1-observation-v2.json` | 诊断登记、hold 定义、范围锁、账本 |
| `run-a5-rc2-pfs1-observation-v2.sh` | 单例编排、预检、账本 |

## a5_recovery.py 的插入点

```text
action(rec_release)
retreat_end = step/time
b._settle(240)                 # 原 recovery 正常 settle，不变
run_recovery_hold(...)          # 新增：120 × b._env.step()
record_stage(after_recovery)    # 原逻辑，现在在 hold 之后
record_material_stage(...)
recovered = 当前顶点            # 重新观测，不缓存
fold_observation 事件
compute fold_yaw / pick         # 原 expert 逻辑
```

## 未改

- 5 个 recovery 动作与 7 个 fold 动作、命令、horizon、目标生成逻辑。
- 物理参数、材料、夹具/附件、评价器、阈值、采样窗口、release clock。
- `a5_capture.py`、`pfs1_observation_v2.py`、`stage4_success_v1.py`、`stage4-success-v1.json`、`square-initial-plan.json` 与 rc8b 逐字节相同。

## 静态审计

- a5_recovery diff：**0 行删除**、新增 helper 与 6 行调用/事件。
- 新增代码中仅 **1 处** `b._env.step()`；无 `_set_garment_world_positions`、`_clear_garment_velocities`、`ParticleMaterial`、`control.move/grasp/ungrasp`、`GripperCommand`、`robot_goto_position`、`set_velocities`、`b._settle(`。
- 核心文件哈希与 rc8b 一致；Python 编译通过；shell `bash -n` 在远端预检执行。
