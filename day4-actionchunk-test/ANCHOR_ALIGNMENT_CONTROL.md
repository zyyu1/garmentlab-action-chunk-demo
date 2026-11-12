# 独立锚点对齐对照

本地已检查 Python 3.10 语法、运行器中嵌入的 Python 语法和刚体坐标变换；实际记录的 28 个点经过 float32 转换再重建后，最大误差约 0.00000090 mm。尚未运行新的 GPU 仿真，运行时 points1 更新的实际行为仍待验证。

## 文件与运行

将以下四个文件放在服务器 <remote-root>/：

- day4-anchor-alignment-test.py
- anchor_alignment_observer.py
- anchor_observer.py
- run-anchor-alignment-pair.sh

运行：`bash <remote-root>/run-anchor-alignment-pair.sh`。

运行器按 baseline、aligned 顺序各启动一个独立 Python 进程；先检查退出状态、最终标记和 result.json，再继续下一组。基线失败时不会启动对齐组。两个进程没有共享 SimulationApp。

## 单变量与检查

- 两组使用相同控制流程、下降路线、5 mm overlap、单进程一次抓取限制、原 30 mm 开启跳变阈值和抬升释放验收。
- baseline 不写 USD 属性。
- aligned 在夹爪关闭、方块已对齐但约束未开启时，仅写 points1。points0、索引、方块缩放、overlap、控制器源码均不修改，不创建或删除刚体/约束。
- 从准确匹配的原始网格顶点取得当前衣物点，用实时刚体位姿及缩放反算 points1。检查写入回读、没有额外物理步、点和刚体未移动、points0 未改变。
- 开启前、开启后及后续快照检查 points1 是否保留；如果自动生成机制覆盖了数组、成员改变或视图失效，实验停止并保存已有证据，不按成功处理。
- 写入回读成功或数组保留不等于内部求解器已采用；需结合几何响应与基线比较。
- 最后比较两组干预前的全部顶点、刚体位姿、原始锚点数组、映射索引与缩放是否逐元素一致。不一致时保存 comparison.json 并停止，不称为严格匹配状态对照。

## 输出

- 每组输出目录前缀：day4-anchor-pair-baseline-*、day4-anchor-pair-aligned-*。
- 每组含 result.json、alignment_metrics.json、alignment_operation.npz、anchors/、reference/ 和 source/。
- 运行器目录 day4-anchor-pair-run-* 含两份完整日志、结果路径与 comparison.json。
- 成功结束标记：ANCHOR_ALIGNMENT_PAIR_COMPLETED。此标记只表示两组流程完成且干预前状态一致，不代表跳变或物理质量已经改善。

分析重点是开启单帧最大位移、逐对几何间距、锚点邻接边长比、抬升、跟随和释放。保留全部原始快照以检查 points1 是否运行时被覆盖；不通过提高阈值或禁用原检查来获取成功标记。
