# GarmentLab 调试日报与交接记录

日期：2026-10-13（Day 3）
状态：Day 3 完成。接口层全部写完，纯 CPU 单测通过。Isaac Sim 启动验证和难度扰动留给 Day 4。

------

## 1. 今日结论

Day 3 目标是把 Day 2 的临时脚本收敨成正式接口。已完成：

- **冻结 observation / action schema**，policy 输入 46 维、输出 5 维，字段顺序写死在代码里，不再修改。
- **`RobotBackend` 抽象类**：policy 与设备之间唯一接口。
- **`MockBackend`**：纯 Python，无 GPU 单测，通过全部 8 项 smoke test。
- **`RealRobotBackendStub`**：真机占位，接口合规，调用即抛 `NotImplementedError`。
- **`GarmentLabBackend`**：封装 GarmentLab `FoldEnv`，懒加载，只有 `start()` 才启动 Isaac Sim。
- **`envs/difficulty.py` + `configs/difficulty.yaml`**：三档初态参数冻结，flat 可用，perturbed/crumpled 抛 `NotImplementedError` 留给 Day 4。

未做（有意延后到 Day 4）：

- `GarmentLabBackend.start() → get_observation() → stop()` 真实启动验证。
- perturbed / crumpled 的物理扰动实现。
- `envs/garmentlab_wrapper.py`：**评估后认为冗余**，backend 已承担 reset/get_observation/execute 三者，Day 4 决定是否还需要。
- 侧视图相机。
- `tests/` 目录。

Day 3 判定：**通过**。

------

## 2. 提交记录

`garmentlab-action-chunk-demo` 本地 main：

text

```
2307770  (HEAD -> main) Day3: GarmentLabBackend + RealRobotBackendStub + difficulty protocol (flat only) + configs
de104ba  Day3: freeze observation/action schemas, RobotBackend base, MockBackend with smoke test
e3ca120  (origin/main) docs: update README to Day 2 status ...
79ea081  Merge remote-tracking branch 'origin/main'
5f2382f  docs: Day 2 report ...
```



`2307770` 和 `de104ba` **尚未 push**。明天和 Day 4 的 commit 一起推。

`GarmentLab` 上游仓库未改动，仍停在：

text

```
f2988b1  (tag: autodl-adapt-2026-10-13)
6ee0620  (grafted, origin/main)
```



------

## 3. 今日新增文件

text

```
garmentlab-action-chunk-demo/
├── schemas/
│   ├── __init__.py
│   ├── observation.py          冻结观测：keypoints + EE pose + gripper + phase，向量 46 维
│   └── action.py               冻结动作：Cartesian waypoint + gripper command，向量 5 维
├── backends/
│   ├── __init__.py
│   ├── base.py                 RobotBackend 抽象类
│   ├── mock_backend.py         纯 Python 单测后端
│   ├── real_robot_backend_stub.py  真机占位
│   └── garmentlab_backend.py   GarmentLab FoldEnv 封装
├── envs/
│   ├── __init__.py
│   └── difficulty.py           三档初态协议
└── configs/
    └── difficulty.yaml         三档参数
```



------

## 4. 已通过的测试

| 测试         | 命令要点                              | 结果                   |
| :----------- | :------------------------------------ | :--------------------- |
| schema 单测  | `OBS_VEC_DIM=46, ACTION_VEC_DIM=5`    | SCHEMAS_SMOKE_OK       |
| base 抽象类  | `inspect.isabstract(RobotBackend)`    | BASE_IMPORT_OK         |
| mock backend | 8 项断言                              | MOCK_BACKEND_SMOKE_OK  |
| real stub    | 接口合规 + NotImplementedError        | STUB_SMOKE_OK          |
| 接口一致性   | 三个 backend 均无抽象方法残留         | IFACE_OK ×3 + GUARD_OK |
| difficulty   | parse / defaults / YAML / determinism | DIFFICULTY_SMOKE_OK    |

全部为纯 CPU 测试，不消耗 GPU。

------

## 5. 关键设计决策

**1. 为什么 `valid_keypoint_count` 单独存一个字段**

Day 2 发现原始 garment 顶点有 9945 个，但 policy 输入不能是 9945 维。方案：

- 取 `num_keypoints=8`，用 `np.linspace` 从 9945 顶点里均匀采样。
- `valid_keypoint_count` 记录真实有效的关键点数（可能小于 8）。
- 如果原始顶点数 < 8，则补零，`valid_keypoint_count` 标出真实数量。

**2. 为什么 `CartesianAction` 只含 4 维 pose + gripper command**

从 Day 2 的脚本看，GarmentLab 控制接口是 `grasp([pos], [None], [True])` / `move` / `ungrasp([False])`，pos 是 3 维 + 方向由 controller 决定。所以：

- `target_pose = [x, y, z, yaw]`，4 维。
- `yaw` 目前在 `GarmentLabBackend` 里**未接线**，传 `ori=[None]`。
- 这样 4 维 pose 是 device-independent 的，真机后端接 yaw 也容易。

**3. 为什么 `GarmentLabBackend` 懒加载**

`from Env.env.FoldEnv import FoldEnv, simulation_app` 会触发 `SimulationApp` 构造。如果在模块顶层 import，任何 `from backends.garmentlab_backend import ...` 都会启动 Isaac Sim，甚至 import 检查也会启动。

方案：`_import_garmentlab()` 在 `start()` 里第一次调用时才执行 import。所以：

- `import backends.garmentlab_backend` 是安全的。
- 构造 `GarmentLabBackend()` 也不会启动 Isaac。
- 只有 `start()` 会。

**4. 为什么删除 `.gitignore` 里的 `envs/`**

merge 时从 GitHub 那版继承了 `envs/`，原意是忽略虚拟环境目录。但我们项目的 `envs/` 是源码（`difficulty.py`），而虚拟环境在 `<remote-root>/envs/isaac40`，不冲突。所以删掉这个忽略规则。

------

## 6. 未解决事项（Day 4 处理）

1. `GarmentLabBackend.start()` 的真实启动未验证。
2. `reset(seed, difficulty)` 目前只接受 `flat`，`perturbed` / `crumpled` 抛 `NotImplementedError`。
3. `_execute_single` 里 `yaw` 未接线。
4. `_read_end_effector_pose` 依赖 `env.robots[0]` 的 `get_end_effector_pose` 方法名，尚未确认 MyFranka 是否提供；如果都没有，返回零填充 + `qw=1`。
5. `_read_garment_geometry` 的 `valid_keypoint_count` 已通过 patch 修正，但未在真实 backend 上跑过。
6. 侧视图相机未加。
7. `envs/garmentlab_wrapper.py` 是否需要，Day 4 决定。
8. `runs/` 里的 npy 仍在 git 里，Day 5 生成大量 demonstrations 前需重新评估。
9. 本地两个 commit 未 push。

------

## 7. Day 4 开工清单

text

```
1. 启动 Isaac Sim，跑 GarmentLabBackend.start() → get_observation() → stop()
   - 确认 observation 向量维度和内容
   - 确认 execute() 能跑单步动作
   - 确认 stop() 能干净退出

2. 实现 envs/difficulty.apply() 的 perturbed 和 crumpled
   - 复用 Day 2 的 grasp-lift-drop 模式
   - 每档保存 10 张 initial-state 截图
   - 肉眼确认三档可区分

3. 参数化 expert
   - 把 scripts/fold-third-grasp-debug.py 的 12 步序列抽成 experts/fold_expert.py
   - 输入：pick_pose / place_pose / lift_height
   - 内部展开成 CartesianAction 序列

4. 定义 alignment / overlap / success threshold（正式训练前冻结）

5. 决定 envs/garmentlab_wrapper.py 是否需要

6. 加侧视图相机占位
```



------

## 8. 一句话交接

Day 3 完成接口层：observation/action schema 冻结（46 → 5 维），`RobotBackend` 抽象类 + `MockBackend` + `RealRobotBackendStub` + `GarmentLabBackend`（懒加载）全部就位，`envs/difficulty.py` 三档参数冻结。纯 CPU 测试全通过。两个 commit（`de104ba`、`2307770`）尚未 push。Day 4 第一件事是启动 Isaac Sim 验证 `GarmentLabBackend.start()`，然后实现 perturbed / crumpled 扰动和参数化 expert。