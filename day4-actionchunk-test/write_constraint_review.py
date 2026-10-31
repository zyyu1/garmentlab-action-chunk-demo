from pathlib import Path
import hashlib,json
b=Path('day4-actionchunk-test/constraint_api_review')
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in b.iterdir() if p.suffix in ['.py','.usda']};(b/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
(b/'API_REVIEW.md').write_text('''# Isaac4.0 夹持约束API审查

## 判定

接口层面具备组合候选所需的布料附件、动态刚体和球形关节；尚未证明粒子布料附件能对动态载体产生足够的反作用力矩。因此结论是“可构造，动力学能力待验证”，不是可用修复。没有启动SimulationApp或GPU仿真，没有修改正式Backend。

## 实例证据

从当前实例root@connect.nmb2.seetacloud.com:23636下载环境内文件：
`/root/autodl-tmp/envs/isaac40/lib/python3.10/site-packages/isaacsim/extsPhysics/`

- omni.usd.schema.physx/plugins/PhysxSchema/resources/generatedSchema.usda:4410–4468：PhysxPhysicsAttachment的actor0/actor1、points0/points1及attachmentEnabled。点对在各actor局部坐标定义；没有独立的“允许附件旋转”或柔顺刚度字段。不能编造一个freeRotation属性。
- omni.physx.demos/omni/physxdemos/scenes/SphericalJointDemo.py：UsdPhysics.SphericalJoint关联两个刚体/静态体；示例设置45度锥角限制。不能原样复制并声称无限制翻转，也不能将球关节直接连接到粒子布料mesh。
- omni.physx.tests/omni/physxtests/tests/PhysxPhysicsAttachment.py:683–724：particle cloth测试在设置RigidBody时传True（运动学），只检查cloth未落地。它不构成动态载体受cloth力矩驱动的测试。

完整快照及SHA256见source_manifest.json。来源是安装文件，不将其等同于在本场景运行通过。

补充官方文档（较新版本，仅背景，不替代4.0验证）：https://docs.omniverse.nvidia.com/kit/docs/omni_physics/108.1/dev_guide/particles/particles.html 说明粒子cloth可以与collider/rigid/deformable建立attachment，但没有为当前组合提供实测保证。

## 候选结构与边界

公共XYZ+yaw+gripper控制跟随点；另一个动态小刚体经球形关节连接跟随点，布料附件连接此动态刚体。局部转角必须来自动力学，不能在实验循环内按fold阶段设置角度、覆盖角速度或更新points1追踪目标。材料选择及附件数据仅在Backend。OPEN关闭cloth附件，保留辅助对象以避免运行时删除拓扑问题。

这是一个允许转动的附件代理，不是已验证的真实Franka夹爪接触模型。即使通过机械测试，也要单独声明这一建模假设。

## 下次唯一运行任务：最小动力学能力验证

先准备独立短场景，不加载Franka、不运行整段fold、不扫描质量或材料参数。测试载体动态性、球关节和粒子cloth反作用三个环节，失败立即记录并停止。

1. 刚体对照：载体有已知偏心重力负载，球形关节枢轴固定，验证出现预期方向转动且枢轴误差小；无角度/角速度强制写入。排除关节误设、惯量锁定和姿态控制。
2. cloth反作用对照：载体质心与枢轴重合、初始速度为零、无刚体外加力矩；仅偏心挂接cloth，在独立重建的enabled与disabled场景比较载体旋转。cloth与载体碰撞须隔离，避免把碰撞力误记为附件反作用。记录attachment点误差及cloth下落，确认附件真的启用。
3. OPEN验证：在attached场景关闭attachment，检查cloth脱离和自由下落；不是仅检查USD布尔值。记录关闭前后完整轨迹及运行日志。

每项必须保存步号、dt、载体姿态/角速度、枢轴误差、各cloth锚点误差、实际质量/惯量和constraint状态。预先声明时间窗口和数值容差，不能事后改阈值凑通过；没有转动时区分测量/配置失败与有效阴性。

只有1通过且2显示附件驱动的自由转动、3真正释放，才把该结构用于衣摆夹持能力测试。反作用证据不足则停止此结构，不回到高度/锚点数/速度扫描；后续需明确讨论执行器/任务能力边界。该最小测试本身不计L1或Day4成功。

## 状态

本轮完成API审查与测试协议；测试脚本尚未编写/上传，未启动任何仿真。下一步是按此协议准备一个可审查的短场景脚本，而非再次核查同一批API，也不是完整折叠重跑。
''',encoding='utf8')
status='''Isaac4.0安装API审查已完成，见day4-actionchunk-test/constraint_api_review/API_REVIEW.md。布料附件+动态载体+球关节可表达候选结构，但cloth附件反作用力矩尚无证据；不能声称已实现自由转动夹持。

唯一下一步：准备独立短场景能力验证脚本，先验证刚体球关节，再比较cloth附件enabled/disabled对动态载体转动的影响，最后验证OPEN。全部通过才接入衣摆短程抓取；当前未编写/运行该测试，无新GPU实验，正式成功0。停止材料/路径参数扫描。

'''
for name in ['DAY4_NEXT_STEPS.md','DAY4_MINIMUM_PLAN.md']:
 p=Path(name);s=p.read_text(encoding='utf8');a=s.index('## 唯一下一步');z=s.index('## 最低完成顺序',a);p.write_text(s[:a]+'## 唯一下一步\n\n'+status+s[z:],encoding='utf8')
p=Path('DAY4_ACCEPTANCE_TRACKER.md');p.write_text('# 2026-10-31 约束API审查\n\n'+status+p.read_text(encoding='utf8'),encoding='utf8')
print('API_REVIEW_AND_PLAN_SAVED')
