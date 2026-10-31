# GarmentLab 交接日报｜2026-10-25｜Day4 折叠与释放异常

## 1. 恢复工作先读这里

用户要求今天暂停，只整理交接。当前首要目标仍是完成原十天计划 Day4，不继续扩展质量、迭代数等物理参数扫描。

**Day4 尚未完成，今天没有新增正式验收成功的 expert episode。** 已从抓取/抬升诊断推进到完整折叠动作开发，但当前阻塞为：布料放下、松开后，即使机器人原地不动，也会持续横向加速飞离。

最新 hem-v5 尝试在松开时移除抓取约束，但远端截图仍显示 `Cloth escaped 2 m diagnostic bound during retreat_clear`。不能称为修复成功，也不能仅凭截图确定新旧轨迹完全相同。

**下次第一步是下载和比较 hem-v5 结果，不要直接再跑实验。**

- 最新远端目录：`/root/autodl-tmp/day4-l1-hem-fold-20261025-081458-011222`
- 本日报写入时，该目录尚未出现在本地 results 中。
- 检查 `source/manifest.json`、`runner.log` 中的 `RELEASE_ATTACHMENT_REMOVED`、`result.json` 和 `release_trace.json`，确认版本及约束移除实际执行情况。
- 与 hem-v4 的逐帧轨迹比较，判断移除约束是否改变释放后的加速。之后才决定下一项修正；目前根因未确定。

本次只做日报收尾，没有新发起仿真、远程关机、Git 提交或推送。服务器开关、计费及 GPU 状态未查询。

## 2. 原计划 Day4 验收与当前缺口

依据 `Marian_Frei_GarmentLab_2024_10_day_execution_plan.md` 的 Day4：

|要求|当前状态|
|---|---|
|Flat / Perturbed / Crumpled|源码和配置存在，固定协议与物理生成尚未完整验收|
|每档 10 张初态截图|未完成三档共 30 张与肉眼区分验收|
|参数化官方 FoldDemo|已有单抓取 L1 候选；尚未完成官方多次抓取流程|
|最多两次 recovery moves|未实现/验收，当前适配器每进程只能抓取一次|
|alignment、overlap、success threshold|已有暂定代理指标，尚未正式冻结|
|每档至少 5 个成功 expert episodes|未完成，不可把诊断通过或动作执行完计入|
|expert rejection rate|尚无正式批次统计，后续失败必须保留在分母|
|simulator-only state 不泄漏|尚待正式接口/数据流检查|

另外，独立 `reset(seed,difficulty)` 和重复 rollout 仍有 Day3 遗留工作。新进程试跑不代表可重复 reset 或 episode 内再次抓取已通过。Day4 验收前不进入 Day5 正式 demonstrations 批量生成。

## 3. 今天的基础工作与实验结果

### 3.1 保持、物理配置及质量对照

- 实测末端位置保持对照已运行，截图出现 `MEASURED_HOLD_COMPARISON_OK`；本地目录 `day4-aligned-measured-hold-20261025-044808-480399`。不要把低末端速度等同于衣物静态平衡。
- 物理配置审计初版因 JSON 不允许 `inf` 失败，后续版本通过；v2 完整结果为 `day4-physics-config-20261025-053727-962061`。
- 默认每粒子质量约 0.01 kg，9945 粒子总质量约 99.45 kg；当前开发候选每粒子 0.0001 kg，总质量约 0.995 kg。并未做真实布料标定。
- 质量读回与请求值存在约 0.00912% 差异，原因未确定。数值读回相对容差从 1e-5 调整为 1e-3，保留有限、正值、均匀性检查；不能称为已经证实的舍入误差或物理验收阈值。
- 成功质量对照：`day4-mass-pair-V0AIYmBy`（最后两个字母为 By）。实际总质量约 99.459075 / 0.994591 kg，比例约 0.0100000004。
- 保持末端最大边长比约 1.720 → 1.407，峰值约 1.727 → 1.442；末端抬升均约 93.41 mm。两者初始静置几何已有平均 5.482 mm、最大 22.05 mm 差异，属于完整策略质量敏感性比较，不是匹配状态的单因素物理隔离。
- 质量对照未保存实际弹簧数组，不能把构造参数一致说成实际弹簧数组完全一致。
- 16→32 迭代对照截图显示 `ITERATION_PAIR_COMPARISON_OK`，质量读回相同、静置几何差异 0、锚点索引相同。完整结果未下载，不推断折叠质量或伸长改善。这项不阻塞 Day4。

### 3.2 取回完整源码

`day4-source-handoff-20261025-063847-681950` 已下载、解压，186 份文件哈希验证通过，包含 demo / garmentlab 源码、配置和 Git 元数据。

官方 `garmentlab/demo/FoldDemo.py` 包含右袖、左袖、下摆三次连续抓取；当前 prepared 适配器限制为每进程一次抓取，不能直接视作官方 expert 已参数化完成。

## 4. 折叠试跑时间线（结果目录为唯一标识）

下列目录均位于 `day4-actionchunk-test/results/`，除最后一项外已下载。

|版本/目录|结果及意义|
|---|---|
|左袖 pilot：`day4-l1-fold-pilot-20261025-064228-005392`|流程与视频保存完成，折叠失败；最终对齐均差约 102.18 mm、IoU 0.097、越线比例 0。放下到最终中心移动约 0.98 m，当时不能分离释放与撤离影响|
|hem-v2：`day4-l1-hem-fold-20261025-072302-119212`|下摆抓取、转移、放下和松开完成；近 y=-0.19 m 的竖直撤离在下一目标 z≈0.202596 m 超时。没有最终稳定状态|
|hem-v3：`day4-l1-hem-fold-20261025-074518-693271`|改斜向撤离后动作完成；最终几何飞离几十米，指标网格保护报错。不是仅仅网格过小|
|hem-v4：`day4-l1-hem-fold-20261025-080109-024474`|增加松开后原地停留及逐帧记录，证实不撤离也会加速；抬起阶段触发 2 m 停止条件|
|hem-v5：`day4-l1-hem-fold-20261025-081458-011222`|松开时移除约束的尝试；截图仍显示 retreat_clear 越界。完整结果待下载/核实|

已有本地 `pilot_review.md` 分别记录 hem-v2/v3/v4 复核及左袖 pilot 复核。

### 4.1 下摆试跑配置与暂定指标

- 通过初始网格下边缘中心选点，pick_index=6174；这次 USD-visible 锚点为 42 对，不是旧左袖的 28 对。
- 初始下摆点约 (-0.01050,-0.65794,0.02965) m；y 中线约 -0.423489 m；镜像目标 y≈-0.189037 m。
- 抬升约 0.15 m，沿折线跨越、转移至镜像点、分层放下；绝对路点间距不超过 2.5 cm，不等于速度上限。
- 当前质量候选为每粒子 0.0001 kg；沿用 5 mm attachment overlap 和 points1 对齐。
- hem-v3 起撤离为抬至 z=.10，斜向折线 y 移动并升至 z=.18，再升至 z=.25。该路径已执行完成过。
- 暂定检查：双向 XY 最近点均差 ≤.04 m，粒子占据 IoU ≥.50，源半片越线比例 ≥.80，衣物 z P95 ≤.06 m。**粒子投影不是三角面重叠、自交或材料质量认证；阈值尚未冻结。**
- `formal_day4_success` 始终为 false；保存成功、动作完成、暂定折叠通过与正式 Day4 验收须分开。

hem-v2 放下时指标为：对齐 66.58 mm、IoU .1803、越线 1.0、高度 P95 98.62 mm；松开后变为 80.07 mm、.1493、.7998、100.11 mm。释放问题解决后，折叠形状仍需改进，不能预设其已经合格。

### 4.2 已证实的释放异常

hem-v3 布料中心位置：

|阶段|x / y（米）|
|---|---|
|放下|-0.01222 / -0.24350|
|松开|-0.03106 / -0.28760|
|撤离结束|-24.93728 / -37.25261|
|静置结束|-33.59531 / -50.67585|

顶点均为有限数；已查看撤离/最终 PNG，布料已离开视野。没有扩大网格掩盖异常。

hem-v4 的 `release_trace.json` 共 85 条，dt=1/60 s：

- step 1229，released_stationary：中心约 (-.0337,-.2926,.0364) m，中心差分速度约 .338 m/s。
- step 1288，仍是 released_stationary：中心约 (-.5697,-1.4932,.0363) m，速度约 2.355 m/s。
- 期间末端约 (-.0105,-.1898,.0369) m，辅助块约 (-.0107,-.1953,.0450) m，基本不动；USD 约束开关读回为 false。
- step 1297 在 retreat_clear_0 达到诊断停止边界；**触发停止的阶段不等于异常开始阶段**。

这些证据排除了“只有撤离运动才触发加速”的解释，但还不能确定求解器残留约束、接触或其他动力学原因。USD 属性关闭不自动证明内部约束已经移除。

### 4.3 最新 hem-v5 修改与验证边界

`HemPreparedGraspControl.ungrasp()` 中先清零辅助块速度、关闭 attachment 开关，再 `stage.RemovePrim(attachment_path)`，检查该 prim 不存在，最后打开夹爪。只移除本次抓取约束，辅助块留在原位。

新增 `constraint_removed` 与 `attachment_enabled()`，同步调整 observer 和主脚本的状态检查，避免读取已删除属性。当前仍不支持第二次抓取。

没有清零布料速度、改质量、改成功阈值或扩大 workspace。保留 60 步原地停留、逐帧日志及 2 m 异常停止；2 m 只是诊断边界。

本地通过 Python 3.10 AST 检查及释放方法假对象检查：移除先于夹爪打开，移除失败则不打开。**这些不是 Isaac/GPU 物理验证。** 远端最新截图仍失败，待取得日志确认详细行为。

## 5. 当前文件、环境与操作方式

本地根目录：`E:\learning\project\thesis`。

主要脚本位于 `day4-actionchunk-test/`：

- `day4-l1-hem-fold.py`：当前 expert_version=hem-v5，录像、快照、逐帧释放记录及结果输出。
- `hem_prepared_grasp_control.py`：下摆单次抓取控制、最新释放逻辑。
- `hem_anchor_alignment_observer.py`：支持可变数量的锚点映射，使用新状态读取方法。
- `hem_fold_geometry.py`、`l1_fold_geometry.py`：抓点、路点、暂定折叠指标。
- `run-l1-hem-fold.sh`、`l1-hem-files.json`：入口及依赖哈希；修改任一依赖后必须刷新 manifest。
- `mass_experiment.py`、`anchor_observer.py`：已有依赖。

远端工作目录 `/root/autodl-tmp`；Python `/root/autodl-tmp/envs/isaac40/bin/python`；Isaac Sim 4.0，Torch/CUDA。两个工程位于 `/root/autodl-tmp/garmentlab-action-chunk-demo` 和 `/root/autodl-tmp/garmentlab_workspace/GarmentLab`。

连接：`root@connect.nmb2.seetacloud.com`，端口 `23636`。助手此前 SSH 非交互登录未成功；当前工作方式为助手改本地文件，用户 PowerShell 上传/下载，VS Code 远程 Bash 执行。不要把助手本地检查说成远端运行。

本地 `D:\Users\yexun\anaconda3\python.exe` 可用于 numpy/scipy 离线分析。此次主要查看 PNG 与 NPZ，未完整解码视频。截图上的 Kit 时间与结果目录时间可能不同，以目录名和 manifest 为准。

实验修正在独立脚本/进程中运行，尚未完成正式 backend 整合。没有重新核实远端仓库当前 HEAD 或清洁状态。

## 6. 下次接手的具体步骤

1. 下载最后结果；先核实版本和移除日志，再对比 v4/v5 trace 的相同阶段、中心速度和辅助块运动。不能仅根据相同错误文本认定轨迹完全一致。
2. 根据对比与源码缩小释放异常原因。不要继续盲目调撤离轨迹、放宽验收、重置布料速度或增加参数扫描。
3. 释放稳定后复核完整 L1 折叠效果；必要时修正 expert 路径/抓点。原地抓起放下成功不替代折叠成功。
4. 完善独立 episode/reset、多次抓取与 recovery、评价定义并冻结，再验收 L1/L2/L3 每档至少 5 次成功、初态截图和 rejection rate。

本机 PowerShell 下载命令：

```powershell
scp -P 23636 -r root@connect.nmb2.seetacloud.com:/root/autodl-tmp/day4-l1-hem-fold-20261025-081458-011222 "E:\learning\project\thesis\day4-actionchunk-test\results\"
```

现有远端运行入口（仅供交接，未要求现在重跑）：

```bash
bash /root/autodl-tmp/run-l1-hem-fold.sh
```

恢复时优先阅读本日报及 `DAY4_ACCEPTANCE_TRACKER.md` 最新状态，避免沿用旧日报中“下一步尚未执行”的过期安排。
