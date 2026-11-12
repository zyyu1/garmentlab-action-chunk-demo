# Stage 5 最小采集试跑登记（2026-11-06）

**状态：试跑登记，运行 1 个 seed、单次、无重试。** 未启动批量采集或训练。

## 1. 试跑 seed

| 项 | 值 |
|---|---|
| seed | **4100**（dev seed） |
| 档 | flat（L1 过折，7 个公开动作） |
| 与 Stage 4 验收 seed 的关系 | 验收集为 4110–4129 / 4210–4229 / 4310–4329；4100 **不重叠** |
| 初态目录 | `<remote-root>/day4-square-initial-20261105-014501-526555` |
| 初态生成协议 | `stage4-initial-v2-task-scoped`（protocol 块：task/level/seed、pfs expected=0/readback=0、材料绑定、生成器身份） |
| 初态哈希（冻结 dev 注册） | `result.json` `df9ed582…`、`initial_geometry.npz` `dd578303…` |
| 授权路径 | `a5_entry.authorize_initial(..., split='dev')`：dev 注册 modes 含 `single`、目录与文件哈希必须一致 |

说明：4100 是已登记的 dev seed，不属于 Stage 4 验收集；试跑用它验证采集/导出链路。另：本轮曾生成 4105 的新协议初态（`day4-square-initial-20261106-234509-540123`），未用于本次试跑，留作后续演示 seed 候选。

## 2. 必需观测字段（Stage 5 计划 §5.2 + STAGE5_FIELD_CHECK）

计划最低完成版：**garment keypoints / sampled particles + gripper pose + grasp state + task phase**；允许 `oracle_keypoints`（状态输入），RGB-D 可选。

| 字段 | 试跑来源 | 形状/类型 |
|---|---|---|
| timestamp | 快照 JSON：`backend_step`、`sim_time_s` | int / float |
| garment_keypoints（状态真值） | 快照 NPZ：`vertices`（441×3，世界坐标） | float64 (441,3) |
| end_effector_pose | 快照 NPZ：`ee`（3） | float64 (3,) |
| gripper_state | 快照 JSON：`holding`；关节位置 `joints`（含两指） | bool / float (N,) |
| task_phase | 由 action label 映射（见 §3），暂作元数据 | str |
| action | 同一 `action_begin` 的 `targets`（[x,y,z,yaw]）与 `commands`（0/1/2） | list[4] / int |
| success | 原评价器 `a5-verdict.json.status` / `result.json.passed` | str / bool |

**采样方式：** 每个公开动作执行前的只读快照（`EpisodeEvidence.emit('action_begin')` 后立即读取 `vertices/ee/joints`，不 step、不调用控制、不写布料）。**不启用全物理帧 overlay。**

**配对：** 快照的 `call_id`（1..N）与 `result.json.actions` 的序号（0..N-1）一一对应（`call_id = index + 1`），同一 `action_begin` 已含 target/command，可按索引与时间戳双重核对。

## 3. action label → TaskPhase 映射（登记）

`phase_map.json`：approach→APPROACH、close→GRASP、hold→TRANSFER、arc45→LIFT、arc90/arc135→TRANSFER、place→PLACE、release/retreat→RELEASE、recovery_*→RECOVERY。phase 暂作元数据，不参与训练目标。

## 4. 导出验证（试跑后）

- single-step：每个公开动作 1 条（observation = 动作前快照，action = target+command）。
- H=4：同一 episode 内连续 4 个公开动作；非重叠切块；尾部不足 4 的块按计划处理（补齐 mask 或丢弃，报告中注明），**禁止跨 episode**。
- 核对观测数 == 动作数、字段形状、call_id 对齐。

## 5. 运行与判定

- 服务器侧：`--preflight` → `--plan-only`（确认只安排 4100）→ 单次 `--run`。
- 仅当 `a5-verdict.status == accepted` 且采集证据完整（action 快照数 == 动作数、result/evidence 齐全）时，才把该轨迹纳入 demonstrations；否则只记录缺口。
- 无自动重试；失败即停并报告。
