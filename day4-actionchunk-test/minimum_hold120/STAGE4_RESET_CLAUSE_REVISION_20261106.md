# Stage 4 reset 条款修订（逐进程 episode 替代进程内 10 次 reset）

**状态：已批准生效。** 批准人：用户；批准时间：2026-11-06（Europe/Berlin）。登记 ID：`stage4-reset-clause-rev-20261106`。日期：2026-11-06。离线文档，未启动 GPU、未改冻结候选、未改验收阈值。

**批准内容：** 冻结候选及 Stage 5 采用“每个 episode 独立进程”，以此替代“连续 10 次进程内场景 reset/rollout”条款；若以后改为同进程复用场景，恢复原 reset 验证要求（实现场景 reset 并完成 10 次验证）。

**生效范围：** 冻结候选 `a5-rc8b-recovery-hold120-rc7-r2` + Stage 5 逐进程采集。**保留：** 2026-11-01 的 10 次 reset/rollout 开发记录及其“题前 `PreparedSquareBackend`”适用范围，不删除、不改写，不作为冻结候选的证据。

## 1. 原条款

| 出处 | 原文 |
|---|---|
| [README](../../README.md) Stage 4 验收计划第 2 条 | “将有效控制整合到正式 Backend，验证 `reset(seed, difficulty)`、episode 内重抓取及**连续 10 次 reset/rollout**” |
| [DAY4_MINIMUM_PLAN.md](../../DAY4_MINIMUM_PLAN.md) 第 5 条 | “**将连续 10 次 reset/rollout 检查并入批次**，检查状态残留、资源和保存错误” |
| [最低验收报告 §6](../results/MINIMUM_ACCEPTANCE_20261106/review.md) | 继承核对不成立：11-01 证据无代码身份、后端不同、reset 控制文件 2026-11-02 变更、冻结候选 `reset()` 不调用场景 reset 钩子 |

## 2. 修订内容（拟登记）

> 对冻结候选 `a5-rc8b-recovery-hold120-rc7-r2` 及后续 Stage 5 数据采集，**以“每个 episode 独立进程”替代“连续 10 次进程内场景 reset/rollout”**：
>
> 1. 每个 episode 由独立进程执行：驱动 → `adapter_run.py` → `a5_entry.py run --initial <dir> --mode single --split formal --journal <state>/episodes` → `a5_l1.py`（或 `a5_recovery.py`）runner 子进程 → 写出结果目录与 verdict → 进程退出。
> 2. 进程退出即释放全部 Isaac/PhysX 状态；下一 episode 重新启动进程、从预登记初态目录加载，**不复用同一进程内的场景**。
> 3. “状态残留”检查由此变为：每个 episode 的初态哈希、动作/证据完整性与审计独立成立；不再要求同一进程内 10 次 reset。
> 4. 11 月 1 日的 10 次 reset/rollout 开发记录**保留**，仅作为题前 `PreparedSquareBackend` 的证据，不删除、不改写、不用于冻结候选。

## 3. 依据（现有入口与正式批次记录）

**进程如何创建与结束**（冻结 app 源码）：

- 驱动 `minimum_driver_v2.py:45-52`（`run_episode`）用 `subprocess.run([python, adapter_run.py, 'run', '--initial', ..., '--journal', ...])`（`:49`）启动子进程；读 `DOWNLOAD_DIR` 行、再单独跑 audit。
- `adapter_run.py:12-16` 只把 `a5_entry.RELEASE` 指向冻结回执（`:15`），然后调用 `a5_entry.main()`（`:16`）。
- `a5_entry.py:130-154`（`episode`）：校验初态身份 → 新建 attempt/journal → 用 `subprocess.run` 启动 runner（`a5_l1.py`/`a5_recovery.py`，`:137-141`）→ 读 `DOWNLOAD_DIR` → 评估 → 写 `a5-verdict.json` → 打印 `DOWNLOAD_DIR` 后返回。
- runner 结束时写出 `result.json`、证据目录与 `success_trace`；进程退出。

**正式批次记录（21 个 episode，全部逐进程）**：`stage4-minimum-hold120-state-v1/attempts.jsonl` 中 21 个 `started` 各对应一个独立 attempt/journal 目录（`episodes/<seed>-single-<uuid>/started.json`、`finished.json`）；无重复 seed；驱动退出后 `completed` 写入、锁移除。L1 4110/4111 的入口失败也证明每 episode 都需要新的 entry 进程，而不是进程内复用。

**Stage 5 计划**：`Marian_Frei_GarmentLab_2024_10_stage_execution_plan.md` Stage 5 只要求“每档 50 条成功轨迹、统一字段、按 seed 切分”，**没有**要求同一进程连续复用场景。逐进程采集因此满足 Stage 5，且结构上消除了跨 episode 状态残留。

## 4. 适用条件

- 本修订**只在 Stage 5 采用逐进程采集时生效**。
- 若 Stage 5 为了吞吐改为“同一进程跑多个 episode”，原条款自动恢复：必须先实现场景 reset 并在冻结候选上完成 10 次验证（最小改动另列，不在本修订内）。
- 本修订不改变：判据、阈值、初态协议、动作、评价器、冻结候选、21 次尝试、15 个成功、30 张初态截图。

## 5. Stage 5 入口现状与待决定项

**现状：** Stage 5 的实际采集入口**尚未实现**（仓库内没有 `generate_demos.py` 或等价脚本）；现有可复用入口是 `a5_entry.py run` + `minimum_driver_v2.py` 的驱动模式。采集方式（逐进程或批内复用）**计划上未强制**，需在登记修订时一并确定。

| 待决定项 | 选项 | 建议 |
|---|---|---|
| A. 采集入口 | 新建 `generate_demos.py` / 复用 `a5_entry.py run` + 批驱动 | 复用现有入口，新增薄驱动（少改冻结代码） |
| B. 进程模式 | 每 episode 独立进程 / 同进程多 episode | 逐进程（本修订的前提） |
| C. 成功筛选 | 只保存 accepted / 保存全部并标注 | 只保存 accepted 为 demonstrations，失败单独日志 |
| D. 观测保存 | 关键点+EE+夹爪+phase / 加 RGB-D | 先按 Stage 5 最低字段；RGB-D 视磁盘与吞吐再定 |
| E. 并发 | 单卡串行 / 多进程并行 | 单卡串行（初版），避免显存与文件竞争 |
| F. 切分 | 按 seed | 已由计划冻结，按 seed |

## 6. 批准后已更新的文件

1. [DAY4_ACCEPTANCE_TRACKER.md](../../DAY4_ACCEPTANCE_TRACKER.md) 2026-11-06 段：reset 条款改为“按修订闭合”，引用本文件；Stage 4 标记完成。
2. [最低验收报告 §6/§7](../results/MINIMUM_ACCEPTANCE_20261106/review.md)：状态由“待闭合”改为“按修订闭合”；Stage 4 完成。
3. [README](../../README.md) 2026-11-06 段：reset 状态与 Stage 4 完成标记。

## 7. 登记字段

| 字段 | 值 |
|---|---|
| 修订 ID | `stage4-reset-clause-rev-20261106` |
| 批准人/时间 | 用户 / 2026-11-06（Europe/Berlin） |
| 状态 | **已批准生效** |
| 生效范围 | 冻结候选 + Stage 5 逐进程采集 |
| 被替代条款 | README Stage 4 第 2 条“连续 10 次 reset/rollout”；DAY4_MINIMUM_PLAN 第 5 条同项 |
| 恢复条件 | 改为同进程复用场景时，恢复原 reset 验证要求 |
| 保留证据 | `results/day4-prepared-square-backend-reset-20261101-080713-870146/review.md`（题前 Backend，范围不变） |
| 不改 | 冻结候选、判据、阈值、21 尝试/15 成功/30 截图 |
