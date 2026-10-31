# Day4 公共接口、动作预算和 recovery 开发规范

状态：离线设计，未接入正式 Backend、未通过物理验证。抓取调试暂停；正式成功 0。不修改当前 schema，不启动仿真。

## 公共动作语义

每行 `[x, y, z, yaw, gripper_command]`：XYZ 单位米，为世界坐标系中的末端参考点；当前 Franka 适配为 right_gripper。yaw 单位弧度，绕世界 Z 轴。命令 OPEN=0、CLOSE=1、HOLD=2。一个 ActionChunk 的 H 行计 H 个高层动作。

候选固定底层姿态为 Rz(yaw)Rx(pi)，由 Backend 对所有调用者统一执行。URDF 指尖中点相对末端局部偏移 +3.4mm 仅是候选参考，不是已标定夹持点。材料抓点到末端的坐标转换封装在适配层；policy 只输出上述五维动作，不输出粒子索引、USD 路径、关节指令、俯仰侧通道或实验开关。oracle_keypoints 仅可作为明确声明的 expert 输入。

OPEN：先解除现有抓取，再移动到给定目标。CLOSE：移动到给定目标并抓取。HOLD：保持当前夹爪状态并移动。底层只允许到目标的统一插值和收敛控制，不能根据 expert 标签插入隐藏的抬升、绕行或折叠路径。settle 为预先记录的固定测量等待，无新空间目标；任何新增撤离或校正目标均计一个动作。

共享 Backend 目前尚未统一上述 yaw 语义；独立 SquarePoseBackend 为开发候选。重抓取、失败恢复和 reset 清理均待整合验证。

## 预算表

| 模板 | 公开 waypoint 顺序 | 动作数 |
|---|---|---:|
| 对折 | approach OPEN → pick CLOSE → lift HOLD → transfer HOLD → place HOLD → release OPEN → retreat OPEN | 7 |
| recovery | approach OPEN → pick CLOSE → lift HOLD → spread_place HOLD → release OPEN | 5 |
| 无 recovery + 对折 | 7 | 7 |
| 一次 recovery + 对折 | 5 + 7 | 12 |
| 两次 recovery + 对折 | 5 + 5 + 7 | 17，拒绝执行 |

这是预算设计，不证明这些直线段可达或能成功对折。若 transfer/place 之间必须新增独立目标，必须重新计算预算；不能隐式塞进 Backend。当前最多两次 recovery 是上限，不是必须执行两次。本模板在 12 步约束下实际最多一次，第二次记录 `budget_exhausted` 后结束失败，不截断对折轨迹、不删失败分母。

动作提交前递增 attempted_actions；失败动作也计数，重试必须另计。恢复前先为完整剩余对折保留预算。安全清理如有额外控制动作，单独保存并将该回合标失败，不当作预算内成功示范。

## 一个参数化 recovery 模板

1. 触发：初态观测有效、未在持布，且已冻结的 spread 判据不通过。L1 不自动启用 recovery；L2/L3 适用相同模板。当前没有已冻结的几何阈值，因此生产调用保持禁用。
2. 选点：在声明的 oracle_keypoints 中取有效、可达的材料角点；选择与名义展平目标偏差最大的角点，同分按固定角点标签排序。目标为配置中的角点展平目标。若输入不足、不可达或需要额外绕行，记录原因并停止，不能随机补点。
3. 参数：pick/approach/lift/spread_place/release 五个明确末端目标、yaw、固定settle步数和预算预留。调用同一个模板，不为不同难度写隐藏分支。不直接修改布料粒子作为 recovery。
4. 停止：一次执行后释放并静置，重新计算 spread 判据；达标则进入对折。未达标时重新检查 recovery 次数和动作预算。本版剩余预算不足第二次，直接记录失败。到达/速度/附件异常、数据无效时立即停止并保留诊断。

目前仅定义模板与停止规则，未给出未经验证的数值阈值或抓取坐标，不计为 recovery 已实现验收。难度初始化的 lift/drop 属于 reset 生成过程，必须单独记录；不能在 episode 开始后做免费初始化动作规避12步上限。

## 批次记录规范

每个尝试都写一行 JSONL：attempt_id、seed、difficulty、asset/config/expert/backend/evaluator 版本或哈希、status、failure_reason、attempted_actions、completed_actions、recovery_attempts、指标及测量步、success、视频/状态/动作路径、reset检查结果。success 在未评价时为 null，不能用 pipeline passed 代替。

status 区分 running / success / rejected / error；仅所有冻结判据通过才设 success=true。初始化、控制、保存和评价错误全部保留。每档报告总尝试、成功、rejected、error、未完成；未完成未结算时不得给出最终拒绝率。全部结束后 rejection rate=(rejected+error)/总尝试。中断批次保留原 attempt_id，重新运行另建尝试，避免覆盖失败。

连续10次 reset/rollout 必须在同一 Backend 生命周期中记录，独立进程生成10张图不能替代此检查。正式每档至少5条成功轨迹及全部失败记录仍待完成。

## 当前交付和下一步

`day4_action_budget.py` 提供纯离线模板构造和执行前预算检查，不控制机器人；已检查7/12/17步边界、失败重试预算和非有限坐标拒绝。下一步完善评价与批次记录工具、审查已有失败样例；仍需有效折叠候选才能冻结最终阈值。L2/L3初态生成、抓取稳定、Backend整合均保留为未完成，不因离线设计而打勾。
