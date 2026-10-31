from pathlib import Path
out=Path('day4-actionchunk-test/results/day4-attachment-canary-v2-e5aV7xe4')
(out/'review.md').write_text('''# 附件短测试v2审查

结论：质量配置正确，测量修订无可见轨迹扰动；持有期转动响应仍未达预注册门槛。停止当前被动载体候选接入L1，不改变阈值、质量、惯量或时长继续试参。正式Day4成功仍为0。退出码2为能力关卡停止，不是脚本崩溃。

## 验证

完整目录已下载。归档SHA256：0512681bfc4223bec4c111a689997d1fe9575c4928f5dd6ad4d46e150961ea2c。三组源码、runner及判读器哈希通过；各181条连续记录、completed=true、errors为空。

21个粒子各0.001000000164kg，总0.02100000344kg，0/120/180步数组完全一致，与USD总质量0.021kg相符。enabled和disabled均通过质量检查。载体质量/惯量已在v1核实。

三组每步的所有v1已有字段（姿态、速度、几何、附件误差等）与v1完全相同。因此新增质量/质心读回未改变这两次观测轨迹；不是一般性的无扰动保证。

球关节刚体对照、disabled自由下落对照、enabled保持和OPEN脱离均通过。持有期正y转角0.0239615rad（1.373度），小于既定0.05rad（2.865度）。全程0.0464748rad最大值发生在OPEN之后，不能拿来替代持有期门槛。有效小幅响应存在，不解释为无反作用或API普遍单向。

布料重力绕枢轴y矩开始约0.0288294Nm、释放前约0.00829079Nm。它是整个布料的外部重力矩，不能直接视为传入载体的附件力矩：布料本身运动、动量及求解器约束响应均参与平衡，当前未测直接传递力矩。因此质量审查排除了配置不符，但没有确定响应偏小的唯一原因。

## 收敛决策

本分支到此结束，不发出v3参数调整或完整折叠命令。未证明当前被动载体能满足翻折要求，也未证明任何其他结构均不可行。

下一步应回到Day4的L1方案决策：将已有中央/侧边抓取、刚性patch、翻腕及被动载体的证据和公共接口限制一起整理，先给出一个有明确物理依据、接口和动作预算的可执行候选；若不存在足够依据，应明确列出必要的抓取模型或任务范围修订供用户选择，而不是继续扩展细碎诊断。不得把未通过能力门槛的载体带入正式Backend，也不得降低释放保持验收要求。

完整数值见independent_audit.json，原始assessment.json保留不覆盖。本轮仅下载/离线审查，没有启动GPU。
''',encoding='utf8')
status='''v2结果已下载审查：21个粒子各约1g，总21g，起止一致；三组已有轨迹字段与v1逐步完全相同。质量配置不符已排除，持有期0.02396rad仍低于0.05rad门槛。停止当前被动转动载体接入L1，不追加参数扫描。报告day4-actionchunk-test/results/day4-attachment-canary-v2-e5aV7xe4/review.md。正式成功0。

下一步回到L1方案决策：基于现有失败证据明确抓取模型、公共接口及≤12动作预算，形成有依据的可执行候选；若需要改变任务/执行器能力，明确列出修订选项，不能隐含修改。当前没有待执行实验命令，不重跑短测试、不降阈值、不增加v3扫描。本轮未启动GPU。

'''
for name in ['DAY4_NEXT_STEPS.md','DAY4_MINIMUM_PLAN.md']:
 p=Path(name);s=p.read_text(encoding='utf8');a=s.index('## 唯一下一步');z=s.index('## 最低完成顺序',a);p.write_text(s[:a]+'## 唯一下一步\n\n'+status+s[z:],encoding='utf8')
p=Path('DAY4_ACCEPTANCE_TRACKER.md');p.write_text('# v2审查完成：停止被动载体分支\n\n'+status+p.read_text(encoding='utf8'),encoding='utf8')
