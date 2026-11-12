# Stage 4 折形任务定义冻结（2026-11-02，第二步 + 第三步表示层）

## A5 候选变更登记 · stage4-a5-rc1（2026-11-03）

任务 B（L2/L3 nominal 20/20）拟采用 right，两种表示共用；L1 沿用 left 过折。登记将最后一个公开 OPEN 的目标设为实测 EE 上方 0.15 m，解除抓取后显式移向该目标，L1/B 仍为 7/12 个公开动作。新 step 0 定义为这次 OPEN 完成的物理步；固定采集 0–330 并以冻结 B 数值判据评价 210–330。旧开发终态不补记本版本成功。状态为候选，须经真实开发复验后另行冻结。详见 [A5 决策与 E 清单](2026-11-02-GarmentLab日报-Stage4-A5候选与E清单.md)。

## 2026-11-02 B项：正式成功判据 v1.0.0 已交付（仅离线）

以 [2026-11-02-GarmentLab日报-Stage4-成功判据v1.md](2026-11-02-GarmentLab日报-Stage4-成功判据v1.md) 与 `day4-actionchunk-test/stage4-success-v1.json` 为当前成功判据。A/L1过折和B/nominal分任务评价；新增OPEN完成后逐物理步0..330采集、3.5–5.5秒连续几何及稳定窗口。原目标、held门槛和7/12动作预算不变。独立评价manifest登记新成功层，旧折叠manifest/runner未修改。

13项离线测试通过；31个历史目录复算20个满足对应终态几何、11个不满足，但全部缺新协议完整时序证据，不能追认正式成功。稳定阈值为预登记工程容差，尚待开发复验。评价配置与分类器已完成，不等于runner采样接入或正式批次已解锁。下一步需单独接入记录并用开发seed复验；held-out保持暂停，正式成功0。right是否正式采用仍需独立登记。下方“数值阈值未冻结”等段落保留为本次之前的历史状态。

> 命名约定与仓库其他文档一致：正文用 Stage，`DAY4_*.md`、脚本名、结果目录名保留。

本文件回答一个问题：**L1 / L2 / L3 各自要折叠成什么形状、用哪个评价器判定、用哪些 seed 测、以及 single-step 与 H=4 怎么对齐**。第一步已离线核实 L1 的 overhang 属最终目标偏移而非轨迹补偿（[review](day4-actionchunk-test/results/L1_OVERHANG_MECHANISM_20261102/review.md)）。第二步按“保留 L1 独立过折目标、L2/L3 保留各自已有目标”冻结定义；第三步（§7）把两种动作表示对齐到同一份目标、评价器与 seed 规则。

## 0. 冻结范围

| 已冻结（本步） | 未冻结（后续步骤） |
|---|---|
| 每档的初始状态生成参数与 seed 集合 | 成功判定的数值阈值 |
| 每档的 commanded 目标几何（place 目标、overhang、width、折向） | 正式批次规模与每格 20 个 held-out seeds 已登记（§5.1，2026-11-02），但尚未生成/运行 |
| 每档的 held gate 与运行断言（来自现有脚本）；H=4 的 waypoint 映射（第 3 步，见 §7） | — |
| 每档的评价器身份（现有实现） | 失败/拒绝率口径、reset/视频/图像验收（第 7 步） |
| 可执行代码身份：两份 SHA256 manifest | — |

**变更规则**：目标、评价器或 seed 集合的任何改动都是版本变更，必须同时（1）在本文新增条目并写明理由；（2）更新 `square-*-files.json` manifest；（3）在验收状态与日报里记录。不得在某一批运行中途改定义，也不得只改脚本不改文档。

## 1. 冻结的共同几何口径

- 布料：441 点、0.4 m 方巾，`pick_index` 由运行时的夹持槽位决定并记录在 `result.json`。
- cloth-local 帧：`q = R(yaw)^T (v - pick)`，`R = Rz(yaw)`；`pick` 是初始（L1）或恢复后（L2/L3）被夹持粒子的世界坐标。
- 折线：`fold_line_local_x = pick_local[0] + width`，`width = 0.2`；moving half 为折线靠 pick 一侧。
- 目标生成 `local_arc`：四个目标角 45°/90°/135°/180°，pick 系横向位移 `width*(1-cos θ)`，高度 `0.02*θ/π + width*sin θ`；`overhang` 只加在第四个（place）目标的横向上。因此 place 横向位移为 `2*width + overhang`（nominal 0.40 m，L1 为 0.42 m），`2*width` 恰好把 flap 自由边送到静止半远端边缘。
- 动作：每个 waypoint 一个公共 5D 动作 `[x, y, z, yaw, gripper]`，`grasp_to_ee(point, yaw) = point - Rz(yaw)Rx(π)@[0,0,0.0034]`，`orientation_euler(yaw) = [π, 0, yaw]`。
- 物理与运行环境（三档脚本内固定）：`bend_stiffness=100`、`particle_friction_scale=0`、`GARMENTLAB_ATTACHMENT_OVERLAP=0.005`、`GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0`。

## 2. 三档任务定义（冻结）

| 档 | 初态（固定） | 公共动作 | 折向 / width | overhang / place 目标 | held gate | 评价器 |
|---|---|---|---|---|---|---|
| L1 | flat，seeds 4100–4109，settle 120 | 7 | local +x（left），0.20 | **0.02**；place 横向 0.42（局部 x 0.22） | `held_error<0.01` | `fold_metrics_yaw` |
| L2 | perturbed：bottom 折条，seeds 4200–4209，settle 180 | 12（5+7） | left 默认，0.20 | 0；place 横向 0.40（局部 x 0.20） | `held_error<0.03` | 内联子集（见 §4.4） |
| L3 | crumpled：left 折条 width 0.20，seeds 4300–4309，settle 240 | 12（5+7） | left 默认，0.20 | 0；place 横向 0.40（局部 x 0.20） | `held_error<0.03` | 内联子集（见 §4.4） |

### 2.1 口径修正（本步核对脚本后）

此前 2026-11-02 的文档把 L2 的 “width 0.16–0.18” 写成**折形目标**。核对 `day4-recovery-fold-episode.py` 后确认：0.16–0.18 是**初态 bottom 折条的宽度**（`square-initial-plan.json` 中 4200–4209 的 `strips[0].width_m`），不是折叠目标。L2 与 L3 的 commanded 折形目标是同一个 nominal 20/20 左半折（`fold_width=0.2`、无 overhang、place 横向 0.40）。

因此正确的划分是：

- **L1 与 L2/L3 是不同折形任务**（过折 21/19 偏置拱形 vs nominal 20/20 对折）。L1 vs L2/L3 的成功率差异不得归因于“初态难度”。
- **L2 与 L3 是同一折形目标下的两种初态族**（bottom 折条 / left 折条），不是第三个折形任务。两者可比，但扰动方式与每 seed 条宽不同（L2 0.1615–0.1793，L3 固定 0.20），仍不构成受控难度梯度，也不产出“纯初态难度曲线”。
- 三档汇总只能称为**多任务平均**（L1 一个任务 + L2/L3 同一任务的两个初态族），不能称为难度曲线。

## 3. L1 冻结细节（`day4-l1-xfold-yaw-aware.py`，hash `0aab8e7c`）

**动作序列（7）**：`approach`(OPEN, pick+[0,0,0.15]) → `close`(CLOSE, grasp_to_ee(pick)) → `arc45` → `arc90` → `arc135` → `place`(均 HOLD) → `release`(OPEN)，随后 `StableHold` 60 步、30 个 release tick、`settle(180)`。

**目标**：`local_arc(grasp_pick, yaw_measured, [1,0,0], 0.20, overhang=0.02)`；`target_reference_local = pick_local + 2*width + overhang`（= 0.22）。overhang 只影响 `index==3`（place）。

**yaw**：`measure_yaw(local_points, initial)` 测静置布料的绝对 yaw；`|yaw_measured - yaw_case| ≤ 0.02 rad`，超限即失败。不做 IK 重试、不改目标。

**运行断言（全部为硬失败）**：

| 断言 | 阈值 | 位置 |
|---|---|---|
| 初态 `passed` 且 `level == flat` | — | 启动 |
| 测量 yaw 与初态 yaw 之差 | ≤ 0.02 rad | 折叠前 |
| grasp 后 pick 点位移 | ≤ 0.01 m | arc 前 |
| `held_error`（EE vs place 目标） | < 0.01 m | 保持末 |
| 臂速（前 7 关节） | < 0.1 rad/s | 保持末 |
| `reach` 与锚点单点间隙 | reach 成立、≤ 0.01 m | 保持末 |
| 动作数 | `== 7` | 结束 |
| `moving_half_crossed_fraction` | ≥ 0.5 | 结束 |
| 结束时无残留 attachment | — | 结束 |

**开发复验的实测构型（描述性，不是成功阈值）**：place 到位误差 −0.1…−2.3 mm；最终 flap 自由边行均值越出静止半远端边缘 39.1–40.2 mm（4108 为 36.6），单顶点最大口径 49–52 mm；自由边落桌面（0.1 mm）；拱高 62.2–63.4 mm；最终 IoU 0.365–0.423；`z_p95` 67.5–67.7 mm；对称对齐 13.8 mm；held 误差 ≤4.1 mm。

**限制（必须与定义同时引用）**：零扰动控制例（seed 0、overhang 0）用名义目标也能保持（自由边悬空 17.1 mm、拱高 63.4 mm、IoU 0.57）。因此 L1 过折是“把 10 个随机 flat 初态收敛到同一个自由边落桌面的稳定构型”，**不是修复了机器人能力缺陷**。

## 4. L2/L3 冻结细节（`day4-recovery-fold-episode.py`，hash `ddad4116`）

**动作序列（12，顺序固定）**：
`rec_approach`(OPEN, current+[0,0,0.12]) → `rec_pick`(CLOSE) → `rec_lift`(HOLD, +0.08) → `rec_spread`(HOLD, flat_pick+[0,0,0.03]) → `rec_release`(OPEN) → `settle(240)` → `fold_approach`(OPEN, pick+[0,0,0.15]) → `fold_close`(CLOSE) → `fold_arc45` → `fold_arc90` → `fold_arc135` → `fold_place`(均 HOLD) → `fold_release`(OPEN)，随后 30 个 release tick、`settle(180)`。

**recovery 目标**：由初态 `strip_records[label='strip_start']` 的 `pick_index / pick_world` 决定，不用随机数。

**折形目标**：`fold_width = 0.2`，`local_arc(pick, fold_yaw, [±1,0,0], 0.20)`，无 overhang。
- 折向 left（默认）：`lateral_local = [+1,0,0]`，`pick_index = 210`，moving half 为 `local_x < fold_line`。
- 折向 right（fallback）：`lateral_local = [-1,0,0]`，`pick_index = 230`，moving half 镜像。right 是同一 nominal 目标的镜像，不是另一个折形。

**yaw**：`fold_yaw = yaw_case + atan2(R_rec)`，其中 `R_rec` 是 `flat_settled` → 恢复后布料的 2D 刚体拟合旋转（两者都是世界坐标，`flat_settled` 已含初态 yaw）。即取恢复后布料的实测世界 yaw；L2/L3 **没有** L1 那样的 yaw 偏差断言（恢复过程本身会小幅旋转：开发例 4200 为 +0.14°、4300 为 −2.0°）。注意：L3 4300 的 2° 说明初始 yaw 版本存在 2° 的折线偏差，改用 recovered-yaw 后该偏差消除；L2 4200 的 0.14° 则不足以解释它从旧版通过变为 recovered-yaw 版回弹（crossed 1.0 → 0.0）。两例的回弹本身在冻结定义下都按失败记录，见 §4.1–§4.2。

**运行断言（硬失败）**：

| 断言 | 阈值 |
|---|---|
| 初态 `passed` 且有 `strips` | — |
| recovery 后相对 `flat_settled` 的刚性残差 | 仅记录，不设阈值（开发例 8.0–8.6 µm） |
| `fold_held_check.position_error_m` | < 0.03 m |
| 臂速（前 7 关节） | < 0.1 rad/s |
| `reach` 与锚点单点间隙 | reach 成立、≤ 0.01 m |
| 动作数 | `== 12` |
| `crossed_fraction` | ≥ 0.5 |
| 结束时无残留 attachment | — |

### 4.1 冻结定义下的当前实测（开发例，不是验收）

| 例 | 折向 | 结果 | crossed | 最终 extent | z_p95 | held 误差 |
|---|---|---|---|---|---|---|
| L2 4200（`103502`） | left（**初始 yaw 旧版**） | 通过 | 1.0 | 0.232×0.421 | 0.0677 | 15.0 mm |
| L2 4200（`115933`） | left（recovered-yaw，冻结版） | **失败** | 0.0 | 0.442×0.442 | 0.0099 | 15.0 mm |
| L2 4200（`151711`） | right | 通过 | 1.0 | 0.227×0.421 | 0.0691 | 14.5 mm |
| L3 4300（`104603`/`113247`） | left（冻结版） | **失败** | 0.0 | 0.458×0.458 | 0.0099 | 15.0 mm |
| L3 4300（`114705`） | right | 通过 | 1.0 | 0.245×0.428 | 0.0691 | 14.5 mm |

`103502` 早于 recovered-yaw 修正，**在冻结定义下不可复现为通过**，只能作为历史记录。

两例 left 回弹的归因不同，不能合并表述：

- L3 4300：恢复前后 yaw 变化 −2.0°，初始 yaw 版本因此带有 2° 的折线偏差；改用 recovered-yaw 后该偏差消除，但例 `113247` 仍回弹（crossed 0.0），所以回弹本身未定因（另一个怀疑是 recovery 与 fold 共用左槽位）。
- L2 4200：yaw 只变 +0.14°，不足以解释 crossed 1.0 → 0.0；且 L2 的 recovery 用 bottom 槽位、fold 用未使用的 left 槽位，不存在共用槽位问题。**2026-11-02 的冻结版配对（§7.1）把这条收紧**：single 与 arc4 两例在同一初态上再次失败且逐字节相同，说明该失败在冻结版下**可复现**，不是运行间随机差异；与旧版通过例（`103502`，初始 yaw 版）的差异仍是版本相关、原因未隔离（旧版到冻结版同时改了 yaw 与其它代码），因此仍按失败记录，不得写成“yaw 修正导致”。

### 4.2 折向选择的冻结状态

冻结的默认折向是 left（脚本默认值），right 是镜像 fallback。当前证据（冻结版）是 left 在 4200/4300 恢复后释放即摊平、right 两例均通过。因此：

- 若正式批次沿用 left，4200/4300 这类例会在正式分母里记为失败；
- 若正式批次改用 right，属于**新建一个冻结变体**，需按 §0 的变更规则记录，且 single-step 与 H=4 必须用同一个折向；
- 不得把 left 记为失败后在同一 seed 上补跑 right 并把补跑算作该格成功——补跑是独立尝试，进入同一格分母。

### 4.3 恢复语义的影响

L2/L3 的 recovery 是“把已成折条的初态展平，再折一次”。因此 L2/L3 的最终形状固定包含一次 recovery 展开（`particle_friction_scale=0`，展平后完全平铺，z extent ≈6e-8），这与 L1 的单次抓取折叠不同。报告时必须写清 L2/L3 的成功包含 recovery 成功。

### 4.4 评价器收口（第 3 步已完成）

原先的问题是：L1 用 `fold_metrics_yaw`（crossed、反射目标误差、对称对齐、粒子占据 IoU、z_p95），L2/L3 只内联算 `moving_count / crossed_fraction / extent / z_p95`，没有 IoU 与反射目标误差；若 single-step 用内联、H=4 用另一份代码，两边就不可比。

第 3 步的处理（**不是新指标**，是把已有指标统一到同一份代码上）：

1. `l1_yaw_fold_geometry.fold_metrics_yaw` 增加 `lateral_local` 参数（`+x` left / `-x` right），默认值保证 L1 结果逐位不变；默认路径在 15 个 L1 目录上复算，IoU 0.365–0.423、对齐 13.8 mm 与内联值完全一致。
2. 新增离线评价器 `stage4_fold_metrics.py`：从已下载目录的 `00_initial.npz / 06_final_3s.npz`（L1）或 `recovered.npz / final.npz`（L2/L3）复算同一函数，并把内联值与复算值逐项交叉校验（crossed、moving_count 要求完全相等；extent、z_p95 容差 1e-6）。任何不一致是错误，不是警告。
3. 评价器身份自校验：`stage4-evaluator-files.json` 记录 `l1_yaw_fold_geometry.py` 与 `stage4_fold_metrics.py` 的 SHA256；评价器每次运行先校验自身文件，哈希写进 `metrics_full.json`。没有这份 manifest 就拒绝打分。
4. 结果：4 个 L2/L3 冻结版目录已用 `fold_metrics_yaw` 重算（left 失败例 IoU 0.015；right 通过例 IoU 0.559–0.563、对齐 8.49 mm、反射误差 19.4–20.0 mm、z_p95 0.0691），2 个 recovered-yaw 之前的历史目录因缺 `fold_yaw` 跳过。L1 的 15 个目录同样重算，15/15 与内联一致。

所以从现在起，"评价器"在三种表示/两个任务间是同一份代码；评价器升级若要再改，属于 §0 的版本变更，必须对两种表示、所有 seed 同时生效。

## 5. Seeds 与数据划分

**开发集（现有 30 个初态，已生成并审查）**：

| 档 | seeds | level | yaw 范围 | settle | 初态附加参数 |
|---|---|---|---|---|---|
| L1 | 4100–4109 | flat | −0.1488…+0.1381 rad | 120 | 无 |
| L2 | 4200–4209 | perturbed | −0.1155…+0.1621 rad | 180 | bottom 折条 0.161505–0.179284 m |
| L3 | 4300–4309 | crumpled | −0.3231…+0.3469 rad | 240 | left 折条 0.20 m |

**测试集规则（冻结）**：

1. 正式批次每格 20 个 held-out seeds，**与上表开发 seeds 不重叠**（计划 §5.8）。
2. 同一档内，single-step 与 H=4 使用**完全相同**的 seed 列表与初态目录。
3. seed 列表在正式批次开始前一次性固定并写入文档；批次中途不得替换、跳过或按结果重抽。
4. 初态生成脚本与参数（`day4-square-initial-stripfold.py`、`square-initial-plan.json`）冻结，测试 seeds 的初态目录必须在批次前生成、审查并留存哈希。

**未定项**：正式成功判据的数值阈值（成功率口径、alignment/overlap 阈值、测量时刻）。正式 Stage 4 成功仍为 **0**；本文件里的 10/10（L1 开发复验）、2 个 right 例等均为开发结果，不构成任何一档的正式成功。

### 5.1 第 7 步登记：held-out seed 集合（2026-11-02，未运行）

按 §0 的变更规则登记：

1. **seed 集合**：L1 `4110–4129`、L2 `4210–4229`、L3 `4310–4329`，每档 20 个，与开发集不重叠。取各档紧邻的连续区间，在任何结果出现前固定，批次中途不得替换、跳过或重抽。
2. **初态参数**：dx、dy、yaw 仍为 `default_rng(seed)` 的前三次抽样（该规则对全部 30 个开发条目逐位复现，容差 1e-15）；L2 条宽为该 seed 流第 4 次抽样 `U(0.16, 0.18)` 取 6 位小数（开发条宽是人工值，无法由 seed 流复现，此处改用按范围抽样并逐条写入）；L3 条宽固定 0.20。
3. **生成前置**：`square-initial-plan.json` 由 30 条扩展为 90 条（新增 60 条，开发条目不变），两个初态 runner 的 seed 区间断言相应放宽。旧/新 LF 归一化哈希与远端更新顺序见 [2026-11-02-GarmentLab日报-Stage4-正式批次计划.md](2026-11-02-GarmentLab日报-Stage4-正式批次计划.md)。
4. **影响面**：两份折叠 manifest 与折叠脚本不变；变的是初态生成侧（plan 与两个初态 runner），因此新 manifest 只用于初态生成，折叠代码身份保持原值。
5. **未完成**：成功判据阈值仍未冻结，因此本集合跑完只产出开发门槛 `passed` 与拒绝率，不直接产生正式成功。

## 6. 代码与文件身份

两份 manifest 由 runner 在远端运行前逐文件校验：

| manifest | 覆盖 | 关键条目（SHA256 前 12 位） |
|---|---|---|
| `day4-actionchunk-test/square-l1-xfold-yaw-files.json` | L1 7 动作链路 | `day4-l1-xfold-yaw-aware.py` `0aab8e7cd42f`；`l1_yaw_fold_geometry.py` `aa1f8a6e3ede`；`run-l1-xfold-yaw-aware.sh` `560d38bbb083` |
| `day4-actionchunk-test/square-recovery-fold-files.json` | L2/L3 12 动作链路 | `day4-recovery-fold-episode.py` `ddad4116ad33`；`run-recovery-fold-episode.sh` `41026c913f12`；`strip_prepared_control.py` `49075fb4bf90` |
| `day4-actionchunk-test/stage4-evaluator-files.json` | 离线评价器 | `l1_yaw_fold_geometry.py` `aa1f8a6e3ede`；`stage4_fold_metrics.py` `8d1f31591c1c` |

2026-11-02 在本地逐条复核：两份 manifest 的每个条目都能由仓库文件复现，差异只是 Windows 检出与远端上传之间的 CRLF/LF 行尾（归一化后内容一致）。初态侧另有 `day4-square-initial-stripfold.py`（`178ab10c0851`）与 `square-initial-plan.json`（`e2cfaebe597e`）决定 seeds 与条宽；这两个文件也应纳入下一版 manifest。

第 3 步加固：两个折叠脚本启动时会把**自己的** SHA256 与 manifest 条目比对（上传漏文件或 manifest 未更新即当场失败），并把整份 manifest 写进 `result.json` 的 `code_files`。离线评价器同样先校验自身哈希。`stage4_representation_audit.py`（`8c31c2f9e7b4…`）只做配对审计，不参与打分，因此不入 manifest。

## 7. 表示层映射（第 3 步：实现、冻结与开发配对结果）

**冻结的 chunk 映射**：只有四个 arc 目标被合成一个 H=4 chunk；抓取/释放等精度关键步一律 H=1。这是延续更早下降控制里 `[1,1,4,1,1,1]` 的“精度步不 chunk”原则。

| 任务 | 动作数 | single-step `call_horizons` | H=4 `call_horizons` | chunk 内容 |
|---|---|---|---|---|
| L1 | 7 | `[1,1,1,1,1,1,1]` | `[1,1,4,1]` | `approach`, `close`, **`arc45…place`（4）**, `release` |
| L2/L3 | 12 | `[1]*12` | `[1]*7+[4,1]` | 5 recovery + `fold_approach` + `fold_close`（各 1），**`fold_arc45…fold_place`（4）**, `fold_release` |

两种表示共用同一组目标，**按构造相同**而不是按数值拟合：

- 目标只在一个位置计算：L1 在 `close` 之后、用实测 `grasp_pick` 算 `local_arc`；L2/L3 在 `fold_approach` 之前、用恢复后布料算 `local_arc`。single 与 H=4 走同一条计算路径，chunk 只是把这四个已经算好的 pose 一次发出去。
- chunk 内**不再重规划**：四行按顺序开环执行，`executed_steps` 必须等于 4。**注意（第 3 步实测修正）**：两种模式在 waypoint 之间都不消费观测——四个目标都是提前算好的，single 模式在调用之间也只读状态、不回灌控制。因此 H=4 只改变公共调用边界，不改变控制序列；实测两模式逐字节相同（见 §7.1），不能把这次配对说成“验证了降低反馈频率的效果”。
- 每行仍带 gripper 命令（HOLD），`grasp_to_ee` / `orientation_euler` 不变，公共 5D 动作契约不变。

**脚本与结果记录**：

- 两个脚本新增 `--execution {single,arc4}`，默认 `single`；默认路径的调用序列、目标与断言不变（L1 的 `03_arc45…03_place` 快照仍在，H=4 只保留 `03_place`）。
- `result.json` 记录 `execution_mode`、`call_horizons`（逐次调用预算）、`chunks`（label / 4 行 label / 4 个 target / response）、每行的 `chunk_label / chunk_index / chunk_size / row_in_chunk / ee_scope='after_chunk'`，以及 `code_files`。
- 硬断言：`sum(call_horizons) == action_count`（7 或 12）；`chunk` 数在 single 下为 0、arc4 下为 1；chunk 的 4 个 `targets` 必须与对应四行的 `target_pose` 逐位相等；`response['executed_steps'] == 4`。runner 再做一遍同样的检查。
- 单行状态（`ee`、`step`、`block_error_m`）在 H=4 下描述的是**整个 chunk 结束时**的状态，用 `ee_scope` 标明；不得把 chunk 内 4 行当成 4 个独立闭环点。

**配对审计** `stage4_representation_audit.py`：给一对 `single/arc4` 目录，检查三件事——(1) 用每例自己记录的 `grasp_pick` / `fold_yaw` / width / overhang 复算四个目标，两例都必须逐位复现（同一个目标规则），并报告两例之间实测 pick 差与目标差；(2) 两边都由 `stage4_fold_metrics.py` 打分且其文件哈希一致；(3) seed / level / 初态目录 / 折向 / width / overhang / `code_files` 完全相同。任一条不满足即 `PAIR_NOT_COMPARABLE`（返回非零）。

**实现状态（已全部完成）**：

- `--execution` 实现与断言、两个 runner 的透传与检查、两份 manifest 与评价器 manifest 刷新、评价器统一与自校验、审计工具，均已完成本地校验（`py_compile`、`bash -n`、合成配对正反例）。
- 远端配对已在两个任务上各跑一对：L1 seed 4100、L2 seed 4200（left），结果见 §7.1。
- 配对审计要求两个目录都记录 `execution_mode` 与 `code_files`，因此**此前下载的 single-step 目录不能直接配对**（缺这两个字段，审计会判 `PAIR_NOT_COMPARABLE`）。single 侧必须用本版脚本重跑；这正是“同代码身份”的含义，不是额外要求。
- 正式测试 seeds（每格 20 个 held-out）仍未选定；选定后两种表示必须共用同一份 seed 列表，这一点在 §5 已冻结。

### 7.1 第 3 步配对实测（2026-11-02 运行，开发例，不是验收）

四例均由用户在远端运行、下载后本地重算与审计：[完整报告与日志](../thesis/day4-actionchunk-test/results/STAGE4_REPRESENTATION_PAIRS_20261102/review.md)。

| 任务 / seed | 模式 | 动作数 | `call_horizons` | 开发 `passed` | crossed | IoU | 对齐 mm | 反射误差 mm | z_p95 mm |
|---|---|---|---:|---|---|---:|---:|---:|---:|---:|
| L1 / 4100 | single | 7 | `[1]*7` | true | 1.000 | 0.3747 | 13.8198 | 44.6166 | 67.6491 |
| L1 / 4100 | arc4 | 7 | `[1,1,4,1]` | true | 1.000 | 0.3747 | 13.8198 | 44.6166 | 67.6491 |
| L2 / 4200 | single | 12 | `[1]*12` | false | 0.000 | 0.0150 | 115.2391 | 222.6952 | 9.9000 |
| L2 / 4200 | arc4 | 12 | `[1]*7+[4,1]` | false | 0.000 | 0.0150 | 115.2391 | 222.6952 | 9.9000 |

复核结果（本次独立核对，不只是照抄报告）：

- 两对都是 `PAIRS_COMPARABLE`：目标规则按各自实测 pick/yaw 逐位复现；调用结构、seed/初态、常量、`code_files`、评价器哈希全部一致；评价器哈希为 `l1_yaw_fold_geometry.py` `aa1f8a6e…`、`stage4_fold_metrics.py` `8d1f3159…`。
- 四例 `result.json` 的 `code_files` 与当前本地两份 manifest **逐条相等**（24 / 21 项，零差异），确认远端跑的就是冻结代码。
- 下载核验 19 + 16 + 9 + 9 = 53 个文件哈希一致。L1 的 arc4 目录按设计少 3 个中间快照（`03_arc45/90/135.npz`），只保留 `03_place.npz`。

**最关键的事实：同一对内所有可比快照逐字节相同**（L1 的 `00_initial / 01_approach / 02_close / 03_place / 03_hold_end / 04_released / 05_release_stationary / 06_final_3s`；L2 的 `recovered / final`）。所以五项指标差为 0 不是“数值上近似”，而是**同一条轨迹**。原因已在实现层确认：后端 `execute()` 对 chunk 逐行调用同一个 `control.move`，两种表示发出的是同一串调用，且都不在 waypoint 之间消费观测。

由此得出的结论边界：

- 第 3 步的要求（同一目标、同一评价器、同一 seed、同一代码身份）**已满足并已核对**，这是后续任何“single vs H=4”比较的前提。
- 但本实验**测不到表示效应**：它证明的是专家轨迹在两表示下等价，不是“H=4 降低了闭环反馈所以效果更好/更差”。关于 H=4 的实质问题发生在**有策略在 chunk 边界做决策**的场景（BC 策略每 H 步决策一次），属于后续 BC 阶段，不能用这次专家配对代替。
- 若后续开发 seed 同样逐字节相同，逐 seed 复跑的信息量为零；是否只在部分 cell 上保留表示配对（省算力）属于计划变更，需按 §0 规则先写文档再执行。

**L2 / 4200 left 的性质**：held gate 通过（15.0 mm、锚点间隙 2.2 mm）、chunk 执行 4 步正确，失败发生在释放之后——最终 extent 0.4424、`z_p95` 9.9 mm，布料完全摊平，即此前记录的 left 回弹。single 与 arc4 表现一致。这也修正了 §4.1 的一处措辞：该失败在冻结版下是**可复现的**，不是运行间随机差异。

**解读限制（保留）**：两对只各覆盖一个 seed；L2 只覆盖 left；本次只报表示效应，不计算成功率，不构成任何一档的正式成功；正式 Stage 4 成功仍为 0。H=4 的失败率不得并入单步成功率，也不得用三档 H=4 结果去谈初态难度。

## 8. 交叉引用

- 第 3 步配对实验报告：[STAGE4_REPRESENTATION_PAIRS_20261102](../thesis/day4-actionchunk-test/results/STAGE4_REPRESENTATION_PAIRS_20261102/review.md)（四例结果、审计输出、逐文件哈希清单）
- 第 4 步分任务报告：[STAGE4_PER_TASK_20261102](day4-actionchunk-test/results/STAGE4_PER_TASK_20261102/review.md)（两任务各自的冻结版/开发历史成功率、失败形态、多任务平均口径与版本边界）
- 第一步机制核实与判据：[results/L1_OVERHANG_MECHANISM_20261102/review.md](day4-actionchunk-test/results/L1_OVERHANG_MECHANISM_20261102/review.md)
- 决策与三档口径：[2026-11-02 日报](2026-11-02-GarmentLab日报-Stage4-L2L3初态与6b交接.md)、[验收状态](DAY4_ACCEPTANCE_TRACKER.md)
- 后续步骤与正式批次要求：[DAY4_NEXT_STEPS.md](DAY4_NEXT_STEPS.md)
- 计划中的冻结原则：[执行计划 §5.4](Marian_Frei_GarmentLab_2024_10_stage_execution_plan.md)
- 接口与动作预算规范：[DAY4_INTERFACE_RECOVERY_CONTRACT.md](day4-actionchunk-test/DAY4_INTERFACE_RECOVERY_CONTRACT.md)


## 2026-11-02 right 开发变体登记 b-right-dev-v1

按 §0 和 §4.2，在新结果出现前登记独立 right 变体，理由是冻结 left 在 4200/4300 可复现地释放后摊平；本变体只验证镜像折向下的释放后保持，不替换 left 的失败结果或默认定义。

- 固定矩阵：L2 4200（023311-548690）single → arc4；L3 4300（074349-406408）single → arc4，共四次；每档只一个开发 seed。每对复用原初态目录，完整失败仍保留，不调参重跑替换。
- 固定目标：right，pick_index=230，lateral_local=[-1,0,0]，width=0.20 m，overhang=0；两表示目标规则、评价器、物理、held gate、12 动作及释放采样时序不变。
- 采样时刻：OPEN 后 30 release ticks + settle(180) 的 final.npz。仅检验这一既有终态窗口；没有独立退让或第二个 retention 样本，不声称更长期保持。
- 使用已有未修改的 run-recovery-fold-episode.sh / day4-recovery-fold-episode.py；新增限制开发目录的 run-recovery-fold-right-v1.sh、配置 stage4-b-right-dev-v1.json 和独立 manifest square-recovery-fold-right-v1-files.json（原21项代码身份+2项变体配置/入口）。原 left manifest 与折叠引擎不改。variant_identity.json 另存变体身份和初态文件哈希。
- 既有开发检查：held gate 通过、crossed>=0.5、12个公共动作、无残留 attachment；不新增正式成功阈值。冻结评价器重算终态指标，single/arc4 另做配对审计。
- held-out 4110–4129 / 4210–4229 / 4310–4329 不生成、不运行；正式批次暂停，正式 Stage 4 成功仍为 0。是否扩大开发 seed 覆盖或正式采用 right，须以后续证据另行登记。

变体配置 SHA256：`37b1dfbafd63ee8d26d9826ac3f56214f55906a65c39c654aed2249737c0387f`。
变体 manifest SHA256：`9b105cf60607bce8d98c8111018a659aabdfc0c3673050573f1bd54a26dc095d`。
底层 manifest SHA256：`cb947b85c4d5acdaf2028cfcbde8eb3743158d3868e9ca082e85994beadb73b1`。


## 2026-11-02 right 验证执行分工更新（用户指定）

用户明确指定“另一聊天继续；本聊天只下载和审计其结果”。本聊天已停止自动提交控制器，之后不再提交 GPU 实验；此前已在途进程不终止。L2 4200 right single/arc4 已下载并通过原版 PAIRS_COMPARABLE，crossed均1.0、IoU约0.559；L3等待外部结果，尚不宣称验证完成。

后续下载保留外部结果的真实来源，核对同一初态、right、seed、execution_mode与21项底层代码身份；未经过本变体入口的外部结果不伪造23项wrapper身份。优先按目录启动时间选取结果，不按passed筛选；额外或失败尝试原样留存。并发运行不作耗时比较。held-out不运行，正式成功仍为0。


## 2026-11-02 b-right-dev-v1 开发复验与移交后审计完成

汇总器缺失结果分母修复与8项离线测试已通过；原项目代码与已测试副本SHA256一致（9a757d34…）。一次通过+一次无结果error的合成回归输出2次尝试、50%拒绝率；空批次保持null。

L2 4200的right single/arc4由本聊天在移交前完成；L3 4300采用另一聊天产出的最早外部single/arc4，按目录启动时间选择而非passed。两对均通过原版PAIRS_COMPARABLE，四份选定结果held gate通过、crossed=1.0，L2 IoU=0.559091、L3 IoU=0.562997；各对目标差及五项指标差值精确为0。底层21项代码不变，四份结果的独立23项变体manifest、配置和初态文件哈希均核对一致。

共下载核验66个远端文件，包含6份完整开发结果：选定4份配对结果与2份额外L3 single重复尝试。额外尝试原样保留，不增加独立seed覆盖，不计算正式成功率。用户移交后本聊天仅下载审计，未再提交GPU仿真，未终止已在途远端进程。

结论仅为每档一个开发seed在OPEN后30 release ticks+settle(180)终态保持；没有独立退让、第二retention样本或长期稳定性验证，不能外推整个开发集/held-out，更不能解释为BC策略或H=4性能提升。right为独立变体，不替换left失败或默认定义。held-out与正式批次保持暂停，正式Stage 4成功仍为0。

完整报告：[right开发复验与移交后审计](../thesis/day4-actionchunk-test/results/TASK_B_RIGHT_DEV_V1_20261102-183740/review.md)。

## 2026-11-02 right 开发验证结果（b-right-dev-v1，开发验证，非正式成功）

按上面的登记矩阵执行完毕：4200/4300 × single/arc4 四例全部 `passed=true`、held gate 通过、12 个公开动作、`errors=[]`。终态 crossed=1.0；L2 4200 extent 0.227265 × 0.421146 × 0.061256、z_p95 0.069068；L3 4300 extent 0.244623 × 0.427518 × 0.061217、z_p95 0.069078。同档 single 与 arc4 的 12 个公开动作（label / target_pose / command）、终态顶点与全部指标逐位相同。

补充核对把主审计未采用的 4200 arc4（`025355-106410`）和 4300 single 重复（`031535-711404`）一并纳入，5 个目录 77 项检查全部通过；同 seed 全部 7 次已下载尝试（4200 三例、4300 四例）的 `final.npz` 441 个顶点逐位相同。未新增 seed，未改任何阈值。

主审计：[TASK_B_RIGHT_DEV_V1_20261102-183740](../thesis/day4-actionchunk-test/results/TASK_B_RIGHT_DEV_V1_20261102-183740/review.md)；补充审计：[B_RIGHT_DEV_AUDIT_SUPPLEMENT_20261102](../thesis/day4-actionchunk-test/results/B_RIGHT_DEV_AUDIT_SUPPLEMENT_20261102/review.md)。

边界：每档仅一个开发 seed；只检验 OPEN 后 30 release ticks + settle(180) 的终态，无第二 retention 样本；right 是独立变体，不替换 left 失败或默认定义；held-out 未生成、未运行，正式批次暂停，正式 Stage 4 成功仍为 0。

## 2026-11-02 right 开发覆盖扩展登记 b-right-dev-v2（未运行）
按 §0 和 §4.2 登记。理由：v1 只在 4200/4300 验证 right，需确认不是初态特定的巧合。本批只扩大**开发覆盖**，不改任务定义、不改阈值、不触碰 held-out。

- 矩阵：L2 4201–4209、L3 4301–4309，每个 seed 一个初态 + 一次 right single 折叠，共 18 个初态 + 18 次尝试。只跑 single：single/arc4 在 4200/4300 的 12 个公开动作目标、后端指令与终态顶点已逐位相同，表示等价不需要逐 seed 重复。

- 目标与口径不变：right、pick_index=230、lateral_local=[-1,0,0]、width=0.20 m、overhang=0、12 个公开动作、held gate、采样 OPEN + 30 release ticks + settle(180 perturbed / 240 crumpled)。

- 初态登记规则：批次先运行 `run-square-initial-stripfold.sh <seed>`，把结果目录连同 `result.json`、`initial_geometry.npz` 的 SHA256 写入 `stage4-b-right-dev-v2-initials.json`（只追加、原子写）；折叠入口只接受 registry 中的目录并每次复核哈希。初态身份在折叠发生前固定，不能事后替换或挑选。

- 失败策略：`passed=false` 记一行 rejected 并继续；初态生成失败或缺结果目录视为基础设施错误并停止整批；不自动重试、不覆盖旧结果；中断后重跑按 attempts 跳过已有结果目录的 seed，强制重跑须换新 tag。

- 文件与哈希：变体配置 `91c0fe7f…`（A1 v2.1 修正 sampling 描述）、入口 `3822bd98…`、独立 23 项 manifest `c3e34c91…`（A1 刷新 config 条目）、批次驱动 `d4c00162…`；21 项底层身份 `cb947b85…` 不变。旧值 `adf4c9a8…` / `2fff0bf9…` 保留在 A1 报告中。详见 [扩展计划](2026-11-02-GarmentLab日报-Stage4-B项right扩展计划.md) 与 [A1 预检](day4-actionchunk-test/results/STAGE4_A1_PREFLIGHT_20261102/review.md)。

- 禁止：held-out 4110–4129 / 4210–4229 / 4310–4329 不生成、不运行；不把本批 `passed` 当正式成功；不据此自动采用 right 或替换 left。

- 状态：A1 预检完成（48/48，仅离线），未运行任何 seed；A2 待启动。正式 Stage 4 成功仍为 0。
