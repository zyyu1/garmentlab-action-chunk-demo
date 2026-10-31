# Day4 最低完成计划（当前有效版本）

## 当前状态

正式成功0。中央单点v5能完成动作但释放后回弹；侧边v6/v7未通过附件跟随检查。停止高度、锚点数量、速度及翻腕微调分支。历史进度已归档同名_HISTORY_THROUGH_V7.md，不再将旧“待运行”混入当前步骤。

## 唯一下一步

统一公共姿态候选已准备：XYZ仍是世界right_gripper；yaw实际映射为Rz(yaw)Rx(pi)，固定局部Z向下；抓取参考点为URDF指尖中点（局部+3.4mm）。仅在独立SquarePoseBackend候选中实现，不覆盖共享Backend。

离线URDF IK/FK通过抓取段，下降相邻关节解变化<=.0531rad；手指网格最低距地约1mm，实际接触仍待验证。完整折叠末段出现约3.15rad解跳变，暂不执行。详见DAY4_SQUARE_FRAME_AUDIT.md及frame_audit报告。

18文件已上传、哈希及语法通过。用户执行短程接近/下降/抓取/释放，不折叠：

```bash
bash /root/autodl-tmp/run-square-grasp-pose.sh
```

完成后自动下载审查位置/姿态/速度、附件和释放状态；接触零事件仍不能排除碰撞。通过后才接回L1并处理连续路径，再整合正式Backend。正式成功0。

## 最低完成顺序

1. 获得一次完整OPEN、退让、静置后保持重叠的L1候选，独立重复一次确认。
2. 将采用的抓取/控制整合到正式Backend，统一公共XYZ+yaw+gripper语义；实际折叠+recovery不超过12个高层动作，不隐藏expert指令或直接材料操作。验证必要重抓取及reset清理。
3. 固定L1/L2/L3扰动、seeds和settle，保存每档10张初态图；一个有停止条件的recovery模板，每回合0–2次，仍满足动作预算。
4. 用开发成功/失败例冻结alignment、overlap、测量时刻及success阈值，再运行正式批次。
5. 每档至少5条正式成功，共至少15条；保留全部尝试及失败分母，报告rejection rate；连续10次reset/rollout可靠性检查并入批次。
6. 核验接口隔离、保存配置/动作/状态/视频及验收表，结束Day4进入Day5。

## 实例和权限

当前`root@connect.nmb2.seetacloud.com:23636`，非交互SSH认证已通过。用户已授权自动上传本任务必要实验文件、下载完整结果，无需重复请求传输权限。当前由用户运行仿真，助手准备/上传/检查及下载审查；本轮未启动GPU实验。
