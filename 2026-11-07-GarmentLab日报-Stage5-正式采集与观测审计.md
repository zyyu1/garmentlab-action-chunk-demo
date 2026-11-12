# 2026-11-07 GarmentLab 日报 · Stage 5 正式采集与观测审计

**结论：Stage 5 独立 demo 注册层上线并完成正式采集启动；flat 达到 50/50，perturbed 开跑；当日发现并修复观测归档缺陷，建立完整导出闸门。**

## 1. 启动与身份

- Stage 5 正式池（`stage5-demo-seeds.json`、`stage5-demo-initial-plan.json`、部署 manifest 9 项）通过 preflight 与 plan-only：360 条 demo plan、每档 120/50/120（seeds/target/cap）。
- 冻结候选 `40858efc…`（gate `A5_GATE_OK_SOURCE 7`）未改；Stage 4 冻结文件与回执未改。
- 首槽 6100 于 17:42 UTC 启动（日志 `stage5-formal-run.log`）。

## 2. 当日事件

| 事件 | 处置 |
|---|---|
| 6100 waypoint 超时（incomplete，5 obs） | 计失败，继续 |
| 6101 初态生成失败（stripfold `APP` 未定义） | 保留原记录，修复生成器后重试成功，不计 episode |
| 6117 启动后中断 | 标记未结算，不重跑 |
| 6131 挂起 >65 分钟（a5_l1 循环） | 人工终止；新增 2700 s episode 超时保护（独立进程组、SIGTERM→SIGKILL、记录后暂停），非 GPU 测试通过 |
| 观测归档事故 | overlay 以 `evidence` 为命名空间导致逐 episode 覆盖；改为 `obs-formal/<result_dir_name>/`，6114 观测迁入独立目录；9 条 accepted 缺观测不收录 |
| 导出闸门缺失 | `_verify_export` 要求观测 + 动作对齐 + single/H4 导出，未通过则记录原因并暂停 |

## 3. flat 结果

| 项 | 数值 |
|---|---:|
| started | 80（6100–6179） |
| accepted | 59 |
| incomplete（waypoint 超时） | 19 |
| 有效演示 | **50**（`stop=target`） |
| 切分（episode） | train 31 / val 10 / test 9 |
| 导出 | single-step 350、H=4 100 块 |

- 演示清单 `state/demonstrations.jsonl`；账本 `state/attempts.jsonl`。
- 6114、6118 起逐例通过完整核验（如 6118：7/7、target 差 9.3e-9）。

## 4. 后续

- perturbed 6300 于 14:34 UTC 开始；crumpled 未开始。
- 缩减版（50/10/10）登记于 11-07，flat 目标不变。

## 5. 证据

- [demo 层登记](day4-actionchunk-test/stage5_collect/STAGE5_DEMO_LAYER_20261106.md)
- [观测事件报告](day4-actionchunk-test/stage5_collect/STAGE5_OBS_INCIDENT_20261106.md)
- [正式运行状态](day4-actionchunk-test/stage5_collect/FORMAL_RUN_STATUS_20261106.md)
- [缩减版登记](day4-actionchunk-test/stage5_collect/STAGE5_REDUCED_PLAN_20261107.md)
- 账本与导出：远端 `/root/autodl-tmp/stage5-formal-state-v1/`
