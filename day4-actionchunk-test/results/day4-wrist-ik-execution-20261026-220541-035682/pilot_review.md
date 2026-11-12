# v8 单变量对照核对（2026-10-26）

新实例 <server>，容器截图为7dde4b87a0-ea1fac3d。运行脚本SHA256匹配。干预发生于probe_step846，第27点原插值完成后、保持前；无时间步进，前后状态完全相同，gains/dt和位置迭代数保持不变，速度迭代getter由64读回0。

与v7b全部目标及逐步trace完全相同，1086行step_states.jsonl逐字节相同。保持240步后仍失败，末速度4.7171196937561035 rad/s。配置前后仅发现USD solverVelocityIterationCount和两个getter对应字段从64变0。

结论：未观察到行为变化。getter读回不证明物理求解器实际更新；也不能将此结果用于排除TGS速度迭代假设。由于更换实例，不能先假定硬件/软件环境完全相同；现有完全一致轨迹仍是直接观测证据。

下一步先读取当前安装版本articulation/view的solver getter/setter实现，确认是否只改USD、是否初始化时加载。新增export-solver-api.py只读SDK源码，不import Isaac，不启动仿真、不改配置。取得实现证据后决定是否需要reset前单变量设置，不继续运行中调参。

没有新增正式Day4成功episode。当前公共接口和带布料折叠主线仍未完成。

![对比](v8_vs_v7b.png)
