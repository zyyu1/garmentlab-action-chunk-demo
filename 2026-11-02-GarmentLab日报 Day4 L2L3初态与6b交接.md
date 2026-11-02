# 2026-11-02 Day4：L2/L3 初态完成，6b recovery 起始交接

## 一句话状态

- 第 1–5 步已完成：L1 x 向半折两次开发运行通过；正式 Backend 的 yaw/抓取/保持/重抓取/reset 10 循环通过。
- **第 6a 步完成**：L1/L2/L3 各 10 张、共 30 张初态图全部 `passed=true`；三档初态肉眼可区分（L1 平铺、L2 宽短折带、L3 窄高半折）。
- **第 6b 步刚开始**：5 动作 recovery 冒烟脚本已写好、**尚未运行**；7 动作折叠压缩尚未实现。当前折叠 9 + recovery 5 = 14 > 12，必须把折叠压到 7。
- 正式 Day4 成功仍为 **0**。

## 环境与连接

| 项 | 值 |
|---|---|
| 远端实例 | `ssh -p 23636 root@connect.nmb2.seetacloud.com`（2026-11-02 新克隆实例；旧 nmb1:22895 不要再用） |
| 容器 | `autodl-container-ac0a41b2f7-bc28942d` |
| 工作目录 | `/root/autodl-tmp` |
| Python | `/root/autodl-tmp/envs/isaac40/bin/python` |
| 项目仓库 | `/root/autodl-tmp/garmentlab-action-chunk-demo` |
| 本地仓库 | `E:\learning\project\garmentlab-action-chunk-demo` |

工作方式：助手改本地文件 → 用户用 PowerShell `scp -P 23636 ...` 上传 → 用户在远端 VS Code bash 运行 → 用户下载结果 → 助手离线审查。助手不直接在远端执行 GPU 实验。所有清单哈希按 **LF** 字节计算；上传后用预检核对。

## 已排除的路线（不要再走）

1. **lift → 原高度释放**：`particle_friction_scale=0`，布料自摩擦为零，任何 lift/release 产生的褶皱都会松弛；L2 4200 与 L3 4300 最终 z extent ≈6e-8，完全平铺。
2. **原始动态附件 `Control`**：其 `move`/`grasp` 在 3 cm `reach` 容差处停止，grasp 悬在角点上方约 2.9 cm，2 cm 动态附件没覆盖到布；`cycle_00_settled` 与 `flat_settled` 差 3.7e-8 m，布料完全没动。v1 动态版的“通过”都是空动作。
3. **角点折角（dog-ear）**：持布时折角存在（`after_lower` 形变残差约 150 mm），但 release 瞬间整体弹平（`after_release` 刚性拟合残差 0.04 mm，整块布刚性旋转）。小三角折角不是稳定平衡。
4. **窄布条**：left 0.11、left 0.165 在 release 后完全展开；bottom 0.11 也失败。bottom 的稳定阈值在 0.162–0.169 之间；left 需要接近半折的 0.20。bottom 的折叠方向与夹爪手指开合方向一致，比 left 更稳。
5. **L3 用 top 边做第二折**：top 边靠近机器人基座，固定下指姿态在 z≈0.013 处不可达（4301 IK 无解）；钳制 dy 只能部分缓解。最终放弃 top，L3 改为左半折。

## 关键实现：prepared 控制的持布阶段放宽

prepared 单点锚点是唯一被证明能抓住布的路径（grasp EE 0.83 mm、块 ≤1.31 mm、锚点 ≤1.4 mm、角点实际抬起 7.8 cm）。但折叠适配器的严格 `_drive`（EE<10 mm + 连续 6 步 + 末臂速<0.1）在布料负载下会在近边/高抬升超时。

`strip_prepared_control.py` 与 `corner_prepared_control.py` 采用同一策略：

- `follow=False`（抓取前 approach/descend）：保持 **10 mm** 严格门限，确保夹爪到布；
- `follow=True`（持布 lift/arc/place）：EE 放宽到公共契约 **3 cm**，块 <5 mm、旋转 <0.03、单点锚点 <10 mm 不变；
- 首次 grasp 之后（`slot.used=True`）的 release 跟随 / retreat / home 也走放宽路径；
- 正式 L1 折叠控制（`square_probe_control.py` 等）**未修改**，哈希不变。

## 6a 最终配置与结果

**plan**：`square-initial-plan.json`，`version=square-initial-v3`，hash `e2cfaebe597e52b5…`；**yaml**：`square-difficulty.yaml`，hash `a42fec8a1069ad43…`。

| 档位 | 初态 | 参数 | 最终形状（典型） |
|---|---|---|---|
| L1 | 平整方巾 | 仅平移/旋转（4100–4109） | 0.4×0.4，z 平 |
| L2 | 一条 **bottom** 折条 | width 0.16–0.18（4200 = 0.174179） | 约 0.42×0.25，z 约 0.06，宽短折带 |
| L3 | 一条 **left 半折** | width 0.20（4300 = 0.20） | 约 0.25×0.43，z 约 0.06，窄高折半 |

L3 的 yaml 已改为 `num_lift_drops: 1`、`max_recovery_moves: 1`；L3 的平移恢复原始采样值（不再需要 top 边的 dy 钳制）。

**30 张图的运行目录**：

- L1（`day4-square-initial-20261031-*`）：
  `094446-203825, 095254-316552, 095611-471489, 095925-799656, 100246-659222, 100558-317616, 100909-165817, 101224-181183, 101541-103282, 101853-191858`
- L2（`day4-square-initial-stripfold-20261102-*`）：
  `4200 023311-548690, 4201 031859-758705, 4202 032804-246519, 4203 033648-809964, 4204 034544-830190, 4205 035436-003676, 4206 040355-509776, 4207 041256-658874, 4208 042215-851125, 4209 043151-454479`
- L3：
  `4300 074349-406408, 4301 075606-421583, 4302 080548-693912, 4303 082753-692325, 4304 083848-796253, 4305 084918-410795, 4306 090016-424984, 4307 091001-304307, 4308 092049-522618, 4309 093018-418187`

30 张对比图（本地）：`day4-actionchunk-test/results/initial30_sheet_v2.png`。每张初态目录含 `initial.png`、`initial_geometry.npz`（`before/applied/flat_settled/final`）、`strip_XX_*.npz`、`result.json`。

**典型结果**：

- L2 4200：bottom crossed 1.0、pick 内移 0.348 m、extent `0.4215×0.2495`、z extent `0.0593`。
- L3 4300：left crossed 1.0、pick 内移 0.382 m、extent `0.2483×0.4263`、z extent `0.0597`。
- L3 4303 的 home 曾因近基座姿态超时；已把 home 改为非致命，失败记录 `home_skipped`，不影响初态。

## 6b 现状（暂停点）

### 已实现、未运行：5 动作 recovery 冒烟

- 脚本：`day4-strip-recovery-smoke.py`（hash `68781cf2316ed103…`）
- 运行脚本：`run-strip-recovery-smoke.sh`（hash `57bdfd6848d185a0…`）
- 清单：`square-strip-recovery-files.json`（20 项，LF）
- 输入：一个初态运行目录。读取 `result.json` 的 `initial_case.strips`、`strip_records[].pick_index/pick_world`（折叠前的 pick 世界坐标），以及 `initial_geometry.npz` 的 `flat_settled/final`。
- 场景：正常构造方巾和 prepared 边槽位，然后把布料世界坐标设为初态的 `final`（折叠态），settle 30。
- 动作（5 个）：approach（折叠后 pick 上方 12 cm）→ pick（CLOSE，到折叠后 pick）→ lift（+8 cm）→ spread_place（折叠前 pick +3 cm）→ release。
- 输出：`recovered.npz`、`recovered.png`、`result.json` 里的 `recovery_metrics`（刚性残差 vs flat、pick 位移、extent、z_p95、action_count）。

**尚未运行。** 两个冒烟命令：

```bash
bash /root/autodl-tmp/run-strip-recovery-smoke.sh /root/autodl-tmp/day4-square-initial-stripfold-20261102-023311-548690   # L2 4200
bash /root/autodl-tmp/run-strip-recovery-smoke.sh /root/autodl-tmp/day4-square-initial-stripfold-20261102-074349-406408   # L3 4300
```

未上传文件：`day4-strip-recovery-smoke.py`、`run-strip-recovery-smoke.sh`、`square-strip-recovery-files.json`。

### 尚未实现：7 动作折叠压缩

当前 L1 x-fold 是 9 个动作（approach → descend → close → arc45 → arc90 → arc135 → place → release → retreat）。要满足 7+5=12，需要压到 7 个动作。建议方案：

1. approach + descend 合并为一个 grasp 动作（从 home 直接到抓取点）；
2. 去掉 retreat（release 后直接 settle，episode 结束）；
3. 保留 close / arc45 / arc90 / arc135 / place / release。

即：**grasp → close → arc45 → arc90 → arc135 → place → release = 7**。

必须重新跑一次完整 L1 折叠验证，确认路径不退化、折叠 IoU/对齐/保持指标与 9 动作版（`062602-150760`）相当，再用于 recovery+fold 组合。

### 预算与组合

- recovery 5 + fold 7 = 12（L2/L3 各一次 recovery；L1 无 recovery）。
- L3 的 recovery 展开的是左半折，随后 fold 再次折左半——同一方向的“展开再折”，需要确认 recovery 后的抓取点/折线与 fold 的 left slot 兼容。
- L2 的 recovery 展开 bottom 折条，fold 折左半；两者正交，兼容性较好。

## 文件与哈希（当前有效）

| 文件 | 哈希（LF） |
|---|---|
| `square-initial-plan.json`（v3） | `e2cfaebe597e52b5…` |
| `square-difficulty.yaml` | `a42fec8a1069ad43…` |
| `day4-square-initial-stripfold.py` | `178ab10c08511b6d…` |
| `strip_prepared_control.py` | `49075fb4bf90d08e…` |
| `run-square-initial-stripfold.sh` | `33a4e142ca81e0d7…` |
| `square-initial-stripfold-files.json` | 23 项，见文件 |
| `day4-strip-recovery-smoke.py` | `68781cf2316ed103…` |
| `run-strip-recovery-smoke.sh` | `57bdfd6848d185a0…` |
| `square-strip-recovery-files.json` | 20 项，见文件 |

共享 prepared 依赖（`multi_prepared_grasp_control.py`、`square_probe_control.py`、`single_anchor_hem_control.py`、`hem_prepared_grasp_control.py`、`hem_fold_geometry.py`、`multi_grasp_geometry.py`、`square_contact_reporting.py`、`square_proxy_ground_control.py`、`square_stable_hold.py` 等）沿用服务器已验证哈希，本轮未修改。

## 上传/下载命令

```powershell
# recovery 冒烟（3 个文件）
scp -P 23636 "<本地>\day4-actionchunk-test\day4-strip-recovery-smoke.py" "<本地>\day4-actionchunk-test\run-strip-recovery-smoke.sh" "<本地>\day4-actionchunk-test\square-strip-recovery-files.json" root@connect.nmb2.seetacloud.com:/root/autodl-tmp/

# 下载某个结果目录
scp -P 23636 -r root@connect.nmb2.seetacloud.com:/root/autodl-tmp/day4-strip-recovery-<时间戳> "<本地>\day4-actionchunk-test\results\"
```

## 下一步顺序

1. 上传 recovery 3 文件，跑 L2 4200 与 L3 4300 两个 recovery 冒烟。
2. 检查 `recovery_metrics`：刚性残差 vs flat、pick 位移、extent 是否回到平铺量级；检查 `recovered.png`。若 5 动作展不平，先调 spread 目标高度/抬升高度/settle（不增加动作数）。
3. 实现 7 动作折叠 runner（合并 approach+descend、去 retreat），在 L1 上重新验证折叠指标。
4. 组合 initial_state → recovery(5) → fold(7)，在 L1/L2/L3 上各跑一遍，统计动作数并验证三档可完成折叠。
5. 进入第 7 步正式批次（每档 ≥5 成功、失败/拒绝率、10 次 reset、接口/视频/30 图/验收表）。

## 参考文档

- `day4-actionchunk-test/SQUARE_INITIAL_STRIPFOLD_V1.md`：6a 的完整演进（角点折、动态空动作、条宽阈值、bottom/left 选择）。
- `day4-actionchunk-test/SQUARE_INITIAL_LIFTDROP_V1.md`：v1/v2/v3 的失败证据。
- `day4-actionchunk-test/SQUARE_L1_XFOLD_V1.md`：9 动作 L1 折叠（062602/065314）。
- `day4-actionchunk-test/SQUARE_BACKEND_RESET_V1.md`：第 5 步 Backend/reset 10 循环。
- `DAY4_NEXT_STEPS.md`：当前收尾计划。
