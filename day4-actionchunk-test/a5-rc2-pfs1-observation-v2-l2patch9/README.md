# a5-rc2-pfs1-observation-v2-l2patch9：九点 z 诊断（已完成，拒绝，响应很小）

**目的：** 固定检验 l2pose 与 new 之间 #91 3×3 邻域的九点 z 差是否足以改变 4202 的验收结果。**只改九点 z，不改 xy、其余顶点、flat 参考或元数据；不平滑。**

**结果：仍 rejected。** 质心 **7.2532 / P95 11.4799 mm**（new 7.4809/11.5382）、stationary 29.68 mm（new 29.91）、首次失败 **251**（new 249）。差异 pre-release 0.50 mm、释放边界 0.77 mm、正式轨迹 max 2.14 mm / mean 0.66 mm；目标 0.016 mm。属于**响应很小、轨迹基本不变**，九点 z 修改不足以改变本例结果；不能认定层序或接触机制。详见 [l2patch9 审查](../results/RC8B_L2_DIAG_20261105/l2patch9_review.md)。

## 1. Patch 定义

| 项目 | 值 |
|---|---|
| 网格 | 21×21 row-major（441 顶点）；#91 = row 4, col 7 |
| 索引 | **69, 70, 71, 90, 91, 92, 111, 112, 113** |
| Δz | −0.0087, −0.2463, −0.1037, −0.0030, −0.2636, −0.1381, −0.0120, −0.0825, −0.0717 mm |
| 规则 | 仅 z 替换为 l2pose derived 值；xy/其余点/`flat_settled`/`before/applied`/元数据不变 |
| 定义哈希 | `68fd2610…`（运行前写入） |

## 2. 身份

| 项目 | 值 |
|---|---|
| 候选 manifest | `ef80bf75…`（63 项；60 项与 rc8b 相同） |
| 父版本 | rc8b `cce573dd…` |
| 派生初态 | `day4-square-initial-stripfold-20261104-221219-l2patch9`（`initial_diagnostic=true`） |
| 派生哈希 | result `3cc0557b…`、geometry `be37dfc3…` |
| rollout | 与 rc8b 相同的 recovery/capture/observation/evaluator/assets |
| 运行 | `…20261105-061356-846153` single 一次；预检 `L2PATCH9_PREFLIGHT_OK`；111/111 |
| 审计 | 恰好 9 点 z 改变；其余数组逐位不变；边缘长最大变化 0.1236 mm；相邻高度差最大变化 0.2606 mm |

## 3. 判读边界

- 可得：九点 z 修改在本配置下**不足以改变验收结果**；只观察到很小响应。
- 不可得：层序/接触机制、因果修复、可推广性；不手工修补正式初态。
- 单次、无重试、无扩批、未冻结；不是正式 task-scoped 初态；正式 Stage 4 成功仍为 0。
- 即使未来 accepted，也应寻找可推广的生成/控制修正，而不是扩大手工 patch。
