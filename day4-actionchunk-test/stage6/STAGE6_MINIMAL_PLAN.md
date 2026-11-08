# Stage 6 最小 single-step BC 闭环：入口、离线核对与阻塞

日期：2026-11-08。复用 Stage 5 缩减版 single checkpoint，不重训、不追加采集、暂不跑 H4。

## 1. 已完成（离线）

| 项 | 状态 |
|---|---|
| 上一轮账本/指标口径收尾 | 完成（见 `results/STAGE5_REDUCED_50_10_10/README.md`） |
| `training/bc_policy.py` | 加载 `best.pt` + train-only `stats.json`；构造 1340 维观测（vertices→ee→quat(wxyz)→joints→holding）；反归一化 XYZ/yaw；夹爪三分类映射回命令 0/1/2 |
| `training/check_policy.py` | 用真实 episode 的 `action_001_obs.npz/.json` 验证：obs 1340、有限值、输出单位合理（xyz 米、yaw 弧度）、夹爪类 0 与真值一致 |
| checkpoint 重载 | 通过（`best.pt` state_dict 与 `BCNet(1340,512,'single')` 匹配） |

## 2. 阻塞：现有评价器与 BC 协议不兼容

`a5_entry.assess()`（Stage 4/5 判决器）硬性要求专家协议：

- `expected = spec['actions']`（L1=7 个公开动作），并要求动作数、horizon、`release_retreat` 末动作、331 步 success trace、hold_3s/hold_4s 双保持、terminal 顶点一致等。
- BC 策略逐步执行任意数量/任意位姿动作，**无法满足**这些身份与证据字段；直接调用只会得到 `status=incomplete`。

因此“直接跑 BC episode 并用原评价器打分”不可行，需要为 Stage 6 单独定义成功判据。

## 3. 建议的最小成功判据（待确认后执行）

沿用同一几何量、同一阈值，只替换“动作来源”：

1. 每个 episode 结束后，在最终位姿保持若干步，采集终态顶点（441×3）。
2. 用 Stage 5 的 `fold_metrics_yaw` 计算折痕指标（与专家评价使用同一函数与阈值，阈值不改）。
3. 成功 = 几何指标通过 + 机器人释放后布面保持（hold 窗口内位移阈值，沿用既有 `stage4_success_v1` 阈值）。
4. learned 与 random 基线使用**完全相同的初态、动作预算、Backend、评价器与阈值**。

## 4. 调试清单（草案，不按结果挑选）

- 初态：L1/L2/L3 各 5 个，排除 train 45 与 test 13（即从 val 12 与未用于演示的合规初态中取；L2 val=0，需从未用 seed 的合规初态补足）。
- 优先复用已有、`passed=true`、协议校验通过的初态目录；不替换 seed。
- L1 random 基线：动作在 learned 策略输出的经验范围内均匀采样（XYZ 每轴 ±0.05 m、yaw ±0.2 rad），夹爪命令按 0/1/2 等概率，固定随机种子（如 0），与 learned 同初态、同预算。
- 动作预算：统一 15 个公开动作（learned/random 相同），逐例记录实际执行数与终止原因。

## 5. 下一步（需放行）

- 确认成功判据（第 3 节）或指定其它判据；
- 定稿 15 个调试初态与随机基线参数；
- 实现 `a5_bc_single.py`（复用 a5_l1 的环境初始化/材质/证据，替换动作来源为 `bc_policy`），先跑 1 例 L1 验证接口，再跑满 15 learned + 5 random；
- 保存逐例结果/视频/动作/失败原因，报告分档成功数与 L1 learned vs random。区分“入口跑通”与“Stage 6 验收通过”。

## 2026-11-08 修订进展（评价适配层）

- 新增 `bc_eval_adapter.py`：不改 `a5_entry`/`stage4_success_v1`，把 `evaluate()` 结果拆为 physics（held / released_continuously / geometry_entire_window / stable）与 protocol（definition / budget / no_runtime_error）。
- 离线一致性：用 6114 已保存的 `success_meta.json` + `success_trace.npz` 运行适配层，结果为 physics_ok=true、四项物理检查全 true，与原 accepted 判定一致（`check_adapter.py`）。
- 未完成：`a5_bc_single.py` rollout runner（环境初始化复制、策略逐步执行、OPEN 后 331 帧评价窗口记录）尚未实现；20 例（15 learned + 5 random）尚未运行。
