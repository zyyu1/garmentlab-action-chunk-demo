# 下一步：采集实际物理参数

已完成实测位置目标保持对照，末端额外上移从 6.687 mm 降至 0.098 mm，持续边界伸长仍约 1.72 倍。当前本地源码缺 GarmentConfig 与 Garment 创建实现，尚不能确定材料和粒子求解设置，不据此猜测参数值。

`day4-physics-config-audit.py` 执行正常 backend.start（包含原有 reset），随后只读采集物理属性、关系、部分对象配置和项目中已导入的 Python 源码。没有抓取、后续显式物理步或参数修改。USD 属性包含 schema fallback，不等同于直接读取内部求解器；authored 标记单独保存。大数值数组存入 physics_arrays.npz。

已确认的控制事实：prepared_grasp_control._tick 中 0.3 m/s 是方块跟随速度上限，不是机器人抬升速度设置；_drive 同时检查末端位置与 robot.reach，并要求连续六步满足条件；BaseEnv 的 TGS 设置在 rigid 条件分支内，不能直接认定布料粒子使用了某个刚体求解设置。

启动前核对与通过实验一致的五份关键源码哈希。运行器额外核对成功标记、JSON passed、采集时无步进和约束关闭状态。仅本地 Python 3.10 语法检查已通过，尚未执行远程参数采集。原实验文件和正式 backend 均未修改。

上传 day4-physics-config-audit.py 与 run-physics-config-audit.sh 到 /root/autodl-tmp，然后远程 Bash 执行 `bash /root/autodl-tmp/run-physics-config-audit.sh`。下载末尾 DOWNLOAD_DIR 所示完整目录后，审阅刚度、阻尼、迭代、粒子接触/质量参数及控制配置，再决定单变量实验。
