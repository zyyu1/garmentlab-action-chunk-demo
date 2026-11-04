# a5-rc2-drift-diag-v1：RC2 释放窗口诊断记录

本目录是 RC2 的独立诊断版本，用于补齐 A5 漂移诊断第 2 步缺失的释放/开爪/退让逐物理步信息。**不是新任务，不是正式批次，不改变 RC2 的物理、控制频率或动作目标。**

## 1. 版本与身份

| 项目 | 值 |
|---|---|
| 版本 | `a5-rc2-drift-diag-v1` |
| 父版本 | `stage4-a5-rc2` |
| 基础 candidate SHA256 | `10a6cb452b9fafd5907f245b68fd02d49c7af1e12fa6cb0f755f1791a5af27a5` |
| 基础 manifest SHA256 | `39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d`（60 项） |
| 诊断 manifest | `a5-rc2-drift-diag-v1-files.json`，66 项（60 项基础 + 6 项诊断） |
| 诊断 manifest SHA256（v1.1） | `13c1f20a5081fdaea7cdbd25a299c3086fec0500eb9773f9fb1351b232a0c922` |
| 诊断配置 SHA256（v1.1） | `aa5da98be1dc03f588125d99ed6e5cc0e41728ae32c8770cfe27dfd3a6c06149` |
| 诊断 runner SHA256 | `125111b276e9e9199eacffb5d132518a02e8eab30614366e05691bde698c9e38` |
| 采集副本 SHA256 | `3a4ce720fc7adca10ba6f0b2064c197f97e53ac0208de14c30e820b3abad86b1` |
| release 记录器 SHA256（v1.1） | `dbb7801c82d685cb572e2ada4d4b55d588c693338e1df66f93ab5607c3840218` |
| 评估器 SHA256（v1.1） | `fcdc3383b9716c24b3d8e4e7b90837f6b1e84c6fd6e7e5fec5e51e422a498771` |
| 入口 SHA256 | `2a1a3028f0998162aeae0fa6d3b43c732f68e5fe57da525b49f7b99f8eebbe7e` |
| 状态 | **v1.1 已运行并完成比较**：4202 `053151-197013`，`DIAG_ASSESS complete=True`、release_rows=157、contact_events=0、quality=rejected（稳定性，符合 baseline）；与 v1、RC2 4202 single 物理数组逐位相同，无需新物理版本；v1 保留为 `complete=False` 的初步记录；正式成功 0 |

## 1.1 v1 运行与 v1.1 修复（2026-11-03）

v1 4202 已运行：`day4-a5-rc2-drift-diag-20261104-050739-915052`，release_diag 157 行（155 state 步 + released/retreated），接触通道 0 事件，`quality=rejected`（稳定性，符合 RC2 baseline）。`complete=False` 的原因是：

1. `release_diag_action_target` 用 float32 记录目标、float64 比较、atol=1e-9；float32 转换后完全相等（最大 float64 差 1.26e-8 m）。
2. 起始锚点被写成额外 `state` 行，和最后一次保持状态共享 step 1943；原 evidence `continuous_steps` 因此 false。release_diag 自身 155 个 state 步连续。

v1.1 只改观察/审计：锚点改为 `release_anchor`（非 state），action target 按 float32 比较；不动物理步进、控制频率或动作目标。离线 fixture 1/1 通过。v1.1 4202 已运行 `day4-a5-rc2-drift-diag-20261104-053151-197013`，得到 **`DIAG_ASSESS complete=True`**、release_rows=157、contact_events=0、quality=rejected（稳定性，符合 baseline）。已与 v1 及 RC2 4202 single 逐项比较：release_diag 全部数组（finger 距离全 NaN、掩码相同）、12 个动作目标、success_trace、快照、2427 条 state 行逐位相同，只有锚点 kind 和三个诊断文件 hash 改变；无需登记新物理版本或重建 baseline。比较报告见 [v1_1_compare.md](../results/STAGE4_A5_RC2_RELEASE_DIAG_4202_20261103/v1_1_compare.md)。runner/capture/entry 未变。注意：`a5-rc2-drift-diag-v1.json` 的 `status` 字段写于运行前（仍为 “v1.1 rerun pending”）；该文件已纳入 66 项 manifest 且哈希冻结，未回写，实际状态以本 README 和运行目录的 `diag-verdict.json` 为准。

诊断对象：4202 single（首个），4302 single（后续复验）。基础初始目录分别为
`day4-square-initial-stripfold-20261103-062710-242560` 与
`day4-square-initial-stripfold-20261103-094143-137994`。

## 2. 新增记录

`release_diag.npz` 从 release 动作开始前的锚点，到 `retreated` 快照，逐物理步记录：

- `vertices`：441×3 布料顶点；
- `ee_m`、`ee_quaternion_wxyz`：夹爪位姿；
- `joint_positions`、`dof_names`、`finger_joint_indices`、`gripper_aperture_m`：关节与开合量（开合量由 finger joint 位置求和，非标定指尖间距）；
- `holding`、`attached`、`enabled_slots`、`logical_attached`、`command_holding`、`gripper_state`；
- `ee_min_vertex_distance_mm`、`finger_min_vertex_distance_mm`：几何距离证据；
- `sample_label`（released/retreated）、`phase`、`sim_time_s`、`observed_step`、`backend_step`、`call_id`。

`release_diag.json` 另存 action_begin/end、采样标签、物理 dt、记录字段、接触通道、距离证据说明和缺失/错误。`contact_report.json`/`contacts.jsonl` 来自现有的 `square_contact_recorder.ContactRecorder`；其 scope 是机器人刚体接触，**零事件不等于无接触**，也不是布料粒子接触认证。

## 3. 物理/控制/动作不变性

- `a5_recovery_diag.py` 相对 `a5_recovery.py` 只改了 manifest 路径、输出前缀、probe 版本、recorder/contact 导入、diagnostic 元数据；`action`、`action_chunk`、`local_arc`、180 步保持、12 动作预算、release 目标和 331 步 success trace 均未改。
- `a5_capture_diag.py` 相对 `a5_capture.py` 只在同一个 `release(target)` 前后加 `start_release_diag`/`finish_release_diag`，并改协议/manifest；331 步循环、采样时钟、`world.step` 次数和 `zero` 时钟未改。
- `release_diag.py` 只读 `world.step` 后的状态，不调用 `world.step`、`execute`、`apply_action` 或位姿设置。
- 离线 fixture `test_release_diag.py` 已通过（1/1）：验证 441 顶点、9 关节、开合量、EE/finger 距离、released/retreated 标签、state dt=1/60、state step 连续、action 目标、且没有额外物理步。
- 运行后 `a5_diag_assess.py` 再检查 12 动作、`state_dt_ok`、`state_step_ok`、release action 目标、诊断 manifest 和原 B v1 证据；若与 RC2 4202 single 的目标序列不一致，停止并登记新版本。

## 4. 远端运行

上传整个目录（保留字节，不做行尾转换）：

```powershell
scp -P 23636 -r E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\a5-rc2-drift-diag root@connect.nmb2.seetacloud.com:/root/autodl-tmp/
```

运行 4202 single：

```bash
cd /root/autodl-tmp/a5-rc2-drift-diag/app
bash run-a5-rc2-drift-diag.sh 4202 single
```

期望日志至少包含：

```text
DIAG_MANIFEST_OK 66 <base-manifest-sha> 4202
DIAG_RUN a5-rc2-drift-diag-v1 passed ... errors ...
DIAG_EVIDENCE True True
DIAG_CONTACT True|False
DIAG_ASSESS complete=True|False quality=... release_rows=... contact_events=...
```

输出目录为 `/root/autodl-tmp/day4-a5-rc2-drift-diag-<timestamp>`。下载：

```powershell
scp -P 23636 -r root@connect.nmb2.seetacloud.com:/root/autodl-tmp/day4-a5-rc2-drift-diag-<timestamp> E:\learning\project\thesis\day4-actionchunk-test\results\
```

4302 single 复验把命令末尾改为 `4302 single`；不要跑 held-out，不要改参数，不要用诊断 run 冒充 RC2 或正式成功。

## 5. 离线检查命令

```powershell
cd E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\a5-rc2-drift-diag\app
python test_release_diag.py -v
python -m py_compile release_diag.py a5_capture_diag.py a5_recovery_diag.py a5_diag_assess.py
bash -n run-a5-rc2-drift-diag.sh
```

## 6. 解释边界

- 诊断 run 的 B v1 质量结果只作比较，不升级为正式成功。
- 接触通道若零事件，记录为 `configured_no_events_channel_not_independently_validated`；不得写成“无接触”或“无碰撞”。
- EE/finger 距离是距离证据，不能替代真实接触力/冲量。
- 若 runner 在 release 前失败，`release_diag` 可能缺失；保留完整失败目录，不重试替换。
- RC2 原始目录不变；本目录与输出目录均为独立诊断版本。
