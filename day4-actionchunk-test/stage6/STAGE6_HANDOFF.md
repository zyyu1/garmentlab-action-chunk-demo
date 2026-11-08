# Stage 6 交接（L1/L2/L3 最低开发评估后）

状态：**Stage 6 最低开发验收完成**（最低开发评估已执行；成功验收未达成）：
learned 2/15 accepted（L1 2/5、L2 0/5、L3 0/5），L1 random 0/5。
本轮未重训 single、未追加采集、未扫描参数、未自动 rollout；H4 仅完成一次
离线固定训练（无 rollout）；旧 dataset/stats/checkpoint 全部保留。

L2/L3 均无完整 331 帧窗口；L2 4211 到达 12 动作/terminal 但 held check 失败。
L2/L3 缩减数据属探索性结果，不是独立 test。4210–4214、4310–4312 曾用于 Stage 4，
未用于 Stage 5 模型训练，不称全新 held-out。详见
[STAGE6_L1_DEV_RESULT.md](STAGE6_L1_DEV_RESULT.md)、
[STAGE6_L2L3_DEV_RESULT.md](STAGE6_L2L3_DEV_RESULT.md)。

Stage 7 离线 H4 已完成：160/590/50 数据核对、10 条小样本拟合通过、500 epochs
best_val epoch 389（val total `0.004146`，`ff8c6945…`）；H4 rollout 未启动。
详见 [STAGE7_H4_OFFLINE.md](STAGE7_H4_OFFLINE.md)。

## 1. 当前文件

| 文件 | 说明 |
|---|---|
| `stage6/step_hook.py` | 只读 `world.step` 包装；每次恰好调用一次，透传 args/kwargs/返回值/异常；step 后记录时间、holding、附件、夹爪、EE、441 顶点 |
| `stage6/a5_bc_single.py` | single-step BC 入口；复用冻结初始化/材料/Backend；逐步 observe→predict→execute；终端按实际 holding/attachment 转换；原 331 帧记录；适配层与失败证据 |
| `stage6/check_stage6_offline.py` | 桩测试 step hook、真实数据+假 torch 模型 I/O、真实 trace 适配层、L1/L2/L3 终端/预算、重复 CLOSE、异常保留 obs、终端 OPEN 不改模型目标、runner 语法 |
| `stage6/check_6120_real.py` | 服务器真实 torch 前向 + 6120 初态/材料/哈希核验 |
| `stage6/compare_6120_observations.py` | 专家 action_002 观测 vs 闭环 partial 观测的真实 torch 对照 |
| `stage6/diagnose_6120_data.py` | holding/标签/字段顺序/归一化/CLOSE 拟合诊断 |
| `stage6/recover_holding.py` | 从 timeline state/action_end 恢复历史 pre-action holding；生成修订数据/stats |
| `stage6/eval_holdingfix.py` | holdingfix single 的输入一致性、全动作/CLOSE 指标、6120 离线预测 |
| `stage6/run_6120_single.sh` | 首例一次性运行脚本；独立 attempt 记录；无自动重试 |
| `stage6/STAGE6_6120_SINGLE_RESULT.md` | 首例实际结果与证据缺口 |
| `stage6/STAGE6_6120_CLOSE_DIAGNOSIS.md` | 6120 CLOSE 误差离线定位 |
| `stage6/STAGE6_TERMINAL_CRITERIA.md` | 终端退让判据源码依据与修改前后 |
| `stage6/STAGE6_RUN_IDENTITY.json` | 首例/修订/terminal 代码身份单独登记 |
| `stage6/STAGE6_HOLDINGFIX_REPORT.md` | holding 修复、重训与离线指标报告 |

当前 sha256：
`step_hook.py` `50aca476…`；`a5_bc_single.py` `562386ee…`；
`check_stage6_offline.py` `0b0ba77d…`；`check_6120_real.py` `d728f835…`；
`compare_6120_observations.py` `a3d2600b…`；`diagnose_6120_data.py` `a392c338…`；
`recover_holding.py` `36a3e8aa…`；`eval_holdingfix.py` `d053d030…`；
`run_6120_single.sh` `e052c3d0…`。

数据/模型：
new dataset `1ed533e8…`、new stats `cbc4d711…`、new single checkpoint
`ce7ee2aa…`；old dataset `ae263a6a…`、old stats `8f1788d1…`、old checkpoint
`5bff9e67…` 保留。

首例实际运行 `a5_bc_single.py` `ae024ea4…`；首例后证据修订 `22b8dc50…`；
终端判据修订 `562386ee…`。证据 source 哈希为 `ae024ea4…`；修订代码未重跑。

## 2. 关键行为（当前实现）

- **不覆盖模型目标**：终端 OPEN 使用 BCPolicy 同次输出的 xyz/yaw/gripper 原值执行；
  不添加 `+0.15 m` 退让、不替换 yaw、不补专家释放动作。原始 Backend OPEN 语义
  （holding 时先 ungrasp，再移动到 policy target）保留，并在 `result.actions`
  中记录 `target_override=false`、`model_target_preserved=true`。
- **终端释放判据**：终端执行后核验实际 detached/open 状态、实际 EE 上升
  `>= 1 cm`、held/fold/reference、331 帧和原 clock。`target == released EE +
  [0,0,0.15]` 只作为 `expert_target_consistency` 记录，**不作为 BC 成功门槛**；
  依据见 [STAGE6_TERMINAL_CRITERIA.md](STAGE6_TERMINAL_CRITERIA.md)。
- **终端状态按实际转换**：`grasp_events` 只在 not-engaged→engaged 时递增；
  重复 CLOSE while engaged 只记 `bc_repeated_close`，不新增抓取；
  initial/idle OPEN、未持布 OPEN 不新增 release；终端 OPEN 要求
  `before.engaged=true` 且实际 grasp 次数达到 L1=1 / L2/L3=2。
- **331 帧**：`_record_release_window` 复刻原 `a5_capture.release_window` 的
  0..330 循环、60 Hz 时钟、`success_trace.npz` 字段、hold_3s/hold_4s 样本；
  不包含额外 release 动作，不覆盖 target。
- **成功判定**：适配层 physics accepted + terminal_ok + 331 trace + 原 clock +
  evidence audit + step hook 计数 + no expert labels + budget + no runtime error。
  缺任一条件只判 incomplete/execution_error/rejected，不判 success。

## 3. 首例结果摘要

- seed 6120，flat/val，single；预算 7，执行 1 个公共动作。
- action 0：BC OPEN，target `[-0.18011859, -0.43757146, 0.16165883]`，
  yaw `0.07461045`，原样执行，`target_override=false`。
- action 1：BC CLOSE，target `[-0.13202764, -0.44208298, 0.03761742]`，
  yaw `0.11356681`，被固定 Backend `choose_unused_region` 拒绝：
  `CLOSE target is outside unused prepared regions`。
- 无抓取、无终端、无 release_clock、无 331 帧；`bc-verdict.status=execution_error`，
  `success=false`，不是几何 rejected。
- step_hook 358 records / 358 calls；evidence 181 frames；基础 evidence checks
  除 retention 外全部 true；retention 缺失是因为没有 terminal。
- 分类：入口正常 + **BC 策略输出不可执行**；首例另有 obs_rows/partial_trace/
  DOWNLOAD_DIR 证据缺口，已在当前代码修复但按“仅运行一次”未重跑。
- 首例结果目录：
  `/root/autodl-tmp/stage6_runs/results/day4-a5-bc-single-20261109-015433-798440`
  attempt：
  `/root/autodl-tmp/stage6_runs/attempts/6120-single-20261108-175431`
  本地下载：`E:\learning\project\stage6_6120_single_20261108\`。

## 4. 真实 torch 检查

- `envs/isaac40/bin/python`：Python 3.10.8，torch 2.2.2+cu121，CUDA available=true。
- 6120 `action_001_obs.npz` → obs `(1340,)`、finite、holding=false；
  输出 xyz/yaw/gripper=0 全部有限，夹爪映射合法。
- checkpoint/stats 哈希：`5bff9e67…` / `8f1788d1…`；与训练产物一致。
- 这是真实 torch 前向；本地假 torch 测试只用于 I/O 回归，不冒充真实模型验证。

## 5. 首例后修复（未重跑）

1. `main` 把 `obs_rows` 列表传入 `_run_policy`；动作异常时仍保存
   `bc_observations.npz`（首例缺失）。
2. `main` 在终端前失败且无 trace 时保存一帧 `partial_trace.npz` 和原因
   （首例缺失）。
3. `RESULT_FILE`/`DOWNLOAD_DIR`/`BC_VERDICT` 在 `SimulationApp.close()` 前打印；
   `run_6120_single.sh` 支持按时间戳回退找 result dir，并记录
   `process_exit_code` 与 `effective_exit_code`。
4. 首例 attempt 的 `finished.json` 已按已知 result dir/verdict 重建，原文件保留为
   `finished.original.json`；标注 `record_repaired_after_run=true`。
5. 派生复核放在 result 的 `posthoc_review/`：预测来自 runner.log，
   failure snapshot 来自 StepHook 最后一帧，均明确标注 posthoc。

## 6. 离线检查（当前代码）

```bash
python -B -c "compile(...)"          # SYNTAX_OK
python -m pyflakes step_hook.py a5_bc_single.py check_stage6_offline.py
# exit 0

python -B check_stage6_offline.py
# STEP_HOOK_* / MODEL_IO_OK / ADAPTER_OK
# POLICY_LOOP_L1_OK / L2L3_OK / REPEATED_CLOSE_OK / NO_TERMINAL_OK
# POLICY_LOOP_EXCEPTION_KEEPS_OBS_OK rows=2
# TERMINAL_OPEN_TARGET_PRESERVED_OK target=[0.2, 0.3, 0.4] yaw=0.500
# RUNNER_SYNTAX_OK / ALL_CHECKS_OK
```

服务器 `envs/isaac40/bin/python -m py_compile a5_bc_single.py step_hook.py
check_stage6_offline.py check_6120_real.py` → `REMOTE_PY_COMPILE_OK`。

## 7. 离线定位结论（本轮新增）

1. **专家观测也错**：专家 action_002 观测的真实 torch 预测 XYZ 误差
   `0.063810 m`，到 left_210 prepared region `0.065246 m`；闭环观测实际预测
   误差 `0.063245 m`，距离 `0.064629 m`。两者几乎相同，**不是闭环漂移**。
2. **CLOSE 在训练集上就欠拟合**：训练集 59 个 CLOSE 样本 mean XYZ L2
   `0.100732 m`、median `0.085605`、p95 `0.224614`；val/test 也 11–13 cm。
   6120 的 6.38 cm 甚至低于 train 均值；不是 6120 单例异常。
3. **holding 通道恒零（Stage 5 观测管线缺陷）**：全部 590 条演示
   `obs_holding=0.0`；6120 的 7 个 saved JSON 全部 `holding:false`。
   `stage5_collect/trial/sitecustomize.py` 第 107-110 行从 `action_begin` 的
   `row.get('holding')` 取值，而 `episode_evidence.py` 第 113-120 行的
   `action_begin` 不携带 holding，所以永远 false。stats 的 holding std=1e-6；
   推理时 holding=1 会归一化成 `1e6`，post-grasp 输入不可用。
4. **标签/字段顺序/归一化未发现错误**：6120 的 7 条 dataset action 与 saved
   JSON 全一致；dataset obs 与 saved obs 最大差 0.0；`build_obs` 与
   `obs_matrix` 各段 allclose，最大差 `2.95e-8`（float32/float64 cast）；
   6120 action_002 z-score max |z|：vertices 1.00、EE 1.35、quat 0.37、
   joints 1.50、holding 0。
5. **B 完整 1340 输入不可恢复**：`bc_observations.npz` 缺失；StepHook 没有
   joints；没有用专家 joints 补、没有追加仿真。B 的预测直接取首例真实
   `runner.log` 输出；A vs B 的 vertices 几乎相同（mean 7.5e-11 m），EE 差
   1.44 cm，quat 差 0.016 rad，holding 都 false。
6. **终端判据**：已把 `target == released EE+[0,0,0.15]` 从 BC 成功门槛改为
   `expert_target_consistency` 登记字段；保留实际 upward>=1cm、detach/open、
   held、331 帧、geometry/stability。源码依据见
   [STAGE6_TERMINAL_CRITERIA.md](STAGE6_TERMINAL_CRITERIA.md)。

## 8. holdingfix 数据与 single 重训（本轮新增）

- 历史 holding 恢复：**590/590 actions，70/70 episodes**；primary source
  `state` 160、`action_end` 430；旧 saved JSON holding 全部只记录、未使用。
- 新数据版本：`/root/autodl-tmp/stage5-trial/holdingfix-20261108/`。
  - new dataset `1ed533e8…`；new stats `cbc4d711…`；
  - new single checkpoint `ce7ee2aa…`；
  - 原 dataset `ae263a6a…`、原 stats `8f1788d1…`、原 checkpoint `5bff9e67…`
    全部保留。
- 归一化：holding identity（index 1339, mean=0, scale=1）；其余 stats 仅 train。
- 固定配置重训一次：best_val `0.3119828`，93 epochs；test 坐标 MAE
  `0.0279849 m`、欧氏 MAE `0.0622569 m`、yaw `0.0250672`、grip acc
  `0.954955`、cont MSE `0.174457`、grip CE `0.190877`。
- CLOSE 欧氏 mean/median/P95：
  train `0.088439/0.073023/0.209502`；
  val `0.126007/0.123480/0.257072`；
  test `0.098268/0.061304/0.252527`。
- 6120 新预测 `[-0.151346, -0.447819, 0.024252]`、yaw `0.116103`、grip 1；
  XYZ L2 `0.040207 m`，left_210 距离 `0.041263 m` > 0.03，**仍不启动 rollout**。
- 未来采集修复：`sitecustomize._snap` 从 `evidence.state()` 读取 holding，
  缺失/非 bool 抛错；`build_dataset.holding_for` 要求 bool；
  `app/sitecustomize.py` 原文件备份为 `.original-20261108`。
- 报告：[STAGE6_HOLDINGFIX_REPORT.md](STAGE6_HOLDINGFIX_REPORT.md)。

### 8.1 train-only 拟合诊断（本轮新增）

- train 分组表与 10 条 flat train 小样本拟合已完成；
  小样本 500 epochs 最终 CLOSE 欧氏 `0.000665 m`、夹爪 acc 1.0，
  说明同一实现可以记忆这 10 条轨迹。
- 全 train 的 CLOSE 误差集中在 **L2 fold 0.1533 m、L3 fold 0.1368 m**；
  L2/L3 recovery 分别为 0.0437/0.0642 m；L3 fold 有 1 个夹爪误判为 OPEN。
- 详细表与产物：[STAGE6_TRAIN_DIAGNOSTICS.md](STAGE6_TRAIN_DIAGNOSTICS.md)。

### 8.2 全量 500-epoch 预算对照（本轮新增）

- 固定数据/stats/架构/loss/优化器/seed，仅把预算从正式 early-stop 改为
  500 epochs 无早停；实际 **2000 optimizer updates**。
- best_val（epoch 498）val total `0.024021`、train 全动作欧氏 `0.016405`；
  last（epoch 500）val `0.025453`、train 欧氏 `0.017708`。
- 相对 epoch 100 和正式 100-epoch/early-stop，train/val 同时明显改善；
  支持训练预算不足是贡献因素，保留 `best_val.pt` 为候选。
- 但 best_val 的 fold CLOSE 仍 `0.0357 m`，train 未到零；test 未评估，
  不自动 rollout。产物：
  `holdingfix-20261108/diagnostics/budget500/`（best_val.pt hash `ade60131…`，
  last.pt hash `81e98dd9…`）。
- 报告：[STAGE6_BUDGET500_REPORT.md](STAGE6_BUDGET500_REPORT.md)。

### 8.3 L1 开发复验（budget500 best_val，本轮新增）

- 同一 6120 初态、同一 runner；checkpoint `best_val.pt` epoch 498
  （`ade60131…`），stats `cbc4d711…`。
- 2 次预测、1 个动作执行；第二次 CLOSE 在 prepared-region 校验抛出
  `CLOSE target is outside unused prepared regions`。
- CLOSE target `[-0.229933, -0.455302, 0.015007]`，最近 left_210
  `0.040755 m > 0.03 m`；无抓取、无终端、无 331；`execution_error`，
  effective exit 3。
- 与旧模型同例相比距离 `0.064629 → 0.040755 m`，但仍是同一失败类；
  无可执行闭环改善。
- 报告：[STAGE6_RECHECK_BUDGET500_RESULT.md](STAGE6_RECHECK_BUDGET500_RESULT.md)。

### 8.4 L1/L2/L3 最低开发评估（本轮新增）

- L1 learned **2/5**（6122、6151 accepted；6120 prepared-region、6121 waypoint
  timeout、6148 geometry rejected）；L1 random **0/5**。
- L2 learned **0/5**：4210 grasp-region；4211 terminal held check（12 actions、
  2 grasps、无 331）；4212/4213/4214 prepared-region。
- L3 learned **0/5**：6504/6507 grasp-region；4310/4311/4312 prepared-region。
- L2/L3 初态：L2 4210–4214（无 final val）；L3 6504/6507（val）+
  4310–4312。4210–4214、4310–4312 曾用于 Stage 4，未用于 Stage 5 模型训练，
  不称全新 held-out；test `6300,6301,6516,6517` 保留。
- L2/L3 无完整 331 帧，几何/稳定性指标不可用；专家 `settle(240)+hold(120)`
  与 runner 只有 `_settle(30)` 的差异已登记，未临时加入等待/补救。
- 报告：[STAGE6_L2L3_DEV_RESULT.md](STAGE6_L2L3_DEV_RESULT.md)。

### 8.5 Stage 7 离线 H4（本轮新增）

- 修正版 H4 数据：160 chunks / 590 valid / 50 padding；start obs/action 与 single
  最大差 0.0；无跨 episode/未来观测；holding true/false = 90/70。
- 新 H4 `e1736499…`、stats `fe5df5c4…`；旧 H4 `75e6831c…`、旧 H4 checkpoint
  `93d4fca4…`、single `ce7ee2aa…` 均保留。
- 小样本 20 chunks/70 valid/10 padding：final total `4.07e-5`、XYZ mean
  `0.000214 m`、grip 1.0。
- 全量 H4 500 epochs，best_val epoch 389，val total `0.004146`，`ff8c6945…`；
  reload shape `[26,4,4]`、finite；test 未评估；H4 rollout 未启动。
- 报告：[STAGE7_H4_OFFLINE.md](STAGE7_H4_OFFLINE.md)。

## 9. 尚存缺口 / 下一轮

1. **首例没有 331 帧/终端**：CLOSE 输出不可执行，episode 提前结束；不能判断
   折叠质量，也不能算 Stage 6 验收。
2. **首例证据缺口**：`bc_observations.npz`、`partial_trace.npz` 缺失；代码已修，
   但按要求没有重跑 6120。B 的 joints/1340 维观测仍缺。
3. **CLOSE 仍偏高**：holding 修复 + 重训后 CLOSE 欧氏仍有 8.8/12.6/9.8 cm；
   6120 距离仍 4.13 cm > 3 cm。需要继续离线检查 CLOSE 拟合/动作表示，
   不能调阈值或裁剪 target 掩盖。
4. **L2/L3 已运行但 0/5、0/5**：均无完整 331 帧；fold reference 属探索性，
   不要与 L1 成功数混判；settle/hold 差异仍是具体剩余项。
5. `a5_entry.assess` 仍不使用；`bc-verdict.json` 是 Stage 6 权威判定。
6. 数据盘：50G 总，剩余 12G；单例 1.9M，20 例约 1G，当前不需要扩容。
7. **Stage 7 H4 离线已完成，rollout 未启动**：新 H4 `e1736499…`、
   best_val `ff8c6945…`；后续 H4 必须沿用 single Backend、预算和终端规则，
   再比较 action chunk 影响。

**下一步**：Stage 6 最低开发验收归档完成，Stage 7 只完成离线；不自动启动 H4 rollout。
若后续需要闭环比较，应作为新的显式登记运行；当前不追加采集、不扫参、不重训。
