# Stage 5 正式采集启动状态与暂停报告（2026-11-06）

**状态：已启动；首槽 6100 未通过（waypoint 超时）；6101 初态生成因 manifest 过期失败；采集已停，等待决定后续续跑规则。**

## 1. 启动前检查

| 项 | 结果 |
|---|---|
| `df -h /root/autodl-tmp` | 50G 总、37G 已用、**14G 可用**（≥12 GB） |
| 既有正式进程 | 无 |
| `STAGE5_DEMO=1` 传递 | `a5_entry_demo.py:65` 在子进程 env 中设置，无需外部导出 |
| preflight / plan-only | 均 exit 0；360 条 demo plan；每档 120/50/120；6100 初态已绑定 |

## 2. 启动

- 命令：注册命令原样（`collect_demos.py --config trial/stage5_config_formal.json --run`）。
- 进程：shell PID **25686**、python PID **25688**（现已停止）。
- 日志：`/root/autodl-tmp/stage5-formal-run.log`（collector 自身无输出）。
- 状态：`/root/autodl-tmp/stage5-formal-state-v1/attempts.jsonl`。

## 3. 首槽 6100 核验

| 项 | 结果 |
|---|---|
| 初态 | 按需生成 `day4-square-initial-20261107-013739-089368`（`DEMO_INITIAL_SAVED 6100 flat`，协议/哈希校验通过） |
| 运行 | 结果目录 `day4-a5-rc2-l1-20261107-014210-906804`；entry_exit 3；runner_exit 0 |
| verdict | `status=incomplete`、`split=demo`（demo 授权生效）、`success=null` |
| 错误 | `RuntimeError('Square waypoint velocity/position did not converge')`（第 5 个公开动作处超时，执行 4 个动作） |
| 动作前观测 | 5 条（`action_001..005`），与已执行动作数一致；未执行的动作无观测 |
| 结论 | **未 accepted，不计入正式演示集**；属专家 waypoint 超时，不是采集/身份异常 |

## 4. 6101 失败与停机原因

- 记录：`{"error":"initial_generation_failed","output":"AssertionError: run-demo-initial.sh"}`。
- 原因：启动前为加入 `DEMO_INITIAL_DIR` 标记修改了 `run-demo-initial.sh`，但**未重建 `stage5-demo-initial-files.json`**；launcher 的哈希校验失败，collector 按 `INIT_FAILED` 停止。
- 已修复：重新生成 `stage5-demo-initial-files.json` 与 `stage5_demo_manifest.json`，校验 **0 bad**。

## 5. 当前状态

- 正式演示集：**0 条**（6100 未 accepted）。
- 账本：6100 `incomplete`；6101 `initial_generation_failed`（未起 episode）。
- 修复后的 demo 层已就绪；采集进程已停，未自动重试。

## 6. 续跑前需要决定

1. **waypoint 超时口径**：是否沿用 Stage 4 已批准的续跑类（`waypoint non-convergence` 计为失败并继续下一 seed），还是按“证据异常暂停”。6100 是首个实例。
2. **6101 记录处理**：该 attempt 未启动 episode（初态生成失败），是否允许删除该 infra error 记录后从 6101 续跑（不重跑任何 episode）。
3. 续跑命令与启动命令相同；state 继续使用 `stage5-formal-state-v1`。
