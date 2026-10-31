# 实测末端位置目标保持对照

2026-10-24 晚间续接：已准备脚本，尚未执行远程 GPU 实验。

基于已通过的原目标保持实验，保持原抬升前缀，在抬升结束后取实测 EE xyz，作为后续 180 次 `_tick(target, None, follow=True)` 的目标。姿态策略仍为 `None`，并非将实测四元数作为控制目标；允许制动和微调，不假定实际位置立即固定。

新增入口为 `day4-aligned-measured-hold-test.py`，观察器为 `measured_hold_step_observer.py`，结果校验与对比为 `compare_measured_hold.py`，运行入口为 `run-measured-hold.sh`。原脚本和 backend 未修改。

使用已有原目标保持运行的 source manifest 核对依赖；原 50 帧抬升前缀、阶段状态、动作矩阵和步数继续检查。新观察器分别保存 lift_ee_target 与 hold_ee_target；保持阶段 CSV 的目标误差相对于新目标计算。

运行器要求最终成功标记、JSON passed、采样完整及参考检查通过，再与原目标保持的 230 帧结果核对前 50 帧，保存 measured_hold_comparison.json。输出使用全新 day4-aligned-measured-hold-时间戳目录。

本地验证：Python 3.10 语法、四份已有观察器 SHA256、使用真实末帧位置进行目标切换及保存字段的离线适配器检查通过。适配器检查模拟了父类 finish，不是完整采样回放或 GPU 物理验证。默认 C:/Python311 缺少 SciPy；适配器检查改用 D:/Users/yexun/anaconda3/python.exe 成功，无环境安装。

本地 PowerShell 上传（使用日报中的现有实例地址）：

```powershell
scp -P 23636 "E:\learning\project\thesis\day4-actionchunk-test\day4-aligned-measured-hold-test.py" "E:\learning\project\thesis\day4-actionchunk-test\measured_hold_step_observer.py" "E:\learning\project\thesis\day4-actionchunk-test\compare_measured_hold.py" "E:\learning\project\thesis\day4-actionchunk-test\run-measured-hold.sh" root@connect.nmb2.seetacloud.com:/root/autodl-tmp/
```

远程 Bash 执行：

```bash
bash /root/autodl-tmp/run-measured-hold.sh
```

结束后查看 ALIGNED_MEASURED_HOLD_TRACE_OK、MEASURED_HOLD_COMPARISON_OK 和 DOWNLOAD_DIR。使用 DOWNLOAD_DIR 的实际路径下载整个结果目录到本地 results，再分析保持末段的边界伸长、锚点间距、刚体与粒子运动。任何失败均保留日志，不提高原诊断阈值。
