# Square L1 v1 开发候选

40cm单层方巾、441顶点、800三角形、单Franka。总质量44.1g。公开动作计划9步，XYZ+yaw+gripper，yaw固定0，无俯仰侧通道。

入口：../run-square-l1.sh；清单：../square-l1-files.json；离线检查：preflight.json。

本地几何与语法检查通过；服务器15文件哈希、Python AST和Bash语法检查通过。尚未进行GPU验证。

运行命令：bash /root/autodl-tmp/run-square-l1.sh

结果必须检查完整OPEN后3秒/4秒保持及视频。pipeline通过不代表fold成功。本候选不计入正式成功；Backend统一整合、重复reset、重抓取和recovery预算尚待验证。
