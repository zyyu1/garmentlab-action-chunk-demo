# Stage 4 收尾计划（当前有效版本）

## 2026-11-02 A1：b-right-dev-v2 预检完成（仅离线）

`stage4_a1_right_v2_preflight.py` 48/48 通过；未启动仿真、未生成 held-out、正式成功仍为 0。发现并修正一处登记描述与实际采样不一致：配置原写 `settle(180 for perturbed, 240 for crumpled)`，实际 runner 对两档都在 fold OPEN 后执行 30 release ticks + `settle(180)`；`settle(240)` 只在 recovery 展开后，180/240 是初态生成 settle。配置修正为 v2.1（仅描述字段，无行为改动），config 新哈希 `91c0fe7f…`、variant manifest `c3e34c91…`；入口 `3822bd98…`、批次驱动 `d4c00162…`、21 项底层 `cb947b85…`、初态 manifest `70b1793b…` 未变。B/C 新增文件不在 21/23 项身份中，登记 runner 未导入它们。初态 registry 本地不存在，A2 首次生成时在远端创建。

下一步 A2：上传修正后的 4 个 v2 文件（原字节、不转换行尾），远端复核 `V2_MANIFEST_BAD [] 23` 与四个新哈希，再按 4201→4209、4301→4309 运行 right single。证据：[A1 预检报告](day4-actionchunk-test/results/STAGE4_A1_PREFLIGHT_20261102/review.md)、[扩展计划](STAGE4_B_RIGHT_DEV_V2_PLAN.md)。

## 2026-11-02 B项：正式成功判据 v1.0.0 已交付（仅离线）

以 [STAGE4_SUCCESS_CRITERIA_V1.md](STAGE4_SUCCESS_CRITERIA_V1.md) 与 `day4-actionchunk-test/stage4-success-v1.json` 为当前成功判据。A/L1过折和B/nominal分任务评价；新增OPEN完成后逐物理步0..330采集、3.5–5.5秒连续几何及稳定窗口。原目标、held门槛和7/12动作预算不变。独立评价manifest登记新成功层，旧折叠manifest/runner未修改。

13项离线测试通过；31个历史目录复算20个满足对应终态几何、11个不满足，但全部缺新协议完整时序证据，不能追认正式成功。稳定阈值为预登记工程容差，尚待开发复验。评价配置与分类器已完成，不等于runner采样接入或正式批次已解锁。下一步需单独接入记录并用开发seed复验；held-out保持暂停，正式成功0。right是否正式采用仍需独立登记。下方“数值阈值未冻结”等段落保留为本次之前的历史状态。

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

> 命名约定：Stage 表示按验收推进的工作阶段，每个阶段可跨多天；原 Day N 对应 Stage N。为兼容既有入口，`DAY4_*.md`、脚本名和结果目录名保留；日报文件名已统一改为 Stage。本计划内的“第 N 步”是 Stage 4 内部的收尾子步骤编号，与 Stage 编号无关（如“第 7 步正式批次”不等于 Stage 7）。

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

限制：本组合脚本在 OPEN 后额外30个release tick和180个settle步取样，未单独退让、未保存第二个延迟保持快照。不得将本轮算作退让后保持或正式批次验收。正式成功仍为0，评价未冻结。L2 right 随后通过（`151711-625509`：12 动作、crossed 1.0、extent 0.227×0.421、z_p95 0.0691、5 文件哈希核对一致），L2/L3 的 right 边组合开发例齐备。下一收敛点为 L1 yaw-aware 复验，再统一路径选择与评价冻结；不启动参数网格、翻腕或完整三阶段折衣。

## 当前步骤：第 6 步进行中：L2 4200 通过，L3 4300 lift 超时，诊断 4300

第 2 步 v6 已通过（末端位置误差0.4733mm、末臂速0.00860rad/s、最大锚点误差1.3906mm、块中心最大跟随误差0.0121mm）。第 3 步离线复核发现：原 y 向候选从 v5 实际抓取关节连续跟踪时，在 place 第 15 个子目标（y=-0.277, z=0.097）被关节限位阻断，最终点 y=-0.25, z=0.033 在该分支上不可连续到达；3.15rad 不是单纯离散 IK 分支选择。

改用同一方巾的 x 向中心对折：`left_sleeve` 槽位、左边缘折到右边缘，仍为 9 个公共动作、同一接口和物理配置。用 v5 实际初态几何对 8 个 descend 分支做连续跟踪，8/8 完成，最大相邻关节变化 ≤0.100rad。

首次运行 `day4-square-l1-xfold-v1-20261101-062036-672015` 因初始化属性错误失败；修正后有效运行 `day4-square-l1-xfold-v1-20261101-062602-150760` 完成：`passed=true`、errors为空、9个公共动作状态一致、held gate 通过（位置0.5033mm、末臂速0.000916rad/s、锚点间隙1.9907mm）、生命周期检查全部通过。运行时折叠各阶段相邻5步关节变化≤0.0206rad、最大速度≤0.257rad/s，无跳变。`moving_half_crossed_fraction=1.0`、投影IoU=0.6617、对齐6.358mm、静置4s漂移0.860mm。

已下载并完成视频/阶段图视觉审查：折叠前后投影由完整方巾变为右半幅，左半覆盖在右半上；释放、退让、静置3s/4s后形状保持，无整件搬移、翻转或持续滑动。折叠层左侧略抬/卷曲（垂直间隙中位数22.1mm、p90 56.8mm，`cloth_z_p95=68.66mm`），固定半片被拖拽约1.1cm；不冻结正式高度/重叠阈值。详见 [x向L1候选](day4-actionchunk-test/SQUARE_L1_XFOLD_V1.md) 和 [视觉审查](day4-actionchunk-test/results/day4-square-l1-xfold-v1-20261101-062602-150760/review.md)。

第 4 步独立重复 `day4-square-l1-xfold-v1-20261101-065314-576894` 也完成：`passed=true`、errors为空、9个公共动作，步数与第一次完全相同（469/616/657/813/961/1119/1293/1375/1550）。`result.json`、`hold_trace.jsonl`、`state_trace.json`、`postcross_trace.npz`、`00_initial.npz`、`10_final_3s.npz` 的 SHA256 与第一次逐字节一致；`episode.mp4` 文件哈希不同，解码帧全图平均差约20.9灰度级，阶段图显示第一次蓝色网格背景、第二次浅灰背景，机器人位姿和折叠形状相同。审查见 [第二例 review](day4-actionchunk-test/results/day4-square-l1-xfold-v1-20261101-065314-576894/review.md)。

第 3/4 步开发判据满足：两次开发运行均完成真正对折；同配置物理轨迹可重复，但不证明种子/初态扰动/难度鲁棒性。两次均为开发候选，不计正式成功。

第 5 步整合候选已上传：`backends/prepared_square_backend.py`（yaw 映射、静止 HOLD 自动 60 步 StableHold、OPEN 释放后允许同槽位重抓取、`reset` 场景重置）、`garmentlab_backend.py` 控制工厂钩子、`multi_prepared_grasp_control.py` 的 `enable_regrasp/prepare_episode_reset/after_scene_reset`，以及测试入口 `day4-prepared-square-backend-reset.py`。清单 20/20 预检通过。

10 循环已通过：远端 `day4-prepared-square-backend-reset-20261101-080713-870146`，`passed=true`、`cycle_count=10`、`ERRORS=[]`、`RESULT_VERIFIED True`。10 个循环全部 reset 检查通过并保存读回：三槽 released/disabled/unused、约束存在且路径唯一、布料 0.4×0.4、z_p95=9.9mm、PNG 480×640。第 1 循环完整折叠 IoU 0.6971、对齐 5.350mm、z_p95 69.39mm，held gate 0.474mm/0.000915rad/s/2.034mm；第 2 循环同 episode 重抓取 `reuse_count=2`、激活最大位移 1.2718mm、yaw 误差 1.9e-4rad；第 3–10 循环短程 held 4.093mm/0.003331rad/s/1.427mm、hold 60 步。详见 [Backend reset 候选](day4-actionchunk-test/SQUARE_BACKEND_RESET_V1.md) 和 [10循环审查](day4-actionchunk-test/results/day4-prepared-square-backend-reset-20261101-080713-870146/review.md)。

第 5 步开发判据满足：同一 episode 可重抓取；连续 10 次 reset/rollout 无状态残留或保存错误。yaw、抓取、静止保持、附件清理和 reset 已接入正式 Backend 候选。正式成功仍为 0。

第 6 步拆为 6a（三档初态）与 6b（recovery + 动作预算）。

**6a 已完成**：L1/L2/L3 各 10 张、共 30 张初态图全部 `passed=true`，三档肉眼可区分（L1 平铺、L2 宽短折带、L3 窄高半折）。最终方案：

- L1：平整方巾；L2：一条 bottom 折条 width 0.16–0.18（典型 extent 0.42×0.25、z 0.06）；L3：一条 left 半折 width 0.20（典型 extent 0.25×0.43、z 0.06）。
- plan `e2cfaebe…`（version square-initial-v3）、yaml `a42fec8a…`、stripfold script `178ab10c…`、strip control `49075fb4…`、run script `33a4e142…`；30 张对比图本地 `results/initial30_sheet_v2.png`。
- 已排除：lift→原高度释放（平铺）、原始动态 Control（3 cm reach 空抓）、角点折角（release 弹平）、left 0.165 / bottom 0.11（展开）、L3 top 第二折（近基座不可达）。

**6b 进行中**：

- 5 动作 recovery 已在 L2 4200（`095917-466741`）与 L3 4300（`095042-400051`）验证：刚性残差 8.0/8.6 µm、`action_count=5`。
- 7 动作折叠 v2（`102118-812499`）通过：approach→close→arc45→arc90→arc135→place→release；crossed 1.0、对齐 6.357 mm、z_p95 68.60 mm、held 与 9 动作一致；IoU 0.607（9 动作 0.652–0.662）。
- 组合 recovery+fold：L2 4200（`103502-594762`）**12 动作通过**（recovery 8.6 µm、fold crossed 1.0、extent 0.232×0.421、z 0.0595）。
- L3 4300 组合（`104603-419951`）失败：recovery 正常，fold 动作执行且锚点跟随，但释放后折半摊平（crossed 0.0）。实测 recovered 相对 flat 的刚性 yaw 差 Δ=-2.007°；旧版用初始 yaw，折叠目标偏差 13.9 mm。已改为 `fold_yaw = case_yaw + Δ`（script `83d1fb24…`，已被第 3 步版本 `ddad4116…` 取代，见上节）；修正后 4 个折叠目标与初始 L3 成功轨迹经同一刚体变换一致到 0.1 mm。
- **right 槽位镜像半折 fallback 已实现**：组合脚本新增 `--fold-edge right`（右边缘 pick、lateral=-x、moving=右半）；默认 `left` 路径不变。run 脚本第二个参数 `left|right`，manifest 已更新。
- 7 动作 fold runner 原固定 yaw=0；L1 yaw-aware 版本已准备（`l1_yaw_fold_geometry.py` + `day4-l1-xfold-yaw-aware.py` + `run-l1-xfold-yaw-aware.sh`，24 项哈希），待远端复验。

recovered-yaw 重跑结果：L3 4300 `left` 仍回弹（`113247-548209`，crossed 0.0）；改用 `right` 后 **通过**（`114705-003675`，12 动作、crossed 1.0、extent 0.2446×0.4275、z_p95 0.0691）。L2 4200 `left` 回弹（`115933-089864`，crossed 0.0）；与旧成功例 `103502-594762` 的 recovered.npz 逐字节相同，fold yaw 仅差 0.0025 rad、place 差约 1.0 mm，说明该候选处于双稳边缘。L2 4200 `right` **通过**（`151711-625509`，12 动作、crossed 1.0、extent 0.2273×0.4211、z_p95 0.0691、held 1.45 cm/0.00154 rad/s/锚点 2.33 mm），脚本/runner/manifest 未改。

下一步：L1 7 动作 yaw-aware 复验。旧 `day4-l1-xfold-7actions.py` 固定 yaw=0；新增 `l1_yaw_fold_geometry.py`、`day4-l1-xfold-yaw-aware.py`、`run-l1-xfold-yaw-aware.sh`、`square-l1-xfold-yaw-files.json`（24 项哈希），旧文件保持不动。新脚本读 L1 初始目录的 `initial_geometry.npz['settled']`，用局部网格→世界顶点的刚体拟合测 yaw（与 `case['yaw_rad']` 差 ≤0.02 rad），7 个公开动作在 cloth-local 帧生成，保留 1 cm held gate 并新增 crossed≥0.5。离线验证：yaw=0 时弧目标与旧版本差 6.0e-9 m；合成 ±0.033/0.13/−0.149 rad 下指标不变。

首例 4100（`day4-l1-xfold-yaw-aware-20261102-165141-003161`）failed：测量 yaw 与 case 差 −4.5e-8，`03_place` 的 cloth-local 折叠几何与 yaw=0 dev 例几乎逐点相同（flap 局部 x [0.2306,0.4006]，z 0.035），但释放动作内 flap 回滑 1.3 cm，30 tick 后 crossed 0.852，180 步静置后完全展平（crossed 0、z_p95 0.0099）。属于折到位后保持不住，不是 yaw/弧错误。

第二例 4107（`day4-l1-xfold-yaw-aware-20261102-171533-773483`，yaw −0.1488，平移 1.78 cm）同样 failed：yaw 差 −4.1e-8，held gate 通过（误差 3.6 mm、锚点 1.99 mm），place flap 局部 x [0.231,0.400]、z 剖面 [0.068,0.062,0.039,0.030,0.030] 与 dev 的 [0.231,0.401]/[0.067,0.060,0.037,0.029,0.029] 几乎相同；04 crossed 0.995、30 tick 后 0.662、180 步后 0.0。两例 place 时都是约 6.7 cm 高的拱形/卷曲，释放后回弹；每动作实际物理步数随初始位姿变化（close/arc45/arc90/arc135/place：dev 107/156/148/156/174，4100 109/155/175/202/208，4107 111/160/174/176/149）。结论：同一折法在不同初始位姿下处于保持临界，初始位姿经机械臂 IK 路径改变了折叠的动力学。

零扰动对照 `initial-cases/dev-zero-perturbation/`（dev 的 `00_initial` 441 点作为 settled，yaw=0、平移 0）**通过**（`173908-646355`），且 close/arc45/arc90/arc135/place/release 物理步数 107/156/148/156/174/82 与 dev 逐项相同，证明 yaw-aware 装载路径是对 dev 状态的精确重放；4100/4107 的失败只来自初始位姿改变机械臂 IK 路径。

诊断重跑（4100，`175052-846321`）：`03_place` crossed 1.000、flap qx [0.231,0.401]、z_p95 0.0701；`03_hold_end` crossed 1.000、qx [0.231,0.400]、z_p95 0.0700（对齐 5.41 mm、IoU 0.583），固定持握 60 步内变化 ≤1 mm；`04_released` 内缘 0.231→0.218、30 tick 后 crossed 0.852、180 步后 0。回滑由 ungrasp 触发；自由拱形是浅势垒平衡（对照例自由状态 zmax 0.069/chord 0.157 稳定，4107 的 chord 0.151→0.125 展开）。速度读取不可用（`ClothPrimView` 无 `get_world_velocities`）。4105（`180153-252676`，yaw +0.0069、平移 1.06 cm）也 failed；已下载核对，事实一致。

下一步：在 4100 上试过折 `L1_XFOLD_OVERHANG=0.02` —— 只把 place 末目标沿折向多伸 2 cm（弧的 45/90/135 目标不变），flap 自由边越过静止半远端边缘约 2 cm、折缝右移约 1 cm（约 21/19 轻微不对称，如实记录），用“尖端落在边缘外桌面”的自重锁住展开。默认 `overhang=0` 与旧行为逐字节一致；runner 断言 `fold_overhang_m` 与 `L1_XFOLD_OVERHANG` 一致。暂不改阈值、不加动作。

```powershell
scp -P 23636 "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\l1_yaw_fold_geometry.py" "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\day4-l1-xfold-yaw-aware.py" "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\run-l1-xfold-yaw-aware.sh" "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\square-l1-xfold-yaw-files.json" root@connect.nmb2.seetacloud.com:/root/autodl-tmp/
```

```bash
L1_XFOLD_OVERHANG=0.02 bash /root/autodl-tmp/run-l1-xfold-yaw-aware.sh /root/autodl-tmp/day4-square-initial-20261031-094446-203825   # 4100 过折
```

**过折复验结果：10/10 通过**（4100–4109）。全部 7 动作、yaw 差 <1e-7、`fold_overhang_m=0.02`、crossed 全 1.000、final.png 640×480；最终 IoU 0.365–0.423、对齐均为 13.8 mm、z_p95 67.5–67.7 mm、held 误差 ≤4.1 mm。基础版（overhang 0）里 4100/4105/4107 的 04/05/06 crossed 为 1.000→0.852→0.000、1.000→0.948→0.000、0.995→0.662→0.000；过折版在 ungrasp 后的 04 定型，05/06 与 04 只差 ≤0.013 IoU。逐例目录与数值见日报 L1 段。

几何代价：十例最终 qx 剖面几乎逐点相同（0.438/0.361/0.292/0.243/0.317/0.397，4108 整体内移约 5 mm），与初始 yaw/平移无关；折脊 qx≈0.29（控制组 0.25），flap 自由边落在桌面、越过静止半远端边缘约 4.1 cm（place 时 2.2 cm）；折形是约 21/19 的偏置拱形，不是 20/20 对折，最终仍为站立拱形（z_p95 6.75 cm，控制组 6.87 cm），俯视 `final.png` 为规整折叠矩形。

**折形口径已定稿（修正版 b，2026-11-02）**：L1 保留独立“过折”定义（`L1_XFOLD_OVERHANG=0.02`，只延长 place 末目标 2 cm，折形约 21/19 偏置拱形），L2/L3 组合脚本本轮不改（仍为 nominal 20/20 左半折：width 0.20、无 overhang、place 横向 0.40；L2/L3 的差别在初态——L2 为 bottom 折条 0.1615–0.1793 m，L3 为 left 折条 0.20 m）。因此 **L1 与 L2/L3 是两个不同折形任务**：L1 vs L2/L3 的成功率差异不能解释为“初态难度”；L2 与 L3 是同一折形目标下的两种初态族，可比但不是受控难度梯度。每档只按自己的冻结折形定义单独验收与报告；三档汇总只能称多任务平均，不做跨档难度归因或成功率梯度比较。该差异记为已知任务差异，不在本轮移植 overhang 到组合脚本重验。**第一步机制核实已完成（离线）**：overhang 属最终目标偏移而非轨迹补偿——place 到位误差 ≤2.3 mm、折形拟合残差与基础例一致（仅平移从 +4 mm 变 +22…+24 mm）、差异来自释放后 flap 自由边落到边缘外桌面（基础例悬空 16–20 mm 后摊平）。限制：零扰动控制例用名义目标也能保持，不得写成修复了机器人缺陷。**第二步任务定义已冻结（2026-11-02）**：目标、held gate、评价器身份、seed 规则与代码 manifest 见 [STAGE4_TASK_DEFINITION_FREEZE.md](STAGE4_TASK_DEFINITION_FREEZE.md)；冻结时修正两点——L2 的 “0.16–0.18” 是初态折条宽度而非折形目标；当前两个折叠脚本（L1 与 L2/L3 组合）在第二步入库时均为单 waypoint chunk（`executed_steps==1`），H=4 当时尚未实现；第 3 步已补齐 `--execution arc4`（见下节），但仍未在远端跑过配对。机制核实见 [review](day4-actionchunk-test/results/L1_OVERHANG_MECHANISM_20261102/review.md)；决策见 [2026-11-02 日报](2026-11-02-GarmentLab日报%20Stage4%20L2L3初态与6b交接.md) 与 [验收状态](DAY4_ACCEPTANCE_TRACKER.md)。

下载 4105 结果：

```powershell
scp -P 23636 -r root@connect.nmb2.seetacloud.com:/root/autodl-tmp/day4-l1-xfold-yaw-aware-20261102-180153-252676 "E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\results\"
```

当前脚本 hash `0aab8e7c…`（geometry `aa1f8a6e…`、runner `560d38bb…`），4 个文件都需覆盖上传。零扰动对照已通过；4100/4105/4107 基础版均失败，过折 0.02 在全部 10 例（4100–4109）通过（04→06 稳定，折形为约 21/19 偏置拱形）。下一步：折形口径与任务定义均已冻结（L1 独立“过折”、L2/L3 保留 nominal 20/20、两档单独验收），第 3 步的表示层已实现并完成两任务各一对开发配对（见下节；两对内部逐字节相同，只证明表示等价，不证明 H=4 收益），第 4 步分任务报告也已完成并补齐任务 B 的冻结版证据（见上节：L1 冻结版 1/1、L2/L3 冻结版 0/2，多任务平均 0.50 不是难度曲线），最后进入第 7 步正式批次（held-out seed 集合、初态 plan 与批次工具已登记，见下节“第 7 步”；尚未运行，且成功判据阈值未冻结）；本批 10 例只算开发复验，正式批次仍需失败/拒绝率、10 次 reset、接口/视频/30 图与验收表。命令见日报与下节。完整交接见 [2026-11-02 日报](2026-11-02-GarmentLab日报%20Stage4%20L2L3初态与6b交接.md)。正式成功仍为 0。下方第 1/2 步及旧交接均为历史状态。

## 第 4 步：分任务报告（已完成）

按用户要求的顺序，前两步（overhang 机制核实、定义冻结）与第 3 步（表示层）已完成，第 4 步的分任务报告已写入 [day4-actionchunk-test/results/STAGE4_PER_TASK_20261102/review.md](day4-actionchunk-test/results/STAGE4_PER_TASK_20261102/review.md)，数据表由 `stage4_task_report.py` 从 27 条已下载 `result.json` 生成（`task_report.json`，可复算；根目录含 `thesis/…/TASK_B_SINGLE_EVIDENCE_20261102-173708/`）。

| 折形任务 | 冻结版（seed 级） | 开发历史（旧版代码） | 失败形态 |
|---|---|---|---|
| A：L1 过折 | 1/1（4100；single 与 arc4 各 1/1） | 过折 0.02：seeds 4100–4109 共 10/10；基线 overhang 0：4100/4105/4107 共 0/3 | 基线失败=释放后回弹摊平（crossed 0、z_p95 9.9 mm） |
| B：L2/L3 nominal 20/20 | **0/2**（L2/4200 left、L3/4300 left；共 4 次尝试全失败） | L2 left 含冻结版共 5 次尝试 1 次通过（recovered-yaw 之前）；L3 left 共 3 次尝试 0 次通过 | left 失败=释放后回弹摊平（extent 回到 0.442–0.458、z_p95 9.9 mm），held gate 均通过 |

- single 与 arc4：L1/4100 均 1/1、L2/4200 left 均 0/1，两组指标差全为 0、快照逐字节相同 → 本数据里 H=4 无任何效果，不存在可报的“H=4 vs single”成功率差异。
- 多任务平均（只有两个任务有冻结版数据）= 0.50（A n=1、B n=2 个 seed）。**只能叫多任务平均**，不能当难度曲线，不能用 L1 vs L2/L3 的成功率差解释初态难度。
- 本步未建立：正式成功（仍为 0）、held-out seeds、rejection rate、10 次 reset、接口/视频/30 图。
- 任务 B 冻结版证据**已补齐**（2026-11-02）：L2/4200、L3/4300 left 各一次冻结版 single，均失败，`code_files` 与 21 项 manifest 一致、18 个下载文件哈希一致、评价器复算通过；与既有同条件运行逐字节相同（L2 与 `001939` 7/9 文件含 `result.json` 相同，L3 与 `113247` 6 个几何/审计文件相同），说明该失败是确定性可复现结果。证据见 [TASK_B_SINGLE_EVIDENCE_20261102-173708](../thesis/day4-actionchunk-test/results/TASK_B_SINGLE_EVIDENCE_20261102-173708/review.md)。L3 只补了 single，没有 arc4 配对。

## 第 7 步：正式批次准备（已登记，未运行）

按冻结文档 §0 登记，完整运行手册见 [STAGE4_FORMAL_BATCH_PLAN.md](STAGE4_FORMAL_BATCH_PLAN.md)。

- **seed**：L1 `4110–4129`、L2 `4210–4229`、L3 `4310–4329`，每档 20 个，与开发集不重叠，批次前固定、single/arc4 共用；已写入 `square-initial-plan.json`（30→90 条）与 `stage4-heldout-seeds.json`。
- **初态参数**：dx/dy/yaw 沿用 `default_rng(seed)` 前三次抽样（对 30 个开发条目逐位复验）；L2 条宽改为同流第 4 次抽样 `U(0.16,0.18)`（开发条宽为人工值，已声明差异）。
- **代码**：两个初态 runner 的 seed 断言放宽（原写死开发区间，held-out 无法生成）；两份折叠 manifest 与折叠脚本未改。刷新两份初态 manifest 时发现 5 项落后于远端：plan 条目自 6a 起未同步（`51e2800d` vs `e2cfaebe`），另有 `square_start.py`、`multi_prepared_grasp_control.py`、`square-difficulty.yaml` 三项仍是旧版。三项依赖的新值取自两份折叠 manifest 与条带 manifest 已共同钉住、且远端核对通过的值，不是仓库本地哈希。
- **远端状态（2026-11-02）**：4 个新文件已转 LF 上传，远端完整 SHA256 与本地一致；两份刷新后的 manifest 也已上传，无排除项的完整核对通过（两个 `bad` 均为空，manifest 哈希 `bccf3e15…` / `70b1793b…`）。**初态生成与折叠都未运行。**
- **状态**：批次**暂停**。按冻结文档 `b-right-dev-v1`，先用开发 seeds 4200/4300 验证 right 的释放后保持；在此之前不生成、不运行任何 held-out 初态。
- **汇总**：`stage4_formal_report.py` 按档/表示给尝试数、通过数、拒绝率 `(rejected+error)/总尝试`（空批次报空，不写 0%）。
- **硬前置**：正式成功判据阈值仍未冻结；跑完也只有开发门槛 `passed` 与拒绝率，不能变成正式成功。
- **先要决定的**：任务 B 的 left 释放后回弹是确定性失败，40 个 held-out 仍走 left 时预期接近全失败。要么先跑一遍作为正式拒绝率基线，要么先解决 B 的保持（right 变体需按 §4.2 单独冻结）再跑。
- 未覆盖：折叠脚本不录视频、10 次 reset 批次未并入、验收图未整理。正式成功仍为 0。

## 第 3 步：表示层对齐（已完成：实现 + 两任务各一对开发配对）

**目标**：同一任务内，single-step 与 H=4 用完全相同的目标、评价器与测试 seeds。定义、实现与结果见 [冻结文档 §7/§7.1](STAGE4_TASK_DEFINITION_FREEZE.md)，配对报告见 [STAGE4_REPRESENTATION_PAIRS_20261102](../thesis/day4-actionchunk-test/results/STAGE4_REPRESENTATION_PAIRS_20261102/review.md)。

**冻结映射**：只把四个 arc 目标合成一个 H=4 chunk，抓取/释放仍 H=1。
- L1：single `[1,1,1,1,1,1,1]`；arc4 `[1,1,4,1]`（`arc45/arc90/arc135/place`）。
- L2/L3：single `[1]*12`；arc4 `[1]*7+[4,1]`（`fold_arc45…fold_place`）。

**已完成**：`--execution {single,arc4}`、两个 runner 透传与断言、`execution_mode / call_horizons / chunks / code_files` 记录、评价器统一（`stage4_fold_metrics.py` + `lateral_local`）与身份自校验、配对审计（`stage4_representation_audit.py`）、两份 manifest 刷新、脚本启动时自身哈希校验。

**本轮配对结果**（开发例；L1 seed 4100 overhang 0.02，L2 seed 4200 left）：

| 任务 / seed | single | arc4 | 审计 |
|---|---|---|---|
| L1 / 4100 | `passed=true`，crossed 1.000，IoU 0.3747，对齐 13.82 mm | 同上，逐字节相同的快照 | `PAIRS_COMPARABLE` |
| L2 / 4200 | `passed=false`（释放后摊平：extent 0.4424、z_p95 9.9 mm、crossed 0） | 同上，逐字节相同的快照 | `PAIRS_COMPARABLE` |

四例 `result.json` 的 `code_files` 与本地 manifest 逐条相等（24 / 21 项，零差异），下载 53 个文件哈希一致；两对目标差、五项指标差全为 0。

**两条必须保留的解释**：

1. **0 差是同一条轨迹，不是“近似等价”**。同一对内所有可比快照逐字节相同，因为后端 `execute()` 逐行发出同一串 `control.move`，两种表示在 waypoint 之间都不消费观测。所以本实验证明的是**专家轨迹在两种表示下等价**，不构成“H=4 降低反馈频率带来收益/损失”的证据；后者属于有策略在 chunk 边界决策的 BC 阶段。
2. **L2 / 4200 left 的失败是可复现的**（本次 single 与 arc4 都与此前冻结版 runs 一致地回弹），不是运行间随机差异；与旧版通过例的差异仍是版本相关、原因未隔离。held gate 与 chunk 执行均正常，失败发生在释放之后。

**若要再补其它 seed 的配对**（当前上传已通过 preflight，无需重复上传）：同一初态、同一 seed 下各跑一次 `L1_XFOLD_EXECUTION=single|arc4` 或 `RECOVERY_FOLD_EXECUTION=single|arc4`，下载两个目录后本地执行

```powershell
cd E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test
python stage4_fold_metrics.py --task l1 --result-dir results\<single目录> --result-dir results\<arc4目录>
python stage4_representation_audit.py --pair results\<single目录> results\<arc4目录>
```

旧目录没有 `execution_mode` / `code_files`，不能与 arc4 配对；single 侧必须用本版脚本重跑。

## 第 1 步几何核对完成（历史记录）

详见 [实际 USD 几何与偏移审查](DAY4_STEP1_GRASP_GEOMETRY.md)。手指有效 contactOffset=5.45 mm、restOffset=0；保存姿态下实际 USD 碰撞源网格仍有约 1.2–1.4 mm 间隙，接触事件可由余量解释，暂不改手指或轨迹高度。辅助块实体半高15 mm而中心目标约10.207 mm，已确认与默认地面不相容。下一步只修正该代理块—地面关系并短程复验，尚未执行。

完成了一次失败读取和一次修正后的仅初始化诊断（无公共动作，读取前后 step=2）。静态地面有效 offset 未被 rigid-body view 读取到，报告保留此限制；不声称所有形状读数或整条轨迹无碰撞认证通过。正式折叠成功仍为0，不进入第3步。完整结果下载由用户手动执行。

## 最新交接：2026-10-31 v5 已审查，今日暂停

以 [2026-10-31 交接日报](2026-10-31-GarmentLab日报%20Stage4%20v5保持与接触审查交接.md) 为最新状态，下方冲突段落仅作历史记录。

v5 两次结果已下载读取：112822-203913 因 KeyError('attachment_bodies') 失败；113930-047613 短程保持/释放和接触正控通过。位置误差 0.4733 mm、末臂速 0.00860 rad/s、锚点间隙 1.361 mm。发现双指持续触地共 356 条事件；接触明细位置、法向、冲量全零，不能据此认定接触力为零。robot_block=0 受已有碰撞过滤限制。正式折叠成功仍为 0。

下次先核对夹爪坐标偏移、手指碰撞几何、地面间隙及辅助块实际/目标高度，判定触地是否符合设计，再决定最小修正与短程复验；尚不直接解锁完整 L1 或正式批次。今天不启动实验。后续下载只给命令，由用户手动执行。

## 最新准备：v5 接触正控修复已上传，待运行

v4 正控为 0 的根因按代码时序定位为：`PhysxContactReportAPI` 在 `env.reset()` 之后才应用，PhysX 已创建刚体；辅助块还可能进入 sleeping，而 sleeping body 不产生接触报告。v5 只改接触诊断：在槽位创建时（reset 前）对 3 个辅助块和 12 个机器人刚体写入 API；reset 后校验；新增 3 块 `RigidPrimView` 净接触力采样作为独立正控（会把块 sleep threshold 设为 0，`disable_stablization=False`）。公共四动作、目标、路径、物理、60 步保持、30 步释放和 held gate 阈值均不变。

本地上传清单 21 个文件；远端 SHA256 全部一致，Python/Bash 语法通过。尚未运行，正式成功 0。预登记判读见 [SQUARE_GRASP_HOLD_V5.md](day4-actionchunk-test/SQUARE_GRASP_HOLD_V5.md)。运行命令：

```bash
bash /root/autodl-tmp/run-square-grasp-hold-v5.sh
```

## v4 结果：关节锁定保持通过 held gate，接触正控失败，第 1 步未解锁

用户已运行 v4（`day4-square-grasp-hold-20261031-104528-426384`），已下载并审查。held gate 通过：末端位置误差 0.474 mm、保持末臂速 0.0086 rad/s、姿态到达、锚点间隙 1.36 mm；60 步内末端漂移 0.003 mm、姿态漂移 0.0005°。保持阶段仅 60 次 joint_indices 0–6 的 apply_action（位置+零速度），controller.forward 和 controller_output 为 0；全轨迹无 Python 层位姿/关节设置调用。00_initial、01_before_close、02_grasp 与 v3 逐顶点/逐位姿相同，说明确定性路径一致；v3 保持末端漂移 19.12 mm，v4 为 0.003 mm。release 步数 731（v3 753），原因是保持结束位姿稳定；公共动作仍为 4，正式成功 0。

接触通道无效：callback_count、event_count、块-地正控均为 0。保持时块中心 z 恒为 15.000 mm、目标 10.207 mm，块持续被地面挡住，说明 0 事件是记录通道失败而非无接触。robot_group 与 attach_group 本就互相过滤，robot_block 记录不能独立证明机械隔离。按预登记规则，第 1 步不解锁，不进入 L1；下一步先修复并验证接触正控（例如启动前应用接触报告 API 或设计确定性接触），不延长保持、不改阈值、不调 RMP 增益。

审查见 [review.md](day4-actionchunk-test/results/day4-square-grasp-hold-20261031-104528-426384/review.md)、`independent_audit.json`、`hold_v3_v4.png`；本地脚本 `review_square_grasp_hold_v4.py`。下方 v3 诊断与预登记判读保留为历史记录。

## 最新离线审查：12个真实负例快照

已运行review_real_negative_examples.py，报告位于 [真实负例指标](day4-actionchunk-test/results/REAL_NEGATIVE_EVALUATION/review.md)，逐项数据和源文件/评价器哈希见同目录metrics.json。

10个L1平整初态IoU均为0、材料反射误差约220mm；同一次失败抓取的保持/释放后两个快照IoU为0、误差约217mm。所有success字段仍为空，未追加正式尝试。10个初态以自身为基线，仅刻画未折叠状态；两个抓取快照非独立episode，不能宣称12次独立验证。

折线数值容差统一为1微米，用于吸收float32中心线误差，不是成功阈值。物料分半来自初始资产索引，不能按最终位置重分。尚无真实正例，分类准确率和最终阈值未验证。

不依赖抓取的接口/预算/记录工具及负例审查已具备。下一项能推动物理验收的工作仍是恢复有效L1候选；用户暂停抓取调试的决定继续有效。本轮未启动仿真，未上传新实验脚本。L1初态10/10，L2/L3各0/10，正式成功0。


## 最新离线交付：评价与批次记录工具

开发版day4_evaluation.py与day4_attempt_log.py已完成，详见 [评价与记录说明](day4-actionchunk-test/DAY4_EVALUATION_RECORDING.md)。合成理想对折/未折叠/整件搬移/整体平移对折/释放后回弹检查通过；追加日志的失败分母、终态不可覆盖、重试独立、未完成批次拒绝率为空、未冻结成功拒绝检查通过。

评价success仍为null，无最终阈值，粒子IoU仅代理，不是正式重叠验收。工具未接入Backend，未新增正式episode。L1初态10/10，L2/L3各0/10，正式折叠成功0；抓取调试保持暂停。本次无上传、无仿真。后续物理验收仍需先恢复有效L1候选，不能靠离线工具替代。


## 最新离线交付：接口、动作预算与 recovery 规范

已完成 [公共接口与 recovery 开发规范](day4-actionchunk-test/DAY4_INTERFACE_RECOVERY_CONTRACT.md) 和纯离线 day4_action_budget.py。保留5维XYZ+yaw+gripper schema；每个waypoint计一次动作，chunk内H行计H次。对折7步、一次recovery5步，总计12；两次需17步，因此本模板实际最多一次，第二次预算不足则记失败，不能隐藏路点或截断。

同一参数化recovery模板的触发、选点、停止及版本/失败统计规范已明确。7/12准入、17拒绝、失败重试预算、非有限坐标拒绝及既有ActionChunk兼容检查通过。尚无冻结阈值或经物理验证的路径，未接入正式Backend，不计recovery执行完成。

当前：L1初态10/10，L2/L3各0/10，正式折叠成功0。抓取调试继续暂停。本轮无上传、无仿真、无新运行命令。下一项独立工作是评价和批次记录工具；实际L1、重抓取/reset和L2/L3生成仍是未完成项。


## 最新进度：L1 初态图 10/10 已下载审查

seeds4100–4109全部生成通过；新增306份文件哈希一致，10张640×480截图、固定参数、441点变换及静置几何逐例核验通过。汇总：[L1十例审查](day4-actionchunk-test/results/L1_INITIAL_BATCH_REVIEW/review.md)。

图像存在机器人中央遮挡及部分回合背景材质不一致，正式视觉数据前需处理；当前计为L1开发初态生成完成，不计折叠或连续reset验收。L2/L3各0/10、正式成功0。三档视觉区分及重复生成一致性仍待验收。

抓取调试继续暂停，不运行旧L2/L3抓起放落代码。下一独立工作为公共接口、≤12高层动作预算、最多两次参数化recovery模板及结果记录规范。本轮只下载审查，未启动新实验。下方“运行剩余9例”为已完成历史步骤。


## 最新状态：L1 首例初态已审查，推进其余9例

seed4100（day4-square-initial-20261031-094446-203825）生成及保存通过：34文件哈希一致，PNG已查看，441点几何与预登记变换一致。机器人遮挡图像中央，局部形状判断需结合几何；尚未验收三档视觉区分。当前已有1/10张L1截图，L2/L3为0/10，正式折叠成功0。

下一步只运行L1 seeds4101–4109，失败即停，完成后逐例下载核验。L2/L3角点lift/drop仍未验证，抓取失稳分支继续暂停。本轮未启动实验。审查见 day4-actionchunk-test/results/day4-square-initial-20261031-094446-203825/review.md。


## 当前主线调整：暂停抓取调试，先做难度初态

用户要求暂缓保持失稳问题，推进独立工作。v3 已反馈失败，本轮没有复跑或宣称通过；其完整结果仍待下载审查。正式成功0，L1折叠尚未解锁。

三档候选参数沿用原 difficulty.yaml 数值，精确采样已存入 day4-actionchunk-test/square-initial-plan.json：L1 seeds 4100–4109、L2 4200–4209、L3 4300–4309，每档10例。平移dx/dy独立从原正区间采样，yaw绕布料质心。此版本只为开发初态批次固定，尚非正式评价冻结。

已有 _lift_drop_once 实现选中心而非角点，且依赖未验证的抓取；L2/L3生成因此阻塞。计划中的corner/lift/drop参数已登记，未用人工变形替代物理生成，也未宣称30张截图完成。

当前唯一运行入口：bash /root/autodl-tmp/run-square-initial.sh 4100。仅L1平移、yaw、清零初态速度、静置120步和截图；无抓取动作。新进程隔离不是重复reset可靠性验收。先审查首例后再生成剩余9例；L2/L3显式拒绝运行。运行后保存参数、变换前/读回/静置后几何、初态PNG、源码、质量及日志。渲染不额外推进物理步。

本地30例唯一性、刚性变换距离保持、无执行抓取动作及AST检查通过；21份远端哈希和Python/Bash语法通过。本次未启动实验。下方抓取诊断“待运行”均为历史入口，暂不执行。


## 最新准备：v3 控制时序诊断已上传，待运行

保留 v2 路径、四个公共动作、物理配置、60步保持/30步释放及原门槛，仅增加 control_trace.jsonl。记录 controller.forward 输出、apply_action 输入、get_applied_action 读回，以及每步前后的关节位置/速度和末端位姿，均带物理步、逻辑步、阶段和序号。Python 位姿/关节设置入口记录调用栈；不声称覆盖原生 PhysX 调用。

本地桩验证原样转发参数/返回值、无额外控制调用和恢复钩子；19份远端依赖哈希及Python/Bash语法通过。当前可执行 bash /root/autodl-tmp/run-square-grasp-pose.sh，一次诊断后审查目标突变与实际响应的先后；不凭零接触事件判定无碰撞，不调整阈值或路径。未启动实验，仍为第1步，正式成功0。此节覆盖下方“尚无新入口/暂停复跑”的历史状态。


## 最新状态：v2 四动作完成，保持失稳，暂停复跑

短程 v2 结果 20261031-091703-655195 已下载：54 文件哈希一致、视频264帧。保持结束位置误差19.188mm、最大臂关节速度0.518rad/s，未过10mm/0.1rad/s门槛；姿态检查和附件误差通过，释放后所有附件disabled。第685–690步间出现速度突增，不能按等待不足处理。正式成功0，第1步仍未通过。

唯一下一步：针对保持失稳区间核对每步控制目标与实际关节响应，追查日志非法setGlobalPose调用来源；尚无因果结论。当前不原样运行旧命令，不增加保持时间、不改阈值、不接回L1。下方运行命令及“待复测”描述仅保留为历史入口。本次未启动实验。

详见 [v2 审查](day4-actionchunk-test/results/day4-square-grasp-pose-20261031-091703-655195/review.md)。


## 最新结果：短程抓取脚本错误已修正，待复测

v1 已执行接近、下降和 CLOSE，但保持阶段姿态 list 类型错误，异常保存又遇到 NumPy JSON 序列化错误，之后出现退出 139。保持及释放未完成，不能计通过。完整结果已下载：45 文件哈希一致、视频 217 帧。修正版 v2-serialization-fix 已上传并通过 18 文件远端静态核验，路径、物理和阈值不变。本次未启动复测。下一步仍运行 run-square-grasp-pose.sh，其他步骤未解锁。

审查：[短程抓取 v1](day4-actionchunk-test/results/day4-square-grasp-pose-20261031-090844-326265/review.md)。


更新时间：2026-10-31。先打通一个符合公共接口要求的 L1 对折，再完成三档验收。正式成功仍为 0；流程完成、静态检查通过和抓取测试通过均不能替代折叠成功。

## 当前唯一推进项：第 1 步

18 份短程测试文件已上传并完成哈希及语法核验，尚无本候选运行通过的证据。本次仅更新计划，未启动实验。由用户在服务器执行：

```bash
bash /root/autodl-tmp/run-square-grasp-pose.sh
```

只验证 approach → descend → CLOSE → OPEN，不执行折叠。完成后助手自动下载完整结果，核对脚本版本、日志和视频，并审查位置误差、姿态误差、关节速度收敛、附件保持及释放状态。保持既定判据，不因结果失败放宽门槛；接触零事件不能直接解释为无碰撞。

当前使用独立 SquarePoseBackend 候选：XYZ 为世界坐标中的 right_gripper，yaw 映射为 Rz(yaw)Rx(pi)，固定局部 Z 向下。抓取参考为 URDF 指尖中点（局部 +3.4 mm），尚非实测夹持点。离线 IK/FK 和网格检查不等于动态或接触验证，详见 [坐标与姿态审查](DAY4_SQUARE_FRAME_AUDIT.md)。

## 五步收尾顺序

1. **短程抓取测试。** 运行上述已上传脚本，只验证接近、下降、抓住和释放；审查位置、姿态、速度及附件状态。结果有效且通过后才进入下一步，失败则围绕本次证据修正，不扩大扫描。
2. **接回 L1 对折。** 先解决末段路径不连续（当前离线完整路径存在约 3.15 rad 关节解跳变），再验证完整释放、退让和静置后的重叠保持，排除整件搬移、翻转、回弹及持续滑动。成功后独立重复一次。两次均为开发候选，不计入正式批次。
3. **整合 Backend 与动作预算。** 将有效抓取、释放及控制修正整合到正式 Backend，统一 XYZ + yaw + gripper_command 公共语义。折叠和 recovery 总计 ≤12 个高层动作；明确内部 waypoint 与高层动作计数，不隐藏 expert 指令或截断轨迹。验证 episode 内必要重抓取，以及 reset 的约束、辅助对象和状态清理。
4. **一次完成三档配置与截图。** 固定 L1/L2/L3 的扰动参数、settle 步数和 seeds，每档保存 10 张初态截图，共 30 张，记录实际生成参数，确保可复现且肉眼可区分。使用一个参数化 recovery 模板，明确触发、选点和停止条件，每回合最多两次，仍须满足总动作预算。
5. **冻结指标并运行正式批次。** 用开发成功/失败样例冻结 alignment、overlap、success 定义、测量时刻及阈值。每档至少取得 5 条成功轨迹，共至少 15 条；保留全部尝试、失败原因、seed、配置版本、指标及 recovery 次数，按档计算 rejection rate = 被拒绝尝试数 / 总尝试数。将连续 10 次 reset/rollout 检查并入批次，检查状态残留、资源和保存错误。最后核验接口隔离，更新验收表并链接配置、30 张截图、结果统计及成功/失败视频。全部完成后进入 Stage 5。

## 冻结范围与进度来源

旧服装、翻腕和参数扫描分支保持冻结，不重跑旧版本，不继续质量、求解器迭代数、高度、锚点数量或速度扫描。当前仅推进第 1 步，其余按通过条件依次解锁。

GitHub README 已于上一轮更新至 Stage 4（提交 d25cea29c3bb376d5504a39d6aac3301a7f41cfb），不再停留在 Stage 2。当前执行顺序以本文件为准，实际完成状态以原始结果及审查记录为准，不能仅凭 README 或 pipeline 标志判定通过。

## 实例和权限

当前服务器：root@connect.nmb2.seetacloud.com:23636。用户已授权自动上传必要实验文件、下载完整结果；当前由用户运行仿真，助手准备、上传、检查和下载审查。本次没有启动 GPU 实验。


## 2026-11-02 汇总器修复与 right 开发验证登记（尚未运行）

stage4_formal_report.py 已把缺失结果转换为 error 尝试，按档/表示/任务计入 attempts 和 (rejected+error)/attempts；空批次保持 null。新增 test_stage4_formal_report.py，8 项纯离线测试通过（一次通过+一次缺失结果得到2次尝试、50%拒绝率）。已有结果与日志不重复计数，非 held-out 日志不纳入，重试独立计数。

按冻结文档最新 b-right-dev-v1 条目，仅以开发 seeds 4200/4300 各运行 single/arc4 验证 right 的释放后保持；独立 manifest 与目录白名单在任何新结果前登记。held-out 与正式批次暂停，正式成功仍为0。检查范围仅现有 OPEN+30ticks+180settle 的终态，不宣称第二时刻保持或长期稳定。


## 2026-11-02 right 验证执行分工更新（用户指定）

用户明确指定“另一聊天继续；本聊天只下载和审计其结果”。本聊天已停止自动提交控制器，之后不再提交 GPU 实验；此前已在途进程不终止。L2 4200 right single/arc4 已下载并通过原版 PAIRS_COMPARABLE，crossed均1.0、IoU约0.559；L3等待外部结果，尚不宣称验证完成。

后续下载保留外部结果的真实来源，核对同一初态、right、seed、execution_mode与21项底层代码身份；未经过本变体入口的外部结果不伪造23项wrapper身份。优先按目录启动时间选取结果，不按passed筛选；额外或失败尝试原样留存。并发运行不作耗时比较。held-out不运行，正式成功仍为0。


## 2026-11-02 b-right-dev-v1 开发复验与移交后审计完成

汇总器缺失结果分母修复与8项离线测试已通过；原项目代码与已测试副本SHA256一致（9a757d34…）。一次通过+一次无结果error的合成回归输出2次尝试、50%拒绝率；空批次保持null。

L2 4200的right single/arc4由本聊天在移交前完成；L3 4300采用另一聊天产出的最早外部single/arc4，按目录启动时间选择而非passed。两对均通过原版PAIRS_COMPARABLE，四份选定结果held gate通过、crossed=1.0，L2 IoU=0.559091、L3 IoU=0.562997；各对目标差及五项指标差值精确为0。底层21项代码不变，四份结果的独立23项变体manifest、配置和初态文件哈希均核对一致。

共下载核验66个远端文件，包含6份完整开发结果：选定4份配对结果与2份额外L3 single重复尝试。额外尝试原样保留，不增加独立seed覆盖，不计算正式成功率。用户移交后本聊天仅下载审计，未再提交GPU仿真，未终止已在途远端进程。

结论仅为每档一个开发seed在OPEN后30 release ticks+settle(180)终态保持；没有独立退让、第二retention样本或长期稳定性验证，不能外推整个开发集/held-out，更不能解释为BC策略或H=4性能提升。right为独立变体，不替换left失败或默认定义。held-out与正式批次保持暂停，正式Stage 4成功仍为0。

完整报告：[right开发复验与移交后审计](../thesis/day4-actionchunk-test/results/TASK_B_RIGHT_DEV_V1_20261102-183740/review.md)。

补充交叉核对（2026-11-02）：把主审计未采用的 4200 arc4 尝试 `025355-106410` 与 4300 single 重复尝试 `031535-711404` 一并核对，5 个目录 77 项检查全部通过；同 seed 全部 7 次已下载尝试（4200 三例、4300 四例）的 `final.npz` 441 个顶点逐位相同（max|Δ|=0），包括并发在途的 4200 arc4 两例。该核对不新增 seed、不改任何阈值、不改变上述结论。[补充审计](../thesis/day4-actionchunk-test/results/B_RIGHT_DEV_AUDIT_SUPPLEMENT_20261102/review.md)。

right 开发覆盖扩展 `b-right-dev-v2` 已登记并完成 A1 预检（48/48，仅离线；v2.1 修正 sampling 描述，config `91c0fe7f…`、manifest `c3e34c91…`），尚未运行任何 seed：L2 4201–4209、L3 4301–4309 共 18 个剩余开发 seed，先登记初态哈希再跑 right single；不跑 arc4、不冻结阈值、held-out 不动。见 [扩展计划](STAGE4_B_RIGHT_DEV_V2_PLAN.md) 与 [A1 预检](day4-actionchunk-test/results/STAGE4_A1_PREFLIGHT_20261102/review.md)。
