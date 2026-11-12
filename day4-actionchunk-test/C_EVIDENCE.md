# C：采集与验收证据

本交付是独立 C 开发入口；不替换既有 L1/recovery 冻结入口、阈值或正式成功计数。当前只完成本地采集集成与离线验证，尚未在 Isaac/GPU 运行新入口。样例为显著标注 SYNTHETIC 的接口验证，不能作为真实折叠成功证据。

## 实现与运行

- `episode_evidence.py`：启动后包装 world.step 和 backend.execute；每物理步记录状态，每两步渲染采集一帧。render 不推进物理；额外渲染会增加墙钟耗时。
- `day4-c-l1-xfold-yaw-aware.py`、`day4-c-recovery-fold-episode.py`：接入采集和 finally 保存。
- `audit_episode_evidence.py`：离线核对哈希、时间、逐步状态、动作调用、视频全解码及退让/双保持证据。
- `square-c-l1-files.json`、`square-c-recovery-files.json`：C 的独立源码清单，按当前文件字节生成；上传须保留字节与换行。还保存实际 backend/env/control/robot 类型所在源码。

上传对应 C 清单列出的文件及清单本身到原远端布局，再运行：

```bash
bash run-c-evidence.sh l1 <remote-root>/<initial-dir> --overhang 0.02
bash run-c-evidence.sh recovery <remote-root>/<initial-dir> --fold-edge right
python audit_episode_evidence.py <remote-root>/<run>/evidence
```

`run-c-evidence.sh` 默认加 `--retention-evidence`。直接运行 Python 而不加此参数仍采集原轨迹，但缺少退让/双保持时完整验收必须失败。`--execution arc4` 可用；时间线仅将 H=4 中间物理步关联到 call_id，不冒充每个子动作完成时的独立状态。public actions 计 horizon 总和，不能以 execute 调用数代替。

采集从 `start_with_square` 返回后开始，构造/reset 前的过程不在视频内。渲染图像使用当前仿真摄像头；正式视觉验收仍需确认视角遮挡与图像内容，自动解码通过不等于画面有用。

## 退让与第二保持要求

原有 OPEN + 30 release ticks + 180 settle 保留。之后新增：released 快照 → 一个公开 OPEN 退让动作（目标为当前 EE 的 z + 0.15m）→ retreated 快照 → 按实际 physics_dt 等待至少 3 秒 → hold_3s → 再至少 1 秒 → hold_4s。

退让方向/距离是待仿真验证的开发候选，控制器失败也保存证据。检查实际 EE 位移至少 1cm、区间内确有公开动作、样本均未持布/未附着以及实际模拟时间差。此位移检查仅为“确实移动”的诊断门槛，不是防碰撞或折叠质量阈值。

L1 总动作数从 7 变为 8；recovery 从 12 变为 13，后者 `action_budget_passed=false`，不能宣称满足 ≤12 动作。若要正式满足预算，应由路径任务另行提交并验证压缩方案。不得隐藏退让或复用旧 7/12 步结果冒充新证据。

原 result.fold_metrics / final.npz 仍对应原轨迹终态。新增保持形状以 evidence/hold_3s.npz 与 hold_4s.npz 为准；尚未接入冻结的折叠质量评估器，不能把旧 metrics 套在新保持快照上。

## 输出字段

| 文件/字段 | 含义 |
|---|---|
| result.json | runner 原结果，finally 写入；passed 是原开发流程门槛，不是完整证据/正式成功 |
| runner.log | shell 保存完整运行日志；启动失败且无结果目录时保留 mktemp 日志路径 |
| evidence/episode.mp4 | RGB 转 BGR 编码 mp4v；播放帧率 30，不以播放时长推导物理时间 |
| timeline.jsonl.kind | start/state/frame/action_begin/action_end/action_error/sample/capture_error/state_error/finish |
| utc / monotonic_ns | UTC 墙钟 ISO 时间 / 本机单调时钟；跨机器不能比较 monotonic_ns |
| sim_time_s / observed_step | world.current_time 实测模拟时间 / 采集器观测到的物理步，未使用墙钟推算 |
| backend_step | backend 自有步计数，和 observed_step 分列保留 |
| frame_index | 从 0 开始的视频帧号，与当前帧采集时的模拟时间和状态关联 |
| call_id | 当前 execute 调用号；动作之外为 null |
| targets / commands / horizon | 实际传给 execute 的 float32 目标、夹爪枚举和动作数；不是离线计划替代值 |
| holding / attached / ee_m | backend 持布标志、控制器 attachment 状态、真实 EE 读回；action 内过渡态也保留，异常需审查 |
| sample.label | released、retreated、hold_3s、hold_4s、terminal；同名 npz 包含 vertices（世界米制坐标） |
| summary.json | 采样计数、错误、样本索引、源码原路径及 SHA256、synthetic 标志 |
| source/* | 运行时源码副本；哈希来自实际字节，外部环境版本仍需另行留档 |
| manifest.json | evidence 内文件 SHA256，自身除外；不涵盖稍后复制的 runner.log/result.json |
| evidence_audit.json | 完整性 checks、逐帧解码数、尝试公开动作数、预算判定；正式成功始终 false |

发生执行异常时保留 action_begin/action_error；保留已有视频、时间线以及尽力读取的 terminal.npz。相机错误记入 errors 并继续物理执行，不吞掉原控制异常。进程硬杀、断电或磁盘写入失败无法保证 finally 执行，不得据残缺目录判成功。启动前参数/输入校验失败可能仅有 shell 日志。

## 完整样例和验证

`examples/c-evidence/complete/` 含 result、audit、126 帧视频、241 步时间线、全部退让/双保持/终态 NPZ、源码副本及哈希清单。`failed/` 为有意在退让前失败：2 帧视频和终态保留，完整性拒绝。两目录 synthetic=true，视频有 SYNTHETIC 水印，三顶点假网格与真实 441 顶点资产不同。

本地测试：`python -m unittest discover -s day4-actionchunk-test -p test_episode_evidence.py -v`（需要 numpy、opencv-python/headless）。覆盖完整采集/解码、哈希篡改、失败保存、缺少第二保持、时间倒退/状态不一致、相机失败。C Python 入口已语法检查；真实相机/物理步包装、退让路径和冻结质量验收仍须真实开发运行验证。
