# 对齐组抬升后目标保持采样

新增文件：day4-aligned-lift-hold-test.py、lift_hold_step_observer.py。原 backend 和此前通过的观察器文件均不修改。

在原有抬升动作结束后，保持同一末端目标，继续执行 180 次原控制器 _tick(..., follow=True)，即 3 秒仿真时间。末端可能继续靠近原目标，脚本不会将“目标保持”当作“机器人立即静止”；记录实测运动以便后续判断。

下降、抓取、锚点对齐、抬升参数与原来一致。在进入新增保持阶段前，核对原始 50 帧完整顶点、末端和方块位姿、缩放、锚点目标及步号，要求与上次逐步采样完全一致。若不一致，保存已采集内容并停止。

采样 phase_code=0 对应原始起始帧和抬升帧，phase_code=1 对应新增的保持步；两段共享的边界位于 hold_start_frame。预期 50 个原始采样加 180 个保持采样，共 230 帧，覆盖 229 次显式 World.step。数据不覆盖 PhysX 内部子步。

保持后另存 03b_hold 快照，使用保持末端的实测位置作为释放动作目标；释放回落和方块漂移以保持结束状态为比较基准。保持前的抬升量与跟随误差单独保存。

源码哈希、原始轨迹前缀、保持前阶段快照、前五次 execute 的动作矩阵及步数均检查。保持和释放后的状态本来就会受新增阶段影响，不与旧的立即释放运行要求逐元素相同。

输出目录：/root/autodl-tmp/day4-aligned-lift-hold-<时间戳>/。
主要轨迹文件：lift_hold_trace/frames.npz、steps.csv、summary.json。summary 另存最后 30 个保持样本的速度与边长范围，作为诊断而非平衡或物理质量验收。

成功标记：ALIGNED_LIFT_HOLD_TRACE_OK，并检查 result.json 中 passed=true、original_lift_trace_exact_checks 全部 true、reference_replay_exact_checks 全部 true 和 lift_hold_trace.capture_complete=true。

本地已验证 Python 3.10 语法；通过重放真实 50 帧检查采样前缀、阶段标记、步进包装调用次数、恢复及保存逻辑。尚未运行新的 GPU 保持实验。
