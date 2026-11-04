# rc8 冻结前检查：身份通过，正式入口未通过 → **freeze 未执行**

按授权执行冻结前核对。身份/回执检查通过；但正式入口的**初态生成**仍固定 `particleFrictionScale=0.0`（L2/L3 应为 1.0），与任务协议不符。按“身份或 gate 检查失败则保留现场、不得绕过”的规则，**未写 `verified-dev.json` / `E_RELEASE.json`，未执行 freeze/gate**，现场保持为“RC 已通过、冻结待修正”。

## 1. 身份核对（PASS）

| 检查 | 结果 |
|---|---|
| candidate manifest | `68930010…`，本地与远端 `sha256sum` 一致 |
| manifest 条目 | 63/63，`bad=[]` |
| 冻结清单 | `freeze_manifest.json` 的 manifest/config/runner/a5_l1/observation 哈希与当前文件一致 |
| 逐例证据哈希 | 7/7 的 `success_trace.npz`、`a5-verdict.json`、`evidence/manifest.json`、`rc8_semantics.json` 与冻结清单一致 |
| 七例账本 | `attempts.jsonl` 14 行 = 7 started + 7 finished；无未完成尝试；全部绑定 manifest `68930010…` |
| 已有回执 | `verified-dev.json`、`E_RELEASE.json` 均**不存在**（无覆盖风险） |
| 远端一致性 | 远端 manifest 哈希与本地一致；远端回执同样不存在 |

## 2. 正式入口核对（FAIL：初态生成）

已确认 RC8 绑定的部分：

- `a5_entry.py` 的 `preflight/gate/freeze/run` 读取候选目录内的 `a5-manifest.json`（`68930010…`），不指向 RC2/RC7。
- `run-stage4-formal-batch.sh` 使用 `$here`（RC8 app），开头调用 `a5_entry.py gate`，rollout 调用 `a5_entry.py run --split formal` → 使用 RC8 的 `a5_recovery.py`（L2/L3=1.0）与 `a5_l1.py`（L1=0.0）。
- reset 在 episode 内由同一材料对象完成，rollout 的任务配置正确。

**未通过的部分：正式 L2/L3 初态生成。**

| 证据 | 位置 |
|---|---|
| L2/L3 初态生成脚本强制 `particle_friction_scale = 0.` | `day4-square-initial-stripfold.py:196` |
| 并断言读回必须为 0 | `day4-square-initial-stripfold.py:261-262` |
| 正式批次对非 flat 选择该脚本 | `run-stage4-formal-batch.sh:73` |
| 正式 `initial` 检查只核对 result/geometry/png，不核对材料 scale | `stage4_batch_preflight.py:83-92` |
| L1 flat 生成强制 0.0 | `day4-square-initial.py:148`（与 L1=0.0 一致） |

因此若现在冻结并生成 60 个正式初态，L2/L3 会在 0.0 下生成、在 1.0 下 rollout，违反“初态生成、reset、rollout 同一任务协议”的要求；`stage4_batch_preflight` 也不会拦住它。

## 3. 当前状态

- **未冻结**、未写回执；未覆盖任何已有文件；未改哈希或阈值。
- rc8 七例 RC 的通过结论仍然有效（那是 rollout 层的证据）；冻结阻塞点仅在正式初态生成入口。
- 冻结材料仍在：[FREEZE_DOSSIER.md](FREEZE_DOSSIER.md)、[freeze_manifest.json](freeze_manifest.json)。

## 4. 解除阻塞的选项

**A（推荐）：rc8b 最小修正 + 重跑七例。**
- 修改 `day4-square-initial-stripfold.py`：L2/L3 设置并断言 `particle_friction_scale=1.0`；
- 更新 `square-initial-stripfold-files.json` 中该脚本哈希（该文件也在候选 manifest 内）；
- 新 manifest → 七例账本的 manifest 不再匹配，需在 rc8b 下重跑七例（约 2 小时）并重新 verify-dev/freeze。
- 这是唯一能让“初态生成/rollout 同协议”与冻结身份同时成立的路径。

**B（不推荐）：冻结 rc8 并登记“正式初态生成 0.0”的协议例外。**
- 与任务协议冲突；需要你显式签字，且正式批次结果不能声称初态与 rollout 同协议。

**C（不推荐）：冻结 rc8，正式 60 个初态用外部 task-scoped 工具预生成，绕过 frozen runner 的生成分支。**
- 实际初态可以是 1.0，但冻结的正式入口仍含 0.0 fallback，不是自洽的协议实现；一旦某个初态缺失就会静默生成 0.0。

## 5. 结论

**freeze 未执行。** 请选择 A（推荐）或明确接受 B/C；在 A 完成前，正式批次与 held-out 都不应启动。
