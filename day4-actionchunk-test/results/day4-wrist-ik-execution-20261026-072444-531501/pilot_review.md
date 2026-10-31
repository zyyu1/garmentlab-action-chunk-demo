# v4高度对照结果

25、26点通过，末帧速度接近零。27点的reached=true仅满足既有位置/姿态/关节误差阈值；末帧joint5速度4.7165 rad/s，不能称为稳定到达。27点插值第26步已有腕部速度异常，28点第20步joint6误差0.224565 rad触发停止。

低位v3异常起始joint2约0.8109 rad、joint6约1.1177 rad；抬高v4起始joint2约0.7786 rad、joint6约0.6438 rad。高度改变失稳发生点，但没有接触证据，尚不能归因于地面碰撞、自碰撞或其他约束。

v5仅添加机器人刚体PhysxContactReportAPI与接触回调，记录相位、step、actor、collider、冲量。原路径和阈值不变，避免无证据继续改高度。接触API参考NVIDIA开发指南：https://docs.omniverse.nvidia.com/dev-guide/latest/programmer_ref/physics/rb_physics.html 。无事件或回调错误不能当作无碰撞证明。脚本待远端运行，本地仅语法与包装检查。
