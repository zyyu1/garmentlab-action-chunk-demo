# v5 接触正控修复候选（待运行）

## 问题定位

v4（`day4-square-grasp-hold-20261031-104528-426384`）held gate 通过，但接触记录 `callback_count=0`、`event_count=0`、块-地正控 0；保持阶段辅助块中心 z 恒为 15.000 mm、目标 10.207 mm，块持续被地面挡住。v4 的 `square_block_contact_recorder.py` 在 `env.reset()` 之后才 `PhysxContactReportAPI.Apply`，此时 PhysX 已创建刚体并开始仿真；另外辅助块可能进入 sleeping，sleeping body 不产生接触报告。两个原因都足以使正控为 0。

## v5 唯一改动范围

只改接触诊断，不改公共四动作、目标、路径、物理配置、60 步保持、30 步释放及 held gate 阈值。

1. `square_contact_reporting.py`：在槽位创建时（`env.reset()` 之前）对 3 个辅助块和 12 个机器人刚体写入 `PhysxContactReportAPI`，threshold=0；reset 后逐路径校验 API 与 threshold 是否保留，写入 `contact_report_setup_early.json` 和 `contact_report_after_reset.json`。
2. 同时在 reset 前创建 3 个辅助块的 `RigidPrimView`（`track_contact_forces=True`），reset 后手动初始化，按 5 步采样 `get_net_contact_forces()`，写入 `contact_force_trace.jsonl`。构造该 view 会把辅助块 sleep threshold 设为 0（接触报告必需），这是本轮唯一的物理相邻改动，需在读取结果时注意；`disable_stablization=False` 保留原 stabilization 设置。
3. `square_block_contact_recorder_v2.py`：不再在 reset 后补写 API；只验证早写结果、订阅接触事件并分类记录。主正控仍按 v4 预登记：`block_ground` 事件数 > 0；独立的力通道正控为任一步辅助块净接触力 > 1e-6。若事件正控仍为 0 而力正控 > 0，则诊断记为 `force_only_positive_control`，事件通道仍未修复，不据此解锁。

## 预登记判读

- held gate 与 v4 相同：位置误差 <10 mm、保持末臂速 <0.1 rad/s、姿态到达、锚点间隙 ≤10 mm，释放后附件全部 disabled。
- 正控有效：`block_ground` 事件 > 0。此时若 `robot_block` 事件为 0，按 v4 预登记可进入第 1 步解锁审查；但 robot↔attach 本就被 collision group 过滤，`robot_block=0` 不能单独证明机械隔离，仍需保留该限制。
- 若 `block_ground` 事件仍为 0，但辅助块净接触力 > 0：说明接触本身存在、事件通道仍失效；本轮不视为正控修复完成，不进入 L1，下一步研究事件订阅/PhysX 配置。
- 若两者都为 0：早写 API 与力通道都未生效，停止该方向，先做最小独立接触测试，不再跑完整保持。
- 本轮只运行一次；不延长保持、不改阈值、不调 RMP 增益、不改块尺寸/质量、不进入 L1 折叠。

## 产物与运行

运行命令：

```bash
bash /root/autodl-tmp/run-square-grasp-hold-v5.sh
```

预期新增产物：`contact_report_setup_early.json`、`contact_report_after_reset.json`、`contact_force_trace.jsonl`、`block_contacts.jsonl`、`block_contact_report.json`；结果 JSON 增加 `contact_positive_control` 汇总。正式成功仍为 0。

## 上传状态

本地清单 `square-grasp-hold-v5-files.json` 共 21 个文件；远端 `/root/autodl-tmp/` SHA256 全部一致，`py_compile` 与 `bash -n` 通过。尚未运行。
