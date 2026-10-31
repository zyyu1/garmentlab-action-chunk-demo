# 方巾末端接口审查与定向下降诊断

## 源码证据

本次运行留存的 runtime_source/robot.py:get_cur_ee_pos 使用 measured joints FK，校验KinematicsSolver末端frame与RMP配置一致；不是直接USD局部坐标。服务器安装的 lula_franka_gen.urdf 中 right_gripper 是 panda_link8 下固定frame，平移[0,0,0.1]、rpy[0,0,2.35619449019]。不能将它不经核实视为布料抓点。

runtime_source/original_control.py 设置局部grasp_offset=[0,0,-0.01]。附件目标为 EE_world + R(EE)*offset。下指姿态可将该偏移转为世界向上，v1/v2已观察到约+10mm。

runtime_source/backend.py:_execute_single 只读取target_pose[:3]，并对所有命令传[None]姿态。yaw当前没有实现；这必须在正式公共接口验收前修复。MyFranka.move在None时传orientation=None，下降不保持初始姿态。v2使用下降前姿态只做一次偏移逆换算，不能保证到达时对齐。

## 本次唯一实验

run-square-descent.sh；独立day4-square-descent.py和square_probe_control.py，保留v2目标生成、物理参数、位置和速度门限。只执行approach OPEN及descend OPEN，不CLOSE、不启用附件、不折叠。每段目标等待上限从1000缩至240步，仅减少诊断等待；不声称与原超时时长完全相同。

新增机器人刚体contact report（阈值0）、回调错误记录，逐事件保存physics step/phase/actors/colliders/position/normal/impulse。状态每5步记录EE位置/姿态、实际抓取参考点、当前线性子目标和关节速度。用同一physics step关联接触与运动。

接触分类：记录错误=>recording_failed；有事件=>contact_events_recorded_review_timing；无事件=>configured_no_events_channel_not_independently_validated。未设独立正控，因此无事件不得称无碰撞或完整记录有效；该记录也不认证布料粒子接触。

16文件本地AST及服务器SHA256/AST/Bash语法通过，未运行GPU。用户手动执行后自动下载结果。若发现同步接触，优先核查明确对象；若无有效证据，不凭结果改高度。后续姿态规则必须统一在Backend中实现并落实yaw，不能引入expert俯仰侧通道。正式成功0。


## 后续落实：统一姿态与指尖参考点候选（2026-10-31）

已下载安装版本lula_franka_gen.urdf、hand.stl和finger.stl，保存在day4-actionchunk-test/frame_audit。URDF完整链推导：right_gripper位于panda_link8的z=0.1m；指尖中点位于z=0.0584+0.045=0.1034m。因此其局部偏移为[0,0,+0.0034]m，三个夹爪开度下均验证。它只是URDF命名参考点，不等于校准后的真实接触面，也不证明旧代理偏移在所有任务中错误。

候选公共定义：XYZ=世界系right_gripper位置；yaw=世界Z轴角（弧度）；姿态Rz(yaw)Rx(pi)，局部Z固定向下；gripper命令不变。square_pose_backend.py在OPEN/CLOSE/HOLD中统一映射姿态，所有slot采用上述参考点。未覆盖正式共享Backend，仅供本候选入口使用。映射测试验证三个命令均传入yaw=.7及固定roll/pitch，末端reach也使用同一姿态。formal接口整合仍待动态验证后进行。

本地数值IK使用URDF、scipy least_squares及与实际Backend一致的基座yaw=-pi/2。独立FK与两份历史Isaac记录误差约2.4e-8m。34个路径点均找到限位内解，但place阶段有约3.15rad的相邻关节解跳变；这不证明路径不可达，但不能直接作为连续执行轨迹。下降段相邻解变化<=.0531rad。报告：frame_audit/pose_audit.json。

手掌/手指URDF网格在抓取段、开闭两种开度下最低z约1.007mm。只是网格点对地检查，不含实际USD碰撞近似/接触offset、全臂、自碰撞或动态稳定性。报告：frame_audit/clearance_audit.json。不能称已无碰撞。

唯一下一步：run-square-grasp-pose.sh，四个公共动作approach/descend/CLOSE/OPEN；抓住后静止60步检查位置、姿态、速度和锚点，再释放；不lift/transfer/fold。目标EE高度由坐标定义推得约13.3mm，不是高度扫描。保持物理参数和门限不变。保留接触记录，负记录仍未正控验证。18文件远端哈希/语法通过，未启动GPU。
