# 官方三阶段位置折叠开发试跑

前置证据：`results/day4-multi-grasp-20261026-234353-347208/pilot_review.md`。两个不同区域在同一rollout内抓取/释放已从完整数据复算通过；下摆槽未使用、第三次抓取尚未验证。

本次开发脚本：`day4-official-three-fold.py`。沿用通过首轮的多槽位适配器、原机器人资产参数、衣物每粒子0.0001kg/摩擦0.3/粒子间摩擦比例0、room碰撞隔离。无v9–v11机器人参数覆盖。

按本地导出的官方FoldDemo三个位置阶段执行：右袖两段搬运→释放、左袖两段搬运→释放、下摆两段搬运→释放。使用初始三处oracle材料点，对官方名义XY关键点求仿射映射；每阶段又按当前抓点相对初始抓点的XY漂移更新目标。z沿用官方阶段高度。无pitch侧通道，公开yaw固定0。

增加显式分段接近/搬运动作、释放静置及退让，以便审查；所有分段都记录为真实H=1公开动作，不隐藏在一次动作中。该版本预计超过正式12动作预算，`formal_12_action_budget_passed`始终False。恢复次数、任意yaw和最终紧凑expert尚未冻结。

输出episode.mp4、阶段PNG/NPZ、三次启用快照、源文件哈希、质量记录、槽位事件、动作矩阵和实际动作数。视频需可解码。对最终状态计算已有hem half-plane代理指标（XY对齐、粒子投影IoU、越线、反射目标误差、P95高度），同时记录名义固定半区位移；这些只是开发测量，不是已冻结的实际表面重叠标准。

`OFFICIAL_THREE_PILOT_PASSED True`只表示流程和产物检查通过，不能解释为真正折叠成功。`fold_success_accepted`、`formal_day4_success`保持False，完整下载后须核对视频和几何，排除整件搬移/翻转/回弹。失败也保存99_failure快照和日志。

本地已检查Python3.10语法、已下载真实快照上的关键点映射、实时抓点XY漂移更新、重复点与越界拒绝，未进行GPU验证。入口`run-official-three-fold.sh`；依赖清单`official-three-files.json`。
