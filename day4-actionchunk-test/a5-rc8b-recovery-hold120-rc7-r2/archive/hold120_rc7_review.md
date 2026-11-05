# hold120 rc7 七例开发回归：六阳性 accepted，4201 有效拒绝

**报告口径：** slot1 首次审计退出 5，同结果经修订审计通过；slots2–7 在修订版下续跑。不得称整批所有入口首次均干净退出。

## 1. 候选与来源

| 项目 | 值 |
|---|---|
| 原候选 / manifest | `a5-rc8b-recovery-hold120-rc7` / `41db790f…`（slot1 运行身份） |
| 修订候选 / manifest | `a5-rc8b-recovery-hold120-rc7-r2` / `40858efc…`（63 项；相对 rc7 仅 config 变化，`a5_recovery.py` 哈希相同） |
| 审计 | 原 `813da5ce…`；修订 `0d4a9d74…`；`hold_contract.py` 独立契约 |
| 继承 | [inheritance.json](../../a5-rc8b-recovery-hold120-rc7-r2/inheritance.json)，仅 slot1；原 manifest/verdict/exit5 未改写 |
| 物理 | L1 pfs=0 无 hold；L2/L3 pfs=1；240 settle + 120 hold；single/arc4 同位置同时长 |
| 初态 | rc8b 原生 4100/4202/4302/4201，完整哈希 |
| 账本 | 原 rc7 runs 保留；续跑 `…-r2-resume` 独立 |

## 2. 七例结果

| 槽 | seed / 模式 | 质量 | 质心 / P95 (mm) | 几何 / 稳定 | hold |
|---:|---|---|---:|---|---|
| 1 | 4100 single | **accepted** | 0.1435 / 0.2072 | 通过 | 不适用 |
| 2 | 4100 arc4 | **accepted** | 0.1435 / 0.2072 | 通过 | 不适用 |
| 3 | 4202 single | **accepted** | 0.2374 / 0.3484 | 通过 | 120 步 / 121 帧 / 2.0 s |
| 4 | 4202 arc4 | **accepted** | 0.2374 / 0.3484 | 通过 | 120 步 / 121 帧 / 2.0 s |
| 5 | 4302 single | **accepted** | 0.2386 / 0.3468 | 通过 | 120 步 / 121 帧 / 2.0 s |
| 6 | 4302 arc4 | **accepted** | 0.2386 / 0.3468 | 通过 | 120 步 / 121 帧 / 2.0 s |
| 7 | 4201 single | **rejected（有效）** | 7.2583 / 11.0030 | stationary_half 30.6 mm；92 帧失败 | 120 步 / 121 帧 / 2.0 s |

- **六个阳性全部 accepted**；4201 为有效拒绝（历史失败对照，允许）。
- 三组 single/arc4 动作目标差 **0.0 m**；L2/L3 两组 hold 均为 120 步、2.0 s，时序一致。
- L1 两例无 `recovery_hold`/trace，`hold_applicable=false`；L2/L3 的 `hold_applicable=true` 且证据完整。

## 3. 验证

| 门禁 | 结果 |
|---|---|
| slot1 初次 audit | exit **5**（L1 N/A 契约缺陷）；历史保留 |
| slot1 同结果修订 audit | exit **0**、overall_valid=true |
| slots2–7 entry/audit | 每槽 exit 0；`overall_valid=true` |
| 质量 | 6/6 阳性 accepted；4201 rejected 有效 |
| 配对 | 4100/4202/4302 目标差 **0.0**；hold 时序一致 |
| 下载核验 | slot1 118/118 + slots2–7 664/664；全部哈希一致 |
| 本地复算 | 7/7 status 与 stability 逐值一致（[local_recompute.json](hold120_rc7_r2_resume/local_recompute.json)） |
| 视频 | 阳性例机械臂释放/退让后布料留在桌面；4201 末态布料随臂收拢，与其拒绝一致 |
| 来源兼容验证 | `verify_rc7_sources.py` → **RC7_SOURCE_VERIFIED**，exit 0；slot1 父 manifest、slots2–7 修订 manifest、六阳性、配对均通过 |
| 原版 verify-dev | **未使用**；原验证器只接受单一 manifest，本轮使用登记后的来源兼容入口，不称“原版直接通过” |

**续跑 runner 汇总说明：** resume 的 `batch_summary.json` 只统计 slots2–7（accepted=5），因此其 `all_six_positives_accepted=false`；加上继承的 slot1 后六阳性为真，最终来源验证器明确输出 `all_six_positives_accepted=true`。不修改该历史汇总文件，另由来源兼容验证入口给出七槽结论。

## 4. 结论与边界

- 按任务配置的开发回归，六个阳性全部 accepted；4201 有效拒绝；配对、证据、本地复算、视频、来源验证均通过。
- single/arc4 专家执行等价不代表学习策略性能；hold 机制未确认，不解释为残余运动衰减。
- **未执行 freeze、未写释放回执、未跑 held-out/正式批次**；正式 Stage 4 成功计数保持 **0**。
- 冻结材料草稿见 [FREEZE_DRAFT.md](hold120_rc7_r2_resume/FREEZE_DRAFT.md)；是否进入 freeze 需另行决定。

## 5. 产物

- [cases.csv](hold120_rc7_r2_resume/cases.csv) · [summary.json](hold120_rc7_r2_resume/summary.json) · [combined_summary.json](hold120_rc7_r2_resume/combined_summary.json)
- [local_recompute.json](hold120_rc7_r2_resume/local_recompute.json) · [source_verification.json](hold120_rc7_r2_resume/source_verification.json) · [source_verify.log](hold120_rc7_r2_resume/source_verify.log)
- [视频接触表](hold120_rc7_r2_resume/hold120_rc7_contact_sheet.png) · [帧目录](hold120_rc7_r2_resume/hold120_rc7_frames)
- [继承记录](../../a5-rc8b-recovery-hold120-rc7-r2/inheritance.json) · [修订登记](../../a5-rc8b-recovery-hold120-rc7-r2/registration.json)
- slot1 暂停现场：[审查](hold120_rc7_pause_review.md) · [batch.log](hold120_rc7/a5-rc8b-recovery-hold120-rc7-runs/batch.log)
