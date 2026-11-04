# 保留：使用未校验速度读回的旧分析

本目录保留 2026-11-04 首次生成的 `comparison.json`、`pfs1_bins.csv` 和 `pfs1_vs_rc2.png`。它们使用了 `ClothPrimView.get_velocities()` 的原始读回作为 pfs1 粒子/质心速度。

后续检查发现该读回与同一 physics view 的世界顶点位置差分不一致：formal 窗口读回粒子平均约 28.76 mm/s，位置差分约 1.29 mm/s；读回场在 2 s 内几乎不变（帧首尾相关 0.998），且与位置差分向量的相关约 −0.006。附件关闭、EE 静止，不能由机器人运动解释。因此该读回不能作为实际布料速度，也不能用于冲量或“滑移速度”结论。

保留原因：不删除失败/不合格分析；同时避免旧图中的 25–35 mm/s 数值被误当作物理速度。正式比较请使用上级目录的 `comparison.json`、`pfs1_bins.csv`、`pfs1_vs_rc2.png`；其中所有速度均为世界顶点有限差分。详细诊断见 [../velocity_readback_diagnostic.json](../velocity_readback_diagnostic.json) 和 [../velocity_readback_check.png](../velocity_readback_check.png)。

这次分析重写没有改变物理运行、候选源码、manifest、初态或结果目录。
