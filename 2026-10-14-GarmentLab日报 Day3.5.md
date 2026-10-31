# GarmentLab 调试日报与交接记录

日期：2026-10-14（Day 4，WIP）
状态：Day 4 未完成。接口层首启通过、world-frame 读取修好、difficulty 三档协议实现并通过单测；三档初态截图脚本因 `ClothPrimView` 未初始化而失败。已提交 WIP 检查点 `233771e`。

------

## 1. 今日结论

Day 4 目标是把 Day 3 的接口真正跑起来，并实现三档初态。

已完成：

- **Day 3 的两个 commit 推送到 GitHub**（`2307770`、`de104ba`）。
- **首次启动 Isaac Sim 验证 `GarmentLabBackend`**：`start() → reset() → get_observation() → execute() → stop()` 全程通过，退出码 0，总启动约 160 秒。
- **定位并修复 backend 的两处 observation bug**：
  - `_read_garment_geometry` 从 `get_vertices_positions()`（局部坐标系，Y≈7.6 米不可用）改为 `get_realvertices_positions()`（世界坐标系）。
  - `_read_end_effector_pose` 从猜方法名改为 `MyFranka.get_cur_ee_pos()`。
- **实现 `envs/difficulty.apply()` 三档协议**：flat 加平移 + yaw；perturbed 加 1 次 lift-drop；crumpled 加 2 次 lift-drop。
- **三档回归单测通过**：FLAT/PERTURBED/CRUMPLED/BARE/LIFT_GUARD。
- **写好 `scripts/day4_difficulty_smoke.py`**：三档 × 5 种子，逐档截图。

未完成（Day 4 明日续）：

- **三档初态截图脚本首次运行失败**：`AttributeError: 'ClothPrimView' object has no attribute '_max_particles_per_cloth'`。原因：GarmentLab 从未调用 `ClothPrimView.initialize()`，导致 `_physics_view is None`，`get_world_positions()` 走入 else 分支，该分支依赖仅在 `initialize()` 中设置的属性。这是**上游 Day 4 新暴露的 bug**，不影响 Day 3 的接口设计。

Day 4 判定：**WIP，不通过也不失败**。明天第一件事是修 `ClothPrimView` 初始化路径。

------

## 2. 环境

| 项目          | 值                                                           |
| :------------ | :----------------------------------------------------------- |
| 容器          | `autodl-container-5d974b909f-0ac9998e`                       |
| GPU           | **RTX 4080 SUPER**（32 GB；与 Day 2 日报里的 “RTX 4080” 略有差异，实际为 SUPER） |
| 驱动          | 580.105.08                                                   |
| CUDA 支持版本 | 13.0                                                         |
| Isaac Sim     | 4.0.0.0                                                      |
| Python venv   | `/root/autodl-tmp/envs/isaac40`                              |
| GarmentLab    | `/root/autodl-tmp/garmentlab_workspace/GarmentLab`           |
| 项目仓库      | `/root/autodl-tmp/garmentlab-action-chunk-demo`              |
| GitHub        | https://github.com/zyyu1/garmentlab-action-chunk-demo（Private） |

------

## 3. 提交记录

`garmentlab-action-chunk-demo` 本地 main：

text

```
233771e  (HEAD -> main) Day4 WIP: backend world-frame reading + difficulty protocol; ClothPrimView init bug to fix
2307770  (origin/main) Day3: GarmentLabBackend + RealRobotBackendStub + difficulty protocol (flat only) + configs
de104ba  Day3: freeze observation/action schemas, RobotBackend base, MockBackend with smoke test
e3ca120  docs: update README to Day 2 status ...
79ea081  Merge remote-tracking branch 'origin/main'
5f2382f  docs: Day 2 report ...
```



- `2307770`、`de104ba` 已推送 GitHub。
- `233771e` 是**本地 WIP 检查点，尚未推送**，明天修好 `ClothPrimView` 后一起推。

`GarmentLab` 上游未改动，仍停在：

text

```
f2988b1  (tag: autodl-adapt-2026-10-13)
6ee0620  (grafted, origin/main)
```



------

## 4. 首次启动验证结果

日志：`/root/autodl-tmp/day4-backend-smoke.log`

关键行：

text

```
IMPORT_BACKEND_OK
CONSTRUCT_OK {...'num_keypoints': 8, 'settle_steps': 120, 'max_action_steps': 15000}
START_OK elapsed=162.0s
RESET_OK
OBS_KEYS timestamp=130.0 kp_shape=(8, 3) valid=8
OBS_CENTER [0.528, 7.627, -0.650]      ← 局部坐标系，不符
OBS_EE [0, 0, 0, 1, 0, 0, 0]           ← 零填充，不符
OBS_GRIPPER 0 PHASE 0
OBS_VEC_DIM 46                          ← 与 schema 一致 ✓
EXECUTE_OK executed_steps=1
BACKEND_SMOKE_OK
STOP_BEGIN
STOP_OK
Python exit code: 0
```



**通过项：** 启动、观测向量维度、execute、clean exit。

**发现问题：** 坐标系不一致 + EE 读取空 + phase 状态机过糙。前两个当天已修；phase 状态机延后。

------

## 5. 今日代码变更

### 5.1 `backends/garmentlab_backend.py`

**修改 1：`_read_garment_geometry`**

python

```
# before
raw = np.asarray(self._env.garment[0].get_vertices_positions()).reshape(-1, 3)

# after：优先 world 坐标，失败回退局部
g = self._env.garment[0]
raw = np.asarray(g.get_realvertices_positions()).reshape(-1, 3)
# 或回退到 g.get_vertices_positions()
```



**修改 2：`_read_end_effector_pose`**

python

```
# before：猜 attr 名，全部失败 → 返回 0 + qw=1
# after：直接调用 MyFranka.get_cur_ee_pos()，返回 (pos, quat)
ret = robot.get_cur_ee_pos()
pos, quat = ret
out[:3] = pos[:3]
out[3:7] = quat[:4] / norm
```



**修改 3：`reset()` 接入 difficulty**

python

```
# after：reset() 里
from envs.difficulty import DifficultyLevel, load_configs, apply as apply_difficulty
rng = np.random.default_rng(0 if seed is None else int(seed))
lvl = DifficultyLevel.parse(difficulty)
cfg = load_configs()[lvl]
apply_difficulty(self, cfg, rng)
```



**新增 6 个 helper（给 difficulty 调用，不属于 policy API）：**

text

```
_garment_world_positions()        读世界坐标粒子
_set_garment_world_positions(pos) 写世界坐标粒子
_clear_garment_velocities()       复位速度
_settle(steps)                    推进物理
_apply_flat_perturbation(rng,cfg) 平移 + yaw
_lift_drop_once(rng,cfg)          一次 grasp-lift-drop
```



### 5.2 `envs/difficulty.py`

**`apply()` 从 Day 3 的 “flat 空实现 + 非 flat 抛错” 改为三档真实分派：**

python

```
# Step 1: flat 平移 + yaw（所有档位都做）
backend._apply_flat_perturbation(rng, config)

# Step 2: lift-drop 循环（perturbed 1 次，crumpled 2 次）
for i in range(config.num_lift_drops):
    backend._lift_drop_once(rng, config)
```



对无 `_apply_flat_perturbation` 的 backend（MockBackend）静默 no-op；对有 flat 但无 lift 的 backend 在非 flat 档位抛 `NotImplementedError`。

### 5.3 `scripts/day4_difficulty_smoke.py`（新增）

一次 Isaac 启动，三档 × 5 种子，每档：

1. `b.reset(seed, difficulty=lvl)`
2. `robot_reset()` 让机械臂离开视野
3. `camera.get_rgb_graph()` 截图
4. 打印世界坐标 center 和 kp_extent

输出目录：`/root/autodl-tmp/difficulty-<timestamp>/`。

------

## 6. 失败定位：ClothPrimView 未初始化

### 6.1 现象

text

```
File ".../GarmentLab/Env/Garment/Garment.py", line 91, in get_realvertices_positions
    return self.garment_mesh._cloth_prim_view.get_world_positions()
File ".../omni/isaac/core/prims/soft/cloth_prim_view.py", line 293, in get_world_positions
    [indices.shape[0], self.max_particles_per_cloth, 3], ...
File ".../omni/isaac/core/prims/soft/cloth_prim_view.py", line 176, in max_particles_per_cloth
    return self._max_particles_per_cloth
AttributeError: 'ClothPrimView' object has no attribute '_max_particles_per_cloth'
```



### 6.2 根因

`ClothPrimView.get_world_positions()` 有两条分支：

python

```
if not timeline.is_stopped() and self._physics_view is not None:
    positions = self._physics_view.get_positions()         # ← 正常路径
else:
    positions = zeros([.., self.max_particles_per_cloth, 3])  # ← 依赖未设属性
```



`_physics_view` 只在 `ClothPrimView.initialize(physics_sim_view)` 里设置。GarmentLab 的 `Garment.__init__` 创建了 `ClothPrimView` 但从未调用 `initialize()`，所以永远走 else 分支，撞上缺失属性。

Day 2 用 `get_vertices_positions()`（走 `_get_points_pose()`），完全绕过了这条路径，所以没有暴露。

### 6.3 候选修法（明日评估）

text

```
A. 在 GarmentLabBackend.start() 里显式调用
   g.garment_mesh._cloth_prim_view.initialize(world.physics_sim_view)
   → 但需确认 world.physics_sim_view 何时可用、是否必须在 world.reset() 之前

B. 读 ClothPrim 源码看有没有 _set_points_pose / _get_points_pose
   → 若有，直接读写 local frame；世界变换通过 garment prim 的 XformCache 补偿

C. 用 USD stage 层 XformCache + local points 手动计算世界坐标
   → 兜底方案，不依赖 ClothPrimView

D. 用 Garment.set_pose() 让 prim 世界变换平移，粒子不动
   → 最弱，flat 扰动只做视觉平移，物理不生效
```



明天先读 ClothPrim 源码（不启动 Isaac），选 A 或 B，跑一次 Isaac 验证。

------

## 7. 今日已通过测试

| 测试             | 证据                                       | 结果             |
| :--------------- | :----------------------------------------- | :--------------- |
| backend 启动     | `START_OK elapsed=162.0s`                  | 通过             |
| observation 维度 | `OBS_VEC_DIM 46`                           | 通过             |
| execute 单步     | `EXECUTE_OK executed_steps=1`              | 通过             |
| clean exit       | `Python exit code: 0`                      | 通过             |
| difficulty 回归  | FLAT/PERTURBED/CRUMPLED/BARE/LIFT_GUARD    | 通过             |
| 三档截图         | `AttributeError: _max_particles_per_cloth` | **失败，明日修** |

------

## 8. 远程文件交接

text

```
/root/autodl-tmp/day4-backend-smoke.py          首次 backend 启动测试脚本
/root/autodl-tmp/day4-backend-smoke.log         首次启动日志（通过）
/root/autodl-tmp/day4-difficulty.log            三档截图失败日志

/root/autodl-tmp/difficulty-20261014-000250/    空目录（截图未生成）

/root/autodl-tmp/garmentlab-action-chunk-demo/
├── backends/garmentlab_backend.py              已 patch（450 行）
├── envs/difficulty.py                          已 patch（225 行）
└── scripts/day4_difficulty_smoke.py            新增
```



------

## 9. 未解决事项

1. **`ClothPrimView` 未初始化**：三档截图阻塞点，明日优先。
2. **phase 状态机过糙**：现在只要发一次 OPEN 就跳到 RELEASE，需要改成基于 `(gripper_command, holding, target distance)` 的组合。
3. **`_read_end_effector_pose` 未真实跑过**：Day 3 patch 了代码，但 Day 4 首启时 `MyFranka.get_cur_ee_pos()` 还没接；需要重启 Isaac 才能验证。
4. **`_lift_drop_once` 未真实跑过**：pick 点计算、`control.grasp/move/ungrasp` 在 world-frame 下是否成立，未验证。
5. **侧视图相机未加**：Day 4 计划里的项。
6. **参数化 expert 未做**：Day 4 计划里的项。
7. **alignment / overlap / success threshold 未定义**：Day 4 计划里的项。
8. **`envs/garmentlab_wrapper.py` 是否要**：Day 3 判断冗余，Day 4 未再评估，倾向不建。
9. **`233771e` 未 push GitHub**。
10. **`runs/` 里已有约 3 MB npy 在 Git**：Day 5 生成大量 demonstrations 前重新评估 LFS 或排除。

------

## 10. 明日 Day 4 续开工清单

text

```
1. 读 ClothPrim 源码（纯文本，不启动 Isaac）
   find .../prims/soft/cloth_prim.py
   grep "^    def " <path>

2. 选 A / B / C 中一种修法并 patch
3. 重启 Isaac，重跑 scripts/day4_difficulty_smoke.py
   - 目标：三档 × 5 种子，各生成 1 张 PNG
   - 肉眼确认三档可区分

4. 若三档可区分 → 继续 Day 4：
   - 参数化 expert（Step 7）
   - 定义 success threshold（Step 8）
   - 侧视图相机占位（Step 9）

5. 提交并 push GitHub
```



------

## 11. 一句话交接

Day 4 部分完成：`GarmentLabBackend` 首启通过（160 秒、clean exit、OBS_VEC_DIM 46），修好了 world-frame 读取和 EE 读取，实现并单测了三档 difficulty 协议，提交 WIP `233771e`。三档初态截图因 `ClothPrimView` 从未 `initialize()` 而失败，是上游遗留 bug，明日优先修。代码 450 行 backend + 225 行 difficulty + 新脚本 `day4_difficulty_smoke.py`。未推送项：`233771e`。