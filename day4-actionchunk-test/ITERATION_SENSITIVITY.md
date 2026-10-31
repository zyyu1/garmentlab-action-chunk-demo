# 轻质量条件下的粒子求解迭代对照

两组独立进程：baseline 16 次，refined 32 次。两组每粒子配置质量均为 0.0001 kg，总配置质量约 0.9945 kg。材料、时间步 1/60 s、接触配置、锚点对齐及动作策略沿用此前轻质量实验。

新文件：day4-iteration-sensitivity-test.py、iteration_experiment.py、compare_iteration_pair.py、run-iteration-pair.sh、iteration-pair-files.json。此前质量实验文件不修改。上传五个文件到 /root/autodl-tmp 后执行 `bash /root/autodl-tmp/run-iteration-pair.sh`。

启动前检查上传哈希。iteration_experiment.py 在当前进程中包装 GarmentConfig.__init__，仅将 solver_position_iteration_count 设置为 16 或 32；仍以 ClothPrim 构造参数显式指定轻质量。两个包装在 backend.start 返回或异常后恢复，正式项目及 SDK 文件不修改。

对每次启动、动作前和释放后保存 USD solverPositionIterationCount 读回、实时粒子质量，以及 reset 后生成的四个实际弹簧数组。要求两组粒子质量数组逐元素相同，弹簧索引、静止长度、刚度、阻尼逐元素相同，粒子系统采集参数除迭代数外一致。USD 迭代属性读回不直接证明内部每一步求解器执行计数；实际几何响应另外观察。

16 次组必须复现已通过轻质量组 day4-mass-pair-V0AIYmBy/day4-mass-light-20261025-060810-245544 的完整抬升+保持轨迹，以及前段快照/动作步数。32 次组只记录轨迹差异，不能假定相同落地状态。两组均保留原抓取/抬升/释放物理检查、质量读回数值容差和 180 步实测末端位置目标保持。

结果父目录 day4-iteration-pair-随机后缀，包含两组完整结果与 comparison.json。最终标记 ITERATION_PAIR_COMPARISON_OK。失败时保留日志并停止，不提高原阈值。

本地已做 Python 3.10 语法检查（含 runner 内嵌 Python）、用替代配置对象验证仅迭代字段变化、以及真实旧轻质量轨迹的前缀切片核对。尚未运行新 GPU 实验；离线包装检查不能替代物理验证。

解释范围：这是固定轻质量下的数值敏感性检查。首次 reset 前改变迭代数仍可能影响落地状态和自适应动作目标；16 与 32 两点对比不足以证明数值收敛，更不构成真实衣物材料标定。
