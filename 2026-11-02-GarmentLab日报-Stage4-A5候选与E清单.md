# Stage 4 A5：候选登记与 E 运行清单

**状态：stage4-a5-rc1 已登记并部署到无卡实例。真实开发复验待执行，正式冻结回执尚未签发。** A4 的 right single 终态几何结果为 L2 7/10、L3 8/10；此次改变了最终 OPEN 目标和采样时序，以上数据只作为选向依据。

|档位|初态|拟执行的正式任务|single 的公开动作数|arc4 的公开动作数|
|---|---|---|---:|---:|
|L1|flat|A_l1_overfold，left，width .20 m，overhang .02 m|7|7|
|L2|perturbed|B_nominal，right，width .20 m，overhang 0|12|12|
|L3|crumpled|同 L2|12|12|

**预算与退让。** 保留 recovery 5 动作及 4 个 arc 路点。末个公开动作名为 release_retreat，命令为 OPEN，目标为当前实测 EE 的 z + 0.15 m，姿态沿用放置姿态。SquarePoseBackend 已有的 OPEN 会先 ungrasp，再对传入目标执行 robot_goto_position。采集器在这个已存在的调用入口读回持布、三槽使能及 EE，再记录动作完成位置。要求公开目标与释放位置上方 0.15 m 在 2 mm 内一致、实际向上移动至少 1 cm。时间线记录动作起止、标签、坐标、horizon；arc4 仅合并调用边界。L2/L3 的 horizons 为 single 的 12 个 1 或 arc4 的 7 个 1 加 [4,1]。C 旧开发入口的独立第 13 动作保留作历史对照。候选不再执行 C 的旧时序（OPEN 后 210 步再退让）。

**采集与评价。** 末个公开 OPEN 完成、机械臂已退让时定义 step 0，立即读数。以实测 dt=1/60 s 逐物理步采集至 step 330。记录绝对物理步、仿真时间、441 点顶点、实际 backend holding、三槽 attachment_enabled 及 gripper_open。C 的 3 s / 4 s 保持快照与帧 180 / 240 对应。final.npz 对应第 330 帧。有时钟跳步或读取错误时保留 partial_trace.npz、视频、状态与错误日志。冻结的 B v1.0.0 几何和稳定阈值原样使用，几何检查覆盖 210–330 共 121 帧；释放状态覆盖全部 331 帧。B 的 held 姿态读数来自释放前 robot.reach。被拒的有效评价与采集不完整/执行错误分别记账。

**身份。** 候选总 manifest 为 `e9757d20a527b3cd8dbdd119640740e039a8a3f5ba3cb4b7462bdacf230795b8`，59 项。包括初态与折叠依赖、任务路由、B 评价配置及代码、两档候选 runner、C 视频采集和离线审计、D 批次与汇总入口。开发与正式使用同一候选入口，由 split、初态身份和冻结回执控制运行范围。远端目录为 /root/autodl-tmp/stage4-a5-rc1/app；顶层 /root/autodl-tmp/run-stage4-formal-batch.sh 已接入候选入口。更改被绑定的代码、配置、初态或任务定义后须重新登记并复验。

## 1. 有卡开发复验

当前已远端核对 59/59 项和全部 7 个开发输入。无卡实例未检测到 GPU 设备。以下开发命令应在有卡模式运行。使用新的开发账本目录，并保留所有已开始、失败及部分结果。

```bash
cd /root/autodl-tmp/stage4-a5-rc1/app
PY=/root/autodl-tmp/envs/isaac40/bin/python
J=/root/autodl-tmp/stage4-a5-rc1-dev-ledger
"$PY" a5_entry.py preflight
"$PY" a5_entry.py dev-batch --journal "$J"
"$PY" a5_entry.py verify-dev --journal "$J"
```

复验顺序在运行前固定：4100、4202、4302 各 single + arc4，再运行历史拒绝对照 4201 single。四个初态目录及 result/geometry 原始字节哈希见 a5-candidate.json。六个阳性运行必须通过完整采集及 B 判据；4201 允许有效通过或有效拒绝，必须达到可评价状态。三组配对须逐目标在 1e-6 m/rad 绝对容差内一致。每例生成独立 started.json、runner.log、finished.json，及结果目录中的 success_meta.json、success_trace.npz、evidence/ 和 a5-verdict.json。不得以更换 seed 或隐去失败来满足复验矩阵。

## 2. 正式冻结

复核七例的视频画面、实际释放与退让、动作计数、时间戳、来源哈希、失败保存和逐例 verdict。核验通过且确认采用后，执行单独的 freeze 步骤。该命令重新评价七例，签发绑定 candidate manifest 的 verified-dev.json 和 E_RELEASE.json，独占创建以保护已有回执。

```bash
"$PY" a5_entry.py freeze --journal "$J"
"$PY" a5_entry.py gate
```

## 3. E 的运行与收尾（冻结后另行启动）

- 核对实例、任务/评价器/manifest、release 回执、初态协议、磁盘空间和 GPU。归档 release、复验账本与视频。
- 固定 L1 4110–4129、L2 4210–4229、L3 4310–4329。60 个初态，每个初态共享给 single/arc4，各 20 个 seed/档，共 120 个计划槽位。唯一批次入口如下。本次未执行。
- 入口在任何初态生成前检查 release。同一 tag 续跑要核对 batch-identity、初态哈希和已登记尝试，遇到未结束或证据错误先保留现场并审计。
- 每例采集完成后同时检查视频、源文件与窗口，依据 a5-verdict.json 的 accepted/rejected/incomplete 分类；D 的 started/finished 日志作为尝试分母。旧 stage4_formal_report.py 可用于开发门槛历史汇总。
- 下载并保留全部初态、完整结果、尝试日志（含未结束记录）、失败视频、manifest 和两个 release 文件。检查 120 个唯一 seed×模式槽位、逐档不少于 5 条正式成功和最终接口隔离；空档用 null，缺失结果按 error，拒绝率=(rejected+error)/attempts。

```bash
cd /root/autodl-tmp
STAGE4_FORMAL_RELEASE=A_B_C_FROZEN bash run-stage4-formal-batch.sh stage4-heldout-seeds.json formal-a5
"$PY" /root/autodl-tmp/stage4-a5-rc1/app/a5_report.py /root/autodl-tmp/stage4-formal-batch-formal-a5 /root/autodl-tmp /root/autodl-tmp/stage4-a5-rc1/app/E_RELEASE.json
```

本地合成联测覆盖 L1/L2/L3 × single/arc4 六种组合，从公开 OPEN 目标、实际采样、视频解码、双保持样本，到冻结评价器的 121 帧检查；合成样例不能取得真实运行资格。跳步注入只留下部分轨迹。原 B 的 13 项评价器测试通过。尚待真实 Isaac 验证的关键风险为释放后退让路径、视频观测效果、真实控制期间状态一致性及稳定窗口保持。

[候选任务和开发矩阵](day4-actionchunk-test/a5-rc1/a5-candidate.json) · [总 manifest](day4-actionchunk-test/a5-rc1/a5-manifest.json) · [A4 证据](../thesis/day4-actionchunk-test/results/A4_RIGHT_TERMINAL_20261103/review.md)
