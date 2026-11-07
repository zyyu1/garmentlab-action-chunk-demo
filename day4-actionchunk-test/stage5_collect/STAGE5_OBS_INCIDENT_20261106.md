# Stage 5 正式采集：证据中断事件与暂停报告（2026-11-06）

**状态：采集已停（人工），暂停并报告。** 6115 已结算 accepted；但本轮发现观测证据未按 episode 归档，多数 accepted 轨迹缺少动作前观测，不能计入正式演示集。

## 1. 6115 / 6116 / 6117

| seed | 结果 | 说明 |
|---|---|---|
| 6115 | **accepted** | 结果目录 `day4-a5-rc2-l1-20261107-053657-097239`；初态 `…053341-492445`；**无动作前观测**（r4 启动时未导出 `STAGE5_OBS_DIR`） |
| 6116 | **accepted** | 同样无动作前观测 |
| 6117 | **started，未结算** | 采集被人工停止时 episode 中断；账本只有 started，无 verdict/结果目录 |

## 2. 观测证据问题

两个独立缺陷叠加：

1. **overlay 命名空间错误**：`EpisodeEvidence.out` 是 `<result_dir>/evidence`，overlay 用来命名的却是 `out.name`（恒为 `evidence`），导致所有 episode 的动作前观测写进同一个 `obs-formal/evidence/` 并相互覆盖；最终只剩最后一个 episode（6114）的 7 个观测。
2. **续跑环境缺失**：r4 启动命令只导出了 `STAGE5_APP`/`PYTHONPATH`，**漏了 `STAGE5_OBS_DIR`**，6115/6116 根本没有启用观测 overlay。

## 3. 累计进度与有效演示

| 项 | 数值 |
|---|---:|
| 已启动 episode 尝试 | **18**（6100–6117，flat） |
| accepted | 10（6103, 6106, 6107, 6110, 6111, 6112, 6113, 6114, 6115, 6116） |
| incomplete（waypoint 超时） | 7（6100, 6101, 6102, 6104, 6105, 6108, 6109） |
| started 未结算 | 1（6117） |
| **有效演示（观测对齐+导出通过）** | **1（6114）** |

6114 核验：7/7 动作前观测、四元数单位范数、target 差 9.8e-9、command 差 0；导出 single-step **7** 条、H=4 **2** 块（1 完整 + 1 尾部 `[1,1,1,0]`）。

无有效观测的 accepted：6103、6106、6107、6110、6111、6112、6113、6115、6116（共 9 个）。按规则不能计入演示集；它们已被结算/启动，**不自动重跑**。

## 4. 已修复（未重启）

1. overlay 改为按结果目录名归档：`OBS / <result_dir_name>/`（`Path(evidence.out).parent.name`）。
2. collector 在 `split=demo` 预检中强制要求 `STAGE5_OBS_DIR`，缺失直接 `OBS_DIR_MISSING` 停止，避免再次静默丢观测。
3. 两个文件已上传并在服务器 `py_compile` 通过。

## 5. 需要决定

1. **9 个无观测 accepted seed**：允许重跑（视为证据无效，需要明确批准），还是放弃并继续新 seed？
2. **6117**：started 未结算；按“已启动不自动重跑”保留为未确认，还是允许按未结算重跑？
3. 续跑时需带 `STAGE5_OBS_DIR`；日志继续用新文件（r5）。

## 6. 路径

- 账本：`/root/autodl-tmp/stage5-formal-state-v1/attempts.jsonl`（36 条 + 1 note）
- 观测：`/root/autodl-tmp/stage5-trial/obs-formal/evidence/`（仅 6114 的 7 条）
- 日志：`/root/autodl-tmp/stage5-formal-run-r4.log`（0 字节，collector 正常无输出）；r1/r2/r3 保留
- 6114 导出：`results/STAGE5_FORMAL_AUDIT_20261106/export_6114/`
