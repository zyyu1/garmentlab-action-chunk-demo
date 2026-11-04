# a5-rc2-pfs1-observation-v2-rc8：task-scoped 七例 RC（已登记；预检后按槽执行）

本候选是 rc7 的**任务协议修正版**：`particleFrictionScale` 按任务身份固定——**L1 flat = 0.0，L2/L3 = 1.0**，在 episode 初始化、物理步进前设置；不按 seed、执行模式或运行结果切换。观测接入、控制、评价器与阈值不变；rc7 作为失败候选保留，其结果不并入本矩阵。

**状态：七例 RC 通过；冻结前检查发现正式初态生成入口不符合任务协议，freeze 暂停（未写回执）。** 六个阳性全部 accepted（4100 s/a 0.1435/0.2072、4202 s/a 0.2642/0.3792、4302 s/a 0.2390/0.3524 mm），4201 为有效拒绝；三组 single/arc4 配对 target 差 **0.0**；7/7 证据完整、807/807 下载哈希一致、本地 evaluator 重算 7/7 一致、原版 `verify-dev` **通过**（`A5_DEV_VERIFIED 7`）。身份核对通过（manifest `68930010…`、14 行账本无未完成、无已有回执），但正式 L2/L3 初态生成脚本仍强制 `particleFrictionScale=0.0`（应为 1.0），因此**未执行 freeze、未生成 `verified-dev.json`/`E_RELEASE.json`**。详见 [FREEZE_PRECHECK](../results/RC8_SEVEN_CASE_20261104/FREEZE_PRECHECK.md)。正式 Stage 4 成功仍为 0。

## 1. 身份

| 项目 | 值 |
|---|---|
| 版本 | `a5-rc2-pfs1-observation-v2`（final candidate `rc8`，task-scoped） |
| 父版本 | `a5-rc2-pfs1-observation-v2-rc7`（失败，保留） |
| 基准 manifest | v2 `d97bf349…`（63 项） |
| 新 manifest | `68930010…`（63 项；**59 项与 v2 逐字节相同**） |
| 变化项 | `a5_l1.py`（L1 0.0）、`pfs1_observation_v2.py`（expected scale 参数化）、登记 JSON、runner |
| 新账本 | `/root/autodl-tmp/a5-rc2-pfs1-observation-v2-rc8-runs` |
| 登记/审计 | [registration.json](registration.json)、[static-audit.json](static-audit.json)、[source-diff.md](source-diff.md)、[audit_rc8_case.py](audit_rc8_case.py) |

## 2. 任务协议（运行前固定）

| 任务 | particleFrictionScale | friction | 说明 |
|---|---:|---:|---|
| L1 独立过折（4100） | **0.0** | 0.3 | 保留观测接入与原控制 |
| L2 nominal right（4201/4202） | **1.0** | 0.3 | 沿用已验证控制与观测 |
| L3 nominal right（4302） | **1.0** | 0.3 | 同上 |

- 路由键是**任务身份**（flat / perturbed / crumpled），在材料构造时设置，早于 reset 与任何物理步；排除 seed、execution mode、运行结果。
- 同任务 single/arc4 配置完全一致。
- 材料五阶段读回：L1 必须为 **0.0**，L2/L3 必须为 **1.0**；不匹配在 release 前停止。
- 后续正式初态生成、reset 与 rollout 采用同一任务协议；本轮初态复用登记目录与哈希（生成本身早于该协议），不重生。

## 3. 七例矩阵（顺序执行，每槽一次）

| 槽 | seed | 档位/任务 | 模式 | 动作 | 通过要求 |
|---:|---:|---|---|---:|---|
| 1 | 4100 | L1 独立过折 | single | 7 | 质量接受、证据完整 |
| 2 | 4100 | L1 独立过折 | arc4 | 7 | 同上；与槽 1 目标一致（1e-6） |
| 3 | 4202 | L2 nominal right | single | 12 | 质量接受、证据完整 |
| 4 | 4202 | L2 nominal right | arc4 | 12 | 同上；与槽 3 目标一致 |
| 5 | 4302 | L3 nominal right | single | 12 | 质量接受、证据完整 |
| 6 | 4302 | L3 nominal right | arc4 | 12 | 同上；与槽 5 目标一致 |
| 7 | 4201 | L2 历史失败对照 | single | 12 | 证据完整，接受或拒绝均可 |

## 4. 证据与停止规则

- 原 RC 采集要求：原版 `a5_entry.py` 的 `assess()`（未改）。
- v2 观测语义：`audit_rc8_case.py`（文件/stage、FD 速度、raw readback unvalidated、任务相关材料五阶段、binding、self/non-particle、solver 边界、contact 能力、release clock、证据 manifest），并按任务核对 expected scale。
- 速度只用世界顶点位置差分；cloth-ground 力/冲量不可得，0 事件不是无接触。
- 停止规则与 rc7 相同：预检不符 → 启动前停止；缺结果/执行错误/采集不完整/语义失败 → 暂停；质量拒绝但证据完整 → 记录并继续；配对超 1e-6 → 暂停；需改代码/参数/阈值 → 结束本批次。

## 5. 报告口径

- 结果**按任务报告**；本矩阵不是“统一物理条件下的纯初态难度比较”。
- rc7 的 uniform pfs=1 在 4100 这个开发例上造成 L1 回归失败；自由边未落桌/自重锁未发生可作为视频支持的机制解释，尚不写成已独立确认的因果机制。
- rc7 被操作者终止的启动记录继续列入运行历史，说明未形成可评价 episode；不计入质量分母，但不从执行记录中消失。

## 6. 结果与放行

| 槽 | seed / 模式 | 质量 | 质心 / P95 (mm) | 协议 expected |
|---:|---|---|---:|---:|
| 1–2 | 4100 single/arc4 | **accepted** | 0.1435 / 0.2072 | **0.0** |
| 3–4 | 4202 single/arc4 | **accepted** | 0.2642 / 0.3792 | 1.0 |
| 5–6 | 4302 single/arc4 | **accepted** | 0.2390 / 0.3524 | 1.0 |
| 7 | 4201 single | rejected（有效） | 0.9409 / 2.8073 | 1.0 |

- 六阳性全部接受；三组配对 0.0；7/7 证据完整；807/807 哈希一致；本地 evaluator 重算 7/7 一致；`verify-dev` 通过（exit 0）。
- 4100 与 RC2 4100（pfs=0）逐值相同，支持“rc7 L1 失败来自 uniform 1.0”的机制解释（仍按视频支持的机制解释报告，不写成已确认因果）。
- 已整理 [FREEZE_DOSSIER.md](../results/RC8_SEVEN_CASE_20261104/FREEZE_DOSSIER.md) 与 [freeze_manifest.json](../results/RC8_SEVEN_CASE_20261104/freeze_manifest.json)。
- **未执行**显式 freeze（`verified-dev.json`/`E_RELEASE.json`）、held-out、正式批次；正式 Stage 4 成功仍为 0。

## 7. 放行条件

六阳性全部接受、4201 有效评价、七例证据完整、三组配对通过、视频审查、本地复算一致、原版 verify-dev 通过——本轮全部满足。通过后整理冻结材料；本轮**不执行 freeze / held-out**。
