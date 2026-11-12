# GarmentLab 交接日报：Stage 4多次抓取与折叠回弹

日期：2026-10-26，Europe/Berlin。**用户明确要求在此暂停。本文为最新交接入口，不后台继续、不启动新实验。**

部分远端文件夹名已到20261027；按原名检索，不因本地日期26日而改名。此前《Day4翻腕控制与接触诊断交接》保留为历史背景，恢复时优先读本文及DAY4_NEXT_STEPS顶部。

## 1. 当前结论与准确暂停点

**Day4尚未完成，正式成功episode仍为0。** 本轮真正新增的可复用进展是：三个约束预建、互斥启停；同一个rollout内两个不同区域抓取/释放通过，随后右袖→左袖→下摆三个槽位均实际执行成功。它们仍是独立开发适配器，未整合到正式Backend，不能据此宣称完整reset、任意位置重抓取或已用槽复用通过。

三阶段位置动作流程及视频产物通过，但折叠失败：衣物被拉伸、整件旋转，释放后回到接近展开形状。后续手动单顶点抓取对照也未解决回弹。

**准确暂停点：单锚点首袖结果已完整下载、视频解码、严格对齐基线并生成报告/对比图；当前没有下一份待执行的新实验脚本。** 不应自动重跑旧三阶段、推广单点三阶段、重启腕部/机器人参数扫描。

下一步的机制问题是区分布料物理可折性与路径放置的影响。尚未决定或实现新的实验；不把这个问题写成已经证实的材料根因。

## 2. 当前环境与操作方式

- 当前SSH：`ssh -p 22895 <server>`。
- 最近截图容器：`autodl-container-7dde4b87a0-ea1fac3d`，VS Code别名`autodl-garmentlab-264`。
- 原430实例地址`<server>`不再用于后续命令。旧日报中nmb1/22895曾是失效地址，但用户本轮明确重新提供，现以本轮为准。
- 助手对新实例只读SSH可达，但认证失败（publickey,password）；远端由用户在PowerShell上传/下载、VS Code远程Bash运行。不要声称助手直接登录运行了GPU实验，也不要求用户在聊天发送密码。
- 远端Python：`<remote-root>/envs/isaac40/bin/python`，Isaac Sim4.0/Torch CUDA。GPU型号及当前磁盘余量未重新核查，不沿用旧截图当成新实例实测。
- 项目：`<remote-root>/garmentlab-action-chunk-demo`；GarmentLab：`<remote-root>/garmentlab_workspace/GarmentLab`。
- 本地开发目录：`E:/learning/project/thesis/day4-actionchunk-test`，结果在其`results/`。

本次仅暂停工作。没有执行远程关机、停止实例计费、Git提交/推送或安排自动继续；云实例当前运行/计费状态未核查。

## 3. 本轮远端结果索引

下表短名均位于远端`<remote-root>/`，已下载项本地为`day4-actionchunk-test/results/<目录名>/`。

|目录名|阶段与最终解释|
|---|---|
|day4-wrist-ik-execution-20261026-185833-233928|v5接触记录。完整记录与v4一致，28点失败；12刚体报告0事件、无回调错误，不证明无碰撞。已下载。|
|day4-wrist-ik-execution-20261026-192104-045218|v6速度到达门限。27点240步保持后约4.717rad/s，拒绝继续到28点。已下载。|
|day4-wrist-ik-execution-20261026-193235-445214|v7在配置JSON保存时遇到Quatf错误，动作前退出。仅截图确认，未要求下载；不是路径失败证据。|
|day4-wrist-ik-execution-20261026-193733-229449|v7b配置与pre/post状态记录。1086步，实际dt=1/60，状态连续；27点失败。已下载。|
|day4-wrist-ik-execution-20261026-220541-035682|v8运行中USD速度迭代64→0。getter变化但全部目标/状态与v7b完全相同。已下载。|
|day4-wrist-ik-execution-20261026-222519-595953|v9首次reset前速度迭代64→0。27点末速度降到1.274502rad/s，仍失败。已下载。|
|day4-franka-asset-audit-20261026-224053-514448|资产审计首版GetPropertyStack缺显式time参数，未完成。仅截图确认，未要求下载。|
|day4-franka-asset-audit-20261026-224552-466537|资产审计修正版，135项来源成功、0错误，有效质量/惯量读回。已下载。|
|day4-wrist-ik-execution-20261026-230420-185319|v10请求几何惯量，实际惯量改变且质量/gains不变；27点0.917149rad/s，仍失败。已下载。|
|day4-wrist-ik-execution-20261026-231825-412721|v11臂增益统一乘1e-6，approach即失败，误差450.278mm；候选拒绝。已下载。|
|day4-multi-grasp-20261026-234353-347208|同rollout右袖、左袖两次抓取释放通过；下摆槽未用。完整下载、独立复算通过。|
|day4-official-three-fold-20261027-000627-746461|三槽位、三阶段位置流程完成，视频可解码；102个公开动作，真实折叠失败。完整下载分析。|
|day4-single-anchor-sleeve-20261027-004413-549160|单点首袖34动作对照完成；仍回弹，不扩展三阶段。完整下载分析，当前暂停点。|

所有“passed”“pipeline completed”标记只能按对应scope解释，不能当成正式折叠成功。各已分析目录有`pilot_review.md`及独立audit JSON。

## 4. 腕部诊断已经取得的结论

v5与v4全部36个目标记录/末段trace完全一致。v6给IK末段增加最大关节速度<0.05rad/s，与原位置/姿态/关节误差同时连续6步成立，240步等待预算不变。第27点旧位置判定通过时joint5约4.72rad/s，原判定不等于动态稳定。

v7b显示位置几乎固定但报告速度较大，尤其joint5/joint7。实际dt=1/60，逐步前后状态连续，getter源码来自实时PhysX张量并克隆。不能把报告速度直接解释为持续同速旋转，也不能从离散差分直接宣布SDK错误。

用户运行`export-solver-api.py`导出当前安装SDK实现：Articulation solver getter/setter最终只调用`get_prim_property/set_prim_property`读写USD，并非实时物理引擎查询。v8运行中设置64→0后，1086步状态文件与v7b逐字节相同，所以getter读回0不证明引擎更新。

v9在timeline停止、time0、step0时修改USD再reset，行为确实改变，但仍不收敛。说明初始化前干预有可测作用；不能泛化为所有参数都只在reset生效。

资产审计确认stage单位米/千克、root/link scale1。极高驱动增益和11个刚体的小惯量来源是加载的`Isaac/4.0/Isaac/Robots/Franka/franka.usd`引用层；实时PhysX质量/惯量与小惯量相符。有效臂kp=572957824、kd=5729578、max effort=100000。不能把USD角度换算差异当作配置错误，也不能仅凭这些值确认唯一根因。

v10仅请求引擎几何惯量：首次reset前将11个非零显式diagonalInertia覆盖为零（USD语义为忽略显式值，不是实际惯量为零）。实际正定惯量明显增大，质量/gains/dt不变，但27点仍失败。v11进一步将七个臂刚度和阻尼统一乘1e-6，保留手指/力上限；approach即偏离并接近限位，无法用于判断翻腕改善。

**这条参数链已经停止。所有修改都只在实验进程内，没有写入正式Backend或永久修改机器人资产。** 接触记录0事件缺少已知接触正对照；启动Direct GPU setGlobalPose错误未取得因果证据，不自动当成根因。

## 5. 已实现并验证的多槽位抓取

核心文件：

- `multi_prepared_grasp_control.py`：三槽位控制；每槽一次，互斥启停。
- `multi_grasp_geometry.py`：右袖、左袖、下摆oracle材料点选择，以及按当前材料位置匹配公开CLOSE目标。
- `day4-multi-grasp-test.py`、`run-multi-grasp-test.sh`：两区域生命周期验证。
- `test_multi_grasp_offline.py`、`multi_grasp_local_checks.json`：本地几何/状态桩检查。
- [首轮协议](day4-actionchunk-test/MULTI_GRASP_PROTOCOL.md)。

每槽reset前创建独立辅助块和约束，初始均禁用。抓取前在禁用状态下，用实时粒子位置和实时刚体姿态对齐points1。释放只禁用、停止辅助块，不在rollout中删除/重建。每步检查启用/holding互斥、预建路径存在及锚点数组保持。

两区域结果独立复算：

|区域|抬升mm|释放下降mm|跟随误差mm|启用最大跳变mm|实际锚点/跟踪顶点|
|---|---:|---:|---:|---:|---|
|右袖|92.803|94.255|0.530|2.790|40 / 28|
|左袖|92.774|94.444|约0.53|2.396|42 / 30|

两轮lift快照到释放静置后的辅助块位置差均为0；252条采样状态互斥，18个H=1公开动作检查通过。质量读回约每点0.000100009kg、总0.994591kg，启动和两轮释放后一致。原机器人资产参数64/64迭代和高增益，没有继承v9–v11修改。

边界：这是两个不同预建槽位，再加下一轮证实的第三槽位；不是已用槽复用、任意点抓取、10次reset或Backend正式整合。

## 6. 三阶段位置流程：完成但没有折好

已读官方`garmentlab/demo/FoldDemo.py`：右袖→左袖→下摆三次抓取，每次两段位置搬运，ori=None，没有显式180°俯仰。原示例末次ungrasp([True])不能直接照抄公开OPEN。

开发文件：`official_fold_geometry.py`、`day4-official-three-fold.py`、`run-official-three-fold.sh`；生成器`prepare_official_three_fold.py`；[试跑说明](day4-actionchunk-test/OFFICIAL_THREE_FOLD.md)。

使用初始三个oracle点对官方名义XY做仿射映射，阶段开始再按当前抓点XY漂移更新目标。yaw固定0，不用set_fold_angle侧通道。显式记录接近、下探、安全分段、释放和退让，实际102个公开动作，**正式12步预算未通过**，不能把长轨迹藏入一次CLOSE而宣称合规。

三阶段均完成，三个槽位均使用并释放；1199视频帧、17张阶段图片、frame_errors=0。最终原代理指标独立复算一致：对齐150.343mm、IoU0.03610、越线比例0.23741、材料反射目标误差168.117mm、P95高度35.143mm。代理指标未冻结，尤其下摆指标不能拿来评价前两次袖口成功。

失败定位：

|阶段|放置→释放120步后抓点XY回移mm|放置最大网格边长比（对初始settled）|
|---|---:|---:|
|右袖|564.7|1.621|
|左袖|456.2|1.930|
|下摆|367.5|2.288|

核心上躯干999个材料点拟合显示整件平移/旋转，最终yaw约18.93°、核心质心位移[-9.4,43.0]mm；释放后衣物基本展开。边长比是几何量，不是应力或材料认证。

最新分析入口：

- [三阶段报告](day4-actionchunk-test/results/day4-official-three-fold-20261027-000627-746461/pilot_review.md)
- [材料阶段对比](day4-actionchunk-test/results/day4-official-three-fold-20261027-000627-746461/three_stage_material_comparison.png)
- [视频抽帧](day4-actionchunk-test/results/day4-official-three-fold-20261027-000627-746461/video_contact_sheet.png)

## 7. 单顶点抓取对照：不足以修复，不推广

文件：`single_anchor_grasp_control.py`、`day4-single-anchor-sleeve.py`、`run-single-anchor-sleeve.sh`；生成器`prepare_single_anchor_sleeve.py`；[对照定义与结果](day4-actionchunk-test/SINGLE_ANCHOR_COUNTERFACTUAL.md)。

首次reset前移除AutoAttachmentAPI，手动为三个槽位各声明一个材料顶点与刚体点；只实际执行右袖。初始化读回恰为指定单点，运行中实际锚点最大间距5.324mm，通过10mm诊断界限。它是抽象点抓取，不能当成实物夹持标定。

严格对齐证据：两组初始9945点网格完全相同；首袖34个公开动作标签/矩阵、两段实际目标完全相同；机器人配置、材料读回一致；源文件与运行源码哈希通过。单点视频470帧、7张阶段图片、frame_errors=0，本地解码通过。

|指标（释放后共同120步快照）|多锚点|单锚点|
|---|---:|---:|
|抓点XY回移mm|564.7|473.6|
|核心yaw°|-19.98|-13.58|
|放置最大边长比|1.621|1.967|
|放置P99边长比|1.166|1.120|

回移减少约16%，但袖口仍展开、最坏局部伸长反而增加。只说明“当前单点替代不足以解决回弹”；不能宣布多点耦合绝对无作用。移除自动附件生成也影响局部过滤声明，不能过度宣称所有内部因素都完全隔离。

单点额外final静置与基线全三阶段04_final不可混比；对照只使用共同的首袖release120步快照。下摆proxy不适合单袖成功判断。

- [单点对照报告](day4-actionchunk-test/results/day4-single-anchor-sleeve-20261027-004413-549160/pilot_review.md)
- [单/多点材料对比](day4-actionchunk-test/results/day4-single-anchor-sleeve-20261027-004413-549160/single_vs_multi_material_comparison.png)
- [单点视频抽帧](day4-actionchunk-test/results/day4-single-anchor-sleeve-20261027-004413-549160/single_anchor_video_contact_sheet.png)

## 8. 恢复时的决策边界与剩余工作

恢复后先读本文、DAY4_NEXT_STEPS顶部及第7节对照报告。先核实实例地址是否仍有效及数据盘，**不用重跑已经完整下载的旧实验**。

接续机制问题：为何释放后回到展开形态？需要区分布料弯曲响应、放置时拉伸/接触与路径形状的影响。当前没有新脚本待运行，没有批准或冻结新的材料配置，不自动做零弯曲、多组刚度扫描或继续减锚点。

已有本地证据可先复用：

- `results/day4-physics-config-20261025-053727-962061/physics_attributes.json`及其数组文件、构造源码。
- 最新单点目录`mass_source/sdk__cloth.py`说明bend是抵抗弯曲的线性弹簧（force/distance），不是角弹簧参数。
- 构造配置stretch=10000、bend=100、shear=100、damping=0.2；早先实际审计有58160条弹簧、刚度范围100–10000、自碰撞开启。
- **早先物理审计不是本轮实时弹簧读回**；不能把构造默认值当成当前所有求解器参数的已确认有效值，也不能仅凭数值100断言材料错误。

下一项新实验必须给出一个明确可证伪问题、最小改动、读回与对照方式，避免再次把Day4变成无边界物理诊断。优先目标仍是符合公共接口的一个L1折叠开发候选。

Day4尚未完成项：完整可重复L1折叠；Backend整合；已用槽复用/恢复动作所需重抓取；10次完整reset/rollout；三档难度与种子、30张初态截图；最多两次recovery及12高层动作语义；冻结评价与成功阈值；每档至少5条正式成功、完整失败分母/rejection rate；最终接口隔离检查。当前全部开发轨迹不补记正式demonstrations。

公共接口仍XYZ+yaw+gripper；本轮yaw固定0，不能声称任意yaw已实现。仿真粒子索引/USD路径只保留在expert/Backend内部及诊断记录，不进入policy action。

## 9. 本地复核工具与维护说明

分析脚本：`review_wrist_v5.py`、`review_wrist_v6.py`、`review_wrist_v7b.py`、`review_wrist_v9.py`、`review_wrist_v10.py`、`review_wrist_v11.py`、`review_franka_asset_audit.py`、`review_multi_grasp.py`、`review_official_three_fold.py`、`review_single_anchor_sleeve.py`。注意部分旧分析文件也会生成候选脚本；暂停期间不批量重跑这些生成器。

本地Python为`D:/phython/python.exe`（命令python），有NumPy/Matplotlib/SciPy，无cv2。已将`imageio-ffmpeg`隔离安装到`day4-actionchunk-test/.analysis-deps/`供本地视频审计使用，不改系统Python；后两份分析脚本会自行加入该目录。远端cv2可用，生成视频后runner检查解码。

实验脚本使用临时类绑定/构造钩子，恢复原绑定后不改磁盘源码；正式Backend文件未在本轮写入。尚未重新核查Git HEAD或最终working tree，不宣称代码干净、已提交或已合并。

PowerShell交互注意：用户曾反向粘贴多行数组进入`>>`。后续上传优先给“先cd，再单行scp”的两条命令；遇到`>>`先Ctrl+C，不反复使用长数组粘贴。当前端口22895，勿带回旧23636。

交接短句：**多区域同回合抓取可用；官方三阶段跑完但回弹；单点对照也失败。暂停在单点完整审计之后，没有下一份待运行脚本。**
