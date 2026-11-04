# D1-120 步骤 6：4202 single 单次运行结果

运行目录：`day4-a5-rc2-d1-120-20261104-071602-499516`（远端 `/root/autodl-tmp/`；本地已下载到 `E:\learning\project\thesis\day4-actionchunk-test\results\`）。

**本次是唯一一次有效 episode；没有重试、没有改参数、没有重跑仿真。**

## 运行结果

| 项目 | 值 |
|---|---|
| episode `passed` | **True** |
| `errors` | `[]` |
| 公开动作 | **12**（最后 `release_retreat`） |
| horizons | 12 × 1，总和 12 |
| 内部等待 | **120 步**；`start_step=1955`、`end_step=2075`、`elapsed_sim_time=2.0000001 s` |
| 等待期间 EE 位移 | **0.0 m**；`control_calls=0`、`target_changes=0` |
| 布料重置 | 位置/速度均未重置 |
| `release_diag` | 277 行；441 顶点、9 关节 |
| 事件 | `ungrasp_return` 1953、`delay_begin` 1953、`delay_end` 2073、`retreat_begin` 2073、`retreat_end` 2217（observed step） |
| phase 行数 | delay **120**、retreat **144**、release_opening 10、released 1、retreat_done 1、anchor 1 |
| success trace | 331 步，absolute step 2219–2549 |
| 视频/证据 | `episode.mp4`、`release_diag.npz`、`release_diag.json`、`release_diag_events.csv`、`success_trace.npz`、`success_meta.json` 等全部存在 |
| contact | subscription 创建；callback/event **0**；**不能写成无接触** |

## 质量结果（postfix）

标准 `a5_diag_assess.py` 在运行结束后崩溃：

```text
ValueError: operands could not be broadcast together with shapes (3,) (4,)
```

原因：`internal_delay.public_action_target` 是 3D XYZ，而公开 action target 是 4D（XYZ+yaw）；评估器的 `np.allclose` 直接比较两者。**这是审计器 bug，不是 episode 或物理失败。** 执行后的 app/manifest 未被修改；独立的 [post_assess_d1_120.py](../../post_assess_d1_120.py) 只比较 XYZ，生成 [diag-verdict-postfix.json](diag-verdict-postfix.json)。

- `complete_diagnostic=True`，32 项 postfix 检查全部通过
- `quality.status=rejected`、`quality.success=False`、`stable=False`
- 质心漂移 **2.040882 mm**（>1 mm）
- 顶点 P95 **4.413414 mm**（>3 mm）
- 几何全过、held 通过、释放连续、无运行错误
- RC2 4202 single 基线为 2.042884 / 4.414119 mm；D1-120 的变化约 **−0.0020 / −0.0007 mm**，正式窗口仍被稳定性拒绝

## 账本与失败证据

- 原始 `run_ledger.json`：[run_ledger.json](run_ledger.json)，记录 `sim_process_status=0`、`episode_passed=true`、`assess_status=1`（标准评估器崩溃）
- 原始 runner 日志：[runner.log](runner.log)
- 完整远端控制台日志（含 postcheck/ledger）：[console-final.log](console-final.log)
- `runs/completed` 已写入；按 one-shot 规则不允许自动重跑
- 步骤 6 启动前的两次 runner 预检失败记录保留在 [D1_120_RUN_PREFLIGHT_FAILURE_20261104](../D1_120_RUN_PREFLIGHT_FAILURE_20261104/review.md)

## 结论

- 步骤 6 的有效运行完成：12 个公开动作不变，120 步等待精确执行，事件与逐阶段记录完整，episode 本身 `passed=True`。
- 质量仍为稳定性拒绝；延迟 120 步没有使正式窗口通过 1 mm / 3 mm。
- 下一步：逐阶段比较等待/退让/退让后窗口（步骤 8），并下载核验全部 SHA256（步骤 7）。不得以本 run 冒充正式成功；正式 Stage 4 成功仍为 0。
