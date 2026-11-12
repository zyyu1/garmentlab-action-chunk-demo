# a5-rc2-pfs1-observation-v2-rc8b：初态协议补齐后的 task-scoped 候选（已登记；七例待运行）

rc8b 在 rc8 的基础上把任务协议**补到初态生成**：L1 flat `particleFrictionScale=0.0`，L2/L3 `=1.0`，在材料构造时设置、早于 reset 与物理步；初态结果记录任务、材料绑定、scale 读回与生成器身份；正式 preflight 拒绝缺失/不符/旧协议的初态。评价器、阈值、专家控制未改。rc8（及 rc7）保留，结果不并入本矩阵。

**状态：初态协议通过；七例 4/6 阳性，4202/4201 失败，未冻结。** 新初态按 0/1 协议生成并带完整身份字段，正式 preflight 通过；七例全部执行、证据完整、三组配对 0 差。但 **4202 s/a 质量拒绝**（质心 7.4809 / P95 11.5382 mm，`stationary_half` 29.9 mm，速度 P95 25.7 mm/s），4201 也拒绝；4100 s/a、4302 s/a accepted。`verify-dev` 失败于 4202 → **不冻结、未写回执**，rc8b 失败保留、**不沿用 rc8 结果补齐**。正式 Stage 4 成功仍为 0。详见 [rc8b 审查](../results/RC8B_SEVEN_CASE_20261105/review.md)。

## 1. 身份

| 项目 | 值 |
|---|---|
| 版本 | `a5-rc2-pfs1-observation-v2`（`rc8b`） |
| 父版本 | `rc8`（manifest `68930010…`，保留） |
| 新 manifest | `cce573dd…`（63 项；**52 项与 rc8 逐字节相同**） |
| 变化项 | 2 个初态生成器、2 个初态 files manifest、`stage4_batch_preflight.py`、正式/初态 runner、`a5-candidate.json`、登记 JSON、批次 runner |
| 新账本 | `<remote-root>/a5-rc2-pfs1-observation-v2-rc8b-runs` |

## 2. 任务协议（初态 / reset / rollout）

| 任务 | particleFrictionScale | 初态生成器 | 备注 |
|---|---:|---|---|
| L1 独立过折（4100） | **0.0** | `day4-square-initial.py` | flat，settle 120 |
| L2 nominal right（4201/4202） | **1.0** | `day4-square-initial-stripfold.py` | bottom 折条，settle 180 |
| L3 nominal right（4302） | **1.0** | `day4-square-initial-stripfold.py` | left 折条 width 0.20，settle 240 |

- 路由只按任务身份；不读取 seed、模式或结果。
- 初态结果新增 `protocol` 块：version、task、level、seed、expected/readback scale、材料绑定（`/World/Garment/particleMaterial` + particle system）、生成器脚本/文件清单哈希、生成时间。
- `stage4_batch_preflight.initial()` 逐项核对；旧初态（无 protocol）、错误 scale、缺失绑定、生成器不符一律拒绝。
- 正式批次与初态 runner 改为 **app-relative** 执行，不再从 `<remote-root>` 共享根目录取旧副本。

## 3. 本次生成的开发初态（各一次，不挑选、无重试）

| seed | 初态目录 | scale | 几何 extent (m) | 旧 extent (m) |
|---:|---|---:|---|---|
| 4100 | `day4-square-initial-20261105-014501-526555` | 0.0 | 0.4129 × 0.4129 | 同值（逐字节相同） |
| 4201 | `day4-square-initial-stripfold-20261105-014825-318974` | 1.0 | 0.4283 × 0.2669 | 0.4286 × 0.2678 |
| 4202 | `day4-square-initial-stripfold-20261105-015817-115841` | 1.0 | 0.4213 × 0.2558 | 0.4206 × 0.2541 |
| 4302 | `day4-square-initial-stripfold-20261105-020706-026048` | 1.0 | 0.2674 × 0.4315 | 0.2847 × 0.4357 |

- 4100 的新初态几何与旧初态**逐位相同**（before/applied/settled max|Δ|=0），只是补了 protocol 元数据。
- L2 条宽 4201 0.1793、4202 0.1714（冻结范围 0.1615–0.1793）；L3 left 条宽 0.20。L3 的 x extent 比旧初态窄约 17 mm，仍为 left 折条、z_p95≈0.069 m，未摊平；需在审查中作为“物理参数改变折条状态”的记录，不默认与旧初态相同。
- 初态哈希已写入 `a5-candidate.json` 与本目录 `registration.json`。

## 4. 七例矩阵（顺序执行，每槽一次）

| 槽 | seed | 任务 | 模式 | 动作 |
|---:|---:|---|---|---:|
| 1–2 | 4100 | L1 过折 | single / arc4 | 7 |
| 3–4 | 4202 | L2 nominal right | single / arc4 | 12 |
| 5–6 | 4302 | L3 nominal right | single / arc4 | 12 |
| 7 | 4201 | L2 历史失败对照 | single | 12 |

同 seed 两种模式共享同一份新初态。停止规则、评价器与 1 mm / 3 mm 阈值不变；六阳性必须接受，4201 允许有效接受或拒绝。

## 5. 离线检查（已完成）

- manifest 63/63；相对 rc8 仅 11 项变化、52 项逐字节相同。
- 初态 files manifest 与生成器/runner 哈希一致。
- `stage4_batch_preflight.initial()`：接受 4100/4202/4302 新初态；拒绝旧 4100（无 protocol）、错误 scale、缺失材料绑定、生成器哈希不符、缺失 protocol。
- `py_compile` 全通过；正式/初态 runner 改为 app-relative。

## 6. 结果（七例）

| 槽 | seed / 模式 | 质量 | 质心 / P95 (mm) | 几何 | stable |
|---:|---|---|---:|---|---|
| 1–2 | 4100 single/arc4 | **accepted** | 0.1435 / 0.2072 | true | true |
| 3–4 | 4202 single/arc4 | **rejected** | 7.4809 / 11.5382 | false | false |
| 5–6 | 4302 single/arc4 | **accepted** | 0.2756 / 0.4125 | true | true |
| 7 | 4201 single | rejected（有效） | 7.0657 / 10.4252 | false | false |

- 六阳性 4/6 accepted；配对 0.0；7/7 `initial_protocol=true`；765/765 下载哈希一致；本地复算 7/7 一致。
- 4202/4201 失败为 fold 后整体滑移（stationary half 29.9/30.1 mm > 25 mm）；4202 的 fold extent 0.196×0.408，旧初态同流程 0.228×0.420。
- `verify-dev` 失败于 4202（exit 1）；**未执行 freeze/gate**，未写回执。

## 7. 通过后

原计划的“通过后冻结”未触发。下一步需决定：调查 L2 初态在 1.0 下的敏感性，或显式修订协议（如 L2/L3 初态生成 0.0、rollout 1.0）作为新登记配置并重跑。不能回退旧初态或复用 rc8 结果。
