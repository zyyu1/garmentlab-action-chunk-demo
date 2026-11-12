# 2026-10-31 GarmentLab 日报：Stage 4 v5 保持与接触审查交接

## 停工状态

用户要求今天暂停。本次只读取已手动下载的 v5 结果并整理交接，不启动实验、不上传、不下载、不推送 GitHub。后续下载只提供命令，由用户手动执行。

当前结论：最新 v5 的短程抓取保持、释放与接触正控通过；尚未获得符合接口要求且可重复的 L1 折叠，正式成功仍为 0。脚本的 passed=True 只代表本次短程测试，不代表 Day4 或折叠验收通过。

## 本次读取的结果

本地结果均位于 `E:/learning/project/thesis/day4-actionchunk-test/results/`。

| 运行目录 | 结论 |
| --- | --- |
| day4-square-grasp-hold-v5-20261031-112822-203913 | passed=False，KeyError('attachment_bodies')，未形成有效保持/接触结论；保留为脚本失败尝试 |
| day4-square-grasp-hold-v5-20261031-113930-047613 | passed=True，errors=[]，短程测试完成；作为本次主要审查对象 |

远端对应目录前缀为 `<remote-root>/`。主要证据：`result.json`、`runner.log`、`hold_trace.jsonl`、`block_contacts.jsonl`、`contact_force_trace.jsonl`、阶段快照以及 `source/`。最新目录保存的 20 份源文件与其本地 manifest 哈希相符；本轮未重新核验服务器与本地传输哈希，也未独立解码整个视频。

### 保持与释放

- 保持轨迹共 60 条，holding 与 attachment_enabled 均保持为 true；采用关节位置保持，不能将其结论推广为 RMP 固定目标保持或移动路径已通过。
- held_check：位置误差 0.0004732958 m（0.4733 mm），臂关节最大速度 0.008601855 rad/s，orientation_reached=True，锚点最大间隙 0.001360942 m（1.361 mm）。
- 释放后 3 个槽位 holding=False、enabled=False。约束对象仍存在，因此仅证明禁用，不证明 reset 清理或资源释放已完成。
- result 记录 video_frames=255、formal success=False。

### 接触正控与新发现

- callback_count=751，event_count=2609；block_ground=2253，robot_ground=356，robot_block=0；回调 errors=[]。
- 事件正控和独立净接触力正控均为 true；力采样 150 条，其中 14 条为正，最大范数 287.5801。该力视图只覆盖辅助块，不能用于量化手指接触力。
- 双指与地面各产生 178 条事件：descend 25、close 41、held_stationary 60、release 22、released_stationary 30。事件日志步号为 585–762，保持阶段双指均持续有接触事件。
- 16104 条接触明细的 position、normal、impulse 全部为零。事件存在有明确证据，但详细接触几何和冲量没有得到有效数值验证；零值不能解释为没有接触力，也不能据此定位冲量峰值。
- robot_block=0 不能证明机械隔离，因为机器人与附件组已有碰撞过滤。不能把“正控通过”写成“无碰撞”。
- v5 增加了 reset 前接触 API 和辅助块力采样；力视图会将块 sleep threshold 设为 0。历史说明中的“物理完全不变”需要带上这一限定。v5 通过不单独证明 v4 零事件的唯一根因。

**诊断结论：已发现接触证据；事件和辅助块净力正控有效，但接触明细冲量不可用。尚未证明手指触地是此前失稳的原因。**

## 下次恢复工作的第一项

先做现有数据与代码的几何核对，不重复运行旧版，也不立即跑完整 L1：

1. 对齐夹爪末端坐标系、抓取点偏移、手指碰撞体与地面高度；检查下降至抓取位姿时是否存在不符合设计的触地或穿透。使用最新保存的源代码、01_before_close/02_grasp/03_held 快照和事件步号。
2. 同时核对辅助块实际中心约 z=15 mm、保持目标约 z=10.207 mm 的差异，以及地面约束对抓取的影响。先解释几何关系，不凭猜测调高度。
3. 若确认几何/坐标问题，做有依据的最小修正，保持公共动作定义与既有 held gate 不变，再验证接近→下降→抓住→保持→释放。
4. 若触地属于预期接触，明确其理由和验收边界；不得仅因事件存在就断言故障根因，也不要求无依据地消灭所有接触。

完成以上审查后再决定是否恢复 L1。接触明细若需要参与根因判断，须先修复或验证其有效性；不将整个工作重新扩展为无边界接触扫描。

## Day4 后续收尾顺序与未完成项

1. 接回 L1：先解决末段路径不连续，再验证 release/settle 后保持真正两半重叠；成功后独立重复一次。开发候选不计入正式成功批次。
2. 整合正式 Backend，统一 XYZ+yaw+gripper 公共接口；不允许实验俯仰侧通道。验证同一 episode 重抓取、reset 清理及状态隔离。
3. 动作预算：折叠与 recovery 总计 ≤12 个高层动作；当前离线模板折叠 7+一次 recovery 5=12，两次为 17，不能隐去 waypoint 或截断。全局最多两次不代表当前模板可执行两次。
4. 三档难度：L1 开发初态 10/10（seeds 4100–4109）；L2/L3 各 0/10。L1 是独立进程生成，不能算连续 10 次 reset/rollout。三档配置与视觉可区分性尚待最终验收。
5. 评价与记录工具、接口/预算规范及真实负例审查已具备离线版本；尚无真实成功正例，阈值未冻结，工具尚未完成 Backend 整合。
6. 冻结评价后运行正式批次：每档至少 5 条成功，共至少 15 条；保留所有失败、配置版本、seed、recovery 次数及拒绝率分母。把连续 10 次 reset/rollout 验证纳入批次。
7. 最后核验接口、视频、30 张初态图和验收表；全部完成后才进入 Day5 正式 demonstrations。

旧服装、翻腕及质量/求解器/高度参数扫描分支保持冻结。不要依据旧 README 或历史 pipeline_passed 标志判断当前折叠进度。

## 继续阅读入口

- [当前下一步](DAY4_NEXT_STEPS.md)
- [最小收尾计划](DAY4_MINIMUM_PLAN.md)
- [验收状态](DAY4_ACCEPTANCE_TRACKER.md)
- [v5 预登记说明](day4-actionchunk-test/SQUARE_GRASP_HOLD_V5.md)
- [最新 v5 原始结果](day4-actionchunk-test/results/day4-square-grasp-hold-v5-20261031-113930-047613/result.json)
- [接口与 recovery 规范](day4-actionchunk-test/DAY4_INTERFACE_RECOVERY_CONTRACT.md)
- [评价与记录说明](day4-actionchunk-test/DAY4_EVALUATION_RECORDING.md)

恢复时先读本日报及上述最新 v5 目录。历史文件中“v5 待运行”“正控尚未通过”等段落已被本次结果取代；今天停工之后没有新实验待自动执行。
