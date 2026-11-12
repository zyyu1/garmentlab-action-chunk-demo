# a5-rc2-d2c-release-order：D2-C 释放顺序单变量干预（已单次运行，quality rejected）

本目录是 **D2-C** 的独立诊断版本，从 D1-120 诊断复制并重定向身份。D2-C 只改变**末次释放的顺序**：夹爪先在与附件仍相连的状态下完成 10 步张开，再解除附件；原 `ungrasp` 内的第二次 `open()` 被抑制。120 步等待、12 个公开动作/目标/命令/horizon、退让目标和原 1 mm / 3 mm 阈值全部保留。

**当前状态：`completed_assessed`。** 已按 D2-D 上传、远端预检并**单次运行 4202 single**：`day4-a5-rc2-d2c-release-order-20261104-090032-412133`，episode `passed=True`、`DIAG_ASSESS complete=True`、`quality=rejected`（稳定性 1.98 mm / 4.34 mm，仍超 1 mm / 3 mm）。无重试。对照结论见 [D2-D 报告](../results/D2_D_COMPARE_20261104/review.md)：释放顺序没有降低释放瞬态（第一步仍约 17.42 mm/s），**不是该例漂移的主要因素**。

## 1. 身份

| 项目 | 值 |
|---|---|
| 版本 | `a5-rc2-d2c-release-order` |
| 父诊断 | `a5-rc2-d1-120`（干净运行 `day4-a5-rc2-d1-120-20261104-071602-499516`） |
| 父 manifest SHA256 | `cd1d7f83d065974e12191486eddbf722edd4a1b7392ec78543966483434b25a6`（66 项） |
| 父 config SHA256 | `a6884eab8ae4bf6d703b0321415cfc2cd501f878472068109addba564ba4d471` |
| 基础 candidate SHA256 | `10a6cb452b9fafd5907f245b68fd02d49c7af1e12fa6cb0f755f1791a5af27a5` |
| 基础 RC2 manifest SHA256 | `39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d`（60 项） |
| D2-C manifest | `app/a5-rc2-d2c-release-order-files.json`，66 项（60 基础 + 6 诊断） |
| D2-C manifest SHA256 | `778935ab6ec62a093470a8485a86e241884ba4f867c1be6d0f57c4f3f9eda537` |
| D2-C config SHA256 | `96acc5fa4a0a318c876437c236a5c9260497a00028adb6db280784ed1725be27` |
| 登记文件 | [registration.json](registration.json) |
| 静态审计 | [static-audit.json](static-audit.json)（全部布尔检查为 true） |
| 状态 | **已单次运行、诊断 complete、quality rejected**；正式 Stage 4 成功仍为 0 |

## 2. 初态身份（4202 single）

| 项目 | 值 |
|---|---|
| 初态目录 | `<remote-root>/day4-square-initial-stripfold-20261103-062710-242560` |
| `result.json` SHA256 | `4472f4df6332a240da52b8c2ebaf7dd91f5f958e10a09803b64658699aea8adb` |
| `initial_geometry.npz` SHA256 | `a6646d66bed8d00d046c2195c733f7f3aefc6471ca458995e247c11091e86106` |
| seed / level / mode | 4202 / perturbed / single |
| 折向 | right |
| 公开动作 | 12（与 D1-120 / RC2 相同） |

## 3. 为什么选这个干预

D2-A/B 证据见 [D2_A_B_SCENE_CONTACT_20261104](../results/D2_A_B_SCENE_CONTACT_20261104/review.md)：

- D1 中附件在 **1944** 变为 `holding=false / attached=false`，但 `gripper_state` 到 **1954** 才变成 OPEN；**附件关闭早于夹爪张开完成 10 步**。
- 附着解除的 1 步内粒子平均速度从 prehold 的 0.26 mm/s 跳到 **17.4 mm/s**，前 5 步达到 **36 mm/s**；说明释放瞬间存在整体冲量。
- 没有发现 particle material 未绑定；`friction=0.3`、`particleFrictionScale=0` 均可读且与 initial protocol 一致。支撑地面只有 PhysX 默认材质，没有显式 material binding。
- PhysX contact-report 不支持粒子布料—地面接触报告；布料接触只能用高度/穿透/速度等几何与运动证据，不能声称接触力。

因此 D2-C 选择**唯一干预**：把夹爪张开的 10 步移到附件解除之前，使释放发生在夹爪已经张开之后；不提高摩擦，不清零布料速度。预期若释放冲量是漂移主因，则释放步/前 5 步速度与后续漂移会下降；若不变，则释放顺序不是主因。

## 4. 单变量改动

实现位于 `app/a5_capture_diag.py` 的 `preopen_while_attached()`，由 `measure_ungrasp()` 在调用原 `control.ungrasp` 前执行：

1. 断言当前 slot `holding=true` 且 `attachment_enabled=true`。
2. 调用 `active.robot.open()`，恰好推进 **10** 个物理步。每一步都重新读取并断言：`active.holding`、`active.attachment_enabled()`、`control.holding`、`control.attachment_enabled()` 一致为 true，并调用 `control.assert_exclusive()`；**没有关闭任何全程状态检查**。允许夹爪张开但布料仍被持住。
3. 保存原 `open` 方法，在调用原 `ungrasp` 时临时替换为 no-op，抑制其第二次 `open()`。
4. 原 `ungrasp` 照常 `set_velocities(0)` 并 `enabled.Set(False)`；随后断言 attachment 与 holding 均已关闭。
5. 记录 `release_order`：干预名、preopen 起止/步数、`preopen_state_checks=10`、attachment 解除 step、开合量前后、`suppressed_second_open=true`，以及释放边界采样字段（见下）。

与 D1-120 相比：**总物理步数不变**（同样的 10 步张开只是移到解除之前；120 步等待保留）。与 RC2 相比仍多 120 步。公开动作、目标、命令、horizon 和退让目标不变。

## 5. 保留的 D1 内容

- 120 步等待仍在第 12 个公开动作 `release_retreat` 内、ungrasp 返回后、原向上退让目标前。
- 等待期间不调用 `robot_goto_position/open/close`，不改变目标，不写布料位置，不清速度。
- 五个事件 `ungrasp_return`、`delay_begin`、`delay_end`、`retreat_begin`、`retreat_end` 与 phase 标签保留。
- 证据仍包含逐物理步的顶点、EE 位姿/四元数、全部关节、开合量、attachment 标志；事件行含布料质心和顶点 SHA256。
- 评估窗口仍为 capture 0..330、evaluate 210..330；阈值仍为质心 1 mm、顶点 P95 3 mm；按释放后的 elapsed time 比较。
- **release t=0** 取附件解除后立即发出的 `released` sample，而不是 `delay_begin`，也不是首个全关 state。该 sample 是零物理步的状态读取，应与最后一个 preopen state 共享 `observed_step`；记录其 step、boundary step 和 delta。若 delta 非零，报告采样误差，不把首个全关 state 当作精确解除瞬间；首个等待 state 是随后一步。
- 瞬态取 release+0..30 步（0–0.5 s），后续滑移取 release+30..120 步；等待窗口对 D1 与 D2-C 都取 release+0..120 步，因此 D1 包含其 10 步开爪。退让和正式 210..330 窗口按公开动作相对时间另报。

## 6. 离线验证

| 检查 | 结果 |
|---|---|
| manifest | 66/66 路径与 SHA256 通过；基础 60 项与 RC2 一致 |
| `py_compile` | 通过（`a5_capture_diag.py`、`a5_recovery_diag.py`、`a5_diag_assess.py`、`release_diag.py`、测试） |
| `bash -n` | 通过 |
| `test_d2c_release_order.py` | **13/13 通过**：5 个等待测试 + 8 个释放顺序测试（10 步、每步 holding/attachment 一致、开合量增加、拒绝错误步数/失附件/中途失附件/未增开合量、config 登记） |
| `test_release_diag.py` | 1/1 通过：五个事件、`events_complete`、事件 CSV |
| 全程状态检查 | `audit_episode_evidence.py`、`episode_evidence.py` 与 D1 字节相同；`state_consistent` 仍要求 holding/attached/logical_attached/enabled_slots 一致，未针对 preopen 放宽 |
| 静态动作身份 | `a5_recovery_diag.py` 与 D1 的 21/21 action/horizon 行相同；`start_ee`、退让目标、`release(target)` 相同 |
| 静态 source diff | `a5_recovery_diag.py` 仅版本字符串和 `release_order` 诊断元数据行不同（11 行 diff，精确重建验证通过） |
| 摩擦/速度清零 | 捕获源码不含 friction 修改；不含 `_clear_garment_velocities` / `set_velocities` |

**已执行：** 远端上传、远端 offline preflight（`D2C_PREFLIGHT_ONLY=1`，66/66，未启动仿真）和一次 4202 single episode。运行证据与退出码见 [D2_D_RUN_4202_20261104](../results/D2_D_RUN_4202_20261104/)，对照见 [D2_D_COMPARE_20261104](../results/D2_D_COMPARE_20261104/review.md)。

## 7. 运行入口（已执行一次）

```bash
# 远端 preflight（不启动 Isaac 模拟）
D2C_PREFLIGHT_ONLY=1 bash run-a5-rc2-d2c-release-order.sh 4202 single

# 单次 4202 single（仅在明确进入 D2-D 后执行）
bash run-a5-rc2-d2c-release-order.sh 4202 single
```

runner 只接受 `4202 single`；`completed` 标记存在时拒绝第二次运行，除非显式 `D2C_ALLOW_RERUN=1` 且已完成首次审查。运行后 `a5_diag_assess.py` 检查 release_order 字段、120 步等待、事件、公开动作身份和原 B v1 质量；诊断完成不等于正式 Stage 4 成功。

## 8. 边界

- 不修改、不覆盖 D1-120、RC2 或 v1.1 目录。
- 不提高摩擦、不改变碰撞/材质、不清零布料速度。
- 原阈值 1 mm / 3 mm 保持不变；正式批次暂停；不使用 held-out。
- D2-C 只做一次 4202 single；失败结果保留，不自动重试。
- 单次运行只能检验预登记现象，不能据此宣称普遍因果；若漂移不变，应报告“释放顺序不是主要因素”。

## 9. 上传（已执行）

```powershell
scp -P 23636 -r E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\a5-rc2-d2c-release-order <server>:<remote-root>/
```
