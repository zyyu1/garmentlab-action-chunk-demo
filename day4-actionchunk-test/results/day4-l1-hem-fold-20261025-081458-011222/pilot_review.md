# Hem-v5 与 hem-v4 比较

已下载并核对 result.expert_version=hem-v5，source/manifest.json 中所有源码哈希一致。runner.log 明确含 RELEASE_ATTACHMENT_REMOVED /World/AttachmentConstraints/prepared_grasp。

两次 release_trace.json 均为 85 条。逐条比较 centroid、min、max、ee、block，所有数值最大绝对差均为 0。约束移除尝试未改变这些观测量；这不能单独证明内部求解器状态，但不足以支持继续沿此路径修改。

下一项有源码依据的假设：BaseEnv 同时 add_default_ground_plane() 和导入 FlatGrid.usd。尚未取得 FlatGrid 内部碰撞结构，不能断言存在重叠地面或确认根因。

准备 hem-v6-room-isolation：首次 reset 前枚举导入 room 的 CollisionAPI，保存 room_collision_audit.json，并关闭其中原本启用的碰撞；验证默认地面碰撞仍启用。如果没有可关闭的 room 碰撞体，则直接停止、返回审计，不重复完整实验。其余折叠、释放、质量、速度及成功阈值不变。更改仅作用于当前进程 stage，不保存 USD 或编辑正式工程。

仅完成本地 Python 3.10 语法检查；尚未运行该物理对照。即使对照成功，也需先确定实际碰撞结构与正式场景配置，不能直接计入 Day4 成功回合。
