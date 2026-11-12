# 已对齐方案的抬升逐步采样

上传 day4-aligned-lift-step-test.py、lift_step_observer.py 至服务器 <remote-root>/。此前上传并通过的 anchor_observer.py、anchor_alignment_observer.py 继续使用，脚本会核对它们和 backend 的哈希。

运行仍使用 5 mm overlap、关闭 disabled probe、aligned 模式。没有改动下降路线、抬升目标、速度上限、求解参数或验收阈值；保留单进程一次抓取。

采样仅包围持物抬升的 execute 调用：先记起始帧，再在每次显式 World.step 返回后读取状态。不增加 World.step，不覆盖内部 PhysX 子步，不采样之后的释放和落地过程。

输出包括每帧全部顶点、实时方块位置和四元数、末端位置和四元数、28 个世界锚点目标、拓扑边、原始边长、抬升开始时边长、步号及时间。CSV 逐帧写入；正常完成或 Python 异常退出会保存已采集的原始帧。

逐步指标包括全局和锚点邻接边长比、最坏边的两个端点、一步最大顶点位移、末端/方块估计速度、跟随误差和逐对锚点间距。边按锚点端点数量分为内部（2）、边界（1）、区域外（0），分别统计，帮助定位变形区域。

流程结束前还比较本次与已通过 aligned 运行的 6 个快照、动作矩阵及每次 execute 物理步数，要求完全一致；如果不一致，会保存结果并拒绝输出成功标记。

输出目录：<remote-root>/day4-aligned-lift-step-<时间戳>/。

- lift_trace/steps.csv：每次显式步进的指标。
- lift_trace/frames.npz：原始轨迹数组，含起始帧。
- lift_trace/summary.json：采样数量、覆盖步号和峰值。
- result.json：抓取抬升释放检查、参考复现检查与轨迹检查。
- 原有 anchors/、reference/、source/ 和阶段快照继续保存。

成功标记：ALIGNED_LIFT_STEP_TRACE_OK，并核对 result.json passed=true、lift_trace.capture_complete=true 和 reference_replay_exact_checks 全部 true。该标记不代表局部拉伸已修复。

本地已用已保存的抬升快照核对采样指标，并用计数适配器验证包装器调用次数、恢复行为及部分轨迹保存；这些检查不是 GPU 仿真验证。
