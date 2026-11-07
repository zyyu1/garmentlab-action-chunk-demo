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

## 当前状态（2026-11-06）

- 试跑：4100（L1）、4202（L2）、4302（L3）均 accepted；4201 用于 EE 姿态字段验证（rejected，仅字段）。
- 观测：动作前只读快照，已补 `ee_quat_wxyz (4)`；字段命名 `ee_position` / `ee_quat_wxyz`；动作 yaw 不代替观测朝向。
- H=4：只用块起始观测；L1 尾部补位 `[1,1,1,0]`；L2/L3 无尾部；禁止跨 episode。
- 切分：按 seed 稳定哈希（70/15/15），single/H4 共用。
- 正式 seed 池：6100–6219 / 6300–6419 / 6500–6619（120/档，target 50，cap 120）。
- **独立 demo 注册层已实现、预检通过**（2026-11-06）：360 条 demo plan、demo 初态生成入口、`split=demo` 授权、独立部署 manifest；预检 `blocked=false`、每档 120/50/120。正式采集**未启动**。详见 [demo 层登记](STAGE5_DEMO_LAYER_20261106.md) 与 [正式池登记](STAGE5_FORMAL_POOL_REGISTRATION.md)。

## 启动前的待确认

1. Stage 5 demo 注册层（demo seed 注册 + demo 初态生成 + `split=demo` 授权）是否批准。
2. RGB-D：仅 mp4 抽帧 / 加低分辨率帧 / 不要。
3. 并发：单卡串行（建议）。

确认后再执行 `--run`；本轮未启动正式采集。
