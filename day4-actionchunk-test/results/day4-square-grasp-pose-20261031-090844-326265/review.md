# 短程抓取 v1 失败审查

正式成功 0；短程完整验收未通过。

## 证据

完整目录 45 份文件经远端 SHA256 核验一致；原始 runner.log 已保留，视频离线解码 217 帧。没有 result.json 或 state_trace.json，不能补写成原始运行结果。

日志确认 approach、descend、close 执行完成，附件实际启用。抓取区域距离 5.104 mm，启用瞬间最大粒子位移 1.361 mm；这些不是完整保持/释放通过证据。

首次 held_stationary 调用将姿态作为 Python list 传给要求 shape 属性的转换函数，触发 AttributeError。随后 finally 保存 state_trace 时嵌套 ndarray 无法 JSON 序列化，触发 TypeError，跳过了原定 b.stop。之后卸载过程中出现 segmentation fault，退出 139。段错误的底层原因未独立确定，不据此认定物理发散。

保持 60 步和 OPEN/释放 30 步均未完成。接触报告 12 刚体已配置，订阅创建成功，回调/事件/错误均为 0；通道未独立验证，不能解释成无碰撞。

## 已准备修正

square-grasp-pose-v2-serialization-fix：保持/释放使用公共 orientation_euler(0.) 返回的 NumPy 数组；JSON 支持嵌套 NumPy 数组和标量；保存流程外加 finally，确保保存失败仍调用 b.stop。路径、物理配置和验收阈值不变。

本地 AST、嵌套 NumPy 序列化和两处姿态调用检查通过；18 份远端依赖哈希/Python AST 通过。新脚本与 manifest 已上传，未启动复测。下一步仍为 bash /root/autodl-tmp/run-square-grasp-pose.sh，通过保持和释放后才讨论 L1。
