# Day4 第 1 步：v5 抓取几何审查

状态：第 1 步的几何核对与修正范围判定已完成。已补读实际 USD 网格和手指运行时偏移；暂不改手指配置，下一步仅处理辅助块—地面目标冲突。尚未执行第 2 步，也未认证完整轨迹无碰撞。下方早期“待补读”段落保留为过程记录，以本节为准。

## 补充完成：实际 USD 与运行时偏移

新实例 `connect.nmb1.seetacloud.com:22895` 上执行了独立的**仅初始化**读取。沿用哈希核验通过的 v5 源码启动段，停止于 robot.open 和所有公共动作之前。初始化后 step=2，读取结束仍为 step=2；初始化本身会进行必要的 reset/物理设置，不能称为完全未启动仿真。没有接近、下降、抓取、保持、释放或折叠 rollout。

首次读取因 NumPy tensor frontend 不支持 GPU 管线失败，但保留了 USD 网格。改用 Torch 读取后的主结果：`/root/autodl-tmp/day4-v5-usd-initialized-20261101-050622-590321`。初次目录为 `day4-v5-usd-initialized-20261101-045734-413822`。目录时间采用服务器时间，与本地日期可能不同。

| 对象 | 实际配置/读数 |
| --- | --- |
| 左右手指 USD | 各 313 个源网格顶点；mesh scale=0.01；右指 rotateZYX=(0,0,180)；convexDecomposition，最多 8 hulls、每 hull 最多 32 vertices、voxelResolution=100000、shrinkWrap=False |
| 左右手指 PhysX | 每指 8 个运行时 shapes；各 shape contactOffset=0.005450000986 m，restOffset=0 |
| hem 辅助块 PhysX | 1 shape；contactOffset=0.10000000149 m，restOffset=0 |
| 默认地面 USD | Plane，碰撞启用，世界平移 z=0；contact/rest offset 仍为自动标记 -inf |

地面是静态平面，所用 rigid-body tensor view 不匹配该 prim；其**有效运行时偏移仍未读取成功**，对应记录明确保留 error，`passed_readout=False`。不能写成“所有偏移读取成功”，也不把 -inf 当作实际距离。安装版本 schema 说明 contactOffset 自动按形状 extent 选取，刚体自动 restOffset 为零。手指和辅助块上表数值来自 tensor backend，不是 schema 推测。

将实际 USD 碰撞源网格经其场景变换转到 hand，再按固定 hand→right_gripper 关系和 v5 保存的实际末端姿态重投影：03_held 的左指最低 z=1.250–1.396 mm，右指=1.216–1.362 mm。区间包含 hand-Y ±40 mm 开度平移包络；不是对 v5 每个粒子步的动态回放，也不是直接导出的 cooked convex-hull 顶点。未据此宣称完全无穿透。

**设计判读：**手指自身 5.45 mm 接触余量已经大于约 1.2–1.4 mm 几何间隙，足以解释“仍有间隙却产生接触事件”；这类接近事件符合当前碰撞检测配置，不等于设计要求夹爪压在地面上，也不是此前控制失稳的因果证明。无需为了消除事件而抬高轨迹、改变 +3.4 mm 坐标偏移、关闭手指地面碰撞或缩小手指 contactOffset。地面有效 offset 的缺失不影响这一保守判读，但限制了精确接触带宽和冲量分析。

**第 2 步明确范围：**仅针对作为辅助代理的块与默认地面的碰撞冲突，选择有针对性的过滤候选，保持机器人—地面和布料—地面碰撞、公共坐标定义及 held gate 不变。随后检验块中心真正跟随目标、附件启用/释放和原门槛。不能以“降低块 contactOffset”代替消除实体穿地目标冲突；restOffset=0 时其实体半高仍为 15 mm。该修正尚未实施。

结果目录含 `geometry_readout.json`、`geometry_summary.json`、`runner.log` 和 v5 源码清单。只在服务器读取摘要，未自动下载；用户手动下载完整目录后可复核。相关独立诊断代码已保存在本仓库，尚未提交 Git。

## 输入与范围

- 原始数据：`E:/learning/project/thesis/day4-actionchunk-test/results/day4-square-grasp-hold-v5-20261031-113930-047613`。
- 已安装版本的 URDF/finger STL：`E:/learning/project/thesis/day4-actionchunk-test/frame_audit`。
- 本仓库新增 `day4-actionchunk-test/audit_v5_grasp_geometry.py`，输出 `day4-actionchunk-test/frame_audit/v5_grasp_geometry.json`。仅 NumPy/SciPy 计算，没有启动 Isaac 或修改控制代码。
- 六个关键模块与 v5 保存源码经换行归一化后内容相同；克隆仓库 CRLF 导致字节哈希不同，后续上传需按实际发送字节重建/验证清单，不能直接宣称旧清单仍匹配。
- 新实例已只读核验环境；未重新下载资产或启动实验。

## 已核实的坐标链

公共 XYZ 是世界系 right_gripper；姿态为 Rz(yaw)Rx(pi)。URDF 命名指尖中点相对 right_gripper 为局部 [0,0,+0.0034] m；在向下姿态下，对应世界 z 减去 3.4 mm。该偏移是命名参考点，不是物理夹持接触面的校准值。

本次 material_pick.z=9.899995 mm，公共目标 ee_target.z=13.299995 mm。保持末实际 EE.z=13.606494 mm，依实际姿态计算的抓取参考点/块中心目标 z=10.206499 mm。3.4 mm 偏移的符号与旋转计算正确，没有证据支持直接翻转符号或凭空增加高度。

## 辅助块冲突：明确需要处理

v5 保存的 original_control.py 创建 30×30×30 mm DynamicCuboid；该块无重力，但 collision_enabled=True。碰撞组过滤机器人、布料、Avatar，未过滤默认地面。室内重复地面已禁用，默认地面保留。

保持末块中心 z=14.999993 mm；考虑保存姿态的块底 z 约 -0.000046 mm，即数值精度内贴合 z=0 地面。中心目标 10.206499 mm 对应立方体底部约 -4.7935 mm。因此 15 mm 与 10.207 mm 不是两个坐标系换算误差，而是地面阻挡与控制目标不相容。

按照保存的 delta/dt 及 0.3 m/s 限速公式，60 步保持期间重建的请求速度为 0.28764–0.28782 m/s，主要朝下。这是代码所请求的速度，不是测得的块实际速度，也不由此推算接触力。

附件初建 points1=0，但 PreparedRegion.align_disabled 在启用前根据当前布料和块位置重新写 points1。activation_hem.npz 中 points1×scale 的 z=-5.099998 mm。附件锚点位于块中心下方约 5.1 mm；held gate 的 1.361 mm 锚点误差不是块中心相对 10.207 mm 目标的误差。原 follow 到达容差为 5 mm，4.797 mm 左右的中心误差可落在该容差内，不能用该通过标志否定地面阻挡。

设计判断：当前是附件代理抓取，块是辅助载体，不是需要落地支撑的夹爪实体。代理块被地面挡住、同时控制器持续要求向下运动，不符合“代理跟随抓取参考点”的目标。下一步最小候选应针对辅助块—默认地面碰撞关系，而非修改世界 XYZ 定义、整条轨迹高度或放宽误差门槛。若决定保留实体块碰撞，则必须重新定义可实现的中心/锚点几何，不能继续复用当前目标；两种方案不同时试改。

## 双指触地：已证实事件，尚未证实穿透

事件由左右 finger 与默认地面产生；两指各 178 条，共 356 条，事件日志步号 585–762，包含下降、闭合、保持、释放和释放后静置。全部接触明细位置、法向、冲量为零，不作为几何坐标或受力证据。

用 v5 保存的实际末端姿态变换安装版本 URDF finger.stl，保持末开闭两种开度下最低 z 为 1.223–1.399 mm。该检查只覆盖 URDF 三角网格，不能替代实际 USD cooked collision shape。历史资产审查记录手指为 convexDecomposition，contactOffset/restOffset 记录为 -Infinity 哨兵值，没有提供有限有效运行时距离；这些历史数据不能认证本次 v5 的运行时值。

设计判断：当前测试没有规划夹爪以地面为支撑或进行力控接触。不能把该触地当作已验收设计行为；但事件也可能在几何未穿透时由接触余量产生，现有资料不足以确定手指需要改高度、碰撞体还是 offset。暂不修改/关闭手指—地面碰撞，也不根据 URDF 间隙声称无碰撞。

## 剩余的第 1 步工作

需要从本次所用 Franka USD 及默认地面读取实际碰撞近似、局部变换、尺度、边界和有效 contact/rest offset，并与 v5 实际姿态对应。优先离线资产读取；如果有效值只能在运行时得到，另行明确为只记录几何的初始化检查，不默认授权运行完整抓取或折叠。记录必须区分 USD 哨兵值与运行时有效值。

拿到这些值后才能最终判定双指接触是否符合预期，并确定手指配置是否需要修改。当前尚不确认第 1 步完全完成，等待用户下一步指令；第 2–7 步未执行。
