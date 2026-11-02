# v6：辅助块与默认地面配对过滤

本次只验证第2步短程抓取，禁止把结果计入正式折叠成功。

## 单一修改

在 reset 前对三个辅助刚体添加 `UsdPhysics.FilteredPairsAPI`，唯一新增目标为 `/World/defaultGroundPlane/GroundPlane/CollisionPlane`。保留已有过滤关系、块 collisionEnabled、手指/布料对地碰撞、抓取偏移、质量、轨迹及控制器。初始化后和保持后读取过滤关系。

## 判读（运行前固定）

- 沿用 v5 四个公共动作和60步保持、30步释放静置。
- 原门槛不变：末端位置误差<10mm、末臂速<0.1rad/s、原姿态到达判断通过、最大锚点误差≤10mm；释放后无 holding 或启用附件。
- 额外诊断：60步块中心与目标的误差。最大误差<1mm作为解除约4.8mm地面顶住现象的假设检查，单独报告，不替换原门槛。
- 原块—地面阳性对照被本次过滤主动移除，保留其原始flags但不得据此推断记录失败，也不得把无事件当成全场景无碰撞。结合回调错误、机器人接触事件和块跟随读数解释。
- 只运行一次；失败则保存并审查，不自动调整阈值或启动扫描。通过也须等待用户指令再进入完整L1。

## 运行

`bash /root/autodl-tmp/run-square-grasp-hold-v6.sh`

使用独立 v6 文件、输出目录和 SHA256 清单。旧依赖hash沿用v5清单，完整结果由用户手动下载。

## 本次结果：第2步完成

远端目录 `/root/autodl-tmp/day4-square-grasp-hold-v6-20261101-051527-577538`。只运行一次，`passed=true`、errors为空，PYTHON_EXIT和TEE_EXIT均0，视频首帧可解码；尚未人工观看完整视频，不计正式折叠。

| 检查 | 结果 |
| --- | --- |
| 原末端位置门槛 | 0.473296 mm，通过 |
| 原姿态门槛 | true |
| 保持末臂速 | 0.00860185 rad/s，通过 |
| 最大锚点间隙 | 1.39056 mm，通过 |
| 60步块中心最大跟随误差 | 0.0120804 mm，额外<1mm假设检查通过 |
| 最终块中心z / 目标z | 10.206694 / 10.206499 mm |
| 释放状态 | 三槽 holding=false、enabled=false |
| 过滤关系 | 创建后、reset后及保持后均仅增加默认地面，块碰撞保持开启 |

辅助块底部可以低于地面，是本次明确允许的虚拟附件代理行为；它不是实体夹爪。手指和布料仍保留原对地关系。与v5约4.8mm偏差相比，此次支持“辅助块被地面支撑阻挡”解释；不证明完整L1或所有接触问题解决。

接触报告：178次回调、356条robot_ground事件、errors为空，说明事件回调工作。块净接触力150次采样均0，无读取异常；原块—地面阳性对照被主动过滤，所以旧event/force/positive_control_valid为false，保持原值。独立力通道未获本次阳性验证，不以零值证明无接触；布料粒子接触也未认证。

仍有资产纹理缺失及退出期GLFW/USD引用警告；本次无异常停止。原依赖SHA校验通过，本地Python语法和原held/release判据一致性检查通过。未启动第3步、未提交或推送Git。

手动下载（本地PowerShell）：

```powershell
scp -P 22895 -r root@connect.nmb1.seetacloud.com:/root/autodl-tmp/day4-square-grasp-hold-v6-20261101-051527-577538 "E:\learning\project\thesis\day4-actionchunk-test\results"
```
