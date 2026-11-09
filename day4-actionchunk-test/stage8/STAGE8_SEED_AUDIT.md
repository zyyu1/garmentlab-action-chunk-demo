# Stage 8 seed 审计与冻结说明

状态：**60 个候选初态按原 2×3×20 计划冻结；本文件记录历史，不改变任何历史结果。**
完整逐 seed 记录（含 initial 路径、result/geometry 哈希、Stage 4/5 状态）见
[STAGE8_FROZEN_MANIFEST.json](../../../stage8_frozen/STAGE8_FROZEN_MANIFEST.json)。

## 审计口径

- **Stage 4 专家**：Stage 4 正式批次使用过该 seed。
- **Stage 5 专家**：Stage 5 formal attempts 中该 seed 有 `started`/结束记录；
  即使未进入最终 70 例，也标为**曾用于专家运行**，不写“从未使用”。
- **最终数据**：Stage 5 final 70 例中的 `train`/`val`/`test`；未进入则写 `unused`。
- **策略调试**：Stage 6 L1/L2/L3 learned/random 或 Stage 7 H4 调试使用过。
- **冲突**：候选若与最终 train/val 或策略调试 seed 重叠，必须报告具体 seed。

## 结果摘要

| 档 | 候选 | Stage4 专家 | Stage5 专家尝试 | 最终 train/val | 最终 test | 策略调试 | 新生成 |
|---|---:|---:|---:|---:|---:|---:|---:|
| flat | 20 | 8 | 10 | 0 | 0 | 0 | 0 |
| perturbed | 20 | 1 | 5 | 0 | 2 | 0 | 10 |
| crumpled | 20 | 4 | 13 | 0 | 0 | 0 | 0 |
| 合计 | **60** | **13** | **28** | **0** | **2** | **0** | **10** |

**冲突检查：**

- 与最终 `train`/`val` 重叠：**0**。
- 与 Stage 6/7 策略调试 seed 重叠：**0**。
- 候选中的 `6300, 6301` 是最终 **test**，不是 train/val；保留并显式标记。
- Stage 4/5 专家使用不是策略训练泄漏；但相应 seed **不是全新未使用初态**。

## 逐段历史

### Flat

- `4110–4117`：Stage 4 专家使用；未进入 Stage 5 最终 70；非策略调试。
- `4118–4119`：未用于 Stage 4/5 专家；未进入最终 70。
- `6100–6109`：**均有 Stage 5 专家尝试**；状态：
  - 6100 incomplete, 6101 error/incomplete, 6102 incomplete,
    6103 **accepted**, 6104 incomplete, 6105 incomplete,
    6106 **accepted**, 6107 **accepted**, 6108 incomplete, 6109 incomplete；
  - 均未进入最终 70；`accepted` 只表示 Stage 5 专家运行，不等于进入训练集。

### Perturbed

- `4215`：Stage 4 专家使用；未进入最终 70。
- `4216–4219`：未用于 Stage 4/5 专家；未进入最终 70。
- `4220–4229`：本轮按 task-scoped 协议新生成；未运行专家折叠/策略；
  只验证生成有效性、任务参数和身份哈希。
- `6300, 6301`：Stage 5 专家 accepted，进入最终 **test**；不是 train/val。
- `6305`：Stage 5 专家 incomplete；未进入最终 70。
- `6310, 6311`：Stage 5 专家 rejected；未进入最终 70。

### Crumpled

- `4313–4316`：Stage 4 专家使用；未进入最终 70。
- `4317–4319`：未用于 Stage 4/5 专家；未进入最终 70。
- `6500–6519` 候选：
  - 6500 incomplete, 6501 rejected, 6503 incomplete, 6506 incomplete,
    6509 incomplete, 6510 rejected, 6511 incomplete, 6512 rejected,
    6513 incomplete, 6514 incomplete, 6515 rejected, 6518 rejected,
    6519 incomplete；
  - 均为 Stage 5 专家尝试，未进入最终 70；无策略调试。

## 明确排除的调试 seed

`6120, 6121, 6122, 6148, 6151`（flat）；
`4210–4214`（perturbed）；`6504, 6507, 4310–4312`（crumpled）。

这些 seed **不作为 Stage 8 全新独立 test**；6120/6121 仅用于管线 dry run，
并单列为非正式结果。
