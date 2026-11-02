# Stage 4 收尾计划（当前有效版本）

> 命名约定：Stage 表示按验收推进的工作阶段，每个阶段可跨多天；原 Day N 对应 Stage N。为兼容既有入口，`DAY4_*.md`、脚本、结果目录和历史日报文件名保留。

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
- L3 4300 组合（`104603-419951`）失败：recovery 正常，fold 动作执行且锚点跟随，但释放后折半摊平（crossed 0.0）。怀疑共用左槽位/初始 yaw 错位；已改为用 recovered vs flat 的刚性拟合 yaw（script `88be0966…`），待重跑。
- 7 动作 fold runner 仍固定 yaw=0；L1 正式批需要 yaw-aware 版本。

下一步：重跑 L2/L3 组合（recovered-yaw 版）；L3 若仍失败则改用未使用的 right 槽位镜像半折。之后 L1 7 动作 yaw-aware 复验，再进入第 7 步正式批次。完整交接见 [2026-11-02 日报](2026-11-02-GarmentLab日报%20Day4%20L2L3初态与6b交接.md)。正式成功仍为 0。下方第 1/2 步及旧交接均为历史状态。

## 第 1 步几何核对完成（历史记录）

详见 [实际 USD 几何与偏移审查](DAY4_STEP1_GRASP_GEOMETRY.md)。手指有效 contactOffset=5.45 mm、restOffset=0；保存姿态下实际 USD 碰撞源网格仍有约 1.2–1.4 mm 间隙，接触事件可由余量解释，暂不改手指或轨迹高度。辅助块实体半高15 mm而中心目标约10.207 mm，已确认与默认地面不相容。下一步只修正该代理块—地面关系并短程复验，尚未执行。

完成了一次失败读取和一次修正后的仅初始化诊断（无公共动作，读取前后 step=2）。静态地面有效 offset 未被 rigid-body view 读取到，报告保留此限制；不声称所有形状读数或整条轨迹无碰撞认证通过。正式折叠成功仍为0，不进入第3步。完整结果下载由用户手动执行。

## 最新交接：2026-10-31 v5 已审查，今日暂停

以 [2026-10-31 交接日报](2026-10-31-GarmentLab日报%20Day4%20v5保持与接触审查交接.md) 为最新状态，下方冲突段落仅作历史记录。

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
