# Stage 5 正式演示 seed 池登记与预检（2026-11-06）

**状态：已登记；预检被冻结入口阻塞，未启动采集。** 正式演示计数为 **0**；4100 / 4202 / 4302 试跑轨迹单独归档，不进入正式集。

## 1. 固定口径

| 项 | 规则 |
|---|---|
| 候选/入口 | 冻结候选 `40858efc…`、`a5_entry.py run`、`stage5_collect` 驱动、动作前只读快照 |
| 观测 | 状态输入：`vertices (441×3)`、`ee_position (3)`、`ee_quat_wxyz (4)`、`joints (9)`、`holding`；`phase` 元数据 |
| 动作 | `[x,y,z,yaw,cmd]`；yaw 仅作动作标签，不替代实测 EE 朝向 |
| H=4 | 每块只用起始动作前观测；L1 尾部 3 个真实动作补到 4，`mask=[1,1,1,0]`，补位不入损失；L2/L3 12 动作无尾部；禁止跨 episode |
| 切分 | 按 seed 稳定哈希：`sha256('stage5-split-v1-<seed>')[:8] % 100`：<70 train、<85 val、否则 test；single 与 H=4 共用 |
| 停止 | 每档 120 个候选 seed、每 seed 一次；每档 50 条有效成功即停；上限 120 次/档（按档计数） |
| 有效成功 | 原评价器 `a5-verdict.status=accepted` + 证据完整 + 动作前观测逐条对齐 |

## 2. 正式 seed 池（预登记）

| 档 | 范围 | 数量 | 与既有 seed 的关系 |
|---|---|---:|---|
| flat | 6100–6219 | 120 | 不重叠 dev 4100–4109、Stage 4 4110–4129、试跑 4100 |
| perturbed | 6300–6419 | 120 | 不重叠 dev 4200–4209、Stage 4 4210–4229、试跑 4202/4201 |
| crumpled | 6500–6619 | 120 | 不重叠 dev 4300–4309、Stage 4 4310–4329、试跑 4302 |

配置：`stage5_config_formal.json`（`split=demo`、target 50、cap 120）。

## 3. 预检结果：阻塞

服务器侧 `--preflight` 输出：

```
SEED_POOL_BLOCKED {"split":"demo","missing_plan":{...360 seeds...},
 "missing_auth":{...360...},"missing_initial":{...360...},
 "demo_registry_present":false}
```

三类阻塞，全部来自**冻结入口的注册约束**：

1. **初态生成不可用**：`day4-square-initial.py:32-33` 要求 seed 在 `square-initial-plan.json` 中恰有一条 L1 记录；`day4-square-initial-stripfold.py:64-66` 要求 seed 在 plan 中。当前 plan 只有 **90 条**（dev 30 + Stage 4 60），6100+/6300+/6500+ 均不存在。
2. **授权不可用**：`a5_entry.authorize_initial` — `split=formal` 要求初态 case 在 `stage4-heldout-seeds.json` 的 heldout（60 条，全是 Stage 4 验收 seed）；`split=dev` 要求 seed 在 `a5-candidate.json` 的 development（4 条：4100/4202/4302/4201）。**没有 `demo` 授权分支**，新演示 seed 两者都不满足。
3. **初态未生成/未绑定**：360 个 seed 没有对应初态目录（`initials` 为空）。

## 4. 需要的最小修订（待批准）

新增 **Stage 5 demo 注册层**，不改 Stage 4 冻结文件：

1. `stage5-demo-seeds.json`：登记 6100–6219 / 6300–6419 / 6500–6619 及 split 规则。
2. `stage5-demo-initial-plan.json` + 独立的 demo 初态生成入口（复用冻结生成逻辑与 `stage4-initial-v2-task-scoped` 协议，仅把 plan 源换成 demo 文件），生成后绑定 `result.json` / `initial_geometry.npz` 哈希。
3. `a5_entry` 增加 `split=demo` 授权分支（或独立的 demo 入口），只校验 demo 注册与初态哈希；不改变 formal/dev 路径与 Stage 4 判据。
4. 预检通过后，按本文件 §1 口径采集。

在这些修订获批前，采集停在预检；不修改 `square-initial-plan.json`、`stage4-heldout-seeds.json`、`a5-candidate.json` 等冻结文件。

## 5. 本轮已完成的非阻塞项

- **EE 姿态字段**：动作前快照新增 `ee_quat_wxyz`（`get_cur_ee_pos` 返回 wxyz），已用独立轨迹 **4201** 验证：12/12 观测、quat 形状 (4,)、单位范数、target 差 1.0e-8、command 差 0。4201 评价器为 rejected（已知案例），仅用于字段验证，不进入演示集。
- **H=4 尾部规则**：已固定为补位 + mask，`verify_export.py` 已实现（L1 7 动作 → 1 完整块 + 1 个 `[1,1,1,0]` 尾部块）。
- **切分**：按 seed 稳定哈希，single/H4 共用。
- **字段命名**：观测用 `ee_position`（3）与 `ee_quat_wxyz`（4）；动作中的 yaw 不冒充观测朝向。
