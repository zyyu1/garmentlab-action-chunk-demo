# GarmentLab 交接日报：Stage 4翻腕控制与接触诊断

日期：2026-10-26（本地 Europe/Berlin）。用户明确要求在此暂停。本文是最新交接入口；不启动实验、不后台继续运行。

## 后续计划更新（2026-10-26）

用户已明确后续主线：**先打通一个符合接口要求的L1折叠，再扩展到三档验收。** 新增 [Day4后续执行计划](DAY4_NEXT_STEPS.md)，包含九步任务、产出及通过条件，作为恢复工作的执行依据。本文后续各节保留当时的技术证据和运行命令，不能替代新计划或视为立即执行授权。

顺序为：核实v5及接触诊断 → 空载路径与速度收敛 → 统一公共动作接口 → 可重复带布料L1开发候选 → Backend整合、10次reset/rollout及重抓取 → 三档协议和30张截图 → recovery、12步动作预算及评价冻结 → 每档至少5条正式成功和完整拒绝率统计 → 接口隔离与验收材料。全部完成后再进入Day5。

当前仅更新文档，仍未检查服务器。恢复后的第一项实际操作是核实是否已有v5结果，有则下载完整目录，无则上传并运行；无需重跑旧版或继续质量/求解器迭代数扫描。

## 1. 结论与暂停点

**Day4尚未完成，当前工作没有新增正式验收成功episode。** 用户的首要目标仍是完成原计划Day4，避免无限扩展物理诊断。

当前瓶颈：下摆折叠动作尚不能稳定完成。释放飞离问题在候选摩擦配置下得到改善，但折叠会回弹或整件搬移。为处理多点抓取局部翻转问题引入腕部俯仰后，又遇到空载翻腕失稳。IK存在不等于实际路径可执行。

**准确暂停点：空载IK执行v4结果已下载分析；v5接触记录脚本已在本地准备好，尚无上传或运行完成的确认，不能视为已经运行。** 用户此前已收到上传和运行命令，随后要求暂停。

最新结果：`day4-actionchunk-test/results/day4-wrist-ik-execution-20261026-072444-531501/`。

下一次恢复首先阅读本文，再检查是否已有v5结果；若没有，执行本文第6节的一次接触记录实验。不要重复旧版本，不继续盲调高度，不放宽验收阈值。

## 2. Day4原计划与验收差距

依据 `Marian_Frei_GarmentLab_2024_10_day_execution_plan.md` 的 Day 4：

- 实现Flat/Perturbed/Crumpled，三档初态肉眼可区分，每档保存10张初态截图。
- 参数化官方FoldDemo，最多两个recovery moves。
- 定义alignment、overlap、success threshold，正式训练前冻结。
- 记录expert rejection rate，检查simulator-only state不泄漏到policy action或Backend公共接口。
- 每档至少5个成功expert episodes。

上述整套验收尚未完成。当前pilot成功标志和空载可达性标志均不能替代正式成功episode；未取得每档5个成功回合证据。恢复后应在动作打通后回到难度协议、截图、重复成功回合及拒绝率，不把额外诊断当成新的Day4要求。

当前翻腕俯仰通过实验侧通道传入，超出原XYZ+yaw动作接口，不能直接用于正式示范或声称符合公共接口。单次抓取pilot也不能替代官方多次抓取FoldDemo；恢复/重抓取能力仍待完成。

## 3. 本轮关键实验与证据

下表结果目录均在 `day4-actionchunk-test/results/`，远端对应 `/root/autodl-tmp/`。完整文件夹名的日期和本地日志时间存在差异，检索以文件夹名为准，不自行改名。

| 实验目录 | 结果及解释 |
| --- | --- |
| `day4-wrist-reach-20261026-063051-813133` | 负向延迟翻腕第18点失败，位置误差88.6 mm；q4/q6接近模型边界，但不能证明全局无解。 |
| `day4-wrist-reach-20261026-063936-107749` | 正向延迟翻腕第25点失败，位置误差94.52 mm；q4/q6距限位较远，不能沿用硬限位解释。 |
| `day4-wrist-ik-audit-20261026-065126-175358` | 第25–30点均有通过FK和关节限位复核的IK解；终点最小限位余量约6.84°。没有执行这些解，也没有验证碰撞。 |
| `day4-wrist-ik-execution-20261026-065716-750384` | v1前24点RMP、末段关节插值。第25点第36/40步误差0.21016 rad停止；仅发送位置目标，缺逐步诊断。 |
| `day4-wrist-ik-execution-20261026-070558-187726` | v2添加零速度目标，但首次提交触发Isaac控制器CUDA→NumPy错误；未验证新控制效果。运行时源码已导出。 |
| `day4-wrist-ik-execution-20261026-071411-159644` | v3修复接口。第25点前14步误差约0.0012 rad，第15–16步开始异常，第36步joint6误差0.150894 rad停止；逐步记录确认已应用速度目标全零。 |
| `day4-wrist-ik-execution-20261026-072444-531501` | v4整条空载路径抬高15 cm。25、26点通过且末帧速度小；27点末帧joint5速度4.7165 rad/s，虽reached=true也不能称稳定。28点第20步joint6误差0.224565 rad停止。 |

v3异常开始joint2≈0.8109 rad、joint6≈1.1177 rad；v4异常开始joint2≈0.7786 rad、joint6≈0.6438 rad。高度改变了失稳发生点，但其他关节构型也改变。没有接触对象/冲量证据，不能认定地面碰撞、自碰撞或求解器故障。

**重要解释限制：现有reached只检查位置、姿态、关节误差连续6步，没有速度收敛条件。v4第27点是位置条件通过，不是动态稳定通过。** 后续若用于动作验收，需要区分这两者；当前v5为可比性保留旧判定。

## 4. 已确认的代码问题与修复

下载的 `articulation_controller_source.py` 显示：Isaac 4.0的 `apply_action` 在 `joint_indices=None` 分支对CUDA速度标量直接调用 `np.isnan`；位置分支已有CPU转换，速度分支没有。

v3起的 `submit_joint_targets` 显式传入完整关节索引，位置与零速度目标使用和机器人状态同dtype、同device的Torch张量。此修复已在远端越过原异常，随后得到真实跟踪失败轨迹。

使用的是执行器位置/速度目标；没有调用set_joint_positions或set_joint_velocities来瞬移或重置实际状态。未修改安装的Isaac SDK。

验证边界：本地用导出的真实apply_action函数和设备标量桩复现旧分支失败、验证显式索引分支；这本身不是GPU仿真测试。v3远端结果才是兼容性已修复的运行证据。

## 5. 当前脚本与参数

本地目录：`E:/learning/project/thesis/day4-actionchunk-test/`。

- 主折叠pilot仍是 `day4-l1-hem-fold.py` 的 hem-v12-pitch-arc-probe，当前空载试验未自动接回它。
- `day4-wrist-ik-execution-v3.py`：原高度、显式索引及零速度目标、逐步关节记录。
- `day4-wrist-ik-execution-v4.py`：在v3基础上起点和终点都增加0.15 m；30个圆弧点已验证均为原点+[0,0,.15]。
- `day4-wrist-ik-execution-v5.py`：保留v4轨迹，增加机器人刚体接触报告。
- 配套 `run-wrist-ik-execution-v5.sh`、`wrist-ik-execution-v5-files.json`；校验脚本和两个几何依赖的SHA256。

共同控制设置：前24点RMP；末段从实时状态重新求IK，FK位置误差≤0.002 m、姿态≤0.02 rad、关节在范围内，单段最大关节变化≤0.35 rad；每个插值步≤0.005 rad；跟踪误差>0.15 rad停止。终点要求位置<0.01 m、姿态<0.1 rad、关节误差<0.02 rad连续6步。不可把这些诊断条件当成折叠质量验收条件。

v5对 `/World/Franka/` 下RigidBodyAPI prim添加PhysxContactReportAPI，阈值0，订阅接触回调，保存 `contacts.jsonl`：step、动作相位、actor/collider路径、接触位置、法线、冲量；result.json还记录事件数与回调错误。仅本地语法及step包装检查通过，服务器安装版本上的回调API尚未验证。无事件或回调错误不能当成无碰撞证明。

接口依据：https://docs.omniverse.nvidia.com/dev-guide/latest/programmer_ref/physics/rb_physics.html

## 6. 恢复后的具体操作

仅在用户要求恢复后执行。用户习惯在本地PowerShell上传/下载，在VS Code远程Bash运行，发截图后再下载结果。无需反复请求已经授权步骤的许可。

本地PowerShell上传：

```powershell
cd E:\learning\project\thesis\day4-actionchunk-test
scp -P 23636 day4-wrist-ik-execution-v5.py run-wrist-ik-execution-v5.sh wrist-ik-execution-v5-files.json root@connect.nmb2.seetacloud.com:/root/autodl-tmp/
```

远端Bash运行：

```bash
bash /root/autodl-tmp/run-wrist-ik-execution-v5.sh
```

按实际输出DOWNLOAD_DIR下载整个结果目录到本地results，不预猜时间戳。下载后优先检查：

1. 接触报告是否启用、回调是否报错；与27点异常起始step对齐。
2. 是否存在机器人与地面/房间/自身的接触，接触冲量是否与失稳同时出现；接触存在不自动证明因果。
3. 若有明确接触证据，针对该接触修正路径或几何，再验证；若没有，保留不确定性，审查控制与动力学配置，避免继续无依据调参。
4. 空载路径通过后再接回带布料折叠；必须单独验证释放后的形状和稳定性，再回到Day4正式验收。

环境：远端Python `/root/autodl-tmp/envs/isaac40/bin/python`，Isaac Sim4.0、Torch CUDA。依赖已有远端参考结果 `day4-l1-hem-fold-20261026-061530-144501` 的 `01_grasp.npz` 与 `fold_definition.npz`，保留它们。

## 7. 更早的折叠背景与文件入口

释放异常研究及候选配置详见前一日报 `2026-10-25-GarmentLab日报-Stage4-折叠与释放异常交接.md` 和 `DAY4_ACCEPTANCE_TRACKER.md`。候选配置包括粒子质量0.0001、材料摩擦0.3、particle_friction_scale=0、关闭导入room重复碰撞并保留默认地面；这是实验配置，不是现实材料标定。

hem-v11低圆弧放下越线约0.975，但释放后回弹为0；高圆弧可能整件翻转，均未完成正式对折。翻腕侧通道的目的在于检验多点锚定局部翻转假设，并未证明该假设。

完整源导出：`day4-actionchunk-test/results/day4-source-handoff-20261025-063847-681950/`。机器人求解器属性实际拼写 `_kinematic_solover`，不要误改为solver。

各下载结果目录已有 `pilot_review.md`。`DAY4_ACCEPTANCE_TRACKER.md` 含大量历史“待运行”段落，按顶部最新状态及本文判断，不把历史状态当成当前任务。

本次暂停仅新增交接文件与状态说明；没有启动v5、提交/推送代码或安排自动继续。
