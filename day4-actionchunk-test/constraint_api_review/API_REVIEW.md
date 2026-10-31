# Isaac4.0 夹持约束API审查

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

短场景约束能力测试已准备、上传并完成远端Python/Shell语法及3文件SHA256核验。判读程序的合成阳性、有效阴性、无效附件记录测试通过；不能将这些静态检查称为物理验证。

下一步由用户执行 `bash /root/autodl-tmp/run-attachment-canary.sh`。依次独立进程运行rigid、disabled、enabled；每组180个1/120秒物理步，应用启动耗时另计。任一失败立即停止，保留完整日志/场景/轨迹/读回。助手收到完成后自动下载审查。当前未启动GPU，正式成功0。

## 预注册判读（脚本为准）

枢轴误差<5mm，>20mm中止；刚体对照1秒内转角>0.1rad且前0.5秒正y转角>0.05rad。关闭附件对照载体总转角<0.01rad，0.5秒内锚点高度下降>0.1m。开启附件前120步最大锚点误差<5mm，正y转角比关闭对照增加>0.05rad，关闭附件后0.5秒锚点下降>50mm且与载体目标分离>50mm。阈值仅诊断本合成场景，不是Day4折叠成功阈值，也不将阴性外推为API全局单向。

此测试采用独立小cloth矩形、载体质量20g、惯量每轴0.0001 kg m²、cloth总质量21g，无地面、载体无碰撞，粒子非粒子碰撞关闭。原GarmentLab参数/场景未改变。偏心刚体对照质心x=50mm，cloth两组载体质心=枢轴。合成cloth不是双层衣摆；测试通过仅允许进入下一抓取能力验证。
