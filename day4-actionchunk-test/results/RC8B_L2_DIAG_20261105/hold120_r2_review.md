# recovery-hold120 r2：4202 干净复验 + 4302 扩展（均通过）

**结论：** 审计入口修复后，4202 r2 复验与 4302 扩展均 **runner/entry/audit 全部 exit 0、质量 accepted、证据完整**。4202 r2 与 r1 轨迹逐位相同；4302 也通过，保持期间运动接近零。两例通过，可以准备七例 RC；本轮不运行七例、不冻结，诊断不计入正式 Stage 4 成功。

## 1. 审计修复与历史保留

- 原 r1：runner exit 3，audit 打印 `KeyError: 'recovery_hold'`；结果 JSON 已完整写出，未重跑仿真。
- 修复：audit 增加 `check_output_contract()`，打印前校验必需字段；`test_audit_output.py` 覆盖 complete / missing / non-bool。
- 对同一 r1 保存结果重跑完整审计 → exit 0、`overall_valid=true`；原 exit 3、异常日志、复审计记录全部保留，不改写历史状态。

## 2. 4202 r2 干净复验

| 项目 | 值 |
|---|---|
| 候选 / manifest | `a5-rc8b-recovery-hold120-r2` / `60733a6b…`（61/63 与 r1 相同，仅 config/runner） |
| 初态 | rc8b 新 4202 `…015817-115841`（pfs=1） |
| 运行 | `…20261105-071812-338703` single 一次 |
| 退出码 | entry 0 / runner 0 / audit 0 |
| 质量 | **accepted**；质心 **0.2374 / P95 0.3484 mm**、stationary 6.69 mm、无失败 |
| 证据 | 113/113 哈希一致 |

**与 r1 逐阶段比较：** initial_loaded、after_recovery、pre_release、release_boundary、success_trace、recovery_hold_trace、动作目标、fold_yaw 的最大差均为 **0.0**。r2 是 r1 的逐位复现，干净退出仅来自审计修复。

## 3. 4302 扩展

| 项目 | 值 |
|---|---|
| 候选 / manifest | `a5-rc8b-recovery-hold120-r2-4302` / `3bc1351b…`（61/63 与 r2 相同，仅 config/runner/seed） |
| 初态 | rc8b 新 4302 `…020706-026048`（pfs=1） |
| 运行 | `…20261105-074146-551052` single 一次 |
| 退出码 | entry 0 / runner 0 / audit 0 |
| 质量 | **accepted**；质心 **0.2386 / P95 0.3468 mm**、stationary 7.16 mm、无失败 |
| 参照 rc8b 4302 | accepted 0.2756 / 0.4125 mm、stationary 7.55 mm |
| 证据 | 113/113 哈希一致 |

**保持阶段（4302）：** 121 帧 / 120 区间 / 2.0 s；质心速度 ~0.0001 mm/s、粒子 P95 0.0045–0.0062 mm/s、旋转 ~0°、EE 漂移 ≤0.00016 mm、附件全关。保持前运动已接近零。

**后续流程（4302 vs rc8b）：**

| 阶段 | max 差 | mean 差 |
|---|---:|---:|
| 载入后 | 0.0 mm | 0.0 mm |
| recovery 后 | 0.004 mm | 0.002 mm |
| pre-release | 1.741 mm | 0.599 mm |
| release boundary | 1.651 mm | 0.618 mm |

- 动作目标 max **0.0025 mm**、fold_yaw 差 ~0；fold extent 见 [hold120_4302_compare.json](hold120_4302_compare.json)。
- recovery、fold、release 与正式窗口均通过；无几何失败。

## 4. 判读与下一步

- **两例均通过**：hold120 作为候选衔接改进可以继续；但不能解释为“残余运动衰减”，也尚未证明稳健修复。
- **准备七例 RC**（不运行）：矩阵与 rc8b 相同（4100 s/a、4202 s/a、4302 s/a、4201 single），L1 不经过 hold，L2/L3 使用同一 120 步；需新登记、新账本与锁。
- 不扩批、不扫摩擦、不延长保持、不重跑七例、不冻结、不跑 held-out；正式成功仍为 0。

## 5. 产物

- [hold120_4302_compare.json](hold120_4302_compare.json)
- 4202 r2：[运行目录](hold120_r2_4202/day4-a5-rc2-pfs1-observation-v2-20261105-071812-338703)
- 4302：[运行目录](hold120_r2_4302/day4-a5-rc2-pfs1-observation-v2-20261105-074146-551052)
- 审计：[r1 复审计](hold120_run/a5-rc8b-recovery-hold120-runs/postrun_semantics_final.json) · [r2 4202](hold120_r2_4202/a5-rc8b-recovery-hold120-r2-runs/semantics.json) · [4302](hold120_r2_4302/a5-rc8b-recovery-hold120-r2-4302-runs/semantics.json)
