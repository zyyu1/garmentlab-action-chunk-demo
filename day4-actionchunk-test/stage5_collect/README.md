# Stage 5 最小采集入口（准备完成，未运行）

状态：入口已就绪、**未启动批量采集**（2026-11-06）。本次只做离线准备。

## 文件

| 文件 | 作用 |
|---|---|
| `collect_demos.py` | 采集驱动：逐 seed、每 episode 独立进程；只把 `accepted` 写入 `demonstrations.jsonl`；全部尝试写 `attempts.jsonl`；默认 plan-only（不启动 GPU） |
| `adapter_run.py` | 复用 `a5_entry.py run`，仅把 `RELEASE` 指向冻结回执（`E_RELEASE.json`） |
| `stage5_config.json` | 路径、seed 列表（20/档）、目标 50/档、尝试上限 120/档、初态索引文件 |
| `STAGE5_FIELD_CHECK.md` | Stage 5 观测字段对照与缺口（逐帧观测、seed 池、RGB-D、phase 映射） |

## 使用

```bash
# 1) 身份与 gate 预检（不启动仿真）
python collect_demos.py --preflight

# 2) 计划模式（默认；不启动仿真）
python collect_demos.py

# 3) 真正采集（当前未授权；启动前需确认 STAGE5_FIELD_CHECK §4 的决定）
python collect_demos.py --run
```

## 规则（已按批准修订）

- 每个 episode 独立进程（driver → `adapter_run.py` → `a5_entry.py run` → runner 子进程 → 退出）；不做进程内场景复用。
- 单卡串行。
- 只有 `a5-verdict.status == accepted` 的 episode 进入 `demonstrations.jsonl`；失败/异常全部保留在 `attempts.jsonl`。
- 按 seed 切分（70/15/15，按档内 accepted seed 顺序），切分在写出 demonstration 时记录。
- 不重跑已有尝试（按 seed 去重）。

## 启动前的待确认（见字段核对 §4）

1. 是否启用**被动逐帧观测 overlay**（当前 episode 产物只有动作边界快照 + 释放后 331 帧，BC 需要每步观测）。
2. 演示 seed 池：现有 20/档 < 目标 50/档；是否新增演示 seed（不进入 Stage 4 验收统计）。
3. RGB-D：仅 mp4 抽帧 / 加低分辨率帧 / 不要。
4. phase 映射表（action label → TaskPhase）。
5. 单卡串行（建议）。

确认后再执行 `--run`；本轮不启动。
