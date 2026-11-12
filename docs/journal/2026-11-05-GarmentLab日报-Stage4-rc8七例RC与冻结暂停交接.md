# 2026-11-05 GarmentLab 日报 · Stage 4 rc8 七例 RC 通过 / 冻结前检查暂停交接

> 后续交接见 [rc8b 日报](2026-11-05-GarmentLab日报-Stage4-rc8b初态协议与七例失败交接.md)：初态协议补齐后，新 L2 初态导致 4202/4201 失败，未冻结。

> 时间说明：rc8 的七次运行在远端（UTC+8）跨过 2026-11-05 凌晨；本地 Europe/Berlin 仍是 2026-11-04 晚间。本报告按远端运行日命名。

**暂停位置**　rc8（task-scoped：L1 `particleFrictionScale=0.0`、L2/L3 `=1.0`）七例 RC **通过**：6/6 阳性 accepted、4201 有效拒绝、三组配对 0 差、证据完整、verify-dev 通过。随后做冻结前核对：**身份检查通过**（manifest `68930010…`、14 行账本无未完成、无已有回执），但**正式入口检查未通过**——正式 L2/L3 初态生成脚本仍强制 `particleFrictionScale=0.0`（协议要求 1.0），因此**未执行 freeze、未写 `verified-dev.json`/`E_RELEASE.json`**，也没有改写任何哈希。正式 Stage 4 成功仍为 **0**；held-out 与正式批次未运行。等 A/B/C 选择后继续。

## 1. 从 rc7 到 rc8：任务协议修正

- **rc7** 把 4202/4302 单例的物理/控制固定为一个候选，但采用 **uniform pfs=1.0（含 L1）**。七例结果 4/6：4100 s/a 质量拒绝（`free_edge_overrun` 15.4 < 20 mm、`free_edge_height_p90` 24.4 > 15 mm、`vertex_speed_max` 64.6 > 50 mm/s；RC2 pfs=0 为 40.7/10.1/16.5），4202/4302 s/a accepted，4201 有效拒绝；verify-dev 失败于 4100。rc7 保留为失败候选。
- **rc8** 按任务身份固定物理：**L1 flat 0.0，L2/L3 1.0**，在材料构造时设置、早于 reset 与任何物理步；路由不读取 seed / 模式 / 结果；同任务 single/arc4 配置一致。材料五阶段读回按任务核对（L1=0.0，L2/L3=1.0）。
- manifest `68930010…`（63 项；**59 项与 v2 逐字节相同**）；变化项 `a5_l1.py`、`pfs1_observation_v2.py`、登记 JSON、runner。新账本 `a5-rc2-pfs1-observation-v2-rc8-runs`。

## 2. 七例结果（全部一次通过/有效拒绝）

| 槽 | seed / 档位 / 模式 | 质量 | 质心 / P95 (mm) | 协议 expected |
|---:|---|---|---:|---:|
| 1–2 | 4100 L1 single/arc4 | **accepted** | 0.1435 / 0.2072 | **0.0** |
| 3–4 | 4202 L2 single/arc4 | **accepted** | 0.2642 / 0.3792 | 1.0 |
| 5–6 | 4302 L3 single/arc4 | **accepted** | 0.2390 / 0.3524 | 1.0 |
| 7 | 4201 L2 single | rejected（有效） | 0.9409 / 2.8073 | 1.0 |

- 4100 与 RC2 4100（pfs=0）**逐值相同**，与“rc7 的 L1 失败来自 uniform 1.0”一致。
- 4201 几何全过、`crossed=1.0`，但 `vertex_speed_p95 = 20.27 mm/s > 10` → 有效拒绝；未强制、未重跑。
- 三组 single/arc4 配对 target 差 **0.0**；动作数 7/12 与 horizon 符合登记。

## 3. 门禁与证据

| 项目 | 结果 |
|---|---|
| 六阳性全部接受 | **是（6/6）** |
| 4201 有效评价 | 是（有效拒绝） |
| 七例证据完整 | 是（7/7 文件 + 观测语义） |
| 下载核验 | **807/807** remote↔local SHA256 一致 |
| 本地复算 | `stage4_success_v1.evaluate` 重算 7/7 status/stability 逐值相同 |
| 视频审查 | 通过（末帧机械臂撤离、布料在桌面；L1 flap 落桌；4201 末段仍滑移） |
| 原版 verify-dev | **通过**：`A5_DEV_VERIFIED 7`，exit 0 |
| 账本 | 14 行 = 7 started + 7 finished；无未完成尝试；全部绑定 `68930010…` |

## 4. 冻结前检查：身份通过，正式入口未通过

**身份（PASS）**

| 检查 | 结果 |
|---|---|
| candidate manifest | `68930010…`，本地与远端一致；63/63 |
| 冻结清单 | manifest/config/runner/a5_l1/observation 与当前文件一致 |
| 逐例证据哈希 | 7/7 与 `freeze_manifest.json` 一致 |
| 已有回执 | `verified-dev.json` / `E_RELEASE.json` 均不存在 |

**正式入口（FAIL：初态生成）**

RC8 绑定的部分是好的：`a5_entry.py` 的 `preflight/gate/freeze/run` 读取 RC8 目录内的 `a5-manifest.json`；`run-stage4-formal-batch.sh` 使用 `$here`，rollout 调用 RC8 的 `a5_recovery.py`（L2/L3=1.0）与 `a5_l1.py`（L1=0.0）；reset 使用同一材料对象。没有指向 RC2/RC7 的路径。

但正式 L2/L3 初态生成仍固定 0.0：

| 证据 | 位置 |
|---|---|
| 强制 `particle_friction_scale = 0.` | `day4-square-initial-stripfold.py:196` |
| 断言读回必须为 0 | `day4-square-initial-stripfold.py:261-262` |
| 正式批次对非 flat 选择该脚本 | `run-stage4-formal-batch.sh:73` |
| 正式 initial 检查不核对材料 scale | `stage4_batch_preflight.py:83-92` |

若现在冻结并生成 60 个正式初态，L2/L3 会在 0.0 下生成、在 1.0 下 rollout，违反“初态生成、reset、rollout 同一任务协议”，且正式 preflight 不会拦住它。L1 flat 生成强制 0.0，与 L1=0.0 一致。

**处置：** 未写回执、未执行 freeze/gate、未改哈希；现场保留。详细证据见 [FREEZE_PRECHECK](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/FREEZE_PRECHECK.md)。

## 5. 当前边界与报告口径

- 正式 Stage 4 成功仍为 **0**；held-out、正式批次未运行；RC8 未冻结。
- RC8 七例 RC 的通过结论有效（rollout 层证据）；冻结阻塞点仅在正式初态生成入口。
- 结果**按任务报告**，不是统一物理条件下的纯初态难度比较。
- rc7 保留为失败候选；其被操作者终止的启动记录仍在运行历史中（未形成可评价 episode，不计入质量分母）。
- 不宣称地面摩擦已修复；cloth-ground 力/冲量仍不可得，0 事件不是无接触。

## 6. 解除冻结阻塞的选项

| 选项 | 内容 | 代价/风险 |
|---|---|---|
| **A（推荐）** | rc8b：把 `day4-square-initial-stripfold.py` 的 L2/L3 改为设置/断言 1.0，更新 `square-initial-stripfold-files.json`；新 manifest，重跑七例后 verify-dev/freeze | 约 2 小时 GPU + 审查；唯一自洽路径 |
| B（不推荐） | 冻结 rc8 并登记“正式初态生成 0.0”的协议例外 | 需显式签字；结果不能声称初态与 rollout 同协议 |
| C（不推荐） | 冻结 rc8，正式初态用外部 task-scoped 工具预生成 | 冻结入口仍含 0.0 fallback，非自洽实现 |

**A 的最小改动范围：** 2 个 manifest 条目（stripfold 脚本 + 其 files json）；`a5_l1.py`/`a5_recovery.py`/观测/评价器不动。因 manifest 变化，rc8 的七例账本不能复用于 rc8b 的 verify-dev，需在 rc8b 下重跑七例。

## 7. 恢复入口与命令（当前状态）

- 冻结/门禁（RC8，**当前不应执行**，因正式入口未修）：
  ```bash
  cd <remote-root>/a5-rc2-pfs1-observation-v2-rc8/app
  <remote-root>/envs/isaac40/bin/python a5_entry.py freeze --journal <remote-root>/a5-rc2-pfs1-observation-v2-rc8-runs/journal
  <remote-root>/envs/isaac40/bin/python a5_entry.py gate
  ```
- 正式批次（**未启动**，需先冻结）：
  ```bash
  bash run-stage4-formal-batch.sh stage4-heldout-seeds.json <batch-tag>
  ```
- 七例证据：`results/RC8_SEVEN_CASE_20261104/`；批次账本：`a5-rc2-pfs1-observation-v2-rc8-runs/`。
- 下一项（暂停中）：选择 A/B/C；若 A，先做 rc8b 登记与预检，再重跑七例；冻结完成前不生成/运行 held-out。

## 8. 关键产物

- [rc8 七例审查](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/review.md)
- [冻结前检查](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/FREEZE_PRECHECK.md)
- [冻结材料](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/FREEZE_DOSSIER.md) · [freeze_manifest.json](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/freeze_manifest.json)
- [cases.csv](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/cases.csv) · [local_recompute.json](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/local_recompute.json) · [verify-dev 日志](day4-actionchunk-test/results/RC8_SEVEN_CASE_20261104/rc8-verify-dev.log)
- [rc8 版本登记](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8/README.md) · [registration.json](day4-actionchunk-test/a5-rc2-pfs1-observation-v2-rc8/registration.json)
- [rc7 审查](day4-actionchunk-test/results/RC7_SEVEN_CASE_20261104/review.md)（失败候选，保留）
