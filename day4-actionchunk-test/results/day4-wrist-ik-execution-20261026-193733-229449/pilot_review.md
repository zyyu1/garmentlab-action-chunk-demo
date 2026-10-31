# v7b 运行配置与状态审查（2026-10-26）

运行脚本哈希、3份导出源码哈希通过；全部目标/轨迹与v6完全相同。1086条pre/post记录连续一致，每步实际时间增量匹配1/60秒；记录条数等于目标累计步数。位置与速度getter均调用实时PhysX张量接口并克隆；没有发现使用静态USD位置代替运动状态的证据，但这不等于SDK内部无问题。

机器人TGS position/velocity iterations=64/64，self-collisions=0。七个臂关节有效kp=572957824、kd=5729578、max effort=100000；组合USD角驱动stiffness=10000000、damping=100000。两套数值表示不同，不能直接把角度换算差异当成配置错误。部分link authored惯量约1e-6，未验证有效惯量/资产长度单位，不据此认定资产错误。dof_properties读取CUDA转换错误已显式记录，不影响已成功读取的字段。

最后60帧固定目标下，joint5位置差分速度约±0.0267 rad/s，而报告速度4.08–4.72 rad/s；joint7位置差分近零而报告速度2.81–3.63 rad/s。差异在实际dt下仍存在，但离散位置差分不解析步内求解过程，不足以断言哪个接口错误。

NVIDIA Isaac Sim 4.1官方物理限制说明：TGS超过4次速度迭代不再静默转为位置迭代，建议尝试零或很少速度迭代。这与本次64次配置及启动警告直接相关，作为下一次单变量实验依据，而非已确定根因：
https://docs.isaacsim.omniverse.nvidia.com/4.1.0/simulation_fundamentals.html

v8保留v7b全部配置和控制，完成第27点原插值后、开始保持前，仅通过运行时API将articulation velocity iteration count从64设为0。保存干预前后状态、迭代数、gains和dt，断言无仿真步进和状态瞬移，继续原速度门限与240步预算。该干预不是永久Backend修复；前缀应可精确比较，但干预后的执行步数和重新求出的后续IK允许改变，应明确记录。高增益、质量、材料、position iterations、轨迹及门限不变。不用大量配置扫描替代Day4主线。

如果通过，再核对28–30点及整条路径，再处理公共接口和带布料折叠；空载通过仍不等于Day4完成。如果失败，根据新轨迹评估此假设，不立即扩展参数扫描。

![运行状态核对](runtime_velocity_consistency.png)
