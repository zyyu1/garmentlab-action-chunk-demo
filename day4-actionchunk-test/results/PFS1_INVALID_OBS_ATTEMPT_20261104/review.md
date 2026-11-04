# a5-rc2-pfs1 attempt 1：观测实现无效，已停止

日期：2026-11-04。第一次 4202 single 尝试在观测阶段被发现无效，**已停止并保留现场**。该尝试不产生物理对照结论，不计为有效单例结果。

## 发生了什么

- 运行开始时间：`2026-11-04T02:04:15Z`；结果目录 `day4-a5-rc2-pfs1-20261104-100417-179837`。
- 当时 manifest `51d560f4…`，config `2d72a405…`。
- 运行进入 recovery 后，`pfs1_stages/initial_loaded.npz` 的 `velocity_present=false`，错误为：
  `AttributeError("'ClothPrimView' object has no attribute 'get_world_velocities'")`。
- 当前安装版本的 `ClothPrimView` 提供 `get_velocities(clone=True)`，不提供 `get_world_velocities`。
- 按“若身份或证据异常，保留现场并停止”的要求，终止 tmux/进程；没有继续 episode，没有进入释放/评价。

## 保留的现场

- [结果目录](day4-a5-rc2-pfs1-20261104-100417-179837/)：仅含早期 `pfs1_stages/initial_loaded.npz`，没有 `result.json`/`success_trace`。
- [runner.log](runner.log)、[console.log](a5-rc2-pfs1-console.log)、[attempts.jsonl](attempts.jsonl)。
- 该 started 记录没有对应 finished；它属于**旧 manifest** 的未完成尝试，不是有效物理运行。

## 修正与后续

- 只修正观测 API：`pfs1_observation.cloth_velocities()` 改用 `ClothPrimView.get_velocities(clone=True)`；粒子摩擦参数、动作逻辑、初态和评价器不变。
- 新 manifest 已更新；新 runner 增加“当前 manifest 存在未完成尝试则阻止”的检查。旧 manifest 的这次未完成尝试不会阻止新 manifest 的预检，但会永久保留在本目录。
- 需要重新上传、重新预检，再执行一次有效的 4202 single。**这次无效尝试不是第二次物理对照。**

## 边界

- 本次没有释放、退让、正式窗口或质量判定，不能用于任何 a5-rc2-pfs1 结论。
- 没有修改 `particleFrictionScale` 以外的物理参数；没有重跑七例、没有 held-out、正式成功计数不增加。
