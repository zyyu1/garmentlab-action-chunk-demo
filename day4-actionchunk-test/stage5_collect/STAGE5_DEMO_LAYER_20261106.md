# Stage 5 独立 demo 注册层（已实现，预检通过，未启动采集）

日期：2026-11-06。**状态：实现 + preflight + plan-only 完成；未生成整池初态、未启动 episode 或训练。** Stage 4 冻结文件、回执、formal/dev 授权路径未改。

## 1. 组件

| 文件 | 作用 |
|---|---|
| `demo/stage5-demo-seeds.json` | 三档范围（6100–6219 / 6300–6419 / 6500–6619）、target 50、cap 120、split 与 H=4 规则 |
| `demo/stage5-demo-initial-plan.json` | 360 条 demo 初态条目；采样规则 = `default_rng(seed)` 前三次抽样（dx/dy/yaw，范围取 `square-difficulty.yaml`）+ L2 第 4 次抽样宽度 + L3 宽度 0.20；生成方式可复算（`make_demo_plan.py`） |
| `demo/day4-square-initial-demo.py`、`demo/day4-square-initial-stripfold-demo.py` | 冻结生成逻辑的副本：仅把 plan 文件、USD 路径、files manifest 名换成 demo 版本；物理/动作/协议逻辑不变 |
| `demo/run-demo-initial.sh` | 单 seed 按需生成：校验 demo 范围/plan、`stage5-demo-initial-files.json` 哈希、difficulty/USD 哈希；输出 `DOWNLOAD_DIR` |
| `demo/a5_entry_demo.py` | demo 运行入口：启动冻结 runner（`a5_l1.py`/`a5_recovery.py`），用原评价器 `assess` 写 `split=demo` verdict |
| `trial/sitecustomize.py`（部署副本） | 当 `STAGE5_DEMO=1` 时把 `a5_entry.authorize_initial` 换成 demo 授权：demo 范围 + demo plan 逐字段匹配 + `stage4-initial-v2-task-scoped` 协议（task/level/seed、pfs 0/1/1、材料绑定、demo 生成器与 files manifest 哈希） |
| `demo/make_demo_manifest.py` | 生成 `stage5-demo-initial-files.json`（7 项）与 `stage5_demo_manifest.json`（5 项 + 冻结候选身份） |

**冻结候选**：`40858efc…`（gate `A5_GATE_OK_SOURCE 7`）。Stage 4 的 `square-initial-plan.json`、`stage4-heldout-seeds.json`、`a5-candidate.json`、回执均未修改。

## 2. 部署 manifest

`demo/stage5_demo_manifest.json`：

- `frozen_candidate_manifest_sha256 = 40858efc…`
- `stage4_frozen_files_unchanged = true`
- 5 项 demo 层条目（seeds / plan / initial-files / entry / generator），实测 **0 bad**
- `stage5-demo-initial-files.json`：7 项（两个 demo runner、plan、生成脚本、launcher、difficulty、USD），实测 **0 bad**

## 3. 预检与 plan-only（服务器）

```
SEED_POOL {split: demo, blocked: false, demo_layer_present: true, plan_entries: 360}
ranges {flat:[6100,6219], perturbed:[6300,6419], crumpled:[6500,6619]}
missing_plan {}  out_of_range {}
missing_initial_counts {flat:120, perturbed:120, crumpled:120}   # 按需生成
levels {flat:120/50/120, perturbed:120/50/120, crumpled:120/50/120}  # seeds/target/cap
PREFLIGHT_EXIT 0; PLAN_EXIT 0
```

- 每档最多 **120** 次（按档计数），**50 条有效成功即停**，每 seed 只尝试一次。
- 未生成整池初态、未启动 episode/训练。

## 4. 正式启动命令（待执行）

```bash
cd /root/autodl-tmp/stage5-trial/collect
export STAGE5_APP=/root/autodl-tmp/stage5-trial/app
export PYTHONPATH=/root/autodl-tmp/stage5-trial/app
export STAGE5_OBS_DIR=/root/autodl-tmp/stage5-trial/obs-formal
nohup /root/autodl-tmp/envs/isaac40/bin/python collect_demos.py \
  --config trial/stage5_config_formal.json --run \
  > /root/autodl-tmp/stage5-formal-run.log 2>&1 &
```

行为：逐档、逐 seed；轮到某 seed 时先用 `run-demo-initial.sh` 生成并校验初态，再绑定该次运行；每 episode 独立进程；只收录 `a5-verdict.status=accepted` 且证据/观测对齐的轨迹；拒绝/异常按规则记账。

## 5. 采集与导出口径（固定）

- 观测：动作前只读快照 `vertices(441×3)`、`ee_position(3)`、`ee_quat_wxyz(4)`、`joints(9)`、`holding`；phase 元数据。
- 动作：`[x,y,z,yaw,cmd]`；yaw 只作标签。
- H=4：每块只用起始动作前观测；L1 尾部补位 `mask=[1,1,1,0]`；L2/L3 无尾部；不跨 episode。
- 切分：`sha256('stage5-split-v1-<seed>')` 70/15/15，single/H4 共用。
- 只收录 accepted；全部尝试保留在 `attempts.jsonl`。

## 6. 待执行

正式采集（预计 150–200 次 episode、数十小时 GPU）。本轮停在预检。
