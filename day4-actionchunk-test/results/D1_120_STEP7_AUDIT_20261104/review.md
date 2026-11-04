# D1-120 步骤 7：下载与核验

对象：`day4-a5-rc2-d1-120-20261104-071602-499516`。离线审计，无新增仿真。

**46/46 检查通过，`D1_STEP7_OK`。**

## 远端与本地完整性

- 远端 97 个文件全部列出 SHA256；本地下载文件集合与远端完全一致，无缺失/多余。
- **97/97 本地 SHA256 与远端一致。**
- 初态 `result.json` `4472f4df…`、`initial_geometry.npz` `a6646d66…` 与 config/registration 一致。
- `success_meta.initial_hashes` 与 config 一致；initial_case 为 seed 4202、perturbed、`blocked_unvalidated_corner_lift_drop`。

## 公开动作

- 12 个动作；labels、commands、call horizons（12×1）与 RC2 4202 single 完全一致。
- 12 个 4D 动作目标最大绝对差 **0.0**；最后动作仍为 `release_retreat`。
- 退让目标未因等待改变。

## 物理时间

- 内部等待：world step `1955→2075`，**120 步**，sim time `32.58333503268659→34.58333513699472`，**2.000000104 s**。
- 等待期间 EE 位移 **0.0 m**；`control_calls=0`、`target_changes=0`；无布料位置/速度重置。
- observed step 的五个事件：`ungrasp_return 1953`、`delay_begin 1953`、`delay_end 2073`、`retreat_begin 2073`、`retreat_end 2217`；`delay_end-delay_begin=120`，顺序正确。
- world step 与 observed step 的固定偏移为 2；success trace absolute start 2219，与 retreated/退让结束的 observed 2217 一致。
- 相对 RC2 4202 single：`absolute_step` **+120**，`sim_time` **+2.0000001 s**；这是唯一全局时钟偏移。

## 附件与事件

- `phase=delay` 恰好 **120** 行；这些行 `holding=false`、`attached=false`、三个 slot 全 false、`logical_attached=false`、`gripper_state=0`。
- `release_diag` 277 行：delay 120、retreat 144、release_opening 10、released 1、retreat_done 1、anchor 1。
- 五个事件完整且顺序正确；`events_complete=true`。
- success trace 331 步，全程 `holding=false`、`attachment_enabled=false`、`gripper_open=true`。
- contact 通道 0 事件，`diagnosis=configured_no_events_channel_not_independently_validated`；**不得写成无接触**。

## 等待前轨迹与基线

D1 与 v1.1 `release_diag` 在 `observed_step ≤ 1953` 的 **12 行**逐数组比较，全部相同：

- 顶点 441×3、EE、四元数、9 关节、开合量、gripper_state
- holding/attached/enabled_slots/logical_attached/command_holding
- sim time、observed/backend step、call id、EE 距离、finger 距离（NaN 掩码相同）、released 标签

同时逐位相同：

- `pre_release_hold.npz` 180 帧
- `recovered.npz`
- `cloth_constructed.npz`
- `success_meta.initial_hashes`
- `pick_index=230`、`yaw_rad=0.10795666139009312`

唯一非精确项是 `upward_displacement_m`：D1 `0.14602033413356336` vs RC2 `0.14602046068486133`，差 **1.27e-7 m**；这是等待/退让之后的量，不是等待前差异，已在 1e-6 m 容差内。

## 质量与审计状态

- postfix verdict：`complete_diagnostic=True`，32 项检查全过；`quality=rejected`。
- 质心 2.040882 mm、P95 4.413414 mm；仍在 1 mm / 3 mm 之外。
- 标准 `a5_diag_assess.py` 仍在收尾时因 3D/4D target 形状 bug 崩溃；`run_ledger.assess_status=1` 原样保留，postfix verdict 是该 run 的审计结果。
- 视频 1279 帧解码通过；证据完整。
- `runs/completed` 已写入；无重跑。

## 产物

- [audit.json](audit.json)、[audit_stdout.txt](audit_stdout.txt)
- [remote-sha256.txt](remote-sha256.txt)、[remote-initial-sha256.txt](remote-initial-sha256.txt)
- 审计脚本：[audit_d1_120_step7.py](../../audit_d1_120_step7.py)

## 结论

步骤 7 完成：远端/本地完整、初态身份一致、动作目标 0 差、物理时间差恰好来自 120 步等待、附件状态全程分离、等待前轨迹与基线逐位相同。未发现需要先排查的等待前差异。

下一步：步骤 8 分别分析等待 120 步、退让和退让后静置窗口，并与基线对照。
