# a5-rc2-d1-120：D1 延迟退让诊断（步骤 6 已运行，postfix 评估完成）

本目录是 **D1-120** 的独立诊断候选，从已验证的 `a5-rc2-drift-diag-v1` v1.1（干净运行 `053151-197013`）复制并重定向版本身份。步骤 2–4 已实现：在末次 OPEN 内、ungrasp 返回后、原退让目标前插入 **120 个物理步**，保持 12 个公开动作/目标/命令/horizon 不变，并记录五个命名事件及逐步 phase。

**2026-11-04 已单次运行 4202 single**：episode `passed=True`，120 步等待精确执行，事件/证据完整。标准 `a5_diag_assess.py` 在收尾时因 3D/4D target 比较崩溃；执行后的 app/manifest 未改，独立 postfix 审计 `complete=True`、`quality=rejected`（稳定性）。详见 [运行结果](../results/D1_120_RUN_4202_20261104/review.md)。RC2 和 v1.1 原目录均未修改。

## 1. 身份

| 项目 | 值 |
|---|---|
| 版本 | `a5-rc2-d1-120` |
| 父诊断 | `a5-rc2-drift-diag-v1` v1.1 |
| 父 manifest SHA256 | `13c1f20a5081fdaea7cdbd25a299c3086fec0500eb9773f9fb1351b232a0c922`（66 项） |
| 父 config SHA256 | `aa5da98be1dc03f588125d99ed6e5cc0e41728ae32c8770cfe27dfd3a6c06149` |
| 基础 candidate SHA256 | `10a6cb452b9fafd5907f245b68fd02d49c7af1e12fa6cb0f755f1791a5af27a5` |
| 基础 RC2 manifest SHA256 | `39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d`（60 项） |
| D1-120 manifest | `app/a5-rc2-d1-120-files.json`，66 项（60 基础 + 6 诊断） |
| D1-120 manifest SHA256 | `cd1d7f83d065974e12191486eddbf722edd4a1b7392ec78543966483434b25a6` |
| D1-120 config SHA256 | `a6884eab8ae4bf6d703b0321415cfc2cd501f878472068109addba564ba4d471` |
| 登记文件 | [registration.json](registration.json) |
| 状态 | **run_completed_postfix_assessed**：4202 single 单次运行 `passed=True`；120 步等待/事件完整；postfix `complete=True`、`quality=rejected`；步骤 7/8 核验与分析完成；无重试 |

## 2. 初态身份（4202 single）

| 项目 | 值 |
|---|---|
| 初态目录 | `/root/autodl-tmp/day4-square-initial-stripfold-20261103-062710-242560` |
| `result.json` SHA256 | `4472f4df6332a240da52b8c2ebaf7dd91f5f958e10a09803b64658699aea8adb` |
| `initial_geometry.npz` SHA256 | `a6646d66bed8d00d046c2195c733f7f3aefc6471ca458995e247c11091e86106` |
| seed / level / mode | 4202 / perturbed / single |
| 折向 | right |
| 公开动作 | 12（与 RC2/v1.1 相同） |

## 3. 步骤 1：独立身份

1. 完整复制 v1.1 的 `app/`（含嵌套 backend/schema）和 `2026-11-02-GarmentLab日报-Stage4-成功判据v1.md`。
2. 删除旧 config/manifest/runner，创建 D1-120 自己的 `a5-rc2-d1-120.json`、`a5-rc2-d1-120-files.json`、`run-a5-rc2-d1-120.sh`。
3. 重定向 probe version、protocol、manifest 路径和输出前缀为 `a5-rc2-d1-120` / `stage4-a5-rc2-d1-120` / `day4-a5-rc2-d1-120-`。
4. 生成 66 项 manifest；基础 60 项 hash 与 RC2 一致；[registration.json](registration.json) 记录父版本、初态、源码和配置哈希。

## 4. 步骤 2：120 步等待

- 插入点：`app/a5_capture_diag.py` 的 `measure_detachment`，即 `ungrasp` 返回后、`original(*args)` 发起原向上退让目标前。
- 实现：`hold_open_for_steps()` 恰好调用 `world.step(render=True)` **120 次**（2.0 s，dt=1/60）。
- 保持：不调用 `robot_goto_position`/`open`/`close`，不改变目标，不写布料位置，不清速度。
- 每一步断言：`holding=false`、三个 slot 都未附着、夹爪保持 OPEN；否则立即失败。
- 等待结束后才调用 `original(*args)`；退让目标仍是原先计算的 `start_ee + [0,0,0.15]`。
- 结果记录 `internal_delay`：起止 step/time、120 步、EE 起止位移、无控制调用、无目标改变、无布料重置。

## 5. 步骤 3：公开动作与登记

- 等待发生在第 **12** 个公开动作 `release_retreat` 内；代码在插入前断言 `len(actions)+1 == 12` 且 `sum(call_horizons) == 12`。
- `a5_recovery_diag.py` 与 v1.1 的 diff 仅限版本字符串和 diagnostic 元数据；12 个 action 调用、目标表达式、命令和 horizon 未改。
- `result['internal_delay']` 明确标记 `public_action: false`、`scope: internal_control_stage`、`public_action_index: 12`、`public_action_label: release_retreat`。
- 运行后 `a5_diag_assess.py` 会检查：120 步、公开动作索引 12、无控制/目标改变、无布料重置、公开目标与末次 action target 一致。
- **静态逐项核对已通过**（[static-audit.json](static-audit.json)：21/21 action/horizon 行、`start_ee`/退让目标/`release(target)` 均与 v1.1 相同）；实际动作数组与基线的逐项比较在运行后（步骤 6–7）进行。

## 6. 步骤 4：事件与 phase

- `ungrasp_return` 由 `control.ungrasp` 返回后的包装器记录；`delay_begin`/`delay_end` 包围 120 步等待；`retreat_begin`/`retreat_end` 包围原退让目标运动。
- 五个事件写入 `evidence/release_diag.json` 的 `events`，并生成 `evidence/release_diag_events.csv`。
- 事件行包含 EE 位姿/四元数、全部关节、开合量、attachment 标志、布料质心和布料顶点 SHA256；逐物理步的完整布料/EE/关节/attachment 数组仍在 `release_diag.npz`。
- `release_diag.npz` 的 `phase` 区分 `release_opening`、`released`、`delay`（恰好 120 个 state 行）、`retreat`、`retreat_done`。
- `a5_diag_assess.py` 将检查：五个事件顺序、`delay_end-delay_begin=120`、`ungrasp_return<=delay_begin`、`retreat_begin>=delay_end`、`retreat_end>=retreat_begin`、`delay` phase 行数 120、`retreat` phase 行数 >0。

## 7. 离线验证

- manifest：66/66 路径与 SHA256 通过；基础 60 项与 RC2 一致。
- `test_d1_120_delay.py`：**5/5 通过**（恰好 120 步、无控制调用、正确耗时、拒绝错误步数/附着/关爪）。
- `test_release_diag.py`：1/1 通过，覆盖五个命名事件、`events_complete` 和 `release_diag_events.csv`。
- `py_compile`、`bash -n` 通过。

## 8. 完成情况与边界

- 步骤 5：离线预检 **65/65 通过**（[预检报告](../results/D1_120_PREFLIGHT_20261103/review.md)）。
- 步骤 6：**已单次运行** 4202 single；`runs/completed` 已写入，不自动重试。结果、日志、视频、事件与 postfix verdict 见 [运行结果](../results/D1_120_RUN_4202_20261104/review.md)。
- 标准 assessor 的 3D/4D target 形状 bug 是收尾审计问题，不是 episode 失败；执行后的 app/manifest 未修改，采用独立 [postfix 审计](../post_assess_d1_120.py)。
- 步骤 7：下载核验 **46/46 通过**（[审计](../results/D1_120_STEP7_AUDIT_20261104/review.md)）。
- 步骤 8：分段分析完成（[分析](../results/D1_120_STEP8_ANALYSIS_20261104/review.md)）：等待 2.0783 mm/4.5603 mm P95、退让 2.4590/5.3214、窗口 2.0409/4.4134；D1 与基线布料在相同 elapsed 时间点 486 点逐位相同。120 步延迟不改变滑移率；优先检查释放瞬态/回弹/地面接触。
- 正式 Stage 4 成功仍为 0；不跑 held-out；不覆盖 RC2 或 v1.1。

## 9. 运行入口

```bash
cd /root/autodl-tmp/a5-rc2-d1-120/app
bash run-a5-rc2-d1-120.sh 4202 single
```

## 10. 上传

```powershell
scp -P 23636 -r E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\a5-rc2-d1-120 root@connect.nmb2.seetacloud.com:/root/autodl-tmp/
```
