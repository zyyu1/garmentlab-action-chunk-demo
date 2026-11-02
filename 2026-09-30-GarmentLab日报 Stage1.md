# GarmentLab 调试日报与交接记录

日期：2026-09-30
状态：今日停止调试，明日继续检查结果下载与折叠效果。

## 1. 今日结论

已打通 Isaac Sim 启动、基础物理仿真、衣服和机械臂场景、相机图像，以及抓取—移动—松手动作序列。

**尚未确认整齐折叠成功。** 衣服从展开变为聚拢，但最终画面中有翘起部分，机械臂遮挡明显。动作脚本执行成功不等于折叠质量合格。

最后的阻塞：本地 `C:/Users/yexun/OneDrive/桌面/fold-action-output/` 内 15 个文件均为 0 字节，无法读取。下载或同步原因未确认；不能据此判断服务器结果丢失。

## 2. 当前可用环境

| 项目 | 值 |
| --- | --- |
| VS Code SSH 别名 | autodl-4090-clone |
| SSH | ssh -p 18117 root@connect.nmb1.seetacloud.com |
| 实例 | autodl-container-d7c2499bc5-fdbdeb71 |
| GPU | RTX 4090，24 GB |
| 驱动 | 560.35.03 |
| nvidia-smi 显示 CUDA | 12.6，表示驱动支持版本 |
| Isaac Sim | 4.0.0 |
| Python | /root/autodl-tmp/envs/isaac40/bin/python |
| 项目 | /root/autodl-tmp/garmentlab_workspace/GarmentLab |
| 模式 | headless=True，仿真需要 GPU 开机 |

此前驱动 595.71.05 的机器启动出现段错误，退出码 139，调用栈位于 RTX/Hydra 相关库。克隆到当前机器后测试通过，支持主机/驱动环境相关的判断，但不是单变量驱动对照实验。

明天继续使用当前环境，不必重新安装。SSH 信息若发生变化，以 AutoDL 控制台为准。今天没有代用户执行关机，也未确认实例已经关机。

## 3. 已处理的问题

### 依赖与启动

- boto3、botocore 对齐到 1.34.68，解决与 Isaac 内置包混用导致的导入错误；当时 pip check 通过。
- 补齐缺失系统库，包括 libGLU.so.1。
- 安装缺少的 imageio 后，场景脚本能导入相机模块并输出图片；最终具体版本待整理。
- 当前机器最小启动测试输出 ISAAC_STARTUP_OK，退出码 0。

### 路径和材质

- Env/env/FoldEnv.py：启用 headless；将 muti_gpu 拼写修正为 multi_gpu；调整原作者路径。
- Env/Config/SceneConfig.py：场景路径改为当前项目下的 Assets/Scene/FlatGrid.usd。
- 测试显式使用真实衣服路径，注意 Garments 为复数、LSleeve 的大小写：

```text
/root/autodl-tmp/garmentlab_workspace/GarmentLab/Assets/Garments/Tops/NoCollar_LSleeve_FrontClose/TNLC_Dress057/TNLC_Dress057_obj.usd
```

- 原默认材质 /home/user/GarmentLab/Assets/Material/linen_Pumpkin.usd 不存在，Assets 下未找到名称包含 linen 的文件。
- 测试设置 visual_material_usd=None，使用 Garment.py 已有分支跳过外部材质覆盖。没有因此修改衣服物理参数。

### 动作控制

- Env/env/Control.py 的 move() 初始化 cur_step 后未递增，导致循环上限可能失效；添加 cur_step += 1。
- ungrasp([False]) 才松手；[True] 保持抓取。新测试三次释放均使用 [False]。
- 动作测试增加 15000 次 world.step() 总上限，以及抓取/移动后的机械臂目标到达检查。此上限不是墙钟超时，不能限制资源加载等待。
- 测试脚本在关闭仿真前打印异常，不能只根据退出码 0 判断通过。

## 4. 测试结果

| 测试 | 证据 | 结论 |
| --- | --- | --- |
| 启动 | ISAAC_STARTUP_OK，退出码 0 | 通过 |
| 方块物理 | PHYSICS_SMOKE_OK；60/120/180 步高度约 0.1000 | 基础物理通过 |
| 衣服场景 | RESET_OK、STEP=120、RGB=(480,640,3)、9945 顶点、FOLD_SCENE_SMOKE_OK | 场景与数据读取通过 |
| 折叠动作 | ACTION_DONE 12_release、FOLD_ACTION_SEQUENCE_OK、退出码 0 | 序列执行完成，约 510 秒 |
| 折叠质量 | 前后图显示明显聚拢，末态不整齐且被遮挡 | 待验收 |

尚未验证多次重复成功率、连续录像、完整训练接口或稳定折叠质量。

## 5. 远程文件交接

以下均在当前克隆实例的 /root/autodl-tmp/ 下：

| 文件或目录 | 用途 |
| --- | --- |
| isaac40-startup-clone.log | 当前机器启动日志 |
| isaac40-cube-smoke.py / .log | 方块物理测试及日志 |
| fold-scene-smoke.py | 衣服场景测试 |
| fold-scene-diagnostic.log | 后续场景诊断日志 |
| fold-scene-output/ | 未执行折叠的场景结果 |
| fold-action-test.py | 有限步数折叠测试 |
| fold-action-test.log | 动作执行日志 |
| fold-action-output/ | 各动作阶段图片与最终顶点 |
| fold-config-backup/ | 早期配置修改备份 |
| isaac-support.tar.gz | 之前的技术支持材料，主要针对旧启动问题 |

Control.py 旁有 Control.py.before-loop-fix 备份；场景脚本有 .before-material、.before-traceback 备份。正式交接时核对实际文件列表。今日修改尚未确认已提交 Git。

### 动作结果目录内容

- 00_before.png：动作前。
- 01_grasp.png～03_move.png：第一次抓取、移动。
- 04_release.png：第一次松手。
- 05_grasp.png～07_move.png：第二次抓取、移动。
- 08_release.png：第二次松手。
- 09_grasp.png～11_move.png：第三次抓取、移动。
- 12_release.png：第三次松手。
- scene.png：全部动作后再稳定 120 步。
- garment_vertices.npy：最终顶点，沿用项目读取方法；未另外确认世界/局部坐标语义。

不要混淆 fold-scene-output/scene.png 和 fold-action-output/scene.png，前者没有执行折叠。

## 6. 未解决事项

1. 本地 15 个文件全部 0 字节：先核对远程大小，再重新下载，不要先重跑仿真。
2. 折叠效果：优先看第 4、8、12 步松手图片，判断偏移或卷曲首次出现在哪一步。
3. 机械臂遮挡：必要时补侧视图或安全移开机械臂，但先分析现有帧。
4. FlatGrid 的部分纹理引用 omniverse://localhost，日志报告缺失；看到网格不代表所有引用已修复。
5. 默认地面 get_assets_root_path/check_server 查询较慢，后续可优化为本地资源流程。
6. NGX、GLFW、关机 USD 引用计数和粒子布料 API 弃用警告仍存在；当前测试通过，不因这些警告直接重装环境。

## 7. 明天从这里继续

### 第一步：检查服务器已有结果

连接当前实例，在远程终端执行：

```bash
ls -lh /root/autodl-tmp/fold-action-output/
grep -E 'ACTION_DONE|FOLD_ACTION_SEQUENCE_OK|Traceback' /root/autodl-tmp/fold-action-test.log | tail -n 20
```

查看和下载已有结果不必启动新的 GPU 仿真。若要重跑仿真，需 GPU 开机。

### 第二步：重新下载并查看阶段图

VS Code 远程资源管理器右键 fold-action-output → Download，保存到新的本地文件夹，例如 Downloads/fold-action-output。确认文件非零后打开。

优先检查：04_release.png、08_release.png、12_release.png。必要时结合对应 grasp/move 图片，定位首次异常阶段。

### 第三步：定位后调整

- 第一轮没带动袖子：检查抓取位置与附件绑定。
- 前两轮正常、末轮变形：重点检查第三轮抓取点与轨迹。
- 主要是视角遮挡：调整观察角度或最终机械臂姿态。
- 一次只改一个关键因素；下一次测试前另存当前结果，避免覆盖唯一证据。

### 第四步：验收和归档

折叠效果确认后，再做重复测试、记录最终依赖版本、检查 Git diff 并整理代码。暂不把“动作序列执行成功”写成“折叠任务成功”。

## 8. 一句话交接

环境已能启动、渲染和仿真，12 个折叠动作执行完成；衣服确实变形但折叠质量未确认。明天先解决本地 0 字节下载结果并查看三次松手图片，无需从安装环境重新开始。
