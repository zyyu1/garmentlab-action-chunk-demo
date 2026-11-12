# GarmentLab 调试日报与交接记录

日期：2026-10-13
状态：Day 2 完成。折叠动作序列跑通、每阶段顶点数据导出、Git 归档、GitHub 推送全部完成。折叠质量尚未验收，无 mp4 视频。

---

## 1. 今日结论

今天在一台**新的 RTX 4080 32 GB 实例**上完成 Day 2：

- Isaac Sim 4.0.0 headless 在新实例上启动通过（`ISAAC_STARTUP_OK`，退出码 0）。
- GarmentLab 原有三处 AutoDL 适配改动仍在，确认无误后提交并打 tag。
- 12 步折叠动作序列（grasp → move → release × 3）执行完成，退出码 0。
- 第三次抓取诊断（D00–D04）执行完成，退出码 0。
- **每个阶段都导出了顶点数据**（`*_vertices.npy`），可离线量化每步对齐误差，不必重跑仿真。
- 折叠效果**未确认整齐**：末态倾斜、一角翘起，主视角被机械臂遮挡约 30–40 %。
- 无 mp4，只有 PNG 序列。Day 2 的 “video is saved” 一项尚未满足，但不阻塞。
- GitHub 仓库 `zyyu1/garmentlab-action-chunk-demo` 已完成首次推送（含合并冲突解决、README 更新）。
- 旧 4090 实例（`autodl-container-d7c2499bc5-fdbdeb71`）在本次新实例上不存在，9/30 的 `fold-action-output/` 未找回，是否已释放未确认。

Day 2 判定：**Go，不切 NVIDIA Warp fallback**。

---

## 2. 当前可用环境

| 项目                 | 值                                                           |
| -------------------- | ------------------------------------------------------------ |
| VS Code SSH 别名     | `ssh:autodl-vGPU-32G-4090clone`（以 AutoDL 控制台为准）      |
| 容器                 | `autodl-container-5d974b909f-0ac9998e`                       |
| GPU                  | RTX 4080，32 GB（注意：与 9/30 的 RTX 4090 24 GB 不是同一台） |
| 驱动                 | 580.105.08                                                   |
| nvidia-smi 显示 CUDA | 13.0（驱动支持版本）                                         |
| Isaac Sim            | 4.0.0.0                                                      |
| Python venv          | `/root/autodl-tmp/envs/isaac40`                              |
| venv 里 `bin/python` | 符号链接 → `/root/miniconda3/bin/python`（正常 venv 行为，非污染） |
| GarmentLab           | `/root/autodl-tmp/garmentlab_workspace/GarmentLab`           |
| 项目收口目录         | `/root/autodl-tmp/garmentlab-action-chunk-demo`              |
| GitHub 仓库          | https://github.com/zyyu1/garmentlab-action-chunk-demo （Private） |
| 模式                 | `headless=True`，需要 GPU 开机                               |

环境验证输出：

```text
which python → /root/autodl-tmp/envs/isaac40/bin/python
isaacsim 4.0.0.0
torch 2.2.2+cu121
numpy 1.26.4
No broken requirements found.
```

---

## 3. 已处理的问题

### 实例迁移与结果文件丢失

- 9/30 的旧 4090 实例已不在当前可见状态，本次全部工作在新 4080 实例完成。
- 旧实例的 `fold-action-output/`、`fold-scene-output/`、`fold-action-test.log` 在新实例上**不存在**，未找回，是否需要回到旧实例取图待确认。
- 本地 OneDrive 下 15 个 0 字节文件的问题本次未重现：改为直接下载到非 OneDrive 目录后，文件大小正常（PNG 约 90 KB，`*_vertices.npy` 约 117 KB，总计 3.2 MB）。

### venv 与仓库清理

- 确认 `envs/isaac40` 和 `isaacsim_env` 里的 `bin/python` 都是指向 miniconda 的符号链接，是正常 venv 行为，不是环境污染。
- 移出 GarmentLab 仓库外的多余目录（未删除，先 relocation）：
  - `isaacsim_env/` 7.2 G → `/root/autodl-tmp/relocated/isaacsim_env_from_garmentlab`
  - `pip_cache/` 3.7 G → `/root/autodl-tmp/relocated/pip_cache_from_garmentlab`
  - `isaacsim_install.log` → `/root/autodl-tmp/relocated/isaacsim_install.log`
- `Control.py.before-loop-fix` 移出 GarmentLab，归档到：
  - `/root/autodl-tmp/garmentlab-action-chunk-demo/third_party/backups/Control.py.before-loop-fix`

### GarmentLab 三处适配改动（确认与提交）

三处改动内容（从旧实例继承，新实例上仍在）：

```diff
# Env/Config/SceneConfig.py
- room_usd_path="/home/user/GarmentLab/Assets/Scene/FlatGrid.usd"
+ room_usd_path="/root/autodl-tmp/garmentlab_workspace/GarmentLab/Assets/Scene/FlatGrid.usd"

# Env/env/Control.py  move() 循环
  cur_step=0
  self.world.step()
  while 1:
+     cur_step += 1
      self.robot_step(pos,ori,flag)

# Env/env/FoldEnv.py
- simulation_app = SimulationApp({"headless": False,"muti_gpu":False})
+ simulation_app = SimulationApp({"headless": True,"multi_gpu":False})
- sys.path.append("/home/user/GarmentLab/")
+ sys.path.append("/root/autodl-tmp/garmentlab_workspace/GarmentLab/")
```

补丁已保存：`third_party/autodl_adaptations.patch`（47 行）。

### Git 归档

GarmentLab 仓库：

```text
base commit : 6ee0620 (grafted, origin/main)
adapt commit: f2988b1  "Autodl adaptation: headless, multi_gpu typo, local paths, Control.step fix"
tag         : autodl-adapt-2026-10-13
```

项目收口目录 `garmentlab-action-chunk-demo`：

```text
e3ca120  (HEAD -> main, origin/main) docs: update README to Day 2 status ...
79ea081  Merge remote-tracking branch 'origin/main'
5f2382f  docs: Day 2 report - fold sequence passed, quality pending
2da2f12  Day2: fold action sequence + third grasp diagnostic on RTX 4080
b68d6df  docs: record initial environment and demo scope
branch   : main
files    : 36 (含 runs/2026-10-13-third-grasp/ 全部 PNG + npy + log)
```

### GitHub 推送

- 仓库：https://github.com/zyyu1/garmentlab-action-chunk-demo （Private）
- 处理了 `.gitignore` 的 add/add 冲突，合并双方内容，加 `!runs/**/*.log` 例外。
- 本地 main 与 origin/main 完全同步。

---

## 4. 测试结果

| 测试           | 证据                                                        | 结论       |
| -------------- | ----------------------------------------------------------- | ---------- |
| 新实例启动     | `ISAAC_STARTUP_OK`，退出码 0                                | 通过       |
| 环境一致性     | `which python`、`pip check`                                 | 通过       |
| 折叠动作序列   | 12 步，`ACTION_DONE`，退出码 0                              | 通过       |
| 第三次抓取诊断 | `D00–D04` 五张图 + npy，`THIRD_GRASP_DIAGNOSTIC_OK`         | 通过       |
| 顶点导出       | 每阶段 `*_vertices.npy` + `garment_vertices.npy`，9945 顶点 | 通过       |
| 折叠质量       | 末态倾斜、翘角、机械臂遮挡 30–40 %                          | **待验收** |
| mp4 视频       | 无 mp4，仅 PNG 序列                                         | **未满足** |
| 重复性         | 仅跑 1 次                                                   | **未测**   |
| GitHub 推送    | `e3ca120` 在 origin/main                                    | 通过       |

运行日志时间：`13:54:20 → 14:00:15`（约 30 分钟，含仿真启动）。当前机器时区未核实，与控制台可能不一致。

---

## 5. 远程文件交接

均在当前 4080 实例：

### 项目仓库

```text
/root/autodl-tmp/garmentlab-action-chunk-demo/
├── .gitignore
├── README.md
├── environment_log.md
├── docs/
│   ├── 2026-10-13_stage2_report.md
│   └── sim2real_assumptions.md
├── scripts/
│   ├── fold-action-test.py
│   └── fold-third-grasp-debug.py
├── runs/2026-10-13-third-grasp/
│   ├── 00_before.png / 00_before_vertices.npy
│   ├── 01_grasp.png  / 01_grasp_vertices.npy
│   ├── 02_move.png   / 02_move_vertices.npy
│   ├── 03_move.png   / 03_move_vertices.npy
│   ├── 04_release.png/ 04_release_vertices.npy
│   ├── 05_grasp.png  / 05_grasp_vertices.npy
│   ├── 06_move.png   / 06_move_vertices.npy
│   ├── 07_move.png   / 07_move_vertices.npy
│   ├── 08_release.png/ 08_release_vertices.npy
│   ├── D00_after_second_release_settled.png / *_vertices.npy
│   ├── D01_approach_without_attachment.png  / *_vertices.npy
│   ├── D02_after_grasp.png                  / *_vertices.npy
│   ├── D03_after_lift.png                   / *_vertices.npy
│   ├── D04_after_release.png                / *_vertices.npy
│   ├── garment_vertices.npy
│   ├── scene.png
│   └── fold-third-grasp-debug.log
└── third_party/
    ├── autodl_adaptations.patch
    └── backups/Control.py.before-loop-fix
```

原始输出目录仍保留在：

```text
/root/autodl-tmp/fold-third-grasp-20261013-214507-737595/
```

### 移出暂存

```text
/root/autodl-tmp/relocated/
├── isaacsim_env_from_garmentlab/      7.2 G（早期误建 venv，未被引用）
├── pip_cache_from_garmentlab/         3.7 G（pip 缓存）
└── isaacsim_install.log
```

以上三项确认无引用后可删除。

---

## 6. 未解决事项

1. **折叠质量未确认**：末态倾斜、一角翘起；不确定是抓取点、轨迹还是释放高度问题。
2. **机械臂遮挡**：主视角约 30–40 % 被挡，无法判定袖子/领口对齐；需要加侧视图或调整机械臂终态。
3. **无 mp4**：只有 PNG 序列；需确认 `Recording_Camera` 是否启用，或用 `ffmpeg` 拼接。
4. **未测重复性**：只跑 1 次，Day 4 前不做重复，避免浪费时间。
5. **旧 4090 实例状态未知**：9/30 的 `fold-action-output/` 未找回；先不追，除非确认要作对照。
6. **FlatGrid 部分纹理引用 `omniverse://localhost`**：日志报告缺失；当前测试通过，先不动。
7. **GLFW / USD 引用计数 / NGX 警告**：headless 下正常噪声，忽略。
8. **硬编码路径**：`FoldEnv.py`、`SceneConfig.py` 里仍是 `/root/autodl-tmp/...`，Day 3 写 `GarmentLabBackend` 时统一配置化。
9. **`runs/` 里的 npy 已进 Git**：当前规模可接受，Day 5 生成大量 demonstrations 时需重新评估是否切换为 Git LFS 或排除。
10. **GitHub 仓库为 Private**：Day 9 做视频和 mini report 时再决定是否公开给 Marian。

---

## 7. 明天从这里继续（Day 3）

### Day 3 目标

把临时脚本收敨成正式接口，并加侧视图相机。

### 要交付的文件

```text
backends/base.py                 RobotBackend 抽象类
backends/garmentlab_backend.py   封装 GarmentLab
backends/mock_backend.py         不依赖 Isaac 的假后端
schemas/observation.py           冻结观测字段
schemas/action.py                冻结动作字段
envs/garmentlab_wrapper.py       reset(seed, difficulty) / step / record
envs/difficulty.py               三档初态占位（Day 4 实现）
```

### 原则

- policy 不直接调用 Isaac Sim API，不输出关节命令。
- observation / action schema 冻结后不再改。
- `mock_backend` 保证无 GPU 时也能跑单测。
- 侧视图相机先占位，Day 4 用来判定对齐和翘角。

### Day 3 开工时先做的事

```bash
cd /root/autodl-tmp/garmentlab-action-chunk-demo
git log --oneline -5
git status --short

cd /root/autodl-tmp/garmentlab_workspace/GarmentLab
git log --oneline -3
git tag
```

确认以下全部都在：

```text
garmentlab-action-chunk-demo  : e3ca120 / 79ea081 / 5f2382f / 2da2f12 / b68d6df
GarmentLab                    : f2988b1 + tag autodl-adapt-2026-10-13 / 6ee0620
工作区两个仓库均干净
```

---

## 8. 一句话交接

新 4080 实例上折叠动作序列 + 第三次抓取诊断全部跑通，退出码 0，每阶段顶点数据完整导出；GarmentLab 适配改动已提交（`f2988b1` + tag `autodl-adapt-2026-10-13`），项目仓库已推送 GitHub（`e3ca120`，含 merge commit 和更新后的 README）。折叠质量未验收（倾斜、翘角、遮挡），无 mp4。Day 2 Go，不切 Warp。明天 Day 3 直接开始写 `GarmentLabBackend` 和统一 schema，不重跑仿真。