# Stage 4 第 4 步：分任务报告（开发例，不是验收）

日期 2026-11-02。汇总已下载的开发运行，按**两个折形任务**分开报告：A = L1 独立“过折”折形；B = L2/L3 nominal 20/20（同一任务下的两种初态族）。single-step 与 arc4 作为任务内的表示列并排给出。

**本报告不产生任何正式成功。** 没有任何一条是正式成功：L1 脚本的记录里 `formal_day4_success` 均为 false，L2/L3 脚本没有该字段（其 `passed` 同样只是开发门槛）。正式 Stage 4 成功仍为 0。开发运行 `passed=true` 只说明通过了该脚本的开发门槛（交叉覆盖 ≥0.5、held gate、释放后静置），不等于验收。

## 0. 判据、数据与复算

- 成功判据：各脚本 `result.json` 的 `passed`；失败一律保留原始 `errors`。不新增、不放宽任何阈值。
- 数据来源：`day4-actionchunk-test/results/`、`thesis/day4-actionchunk-test/results/` 及其下的 `TASK_B_SINGLE_EVIDENCE_20261102-173708/` 中已下载的 `day4-l1-xfold-yaw-aware-*`、`day4-recovery-fold-*` 目录，共 27 条可用结果（另有 1 条 `112937-225297` 未写 `result.json`，不计入）。
- 指标来源：全部 27 条都用统一评价器 `stage4_fold_metrics.py` 复算（`--no-write`）：L1 17/17、L2/L3 8/10 成功复算；在两边都有的字段上与内联指标一致（crossed / moving_count 精确相等，extent / z_p95 容差 1e-6，不一致会报错退出）——L1 的 IoU / 对齐 / 反射误差两边都有，L2/L3 只有 crossed/extent/z_p95 可交叉核对。剩余 2 条 pre-recovered-yaw 目录没有 `fold_yaw`，评价器按设计 `SkipEpisode`，只有内联的 crossed/extent/z_p95。下表列出的 IoU / 对齐 / 反射误差均为复算值。
- 汇总脚本与原始表：

```powershell
cd E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test
python -I stage4_task_report.py --root results --root ..\..\thesis\day4-actionchunk-test\results --root ..\..\thesis\day4-actionchunk-test\results\TASK_B_SINGLE_EVIDENCE_20261102-173708 --out results\STAGE4_PER_TASK_20261102\task_report.json
```

`task_report.json` 记录每一行的目录名、seed、折向、代码身份（是否有 `code_files`）、动作数、指标与失败分类，本文所有数字都可从它复算。汇总脚本 `stage4_task_report.py` 的 SHA256 为 `af38df35…`；它是离线分析工具，不进入任何运行 manifest，也不改变实验代码身份。

## 1. 任务 A：L1 过折（7 动作，width 0.20，place 沿折向多伸 2 cm）

### A1. 折形对照：基线（overhang 0）vs 过折（0.02）

| 条件 | seeds | 通过 | crossed | IoU | 对齐 | 反射误差 | z_p95 |
|---|---|---:|---:|---:|---:|---:|---:|
| 基线 overhang 0（旧版 single；目录未记录 `fold_overhang_m`，place 横向目标 0.40 对过折的 0.42） | 4100 / 4105 / 4107 | **0/3**（4100 另重复 1 次也失败，共 0/4 次尝试） | 0.000 | 0.0150–0.0152 | 115.2 mm | 224.0–225.2 mm | 9.9 mm |
| 过折 0.02（旧版 single） | 4100–4109 | **10/10** | 1.000 | 0.3646–0.4226 | 13.8 mm | 39.9–45.0 mm | 67.5–67.7 mm |

基线失败形态统一：held gate 通过（0.2–3.6 mm），释放后整片回弹（crossed 0、z_p95 9.9 mm、IoU 0.015 说明最终占据与折叠目标几乎不重合）。这不是“抓取/保持失败”，而是释放后的稳定性失败。零扰动对照（seed 0，overhang 0）通过（IoU 0.5702、对齐 7.1 mm），说明 overhang 不是唯一能保持的折法；它不计入 4100–4109 的成功率。

### A2. 过折 10 例逐 seed

| seed | crossed | IoU | 对齐 | z_p95 | held 位置误差 | 动作数 |
|---|---:|---:|---:|---:|---:|---:|
| 4100 | 1.000 | 0.3747 | 13.8 mm | 67.6 mm | 0.3 mm | 7 |
| 4101 | 1.000 | 0.3646 | 13.8 mm | 67.7 mm | 4.1 mm | 7 |
| 4102 | 1.000 | 0.3714 | 13.8 mm | 67.5 mm | 2.3 mm | 7 |
| 4103 | 1.000 | 0.3700 | 13.8 mm | 67.5 mm | 3.6 mm | 7 |
| 4104 | 1.000 | 0.3726 | 13.8 mm | 67.5 mm | 3.5 mm | 7 |
| 4105 | 1.000 | 0.3743 | 13.8 mm | 67.5 mm | 1.0 mm | 7 |
| 4106 | 1.000 | 0.3766 | 13.8 mm | 67.5 mm | 0.3 mm | 7 |
| 4107 | 1.000 | 0.3711 | 13.8 mm | 67.5 mm | 4.1 mm | 7 |
| 4108 | 1.000 | 0.4226 | 13.8 mm | 67.5 mm | 0.1 mm | 7 |
| 4109 | 1.000 | 0.3739 | 13.8 mm | 67.5 mm | 1.6 mm | 7 |

所有 10 例的 commanded 折形相同（width 0.20、overhang 0.02、place 横向 0.42），指标差异只来自初始位姿改变机械臂路径后的自由构型微差。

### A3. 冻结代码下的 single 与 arc4（seed 4100）

| 表示 | `call_horizons` | 通过 | crossed | IoU | 对齐 | z_p95 | 与另一侧 |
|---|---|---:|---:|---:|---:|---:|---|
| single | `[1,1,1,1,1,1,1]` | 1/1 | 1.000 | 0.3747 | 13.8 mm | 67.6 mm | 快照逐字节相同 |
| arc4 | `[1,1,4,1]` | 1/1 | 1.000 | 0.3747 | 13.8 mm | 67.6 mm | 同上 |

冻结版 single 的指标与旧版过折 4100（`191710-553973`）完全相同（0.3747 / 0.0138 / 0.0676），说明加入 `--execution` 没有改变默认路径行为；arc4 与 single 的配对审计为 `PAIRS_COMPARABLE`，同一对内所有可比快照逐字节相同（详见 [STAGE4_REPRESENTATION_PAIRS_20261102](../../../../thesis/day4-actionchunk-test/results/STAGE4_REPRESENTATION_PAIRS_20261102/review.md)）。

**任务 A 结论（开发）**：在冻结的过折定义下，开发 seeds 4100–4109 共 10/10 通过；single 与 arc4 在 4100 上各 1/1 且结果逐字节相同。这是开发复验，不是验收；正式 held-out seeds 尚未选定。

## 2. 任务 B：L2/L3 nominal 20/20（12 动作：5 recovery + 7 fold）

两种初态族：L2 = perturbed（bottom 折条 0.1615–0.1793 m，seed 4200），L3 = crumpled（left 折条 0.20 m，seed 4300）。两族共用同一 commanded 折形（width 0.20、无 overhang、place 横向 0.40），因此属于同一任务下的两种初态，不是两个任务。

两个 seed 都有冻结代码的 left single 运行（L3 于 2026-11-02 补齐），L2/4200 另有 arc4 配对：

| 初态族 | 折向 | 代码版本 | 结果目录 | 通过 | crossed | extent（x×y） | z_p95 | IoU / 对齐 / 反射误差（复算） |
|---|---|---|---:|---:|---|---:|---:|---|
| L2/4200 | left（旧版无字段，按目标几何推断） | 旧版（无 recovered-yaw） | `…103502-594762` | **true** | 1.000 | 0.2318×0.4207 | 67.7 mm | 跳过（无 `fold_yaw`） |
| L2/4200 | left | 旧版 + recovered-yaw | `…115933-089864` | false | 0.000 | 0.4424×0.4423 | 9.9 mm | 0.015 / 115.24 mm / 222.70 mm |
| L2/4200 | left | **冻结版 single** | `…20261103-001939-437540` | false | 0.000 | 0.4424×0.4423 | 9.9 mm | 0.015 / 115.24 mm / 222.70 mm |
| L2/4200 | left | **冻结版 arc4** | `…20261103-003720-939237` | false | 0.000 | 0.4424×0.4423 | 9.9 mm | 0.015 / 115.24 mm / 222.70 mm |
| L2/4200 | left | **冻结版 single（补充复跑）** | `…20261103-013721-349271` | false | 0.000 | 0.4424×0.4423 | 9.9 mm | 0.015 / 115.24 mm / 222.70 mm |
| L2/4200 | right | 旧版 + recovered-yaw | `…151711-625509` | true | 1.000 | 0.2273×0.4211 | 69.1 mm | 0.559 / 8.49 mm / 19.38 mm |
| L3/4300 | left（旧版无字段，按目标几何推断） | 旧版（无 recovered-yaw） | `…104603-419951` | false | 0.000 | 0.4581×0.4581 | 9.9 mm | 跳过（无 `fold_yaw`） |
| L3/4300 | left | 旧版 + recovered-yaw | `…113247-548209` | false | 0.000 | 0.4577×0.4577 | 9.9 mm | 0.015 / 115.24 mm / 222.12 mm |
| L3/4300 | left | **冻结版 single（补充）** | `…20261103-015744-843642` | false | 0.000 | 0.4577×0.4577 | 9.9 mm | 0.015 / 115.24 mm / 222.12 mm |
| L3/4300 | right | 旧版 + recovered-yaw | `…114705-003675` | true | 1.000 | 0.2446×0.4275 | 69.1 mm | 0.563 / 8.49 mm / 20.02 mm |

旧版目录没有 `fold_edge` / `fold_yaw` 字段，表中的 left 是按第一个折叠 target 的 x 符号推断的，并与同 seed 的显式 left 例交叉核对：L2 推断 −0.1243 对显式 left −0.1242，L3 推断 −0.1417 对显式 left −0.1420，一致。

**失败形态**：所有 left 失败例的 held gate 都通过（14.5–15.0 mm，阈值 30 mm），12 个动作全部执行、`fold_targets` 全部到达；失败发生在释放之后——布料回弹摊平（crossed 0、extent 回到 0.442–0.458 的整片量级、z_p95 9.9 mm）。因此这不是恢复失败、保持失败或动作预算超支，而是**释放后折形保持失败**。

**复跑一致性（2026-11-02 补充两例）**：L2 补充的冻结版 single（`013721`）与此前冻结版 single（`001939`）的 9 个共有文件中 7 个逐字节相同（含 `result.json`、`cloth_constructed.npz`、`recovered.npz`、`final.npz`、`mass_audit.json`、`particle_masses_after_start.npy`、`room_collision_audit.json`），只有 `metrics_full.json`（本地评价器产物）与 `runner.log` 不同；L3 的冻结版 single（`015744`）与 recovered-yaw 旧版 left（`113247`）的 6 个几何/审计文件逐字节相同（`result.json` 因新增 `execution_mode`/`code_files` 字段而不同）。两例评价器指标与对应旧例完全相同。因此这两次失败是**可复现的确定性结果**，不是随机未命中；在这两个 seed 上，表示方式与版本差异都没有改变结局。

**冻结定义下的任务 B 成功率**：L2/4200 left 为 **0/1 个 seed**（冻结版 single 2 次尝试、arc4 1 次，全部失败）；L3/4300 left 为 **0/1 个 seed**（冻结版 single 1 次，失败）——任务 B 合计 **0/2 seeds、0/4 次尝试**。right 边通过例不能计入：按冻结文档 §4.2，right 是需要单独按变更规则冻结的变体，不能在同一 seed 上把补跑算作该格成功。

## 3. single 与 arc4 的并排结论

| 任务 | seed | single | arc4 | 指标差 | 结论 |
|---|---|---:|---:|---|---|
| A（L1 过折） | 4100 | 1/1 | 1/1 | 全 0，快照逐字节相同 | 表示等价 |
| B（L2/L3） | 4200 left | 0/1 | 0/1 | 全 0，extent 相同 | 表示等价 |

本专家数据里 H=4 对成功率、指标、轨迹**没有任何影响**（后端逐行发出同一串 `control.move`）。因此不存在“H=4 组 vs single 组”的成功率差异可报；任何把这两列写成“H=4 效果”的做法都是错误的。策略层的 chunk 效应属于 BC 阶段，需要策略在 chunk 边界决策才能测量。L3 只补了 single、没有 arc4，不能称 L3 的配对已完成。

## 4. 汇总：只能叫多任务平均

冻结代码、按 seed 计：

| 任务 | 冻结版通过（seed） | 成功率（seed 级） | 备注 |
|---|---:|---:|---|
| A：L1 过折 | 1/1 | 1.00 | seed 4100；开发全集另有 10/10（旧版 single） |
| B：L2/L3 nominal 20/20 | 0/2 | 0.00 | seeds 4200（L2）、4300（L3）均为 left；共 4 次尝试全失败 |
| —— 多任务平均 —— | — | **0.50** | (1.00 + 0.00) / 2；A n=1、B n=2 |

**这个 0.50 不能当难度曲线用**：两个任务的折形目标不同（过折 vs nominal 20/20），初态族不同，A 只有 1 个 seed、B 有 2 个 seed 且都是 left，样本极少。它只是“按任务分别算完再取平均”的机械结果。L1 与 L2/L3 的成功率差异不得归因于初态难度；L2 与 L3 之间也不构成受控梯度。

若把开发历史（不同代码版本）也算进来：L1 过折 10/10；L2 left 共 5 次尝试、1 次通过（通过例是 recovered-yaw 之前的版本）；L3 left 共 3 次尝试、0 次通过。这些数字只用于追溯，不参与上面的多任务平均。

## 5. 版本与可比性边界（必须保留）

1. **旧版目录不可与冻结版配对**：没有 `execution_mode` / `code_files`，配对审计会判 `PAIR_NOT_COMPARABLE`；其中 pre-recovered-yaw 的两条（`103502`、`104603`）还因为没有 `fold_yaw` 被统一评价器跳过，只有内联指标。
2. **L2/4200 left 的通过→失败翻转不是同一代码**：`103502` 用初始 yaw，`115933`/冻结版用 recovered yaw（折向角差 0.0025 rad，place 差约 1 mm），recovered 状态逐字节相同。通过例不能算作冻结定义的通过，也不能把翻转归因于单一物理原因。
3. **right 边通过例是另一条折向**：`151711`（L2）、`114705`（L3）证明脚本能在该 seed 上完成镜像折叠，但不改变 left 的结论。
4. **L1 旧版与冻结版在 4100 上指标完全相同**，说明 `--execution` 改动没有扰动默认路径；但其余 9 个旧版过折目录仍未在冻结版下重跑，不能写成“冻结版 10/10”。
5. **收尾 runner 的退出码 1 不是缺结果**：runner 在结果落盘后断言 `passed`，失败例必然返回 1；`result.json`、快照与 `runner.log` 都完整保留，失败不被重跑替换。补充的 L2/L3 两例均属这种情况。

## 6. 本报告没有建立的内容

- 正式 Stage 4 成功仍为 0；`passed=true` 只表示开发门槛通过。
- held-out seeds（每格 20 个）尚未选定；本表全部是开发 seeds。
- 没有 rejection rate、没有 10 次 reset 批次、没有接口/视频/30 图验收材料。
- L2 与 L3 各只有 1 个 left seed 有冻结版数据；L2 的 right 通过例是旧版代码；L3 没有 arc4 配对。
- 没有评价任何策略；single 与 arc4 的差异在本数据里为 0，不代表 BC 策略下也为 0。

## 7. 下一步

1. **已补齐（2026-11-02）**：L2/4200 与 L3/4300 的 left 冻结版 single 各跑一次，均失败，证据见 [TASK_B_SINGLE_EVIDENCE_20261102-173708](../../../../thesis/day4-actionchunk-test/results/TASK_B_SINGLE_EVIDENCE_20261102-173708/review.md)；两例的 18 个下载文件哈希、`code_files` 与 21 项 manifest、评价器复算均已核对。除非初态或代码变更，不需要再重复这两个 seed。
2. 第 7 步正式批次前先选定 held-out seeds（与开发集不相交、single/arc4 共用同一列表），并准备失败/拒绝率、10 次 reset、接口/视频/30 图。
3. 任何“缩减配对 seed 范围”的决定属于计划变更，按冻结文档 §0 先登记。
