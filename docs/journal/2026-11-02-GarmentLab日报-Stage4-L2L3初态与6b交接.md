# 2026-11-02 Stage 4：L2/L3 初态完成，6b recovery 起始交接

## 2026-11-02 L1 过折 0.02：最后三例已执行并逐例下载

按用户指定顺序 4101 → 4106 → 4103，各执行一次 `L1_XFOLD_OVERHANG=0.02`；每例完成后下载完整目录并核对 SHA256，再启动下一例。三例 runner_exit=0、passed=true、errors=[]，各7个公开动作，总计57份原始文件哈希一致。未追加重试或其他GPU实验，三例进程均已结束。

| seed | 完整运行目录 | crossed | alignment (mm) | IoU代理 | z_p95 (mm) |
|---|---|---:|---:|---:|---:|
| 4101 | `day4-l1-xfold-yaw-aware-20261102-224914-136557` | 1.0 | 13.823 | 0.3646 | 67.657 |
| 4106 | `day4-l1-xfold-yaw-aware-20261102-225757-935709` | 1.0 | 13.824 | 0.3766 | 67.527 |
| 4103 | `day4-l1-xfold-yaw-aware-20261102-230743-527418` | 1.0 | 13.811 | 0.3700 | 67.468 |

独立重算与日志一致：seed/overhang、441顶点、动作状态、60步保持、最终OPEN未附着及释放后几何检查全部通过。05_release_stationary→06_final_3s 平均顶点位移：4101约0.186mm、4106约0.223mm、4103约0.181mm。阶段图及三张最终PNG已视觉检查，未摊平；仍存在拱形/偏置覆盖和机器人遮挡，不能用passed替代正式折叠质量验收。

本地overhang=0.02的结果现已覆盖seeds4100–4109，10例runner均通过且crossed=1.0；覆盖CSV记录各结果JSON哈希。该覆盖统计不证明正式统一配置/阈值已经冻结，也不等同正式批次成功。

本轮汇总位于 `day4-actionchunk-test/results/L1_OVERHANG_002_REMAINING_20261102-144907/`，含 `batch.json`、每例SSH完整日志/下载哈希、`independent_audit.json`、`review.md`、`l1_overhang_comparison.png` 和 `l1_overhang_002_development_coverage.csv`。完整原始目录位于同级results目录。

限制：本7动作runner在OPEN后30个release tick和180个settle步取样，没有独立退让或3秒后的第二保持样本；本轮为开发验证，正式成功仍为0。下一步需统一L1过折与L2/L3折叠定义和评价口径，再冻结正式评价；不自动启动额外实验。

## 2026-11-02 自动接续结果：L3 right 保持，L2 recovered-yaw left 回弹

本轮通过 SSH 等待正在运行的 L3 right 结束，再执行一次 L2 left；两组均已退出，未追加其他 GPU 实验。完整结果均下载至本仓库 `day4-actionchunk-test/results/`，与远端逐文件 SHA256 一致。

| 开发尝试 | 结果目录后缀 | crossed | 释放静置后 XY extent (m) | z_p95 (m) | 动作 |
|---|---|---:|---|---:|---:|
| L3 4300 left（已运行对照） | 113247-548209 | 0.0 | 0.458×0.458 | 0.00990 | 12 |
| L3 4300 right fallback | 114705-003675 | 1.0 | 0.245×0.428 | 0.06908 | 12 |
| L2 4200 left recovered-yaw 重跑 | 115933-089864 | 0.0 | 0.442×0.442 | 0.00990 | 12 |

三组 441 顶点快照、5+7 动作、逐动作状态、60步保持记录和最终 OPEN 未持布/未附着记录核对通过。L3 right 的截图及材料分半投影支持半折候选；两个 left 最终网格为平铺，不能按动作完成认定折叠成功。9/10/9 份原始结果文件哈希核对通过。失败例的 final.png 未生成（脚本在几何门槛失败后进入 finally），但 final.npz、result.json、hold_trace 和 runner.log 均保留。另有 112937-225297 未写 result.json 的未完成目录，原因未判定，单独记录。

L2 新旧对照：旧成功例 103502-594762 与新失败例的 recovered.npz 逐字节相同；5个 recovery 目标相同；fold yaw 改变 0.002499711 rad（约0.143°），place XYZ 改变约1.000 mm。结果由 crossed=1 变为0，说明候选敏感，不能宣称 recovered-yaw 修正已普遍通过，也不据此断定单一物理根因。

审查产物：`day4-actionchunk-test/results/RECOVERY_FOLD_REVIEW_20261102/` 下的 `review.md`、`audit.json`、`recovery_fold_comparison.png`、`transfer_verification.json`、`L2_old_vs_recovered_yaw.json`、`development_attempts.json`；脚本 `day4-actionchunk-test/review_recovery_fold_nov2.py`。

限制：本组合脚本在 OPEN 后额外30个release tick和180个settle步取样，未单独退让、未保存第二个延迟保持快照。不得将本轮算作退让后保持或正式批次验收。正式成功仍为0，评价未冻结。下一收敛点为处理 L2 的 yaw-aware 回弹与最终统一路径选择（先用未使用的 right 槽位验证），再补齐 L1 yaw-aware及评价冻结；不启动参数网格、翻腕或完整三阶段折衣。

## 一句话状态

- 第 1–5 步已完成：L1 x 向半折两次开发运行通过；正式 Backend 的 yaw/抓取/保持/重抓取/reset 10 循环通过。
- **第 6a 步完成**：L1/L2/L3 各 10 张、共 30 张初态图全部 `passed=true`；三档初态肉眼可区分（L1 平铺、L2 宽短折带、L3 窄高半折）。
- **第 6b 步进行中**：5 动作 recovery 已在 L2/L3 验证（刚性残差 8–9 µm）；7 动作折叠 v2 已验证（crossed 1.0、对齐/高度/保持与 9 动作一致，IoU 0.607）；L2 4200 组合 left 旧例通过、recovered-yaw left 回弹；L3 4300 组合 left 回弹、**right 槽位 fallback 通过**（12 动作、crossed 1.0、extent 0.245×0.428）；**L2 4200 right 槽位也已通过**（151711-625509：12 动作、crossed 1.0、extent 0.227×0.421、z_p95 0.0691、5 文件哈希核对一致）。L2/L3 均已有 right 边 12 动作组合开发例；下一步 L1 yaw-aware 复验。
- **第 3 步表示层已实现并完成两任务各一对开发配对**：两个折叠脚本支持 `--execution single|arc4`（默认 single 行为不变），冻结映射为只把四个 arc 目标合成 H=4；评价器统一到离线 `stage4_fold_metrics.py` 并自校验哈希。L1/4100 与 L2/4200 各跑 single+arc4 共四例，两组审计均 `PAIRS_COMPARABLE`，`code_files` 与 manifest 零差异，**同一对内所有可比快照逐字节相同**、指标差全为 0 → 本步只证明两种表示等价（专家轨迹），**不构成 H=4 收益证据，H=4 不能写成已验证**。
- **第 4 步分任务报告已完成（2026-11-02 补齐任务 B 两例）**：L1（过折）冻结版 1/1（4100，single/arc4 各 1/1），L2/L3 冻结版 **0/2**（L2/4200、L3/4300 left，共 4 次尝试全失败）；多任务平均 0.50（A n=1、B n=2 个 seed），**不是难度曲线**；失败形态统一为释放后回弹摊平，held gate 通过；补充两例与既有同条件运行逐字节相同，属确定性可复现失败。见 [分任务报告](day4-actionchunk-test/results/STAGE4_PER_TASK_20261102/review.md) 与 [任务 B single 证据](../thesis/day4-actionchunk-test/results/TASK_B_SINGLE_EVIDENCE_20261102-173708/review.md)。
- **第 7 步正式批次已登记、未运行**：held-out seeds 每档 20 个（L1 4110–4129、L2 4210–4229、L3 4310–4329），与开发集不重叠、批次前固定、single/arc4 共用；已写入 `square-initial-plan.json`（30→90 条）和 `stage4-heldout-seeds.json`，并放宽两个初态 runner 的 seed 断言（折叠 manifest 与折叠脚本未改）。批次驱动与拒绝率汇总工具已写好。**前置**：正式成功阈值未冻结；且要先决定先跑 left 基线还是先解决 B 的释放后回弹。见 [正式批次准备](2026-11-02-GarmentLab日报-Stage4-正式批次计划.md)。
- **right 开发验证完成、覆盖扩展已登记未运行（2026-11-02）**：`b-right-dev-v1` 四例（4200/4300 × single/arc4）全部 `passed`、held gate 通过、crossed 1.0；同档 single 与 arc4 的 12 个公开动作目标、后端指令与终态顶点逐位相同；补充核对把额外与重复尝试一并纳入，同 seed 全部 7 次尝试的 `final.npz` 441 顶点 `max|Δ|=0`。`b-right-dev-v2` 已登记（L2 4201–4209、L3 4301–4309 共 18 个剩余开发 seed，只跑 single），**未运行**。left 的失败记录不变，right 不替换默认定义。
- 正式 Stage 4 成功仍为 **0**。

## 环境与连接

| 项 | 值 |
|---|---|
| 远端实例 | `ssh -p <port> <server>`（2026-11-02 新克隆实例；旧 nmb1:22895 不要再用） |
| 容器 | `autodl-container-ac0a41b2f7-bc28942d` |
| 工作目录 | `<remote-root>` |
| Python | `<remote-root>/envs/isaac40/bin/python` |
| 项目仓库 | `<remote-root>/garmentlab-action-chunk-demo` |
| 本地仓库 | `E:\learning\project\garmentlab-action-chunk-demo` |

工作方式：助手改本地文件 → 用户用 PowerShell `scp -P 23636 ...` 上传 → 用户在远端 VS Code bash 运行 → 用户下载结果 → 助手离线审查。助手不直接在远端执行 GPU 实验。所有清单哈希按 **LF** 字节计算；上传后用预检核对。

## 已排除的路线（不要再走）

1. **lift → 原高度释放**：`particle_friction_scale=0`，布料自摩擦为零，任何 lift/release 产生的褶皱都会松弛；L2 4200 与 L3 4300 最终 z extent ≈6e-8，完全平铺。
2. **原始动态附件 `Control`**：其 `move`/`grasp` 在 3 cm `reach` 容差处停止，grasp 悬在角点上方约 2.9 cm，2 cm 动态附件没覆盖到布；`cycle_00_settled` 与 `flat_settled` 差 3.7e-8 m，布料完全没动。v1 动态版的“通过”都是空动作。
3. **角点折角（dog-ear）**：持布时折角存在（`after_lower` 形变残差约 150 mm），但 release 瞬间整体弹平（`after_release` 刚性拟合残差 0.04 mm，整块布刚性旋转）。小三角折角不是稳定平衡。
4. **窄布条**：left 0.11、left 0.165 在 release 后完全展开；bottom 0.11 也失败。bottom 的稳定阈值在 0.162–0.169 之间；left 需要接近半折的 0.20。bottom 的折叠方向与夹爪手指开合方向一致，比 left 更稳。
5. **L3 用 top 边做第二折**：top 边靠近机器人基座，固定下指姿态在 z≈0.013 处不可达（4301 IK 无解）；钳制 dy 只能部分缓解。最终放弃 top，L3 改为左半折。

## 关键实现：prepared 控制的持布阶段放宽

prepared 单点锚点是唯一被证明能抓住布的路径（grasp EE 0.83 mm、块 ≤1.31 mm、锚点 ≤1.4 mm、角点实际抬起 7.8 cm）。但折叠适配器的严格 `_drive`（EE<10 mm + 连续 6 步 + 末臂速<0.1）在布料负载下会在近边/高抬升超时。

`strip_prepared_control.py` 与 `corner_prepared_control.py` 采用同一策略：

- `follow=False`（抓取前 approach/descend）：保持 **10 mm** 严格门限，确保夹爪到布；
- `follow=True`（持布 lift/arc/place）：EE 放宽到公共契约 **3 cm**，块 <5 mm、旋转 <0.03、单点锚点 <10 mm 不变；
- 首次 grasp 之后（`slot.used=True`）的 release 跟随 / retreat / home 也走放宽路径；
- 正式 L1 折叠控制（`square_probe_control.py` 等）**未修改**，哈希不变。

## 6a 最终配置与结果

**plan**：`square-initial-plan.json`，`version=square-initial-v3`，hash `e2cfaebe597e52b5…`；**yaml**：`square-difficulty.yaml`，hash `a42fec8a1069ad43…`。

| 档位 | 初态 | 参数 | 最终形状（典型） |
|---|---|---|---|
| L1 | 平整方巾 | 仅平移/旋转（4100–4109） | 0.4×0.4，z 平 |
| L2 | 一条 **bottom** 折条 | width 0.16–0.18（4200 = 0.174179） | 约 0.42×0.25，z 约 0.06，宽短折带 |
| L3 | 一条 **left 半折** | width 0.20（4300 = 0.20） | 约 0.25×0.43，z 约 0.06，窄高折半 |

L3 的 yaml 已改为 `num_lift_drops: 1`、`max_recovery_moves: 1`；L3 的平移恢复原始采样值（不再需要 top 边的 dy 钳制）。

**30 张图的运行目录**：

- L1（`day4-square-initial-20261031-*`）：
  `094446-203825, 095254-316552, 095611-471489, 095925-799656, 100246-659222, 100558-317616, 100909-165817, 101224-181183, 101541-103282, 101853-191858`
- L2（`day4-square-initial-stripfold-20261102-*`）：
  `4200 023311-548690, 4201 031859-758705, 4202 032804-246519, 4203 033648-809964, 4204 034544-830190, 4205 035436-003676, 4206 040355-509776, 4207 041256-658874, 4208 042215-851125, 4209 043151-454479`
- L3：
  `4300 074349-406408, 4301 075606-421583, 4302 080548-693912, 4303 082753-692325, 4304 083848-796253, 4305 084918-410795, 4306 090016-424984, 4307 091001-304307, 4308 092049-522618, 4309 093018-418187`

30 张对比图（本地）：`day4-actionchunk-test/results/initial30_sheet_v2.png`。每张初态目录含 `initial.png`、`initial_geometry.npz`（`before/applied/flat_settled/final`）、`strip_XX_*.npz`、`result.json`。

**典型结果**：

- L2 4200：bottom crossed 1.0、pick 内移 0.348 m、extent `0.4215×0.2495`、z extent `0.0593`。
- L3 4300：left crossed 1.0、pick 内移 0.382 m、extent `0.2483×0.4263`、z extent `0.0597`。
- L3 4303 的 home 曾因近基座姿态超时；已把 home 改为非致命，失败记录 `home_skipped`，不影响初态。

## 6b 现状（暂停点）

### 已实现、未运行：5 动作 recovery 冒烟

- 脚本：`day4-strip-recovery-smoke.py`（hash `68781cf2316ed103…`）
- 运行脚本：`run-strip-recovery-smoke.sh`（hash `57bdfd6848d185a0…`）
- 清单：`square-strip-recovery-files.json`（20 项，LF）
- 输入：一个初态运行目录。读取 `result.json` 的 `initial_case.strips`、`strip_records[].pick_index/pick_world`（折叠前的 pick 世界坐标），以及 `initial_geometry.npz` 的 `flat_settled/final`。
- 场景：正常构造方巾和 prepared 边槽位，然后把布料世界坐标设为初态的 `final`（折叠态），settle 30。
- 动作（5 个）：approach（折叠后 pick 上方 12 cm）→ pick（CLOSE，到折叠后 pick）→ lift（+8 cm）→ spread_place（折叠前 pick +3 cm）→ release。
- 输出：`recovered.npz`、`recovered.png`、`result.json` 里的 `recovery_metrics`（刚性残差 vs flat、pick 位移、extent、z_p95、action_count）。

**2026-11-02 09:50 L3 4300 recovery 已通过**（`day4-strip-recovery-20261102-095042-400051`，`passed=true`）：

- 5 个动作全部成功，块跟随 ≤1.04 mm、锚点 ≤2.32 mm；
- 相对 `flat_settled` 的刚性拟合残差最大 **8.0e-6 m**，左半折完全展开（形状与折叠前一致，仅差刚性旋转/平移）；
- pick 位移 19.3 mm、recovered extent `0.4583×0.4583`、z extent ~6e-8；`recovered.png` 为完整平铺方巾；`action_count=5`。

**L2 4200 recovery 也通过**（`day4-strip-recovery-20261102-095917-466741`）：5 个动作、块 ≤1.05 mm、锚点 ≤1.96 mm、相对 flat 的刚性残差 **8.6e-6 m**、pick 位移 4.2 mm、extent `0.4426×0.4425`、`recovered.png` 为平铺方巾。**L2/L3 的 5 动作 recovery 均验证通过。** 两个冒烟命令：

```bash
bash <remote-root>/run-strip-recovery-smoke.sh <remote-root>/day4-square-initial-stripfold-20261102-023311-548690   # L2 4200
bash <remote-root>/run-strip-recovery-smoke.sh <remote-root>/day4-square-initial-stripfold-20261102-074349-406408   # L3 4300
```

未上传文件：`day4-strip-recovery-smoke.py`、`run-strip-recovery-smoke.sh`、`square-strip-recovery-files.json`。

### 尚未实现：7 动作折叠压缩

当前 L1 x-fold 是 9 个动作（approach → descend → close → arc45 → arc90 → arc135 → place → release → retreat）。要满足 7+5=12，需要压到 7 个动作。建议方案：

1. approach + descend 合并为一个 grasp 动作（从 home 直接到抓取点）；
2. 去掉 retreat（release 后直接 settle，episode 结束）；
3. 保留 close / arc45 / arc90 / arc135 / place / release。

即：**grasp → close → arc45 → arc90 → arc135 → place → release = 7**。

必须重新跑一次完整 L1 折叠验证，确认路径不退化、折叠 IoU/对齐/保持指标与 9 动作版（`062602-150760`）相当，再用于 recovery+fold 组合。

### 预算与组合

- recovery 5 + fold 7 = 12（L2/L3 各一次 recovery；L1 无 recovery）。
- L3 的 recovery 展开的是左半折，随后 fold 再次折左半——同一方向的“展开再折”，需要确认 recovery 后的抓取点/折线与 fold 的 left slot 兼容。
- L2 的 recovery 展开 bottom 折条，fold 折左半；两者正交，兼容性较好。

## 6b 进展（2026-11-02 10:00 后）

- **5 动作 recovery 已验证**：L3 4300（`095042-400051`）与 L2 4200（`095917-466741`）均 `passed=true`，相对 `flat_settled` 的刚性残差分别为 8.0 µm / 8.6 µm，布料完全展平；块/锚点跟随 <2.4 mm。
- **7 动作折叠已验证（v2）**：`day4-l1-xfold-7actions-20261102-102118-812499`，labels `approach/close/arc45/arc90/arc135/place/release`。
  - 压缩方式：保留 approach（+15 cm），把 descend 合并进 close（`Control.grasp` 内部先 drive 到抓取点再闭爪），去掉 retreat。
  - crossed 1.0、对齐 6.357 mm（9 动作 6.358）、z_p95 68.60 mm（68.66）、held gate 0.505 mm/0.000916 rad/s/1.960 mm（与 9 动作一致）。
  - `particle_occupancy_iou=0.607`（9 动作 0.652–0.662）、反射目标误差 7.63 mm（9 动作 5.7 mm）。原因：去掉单独 descend 后，close 在 `_drive` 结束时立即闭爪，抓取点没有 descend 的末速 settle；折叠仍有效。
  - v1（把 approach 也合并成从 home 直接到抓取点）的 IoU 只有 0.570，已放弃。
- **组合 episode（5+7=12）已实现**：`day4-recovery-fold-episode.py`。L2 4200（`103502-594762`）通过：recovery 残差 8.6 µm、fold crossed 1.0、extent `0.232×0.421`、z 0.0595、held 通过、12 动作。
- **L3 4300 组合失败**（`104603-419951`）：recovery 正常（8.0 µm），fold 7 个动作执行、锚点跟随 ≤2.15 mm，但释放后布料完全摊平（crossed 0.0、extent 回到 0.458）。原因尚未定论：怀疑 ① 恢复与折叠共用左槽位（同一单点锚点先展开再折）；② 折叠用了初始 yaw，恢复后布料实际旋转约 1.3°，折线错位。
- **已实现、待上传重跑**：组合脚本用 recovered vs flat 的刚性拟合 yaw（`fold_yaw = case_yaw + Δ`）构造折叠弧线和动作姿态。L3 失败例实测 Δ=-2.007°；修正后的 4 个折叠目标与初始 L3 成功轨迹经同一刚体变换后一致到 0.1 mm（旧版目标差 13.9 mm）。script `83d1fb24…`（该版已被第 3 步版本 `ddad4116…` 取代，见 §文件与哈希）。
- **right 槽位 fallback 已实现**：`--fold-edge right` 用未使用的 right 槽位做镜像半折（右边缘 pick、lateral=-x、moving=右半、crossed 投影同式）；默认仍为 `left`，默认路径的训练/物理行为不变。run 脚本第二个参数为 `left|right`。
- 7 动作 runner 仍是 world x / yaw=0；L1 正式批（yaw ≠ 0）也需要局部轴版本。

## 文件与哈希（当前有效）

| 文件 | 哈希（LF） |
|---|---|
| `square-initial-plan.json`（v3） | `e2cfaebe597e52b5…` |
| `square-difficulty.yaml` | `a42fec8a1069ad43…` |
| `day4-square-initial-stripfold.py` | `178ab10c08511b6d…` |
| `strip_prepared_control.py` | `49075fb4bf90d08e…` |
| `run-square-initial-stripfold.sh` | `33a4e142ca81e0d7…` |
| `square-initial-stripfold-files.json` | 23 项，见文件 |
| `day4-strip-recovery-smoke.py` | `68781cf2316ed103…` |
| `run-strip-recovery-smoke.sh` | `57bdfd6848d185a0…` |
| `square-strip-recovery-files.json` | 20 项，见文件 |
| `day4-l1-xfold-7actions.py` | `baaba5cde14b416d…` |
| `run-l1-xfold-7actions.sh` | `a65820c0e67b…` |
| `square-l1-xfold-7actions-files.json` | 23 项，见文件 |
| `day4-recovery-fold-episode.py` | `ddad4116ad33…` |
| `run-recovery-fold-episode.sh` | `41026c913f12…` |
| `square-recovery-fold-files.json` | 21 项，见文件 |
| `day4-l1-xfold-yaw-aware.py` | `0aab8e7cd42f…` |
| `run-l1-xfold-yaw-aware.sh` | `560d38bbb083…` |
| `l1_yaw_fold_geometry.py` | `aa1f8a6e3ede…` |
| `square-l1-xfold-yaw-files.json` | 24 项，见文件 |
| `stage4_fold_metrics.py`（离线评价器） | `8d1f31591c1c…` |
| `stage4-evaluator-files.json` | 2 项，见文件 |
| `stage4_representation_audit.py`（配对审计） | `8c31c2f9e7b4…` |

共享 prepared 依赖（`multi_prepared_grasp_control.py`、`square_probe_control.py`、`single_anchor_hem_control.py`、`hem_prepared_grasp_control.py`、`hem_fold_geometry.py`、`multi_grasp_geometry.py`、`square_contact_reporting.py`、`square_proxy_ground_control.py`、`square_stable_hold.py` 等）沿用服务器已验证哈希，本轮未修改。

## 上传/下载命令

```powershell
# recovery 冒烟（3 个文件）
scp -P 23636 "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\day4-strip-recovery-smoke.py" "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\run-strip-recovery-smoke.sh" "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\square-strip-recovery-files.json" <server>:<remote-root>/

# recovery+fold 组合（3 个文件：recovered-yaw + right fallback）
scp -P 23636 "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\day4-recovery-fold-episode.py" "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\run-recovery-fold-episode.sh" "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\square-recovery-fold-files.json" <server>:<remote-root>/

# 下载某个结果目录
scp -P 23636 -r <server>:<remote-root>/day4-recovery-fold-<时间戳> "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\results\"
```

```bash
# 1) recovered-yaw 重跑（默认 left；预检会打印 fold_edge）
bash <remote-root>/run-recovery-fold-episode.sh <remote-root>/day4-square-initial-stripfold-20261102-023311-548690 left
bash <remote-root>/run-recovery-fold-episode.sh <remote-root>/day4-square-initial-stripfold-20261102-074349-406408 left
# 2) right 槽位镜像半折（L3/L2 均已通过）
bash <remote-root>/run-recovery-fold-episode.sh <remote-root>/day4-square-initial-stripfold-20261102-074349-406408 right
bash <remote-root>/run-recovery-fold-episode.sh <remote-root>/day4-square-initial-stripfold-20261102-023311-548690 right
```

## L1 yaw-aware 7 动作复验（新增，先于下一批正式）

旧 `day4-l1-xfold-7actions.py` 的折线固定为世界 x、yaw=0；L1 的 10 个初始态 yaw 覆盖 −0.1488…+0.1381 rad（约 ±8.5°），直接复用会把折线折歪。新增 3 个脚本 + 1 个 manifest，旧脚本/runner/manifest 保持不动：

- `l1_yaw_fold_geometry.py`：`measure_yaw` 用局部网格点到 settled 顶点的 2D 刚体拟合测 yaw；`local_arc` 在 cloth-local 帧生成 4 个弧目标（可选 `overhang` 只延长末个 place 目标，默认 0）；`fold_metrics_yaw` 在 cloth-local 帧算 crossed、反射目标误差、对称对齐和粒子占据 IoU。
- `day4-l1-xfold-yaw-aware.py`：读 L1 初始目录的 `result.json` 与 `initial_geometry.npz['settled']`，settle 30 步后测 yaw（要求与 `case['yaw_rad']` 差 ≤0.02 rad），7 个公开动作全部用 `[π,0,yaw]` 朝向与 cloth-local 弧；保留严格 1 cm held gate，另加 crossed≥0.5 门槛；精确 7 动作；`--overhang` 默认 0，过折量写入 `fold_definition.fold_overhang_m`。
- `run-l1-xfold-yaw-aware.sh <initial-dir>`：预检 24 项哈希，断言 passed、7 动作、yaw 一致、crossed≥0.5、`fold_overhang_m` 与 `L1_XFOLD_OVERHANG` 一致、final.png 480×640。

离线验证：yaw=0 时 `local_arc` 与旧 `square_edge_targets` 最大差 6.0e-9 m；dev 平整态测得 yaw −4.3e-8 rad；合成 yaw 0.0328/0.13/−0.1488 rad 下指标完全一致。指标口径注意：新指标用严格 cloth-local 掩码（210 点），旧 L1 结果保存的是世界 x 掩码（223 点，多含中心列浮点负值），因此 IoU 0.578 vs 旧 0.607、对齐 7.14 mm vs 旧 6.36 mm 是掩码口径差异，不是折叠变化。

首例结果（seed 4100，yaw +0.0328，`day4-l1-xfold-yaw-aware-20261102-165141-003161`）：crossed 门槛失败，passed=false。测量 yaw 与 case 差 −4.5e-8；`03_place` 的 cloth-local 折叠几何与 yaw=0 dev 例几乎逐点相同（flap 局部 x [0.2306, 0.4006] vs [0.2306, 0.4006]，z 均值 0.035 vs 0.035），说明 yaw 与弧不是失败原因。释放动作内 flap 沿局部 x 回滑约 1.3 cm，30 tick 后 crossed 1.0→0.852，180 步静置后完全展平（crossed 0、z_p95 0.0099、extent 回到 0.416×0.416）。与 L2/L3 left 的回弹同类：折到位但保持不住。

第二例（seed 4107，yaw −0.1488，`day4-l1-xfold-yaw-aware-20261102-171533-773483`）同样在 crossed 门槛失败：测量 yaw 差 −4.1e-8，held gate 通过（位置误差 3.6 mm、锚点 1.99 mm），`03_place` 的 flap 局部 x [0.231,0.400]、z 剖面 [0.068,0.062,0.039,0.030,0.030]，与 dev 的 [0.231,0.401]/[0.067,0.060,0.037,0.029,0.029] 几乎相同；释放后 04 crossed 0.995（尖端回滑 1.6 cm）、30 tick 后 0.662（qx [0.168,0.325]）、180 步后完全展平。两例都表明 place 时布面折成约 6.7 cm 高的拱形/卷曲，释放后整片回弹；而每个动作实际推进的物理步数随初始位姿不同（close/arc45/arc90/arc135/place：dev 107/156/148/156/174，4100 109/155/175/202/208，4107 111/160/174/176/149），即初始位姿改变了机械臂 IK 路径与时间剖面，折叠保持处于临界状态。4100 与 4107 的失败不是 yaw/弧/held gate 错误，而是同一折法在不同初始位姿下的回弹。

为区分“yaw-aware 装载路径（teleport + settle 30 + 零速度）”与“扰动敏感性”，新增零扰动对照初始态 `day4-actionchunk-test/initial-cases/dev-zero-perturbation/`（直接把 dev 例 `00_initial` 的 441 点作为 settled，yaw=0、平移 0）。**对照通过**（`day4-l1-xfold-yaw-aware-20261102-173908-646355`，`L1_YAW_XFOLD_COMPLETED`、`L1_XFOLD_YAW_SAVED`），且 close/arc45/arc90/arc135/place/release 的物理步数为 107/156/148/156/174/82，与 dev 逐项相同，证明装载路径是对 dev 状态的精确重放，4100/4107 的失败只来自初始位姿改变机械臂路径。4105 当时结果尚未下载，runner 日志显示它也 failed（yaw 仅 +0.0069、平移 1.06 cm，`day4-l1-xfold-yaw-aware-20261102-180153-252676`）；后补下载核对，事实一致，即 1 cm 量级扰动也足以翻掉折叠。

为定位 flap 从哪一步开始回滑，脚本新增 `03_hold_end` 快照（hold 结束、attachment 仍启用时）与 `hold_end_metrics`；该改动只读状态、不推进物理。

诊断重跑（4100，`175052-846321`，各动作步数与首跑 165141 完全相同 377/486/641/816/1018/1226/1308，新增快照不扰动物理）：`03_place` crossed 1.000、flap qx [0.231,0.401]、z_p95 0.0701；`03_hold_end` crossed 1.000、qx [0.231,0.400]、z_p95 0.0700（对齐 5.41 mm、IoU 0.583）——固定持握 60 步内 flap 变化 ≤1 mm；ungrasp 后的 `04_released`（82 步释放动作内）crossed 仍 1.000、内缘 0.231→0.218，但 30 tick 后 `05` crossed 0.852（qx [0.188,0.360]）、180 步后 0.000。**回滑由 ungrasp 触发**，place/hold 不是失衡点。对照例的自由拱形在 04/05/06 几乎不变（zmax 0.069、chord 0.157），4100/4107 的自由拱形在 0.5 s 内展开（4107 的 chord 0.151→0.125），稳定例与失败例的 place/hold 几何只差 3–6 mm：自由状态是浅势垒平衡。速度读取不可用（`ClothPrimView` 无 `get_world_velocities`，npz 记录 `velocity_error`），位置数据已足够定位。

上传（4 个文件，geometry/script/runner/manifest 均有改动）：

```powershell
scp -P 23636 "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\l1_yaw_fold_geometry.py" "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\day4-l1-xfold-yaw-aware.py" "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\run-l1-xfold-yaw-aware.sh" "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\square-l1-xfold-yaw-files.json" <server>:<remote-root>/
```

下载 4105 结果（此前未下载）：

```powershell
scp -P 23636 -r <server>:<remote-root>/day4-l1-xfold-yaw-aware-20261102-180153-252676 "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\results\"
```

运行（4100 过折试验；`L1_XFOLD_OVERHANG` 缺省 0，默认路径与旧行为逐字节一致）：

```bash
L1_XFOLD_OVERHANG=0.02 bash <remote-root>/run-l1-xfold-yaw-aware.sh <remote-root>/day4-square-initial-20261031-094446-203825   # 4100 过折
```

过折的含义：`--overhang 0.02` 只把 place 的末目标沿折向多伸 2 cm（45/90/135 三个弧目标不变），flap 自由边越过静止半远端边缘约 2 cm，折缝右移约 1 cm（约 21/19 的轻微不对称，需在折形定义里如实记录）；目的是把自由拱形从“尖端浮在边缘上方”改成“尖端落在边缘外桌面”，用自重锁住展开。runner 会把 `L1_XFOLD_OVERHANG` 传给脚本并断言 result 的 `fold_definition.fold_overhang_m` 与之一致，不允许静默加过折。若远端初始目录已清理，runner 会在预检前报 `missing L1 initial files`，需先用 L1 初始 runner 重新生成。

**过折复验结果（10/10 通过 runner 断言）**：4100–4109 全部 `passed=true`、7 动作、yaw 差 <1e-7、`fold_overhang_m=0.02`、crossed≥0.5、final.png 640×480。

| seed | case yaw | 结果目录 | final crossed / IoU / 对齐 / z_p95 | held 误差 |
|---|---|---|---|---|
| 4100 | +0.0328 | 191710-553973 | 1.000 / 0.375 / 13.8 mm / 67.6 mm | 0.34 mm |
| 4101 | −0.1310 | 224914-136557 | 1.000 / 0.365 / 13.8 mm / 67.7 mm | 4.08 mm |
| 4102 | −0.0608 | 220311-323277 | 1.000 / 0.371 / 13.8 mm / 67.5 mm | 2.32 mm |
| 4103 | −0.0751 | 230743-527418 | 1.000 / 0.370 / 13.8 mm / 67.5 mm | 3.56 mm |
| 4104 | −0.0730 | 223733-117878 | 1.000 / 0.373 / 13.8 mm / 67.5 mm | 3.52 mm |
| 4105 | +0.0069 | 193027-293315 | 1.000 / 0.374 / 13.8 mm / 67.5 mm | 1.01 mm |
| 4106 | +0.1029 | 225757-935709 | 1.000 / 0.377 / 13.8 mm / 67.5 mm | 0.25 mm |
| 4107 | −0.1488 | 195321-377100 | 1.000 / 0.371 / 13.8 mm / 67.5 mm | 4.12 mm |
| 4108 | +0.1381 | 212833-677443 | 1.000 / 0.423 / 13.8 mm / 67.5 mm | 0.14 mm |
| 4109 | +0.0088 | 210021-447296 | 1.000 / 0.374 / 13.8 mm / 67.5 mm | 1.58 mm |

详细快照轨迹（4100/4105/4107 逐例核对）：03_hold_end → 04_released → 05 → 06 的 crossed 均为 1.000；03→04 之间 IoU 从 0.50–0.67 降到 0.38 左右（ungrasp 时折形松弛一次），之后 04→06 只差 ≤0.013 IoU，180 步静置不再展开。同三例的基础版（overhang 0）在 04/05/06 的 crossed：4100 1.000/0.852/0.000、4105 1.000/0.948/0.000、4107 0.995/0.662/0.000。

几何代价（如实记录）：十例的最终 qx 剖面几乎逐点相同（材料 x=−0.20/−0.12/−0.04/+0.04/+0.12/+0.20 → qx 0.438/0.361/0.292/0.243/0.317/0.397，4108 整体内移约 5 mm），说明过折把自由状态收敛到同一个稳定构型，与初始 yaw/平移无关；折脊在 qx≈0.29（零扰动控制组 0.25），flap 自由边落在桌面（z≈1.0 cm）、越过静止半远端边缘约 4.1 cm（place 时 2.2 cm，释放动作内又外滑 1.9 cm）；折形是约 21/19 的偏置拱形，不是 20/20 对折；最终仍是站立拱形（z_p95 6.75 cm，控制组 6.87 cm），`final.png` 俯视为规整折叠矩形。

**折形口径（2026-11-02 定稿，修正版 b；同日第二步核对脚本后修正）**：L1 保留独立的“过折”折形定义，L2/L3 组合脚本本轮不改。

| 档 | 初态（固定） | 折形目标（冻结） |
|---|---|---|
| L1 | flat，seeds 4100–4109 | 过折：只把 place 末目标沿折向多伸 2 cm（`L1_XFOLD_OVERHANG=0.02`），45/90/135 三弧目标不变；拱形：释放后 flap 自由边落到边缘外桌面并再外滑 1.5–1.8 cm，最终行均值越边 39–40 mm、拱高 62–63 mm、最终 IoU 0.37–0.42（不是平面对折） |
| L2 | perturbed：bottom 折条 0.1615–0.1793 m，seeds 4200–4209 | nominal 20/20 左半折：width 0.20、无 overhang、place 横向 0.40 |
| L3 | crumpled：left 折条 0.20 m，seeds 4300–4309 | nominal 20/20 左半折：width 0.20、无 overhang、place 横向 0.40 |

**口径修正（2026-11-02 第二步）**：本段此前写“三档是三个不同的折形任务”，并把 L2 的 “width 0.16–0.18” 列为折形目标。核对 `day4-recovery-fold-episode.py` 后确认：0.16–0.18 是**初态 bottom 折条宽度**（`square-initial-plan.json` 的 `strips[0].width_m`），L2 与 L3 的 commanded 折形目标是同一个 nominal 20/20。正确划分是 **L1 与 L2/L3 两个折形任务**，L2/L3 是同一任务下的两种初态族（bottom 折条 / left 折条），不是第三个折形任务。

后果：**L1 vs L2/L3 的成功率差异不能解释为“初态难度”**——两者折形目标不同。L2 vs L3 可以对比，但两族的扰动方式与每 seed 条宽不同（L2 0.1615–0.1793，L3 固定 0.20），不是受控难度梯度。每档仍按自己冻结的折形定义单独判定、单独报告；三档汇总只能称**多任务平均**，不产出“L1 vs L3 成功率梯度”这类结论。L1 过折与 L2/L3 的 20/20 之间的差异记为已知任务差异，本轮不把 overhang 移植到组合脚本重验。完整冻结（目标、held gate、评价器、seed 规则、代码 manifest）见 [2026-11-02-GarmentLab日报-Stage4-任务定义冻结.md](2026-11-02-GarmentLab日报-Stage4-任务定义冻结.md)。

**第一步机制核实（2026-11-02，离线，未跑仿真）**：判定 overhang 属**最终目标偏移**，不是轨迹补偿。证据三条：① `03_place` 时 pick 粒子与 commanded place 目标之差为 overhang 例 −0.1…−2.3 mm、基础例 −0.1…−1.4 mm，两种配置都精确到位，没有需要补偿的 2 cm 欠达；② 把理想 20/20 折形刚体拟合到实测 flap，残差在两种配置里一致（4.0–4.9 mm、p95≈8 mm），只有平移量 dx 从 +4.0…+4.4 mm 变为 +21.1…+24.5 mm，折形质量未变；③ 差别发生在释放之后：基础例 flap 自由边始终悬空 16–20 mm 并沿折向内滑后摊平，overhang 例自由边在释放瞬间落到桌面（0.1–1.0 mm）、再外滑 1.5–1.8 cm 后稳定（04→06 ≤0.013 IoU）。限制：零扰动控制例（seed 0、overhang 0）同样保持且自由边悬空 17.1 mm，所以过折不是“唯一能保持的折法”，不能写成修复了机器人能力缺陷。完整表格与脚本见 [机制核实](day4-actionchunk-test/results/L1_OVERHANG_MECHANISM_20261102/review.md)。

**第二步任务定义冻结（2026-11-02，离线，未跑仿真）**：按“保留 L1 独立过折目标、L2/L3 保留各自已有目标”冻结三档定义，写入 [2026-11-02-GarmentLab日报-Stage4-任务定义冻结.md](2026-11-02-GarmentLab日报-Stage4-任务定义冻结.md)。要点：L1 = 7 动作、width 0.20、overhang 0.02、place 横向 0.42、held <0.01 m、`fold_metrics_yaw`；L2/L3 = 12 动作（5 recovery + 7 fold）、width 0.20、无 overhang、place 横向 0.40、held <0.03 m、left 默认 / right 镜像 fallback；开发 seeds 为 L1 4100–4109、L2 4200–4209、L3 4300–4309，正式 held-out 每格 20 seeds 尚未选定，规则已冻结（与开发集不相交、single-step 与 H=4 共用同一列表）。

核对时发现并修正两处口径：① L2 的 “0.16–0.18” 是初态折条宽度，不是折形目标，L2/L3 折形目标相同（见上一段修正）；② 当前两个折叠脚本（L1 与 L2/L3 组合）的每个动作都是单 waypoint chunk（断言 `executed_steps == 1`），H=4 只在更早的自由下降控制里出现过（`[1,1,4,1,1,1]`），“H=4 已在这三个任务上验证过”不成立，第 3 步需要真正实现，而不是换一个 flag（第 3 步已实现 `--execution arc4` 并完成配对，见下段）。另记录：L2/L3 的 left 在 4200/4300 恢复后释放即摊平（crossed 0.0、extent 回到 0.44–0.46），right 镜像两例均通过；left 是脚本默认折向，right 属另一个需按变更规则冻结的变体，不能在同一 seed 上把补跑算作该格成功。

**第三步表示层对齐（2026-11-02，实现 + 两任务各一对开发配对，已完成）**：给两个折叠脚本加 `--execution {single,arc4}`，默认 `single` 且行为不变；冻结映射为“只 chunk 四个 arc 目标，抓取/释放仍 H=1”——L1 single `[1,1,1,1,1,1,1]` / arc4 `[1,1,4,1]`，L2/L3 single `[1]*12` / arc4 `[1]*7+[4,1]`。目标按构造相同（两种表示在同一位置各算一次 `local_arc`），`result.json` 记录 `execution_mode / call_horizons / chunks / code_files`，并硬断言 `sum(call_horizons)==action_count`、chunk 目标与四行 `target_pose` 逐位相等、`executed_steps==4`；runner 重复同样检查。评价器统一到 `stage4_fold_metrics.py`（L1 15/15、L2/L3 4/4 复算一致，自身哈希自校验），配对审计 `stage4_representation_audit.py` 比对目标规则、结构、seed/初态/折向/常量/`code_files`/评价器哈希。

**配对实测（开发例，非验收）**：L1/4100（overhang 0.02）single 与 arc4 均 `passed=true`（crossed 1.000、IoU 0.3747、对齐 13.82 mm）；L2/4200 left single 与 arc4 均 `passed=false`（释放后摊平：extent 0.4424、z_p95 9.9 mm、crossed 0）；两组审计均 `PAIRS_COMPARABLE`。四例 `result.json` 的 `code_files` 与本地 24/21 项 manifest 逐条相等，下载 53 个文件哈希一致，**同一对内所有可比快照逐字节相同**，两对的目标差与五项指标差全为 0。结论边界：本实验证明的是**专家轨迹在两种表示下等价**（后端 `execute()` 逐行发出同一串 `control.move`，两种表示在 waypoint 之间都不消费观测），**不能写成“H=4 已验证”或“H=4 带来收益”**；策略层的 chunk 效应属后续 BC 阶段。L2/4200 left 的失败在冻结版下可复现（不是运行间随机），与旧通过例的差异仍是版本相关、原因未隔离。旧目录无 `execution_mode`/`code_files`，不可与 arc4 配对。完整报告见 [STAGE4_REPRESENTATION_PAIRS_20261102](../thesis/day4-actionchunk-test/results/STAGE4_REPRESENTATION_PAIRS_20261102/review.md)，冻结记录见 [2026-11-02-GarmentLab日报-Stage4-任务定义冻结.md §7.1](2026-11-02-GarmentLab日报-Stage4-任务定义冻结.md)。

**第四步分任务报告（2026-11-02，离线汇总，已完成；当日补齐任务 B 两例）**：按两个折形任务分别汇总 27 条已下载结果（含 `thesis/…/TASK_B_SINGLE_EVIDENCE_20261102-173708/` 下两例），全部用统一评价器 `stage4_fold_metrics.py` 复算（L1 17/17、L2/L3 8/10；2 条 pre-recovered-yaw 目录无 `fold_yaw`，按设计跳过）。脚本 `stage4_task_report.py`，原始表 `results/STAGE4_PER_TASK_20261102/task_report.json`，报告 `review.md`。A（L1 过折）：冻结版 seed 4100 的 single 与 arc4 各 1/1；开发历史过折 0.02 为 seeds 4100–4109 共 10/10，基线 overhang 0 为 4100/4105/4107 共 0/3（释放后回弹摊平）。B（L2/L3 nominal 20/20）：冻结版 L2/4200 left（single 2 次尝试 + arc4 1 次）与 L3/4300 left（single 1 次）全部失败，合计 **0/2 seeds、0/4 次尝试**；L2 left 含冻结版共 5 次尝试 1 次通过（通过例是 recovered-yaw 之前的版本）、L3 left 共 3 次尝试 0 次通过，失败均为释放后回弹摊平（extent 回到 0.442–0.458、z_p95 9.9 mm，held gate 通过）。补充的两例与既有同条件运行逐字节相同（L2 与 `001939` 的 9 个共有文件中 7 个相同、含 `result.json`；L3 与 `113247` 的 6 个几何/审计文件相同），说明该失败是确定性可复现结果，不是随机未命中。single 与 arc4 的指标差全为 0、快照逐字节相同，本数据里 H=4 无任何效果。多任务平均 = 0.50（A n=1、B n=2 个 seed），**只能叫多任务平均，不是难度曲线**，L1 vs L2/L3 的成功率差不得归因于初态难度。正式成功仍为 0。

## 下一步顺序

**第五步（第 7 步预备）正式批次登记（2026-11-02，未运行）**：按冻结文档 §0 登记 held-out seed 集合：L1 4110–4129、L2 4210–4229、L3 4310–4329，每档 20 个，与开发集不重叠，批次前一次固定、single/arc4 共用。初态参数仍由 `default_rng(seed)` 前三次抽样生成（对全部 30 个开发条目逐位复验，容差 1e-15）；L2 条宽改用同 seed 流第 4 次抽样 `U(0.16,0.18)`（开发条宽是人工写入值，无法从 seed 流复现，此差异在文档中声明）；L3 固定 0.20。`square-initial-plan.json` 由 30 条扩展为 90 条，两个初态 runner 的写死 seed 区间相应放宽，折叠 manifest 与折叠脚本未改。同时发现 `square-initial-files.json` 的 plan 条目自 6a 起未同步（`51e2800d` 对 `e2cfaebe`），本次刷新一并修正。批次驱动 `run-stage4-formal-batch.sh`（60 初态 + 120 次尝试，失败不中断、不覆盖）与汇总 `stage4_formal_report.py`（拒绝率 `(rejected+error)/总尝试`，空批次报空）已写好。**未运行**；正式成功判据阈值仍未冻结，且任务 B left 的释放后回弹是确定性失败，需先决定“先跑基线”还是“先解决保持”。详见 [正式批次准备](2026-11-02-GarmentLab日报-Stage4-正式批次计划.md)。远端部署已就位：4 个新文件与两份刷新后的初态 manifest 均上传并核对通过（两份 manifest 无排除项 `bad` 为空，哈希 `bccf3e15…` / `70b1793b…`）；`square-initial-files.json` 此次共修正 5 项落后条目，其中三项依赖取的是折叠/条带 manifest 已在远端验证的值。未生成任何 held-out 初态。

**当前立即执行（2026-11-02 暂停点）**：第 1–4 步已完成（机制核实、定义冻结、表示层配对、分任务报告），任务 B 的 L2/4200 与 L3/4300 left 冻结版 single 证据也已补齐（均失败，见 [任务 B single 证据](../thesis/day4-actionchunk-test/results/TASK_B_SINGLE_EVIDENCE_20261102-173708/review.md)）。right 开发验证已完成：v1 四例全部通过且逐位可复现，补充审计见 [B_RIGHT_DEV_AUDIT_SUPPLEMENT_20261102](../thesis/day4-actionchunk-test/results/B_RIGHT_DEV_AUDIT_SUPPLEMENT_20261102/review.md)。**现在唯一待执行的是 `b-right-dev-v2` 批次**：18 个剩余开发 seed、只跑 single，已登记、未运行，命令与核对步骤见 [扩展计划](2026-11-02-GarmentLab日报-Stage4-B项right扩展计划.md)。第 7 步正式批次仍未运行且与前一步无依赖关系，held-out 不生成、不运行；正式成功判据阈值仍未冻结，跑得再多也只有开发门槛 `passed` 与拒绝率。不改阈值、不加动作、不在批次中途改 seed 或折向。正式成功仍为 0。

注：本次测得同一对内逐 seed 逐字节相同，因此若继续扩大 per-seed 配对复跑，信息量为零；若要缩减配对 seed 范围（例如只做 1–2 对 + 其余种子只跑 single），这属于计划变更，须按冻结文档 §0 的变更规则先书面登记原因与影响，不能静默改。

1. ~~上传 recovery 3 文件，跑 L2 4200 与 L3 4300 两个 recovery 冒烟。~~ **均通过**：L3 4300 残差 8.0 µm、L2 4200 残差 8.6 µm，5 动作展平。
2. 检查 `recovery_metrics`：刚性残差 vs flat、pick 位移、extent 是否回到平铺量级；检查 `recovered.png`。若 5 动作展不平，先调 spread 目标高度/抬升高度/settle（不增加动作数）。
3. 实现 7 动作折叠 runner（合并 approach+descend、去 retreat），在 L1 上重新验证折叠指标。
4. L1 yaw-aware 复验：4100/4105/4107 基础版均失败（折到位、释放后回弹；三例结果均已下载核对），零扰动对照通过；过折 0.02 在全部 10 例（4100–4109）通过且 04→06 稳定，折形为约 21/19 偏置拱形（crossed 全 1.000、IoU 0.365–0.423、对齐 13.8 mm、z_p95 67.5–67.7 mm）；记录 yaw 测量、crossed、held 误差与 final.png 已齐。
5. 组合 initial_state → recovery(5) → fold(7)，在 L1/L2/L3 上各跑一遍，统计动作数并验证三档可完成折叠。
6. 进入第 7 步正式批次（每档 ≥5 成功、失败/拒绝率、10 次 reset、接口/视频/30 图/验收表）。

## 参考文档

- `day4-actionchunk-test/SQUARE_INITIAL_STRIPFOLD_V1.md`：6a 的完整演进（角点折、动态空动作、条宽阈值、bottom/left 选择）。
- `day4-actionchunk-test/SQUARE_INITIAL_LIFTDROP_V1.md`：v1/v2/v3 的失败证据。
- `day4-actionchunk-test/SQUARE_L1_XFOLD_V1.md`：9 动作 L1 折叠（062602/065314）。
- `day4-actionchunk-test/SQUARE_BACKEND_RESET_V1.md`：第 5 步 Backend/reset 10 循环。
- `DAY4_NEXT_STEPS.md`：当前收尾计划。


## 2026-11-02 汇总器修复与 right 开发验证登记（尚未运行）

stage4_formal_report.py 已把缺失结果转换为 error 尝试，按档/表示/任务计入 attempts 和 (rejected+error)/attempts；空批次保持 null。新增 test_stage4_formal_report.py，8 项纯离线测试通过（一次通过+一次缺失结果得到2次尝试、50%拒绝率）。已有结果与日志不重复计数，非 held-out 日志不纳入，重试独立计数。

按冻结文档最新 b-right-dev-v1 条目，仅以开发 seeds 4200/4300 各运行 single/arc4 验证 right 的释放后保持；独立 manifest 与目录白名单在任何新结果前登记。held-out 与正式批次暂停，正式成功仍为0。检查范围仅现有 OPEN+30ticks+180settle 的终态，不宣称第二时刻保持或长期稳定。


## 2026-11-02 b-right-dev-v1 开发复验与移交后审计完成

汇总器缺失结果分母修复与8项离线测试已通过；原项目代码与已测试副本SHA256一致（9a757d34…）。一次通过+一次无结果error的合成回归输出2次尝试、50%拒绝率；空批次保持null。

L2 4200的right single/arc4由本聊天在移交前完成；L3 4300采用另一聊天产出的最早外部single/arc4，按目录启动时间选择而非passed。两对均通过原版PAIRS_COMPARABLE，四份选定结果held gate通过、crossed=1.0，L2 IoU=0.559091、L3 IoU=0.562997；各对目标差及五项指标差值精确为0。底层21项代码不变，四份结果的独立23项变体manifest、配置和初态文件哈希均核对一致。

共下载核验66个远端文件，包含6份完整开发结果：选定4份配对结果与2份额外L3 single重复尝试。额外尝试原样保留，不增加独立seed覆盖，不计算正式成功率。用户移交后本聊天仅下载审计，未再提交GPU仿真，未终止已在途远端进程。

结论仅为每档一个开发seed在OPEN后30 release ticks+settle(180)终态保持；没有独立退让、第二retention样本或长期稳定性验证，不能外推整个开发集/held-out，更不能解释为BC策略或H=4性能提升。right为独立变体，不替换left失败或默认定义。held-out与正式批次保持暂停，正式Stage 4成功仍为0。

完整报告：[right开发复验与移交后审计](../thesis/day4-actionchunk-test/results/TASK_B_RIGHT_DEV_V1_20261102-183740/review.md)。

补充交叉核对（2026-11-02）：把主审计未采用的 4200 arc4 尝试 `025355-106410` 与 4300 single 重复尝试 `031535-711404` 一并核对，5 个目录 77 项检查全部通过；同 seed 全部 7 次已下载尝试（4200 三例、4300 四例）的 `final.npz` 441 个顶点逐位相同（max|Δ|=0），包括并发在途的 4200 arc4 两例。该核对不新增 seed、不改任何阈值、不改变上述结论。[补充审计](../thesis/day4-actionchunk-test/results/B_RIGHT_DEV_AUDIT_SUPPLEMENT_20261102/review.md)。

right 开发覆盖扩展 `b-right-dev-v2` 已登记、未运行：L2 4201–4209、L3 4301–4309 共 18 个剩余开发 seed，先登记初态哈希再跑 right single；不跑 arc4、不冻结阈值、held-out 不动。见 [扩展计划](2026-11-02-GarmentLab日报-Stage4-B项right扩展计划.md)。

## 2026-11-02 暂停点交接：right 验证完成，v2 覆盖扩展待运行

### 已完成（开发验证，非正式成功）

| seed | 档 | 表示 | 结果目录 | crossed | extent (m) | z_p95 (mm) | held |
|---|---|---|---:|---:|---|---:|---|
| 4200 | perturbed | single | `023749-213160` | 1.000 | 0.227265 × 0.421146 × 0.061256 | 69.068 | 通过 |
| 4200 | perturbed | arc4 | `025337-835928` / `025355-106410` | 1.000 | 同上 | 69.068 | 通过 |
| 4300 | crumpled | single | `031351-818421`（另 `031336`、`031535`） | 1.000 | 0.244623 × 0.427518 × 0.061217 | 69.078 | 通过 |
| 4300 | crumpled | arc4 | `035003-534230` | 1.000 | 同上 | 69.078 | 通过 |

同档 single 与 arc4 的 12 个公开动作（label / target_pose / command）逐项相同，终态 441 顶点逐位相同；同 seed 全部 7 次已下载尝试顶点 `max|Δ|=0`（含 4200 两个并发在途 arc4）。逐例核对 23 项变体身份、21 项底层身份、config、初态登记条目，并从 `final.npz` 重算指标，77 项检查 0 失败。
产物：主审计 [TASK_B_RIGHT_DEV_V1_20261102-183740](../thesis/day4-actionchunk-test/results/TASK_B_RIGHT_DEV_V1_20261102-183740/review.md)；补充审计 [B_RIGHT_DEV_AUDIT_SUPPLEMENT_20261102](../thesis/day4-actionchunk-test/results/B_RIGHT_DEV_AUDIT_SUPPLEMENT_20261102/review.md)；工具 `day4-actionchunk-test/stage4_b_right_audit.py`。

### 待执行（唯一一项）
`b-right-dev-v2`：L2 4201–4209、L3 4301–4309，共 18 个剩余开发 seed，每个先登记初态哈希再跑一次 right single。已登记、未运行，完整命令见 [扩展计划](2026-11-02-GarmentLab日报-Stage4-B项right扩展计划.md)。要点：
- 上传 4 个文件**原样**（manifest 的登记哈希是含 CRLF 的原始字节，不能转行尾）：`run-recovery-fold-right-v2.sh`、`stage4-b-right-dev-v2.json`、`square-recovery-fold-right-v2-files.json`、`run-stage4-b-right-dev-v2-batch.sh`。
- 远端核对期望 `V2_MANIFEST_BAD [] 23`，四个自哈希 `MATCH True`（`2fff0bf9…`、`adf4c9a8…`、`3822bd98…`、`cb947b85…`）。
- 运行：`cd <remote-root> && bash run-stage4-b-right-dev-v2-batch.sh dev-v2`。
- 状态：`stage4-b-right-dev-v2-dev-v2/`（`batch.log`、`attempts.jsonl`、逐 seed 日志）；初态登记：`stage4-b-right-dev-v2-initials.json`。
- rejected 继续、不重试不覆盖；初态失败或缺结果目录停止整批；中断重跑跳过已有结果目录的 seed，强制重跑换新 tag。


下载后汇总：`python -I stage4_b_right_dev_v2_audit.py --results <下载根目录> --attempts <state>/attempts.jsonl --out <输出>`

### 边界（不得越过）
- 正式 Stage 4 成功仍为 0；`passed=true` 只是脚本开发门槛。
- held-out（L1 4110–4129、L2 4210–4229、L3 4310–4329）未生成、未运行，正式批次暂停。
- v2 只跑 single，不产生 H=4 收益或精度结论；v1 的表示等价已在两个初态上逐位验证。
- right 是独立变体，不替换 left 的失败记录，也未自动成为任务 B 的默认定义；是否采用需按冻结文档 §0/§4.2 另行登记。
- 只检验 OPEN 后 30 release ticks + settle 的终态，无独立退让或第二 retention 样本，不声称长期稳定。


### 文档入口
[2026-11-02-GarmentLab日报-Stage4-任务定义冻结.md](2026-11-02-GarmentLab日报-Stage4-任务定义冻结.md) · [2026-11-02-GarmentLab日报-Stage4-B项right扩展计划.md](2026-11-02-GarmentLab日报-Stage4-B项right扩展计划.md) · [2026-11-02-GarmentLab日报-Stage4-正式批次计划.md](2026-11-02-GarmentLab日报-Stage4-正式批次计划.md) · [DAY4_NEXT_STEPS.md](DAY4_NEXT_STEPS.md) · [DAY4_ACCEPTANCE_TRACKER.md](DAY4_ACCEPTANCE_TRACKER.md) · [README.md](README.md)
