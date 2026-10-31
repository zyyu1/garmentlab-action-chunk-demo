from pathlib import Path
import json
base=Path('day4-actionchunk-test');out=base/'results/day4-minimum-half-fold-20261031-070836-491946'
report='''# bend100/10 对照审查（2026-10-31）

结论：参数修改有效，两组均释放回弹，未得到 L1 折叠候选。停止 bend 扫描，正式成功仍为0。不重复失败组，不接着试1/0/50或质量/迭代数。

## 完整性与作用证据

完整目录已自动下载；归档SHA256 ced8d3109a658a33050140b6f348ffeb4d1e2cd093e7cbc805b130916c0ce265。11份源码哈希通过，两组源码manifest相同。B视频643帧完整解码，340帧逐步几何记录连续、有限，57个动作，错误列表为空，OPEN后约束禁用及停止检查通过。

构造入参及起止USD bend均10。运行时58160项弹簧刚度在本组起止一致；对A有22726项100→10，其余11462项100、23972项10000不变。数组没有弹簧类型标签，不将每项直接解释为bend弹簧。

## 结果

|测量|bend100|bend10|
|---|---:|---:|
|释放前移动半片高度中位数|68.67 mm|69.28 mm|
|释放前近层比例（XY<10mm，垂直间隙0–30mm）|18.28%|15.52%|
|释放前末30间隔移动半片速度P95|0.375 m/s|0.423 m/s|
|抓取材料点从放置到释放静置的XY位移|501.76 mm|493.54 mm|
|4秒保持时越线比例|0|0|
|4秒保持时粒子投影IoU|0.03637|0.03633|

几何对照图 bend_pair_geometry.png 显示两组在持有阶段形成聚拢的移动片，释放后均恢复展开形态。以上近层/IoU是几何代理，不是接触力或三角面重叠证明。

沉降初态顶点平均差2.274mm、最大差9.350mm；动作标签相同，但自适应数值目标和材料分组可随沉降变化。这是一次整体policy敏感性对照，不能据此推断bend在所有路径中无影响，也不能证明某个唯一回弹根因。57动作超12预算，仅开发试跑。

## 下一步：离线结构审查，暂不启动GPU

以现有阶段顶点、初始网格拓扑和实际附件坐标，核对闭合衣物上下材料层在抓取及折叠时如何变形；对比原实现抓取语义和当前中央单点，明确能否通过真实可表达的夹持形成整段衣摆翻折。输出一份抓取/路径方案，写清公共XYZ+yaw+gripper如何表达、是否需要Backend固定执行规则、释放条件和可观测失败条件。禁止直接移动布料顶点、隐藏俯仰指令或用保留约束冒充成功。

仅在该审查支持具体机制后准备一个L1候选，仍使用原物理基准；没有支持则明确任务/抓取能力限制，先讨论必要的接口或任务修订，不继续高度、锚点数量或速度扫描。三档验收和Day5继续等待真正可重复的L1。
'''
(out/'pilot_review.md').write_text(report,encoding='utf8')
status='''bend100/10已完成审查：构造/USD及运行时数组证实B生效（22726项100→10），但两组均释放回弹约0.5m，保持时越线比例0。B视频643帧、几何340帧完整，仍无L1候选，正式成功0。报告：day4-actionchunk-test/results/day4-minimum-half-fold-20261031-070836-491946/pilot_review.md。

下一步仅进行离线抓取/材料拓扑与路径结构审查：检查上下材料层和当前附件的作用，核对原抓取语义，形成符合XYZ+yaw+gripper的一个可检验L1方案，再决定是否准备实验。停止bend及质量/迭代数、高度、锚点数量和速度扫描；不重复失败组。本轮未启动新实验。

'''
for name in ['DAY4_NEXT_STEPS.md','DAY4_MINIMUM_PLAN.md']:
 p=Path(name);text=p.read_text(encoding='utf8');start=text.index('## 唯一下一步');end=text.index('## 最低完成顺序',start);text=text[:start]+'## 唯一下一步\n\n'+status+text[end:];p.write_text(text,encoding='utf8')
p=Path('DAY4_ACCEPTANCE_TRACKER.md');p.write_text('# 2026-10-31 bend对照结束\n\n'+status+p.read_text(encoding='utf8'),encoding='utf8')
p=base/'BEND_PAIR_DECISION.md';s=p.read_text(encoding='utf8');s=s[:s.index('## 文件与状态')]+'## 文件与状态\n\n'+status;p.write_text(s,encoding='utf8')
print('REPORT_AND_PLANS_UPDATED')
