# rc8 冻结材料（**冻结前检查未通过，freeze 未执行**）

> **状态：freeze 暂停。** 身份核对通过；但正式 L2/L3 初态生成仍强制 `particleFrictionScale=0.0`（应为 1.0），与任务协议不符。未写 `verified-dev.json` / `E_RELEASE.json`，未执行 freeze/gate。详见 [FREEZE_PRECHECK.md](FREEZE_PRECHECK.md)。

本文件整理通过七例 RC 的候选材料，供修正后显式冻结使用。本轮**没有**写 `verified-dev.json` / `E_RELEASE.json`，**没有**运行 held-out 或正式批次；正式 Stage 4 成功仍为 **0**。

## 1. 候选身份

| 项目 | 值 |
|---|---|
| 版本 / revision | `a5-rc2-pfs1-observation-v2` / `final-candidate-rc8-task-scoped` |
| manifest | `6893001070f6bfc24307927cafe95bb83001524edcb35804a4aaf57479f457aa`（63 项） |
| 变化项 vs v2 | `a5_l1.py`、`pfs1_observation_v2.py`、登记 JSON、runner（59 项不变） |
| config / runner | `1a02db29…` / `bec54ade…` |
| a5_l1 / observation | `7cbdc1e4…` / `b0d6c6d4…` |
| 父 manifest | v2 `d97bf349…`；rc7 `bcba8c11…`（失败候选，保留） |

## 2. 任务协议

| 任务 | particleFrictionScale | 备注 |
|---|---:|---|
| L1 独立过折（4100） | **0.0** | 保留观测接入与原控制 |
| L2/L3 nominal right（4201/4202/4302） | **1.0** | 沿用已验证控制与观测 |

路由键为任务身份，在材料构造时设置，早于 reset/物理步；不读取 seed、模式或结果。结果按任务报告，不是统一物理条件下的难度比较。

## 3. 七例结果（全部证据完整）

| 槽 | seed / 模式 | 质量 | 质心 / P95 (mm) | 协议 expected |
|---:|---|---|---:|---:|
| 1 | 4100 single | accepted | 0.1435 / 0.2072 | 0.0 |
| 2 | 4100 arc4 | accepted | 0.1435 / 0.2072 | 0.0 |
| 3 | 4202 single | accepted | 0.2642 / 0.3792 | 1.0 |
| 4 | 4202 arc4 | accepted | 0.2642 / 0.3792 | 1.0 |
| 5 | 4302 single | accepted | 0.2390 / 0.3524 | 1.0 |
| 6 | 4302 arc4 | accepted | 0.2390 / 0.3524 | 1.0 |
| 7 | 4201 single | rejected（有效） | 0.9409 / 2.8073 | 1.0 |

三组 single/arc4 配对 target 差 0.0；7/7 文件与观测语义有效；807/807 下载哈希一致；本地 evaluator 重算 7/7 逐值相同。

## 4. 门禁

| 门禁 | 结果 |
|---|---|
| 六个阳性全部接受 | 通过（6/6） |
| 4201 有效评价 | 通过（有效拒绝） |
| 七例证据 + 三组配对 | 通过 |
| 视频审查 | 通过（末帧机械臂撤离、布料在桌面；L1 flap 落桌；4201 末段滑移） |
| 本地复算 | 通过 |
| 原版 verify-dev | 通过（`A5_DEV_VERIFIED 7`，exit 0） |

逐例哈希与机器可读材料见 [freeze_manifest.json](freeze_manifest.json)。

## 5. 冻结前仍需（不在本轮）

1. **显式冻结动作**：写 `verified-dev.json` / `E_RELEASE.json`（本轮未做）。
2. **held-out**：`4110–4129 / 4210–4229 / 4310–4329`，与开发 seeds 不重叠；本轮未生成、未运行。
3. **正式批次**：held-out 初态 + 正式运行；正式 Stage 4 成功计数当前为 0。
4. **初态生成协议**：后续正式初态生成须按任务设置对应 `particleFrictionScale`；本轮复用开发初态（L2/L3 初态为早期 0.0 settle），已在登记中声明。
5. **报告口径**：按任务报告；rc7 uniform 失败的解释保留为视频支持的机制解释，不写成已确认因果；rc7 被终止的启动记录保留在运行历史、不计入质量分母。

## 6. 相关材料

- [rc8 七例审查](review.md)
- [cases.csv](cases.csv) / [cases.json](cases.json) / [local_recompute.json](local_recompute.json)
- [verify-dev 日志](rc8-verify-dev.log)
- [视频帧接触表](rc8_contact_sheet.png)
- [批次账本](a5-rc2-pfs1-observation-v2-rc8-runs/batch_summary.json)
- [版本登记](../../a5-rc2-pfs1-observation-v2-rc8/registration.json)
