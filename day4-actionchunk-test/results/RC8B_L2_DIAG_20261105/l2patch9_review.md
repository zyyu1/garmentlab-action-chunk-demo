# l2patch9 九点 z 修改诊断：拒绝，响应很小，轨迹基本不变

**结论：** 固定九点 z patch 后 4202 single 仍 **rejected**（质心 **7.2532 mm**、P95 **11.4799 mm**，new 为 7.4809/11.5382；stationary 29.68 vs 29.91 mm；首次失败 **251 vs 249**，失败帧 80 vs 82）。差异在 pre-release 约 0.5 mm、释放边界约 0.77 mm、正式轨迹 max 2.14 mm / mean 0.66 mm；目标仅差 0.016 mm。属于**响应很小、轨迹基本不变**，九点 z 修改在本配置下不足以改变验收结果；不能据此认定层序或接触机制。

## 1. Patch 定义（运行前固定）

- 网格：21×21 row-major（441 顶点）；#91 = (row 4, col 7, 0-based)。
- 3×3 邻域索引：**69, 70, 71, 90, 91, 92, 111, 112, 113**。
- 规则：仅将这九点的 z 替换为 l2pose derived 初态的对应 z；xy、其余顶点、`flat_settled`、`before/applied`、元数据均不变；不平滑、不移动其他点。

| 索引 | z_new (mm) | z_derived (mm) | Δz (mm) |
|---:|---:|---:|---:|
| 69 | 40.3090 | 40.3003 | −0.0087 |
| 70 | 40.7683 | 40.5219 | −0.2463 |
| 71 | 40.7183 | 40.6146 | −0.1037 |
| 90 | 53.6579 | 53.6549 | −0.0030 |
| 91 | 54.1992 | 53.9356 | −0.2636 |
| 92 | 53.8419 | 53.7037 | −0.1381 |
| 111 | 66.0020 | 65.9900 | −0.0120 |
| 112 | 66.3894 | 66.3069 | −0.0825 |
| 113 | 65.7145 | 65.6428 | −0.0717 |

[patch_definition.json](patch_definition.json) 在运行前写入并哈希；候选 config 绑定该哈希 `68fd2610…`。

## 2. 派生初态与离线审计

- 源：rc8b new 初态 `day4-square-initial-stripfold-20261105-015817-115841`。
- 派生：`day4-square-initial-stripfold-20261104-221219-l2patch9`；`initial_diagnostic=true`、`diagnostic_control=nine_point_z_patch`、protocol `diagnostic-l2-nine-point-z-patch-v1`（非 task-scoped 正式初态）。
- 审计：**恰好 9 点** z 改变，changed_indices 与定义一致；xy、其余 432 点、`before/applied/flat_settled` 逐位不变；无平滑/额外移动。
- 局部边长最大变化 **0.1236 mm**；相邻高度差最大变化 **0.2606 mm**（即最大 |Δz|）。
- 派生哈希：`result.json` `3cc0557b…`、`initial_geometry.npz` `be37dfc3…`、`initial.png` `50c765ab…`。
- 初态 case 仍在 4202 plan 中（1 次匹配）；policy modes 仅 single。

## 3. 运行身份

| 项目 | 值 |
|---|---|
| 候选 | `a5-rc2-pfs1-observation-v2-l2patch9` |
| manifest | `ef80bf75…`（63 项；**60 项与 rc8b 相同**，仅 candidate/config/runner 变化） |
| 父版本 | rc8b（`cce573dd…`） |
| rollout | `a5_recovery` / `a5_capture` / `pfs1_observation_v2` / `stage4_success_v1` / 资产与 rc8b 相同 |
| 运行 | `day4-a5-rc2-pfs1-observation-v2-20261105-061356-846153`，single 一次，无重试 |
| 预检/下载 | `L2PATCH9_PREFLIGHT_OK`；111/111 哈希一致 |
| 审计 | `L2PATCH9_CASE_AUDIT` 全过（`initial_diagnostic=true`、材料 1.0、语义有效） |

## 4. 结果与逐阶段比较（patch vs 未修改 new）

| 指标 | new（未修改） | **l2patch9** |
|---|---:|---:|
| 质量 | rejected | **rejected** |
| 质心 / P95 (mm) | 7.4809 / 11.5382 | **7.2532 / 11.4799** |
| stationary half (mm) | 29.914 | **29.682** |
| 首次失败 / 失败帧 | 249 / 82 | **251 / 80** |
| fold extent (m) | 0.1958 × 0.4078 | **0.1960 × 0.4080** |

| 阶段 | max 差 | mean 差 |
|---|---:|---:|
| 动作目标 | 0.016 mm（yaw 0.004°） | — |
| 载入后 | 0.039 mm | 0.009 mm |
| recovery 后 | 0.021 mm | 0.012 mm |
| pre-release | 0.502 mm | 0.209 mm |
| 释放边界 | 0.768 mm | 0.223 mm |
| success_trace（331 帧） | **2.137 mm** | **0.662 mm** |

- 影响从 **pre-release** 开始可见（0.5 mm），释放边界 0.77 mm，正式轨迹 max 2.14 mm；但没有改变失败模式。
- 首次失败从 249 推迟到 251（+2 帧，约 0.03 s），失败帧 82→80；stationary 仅下降 0.23 mm。
- 质心/P95 的约 3% / 0.5% 改善幅度小，不能称为“明显改善”；按预登记归为**轨迹基本不变/响应很小**。

## 5. 判读与边界

- **可得结论：** 九点 z 修改在本配置下**不足以改变验收结果**；观察到很小响应，但未改变持续滑移。
- **不可得结论：** 不能据此认定层序或接触机制；不能认定该 patch 是因果修复；不能推广为正式初态的手工修补。
- 只跑一次；无重试、无扩批、未冻结；不改控制/物理/评价/采样；formal Stage 4 成功仍为 0。
- 不自动扩大 patch。即使未来出现 accepted，也应据此寻找**可推广的生成/控制修正**，而不是手工修补正式初态。

## 6. 产物

- [patch_definition.json](patch_definition.json)、[patch_audit.json](patch_audit.json)
- [l2patch9_compare.json](l2patch9_compare.json)
- 派生初态：[day4-square-initial-stripfold-20261104-221219-l2patch9](day4-square-initial-stripfold-20261104-221219-l2patch9)
- 运行：[l2patch9_run/…061356-846153](l2patch9_run/day4-a5-rc2-pfs1-observation-v2-20261105-061356-846153)
- 预登记：[单例预登记](SINGLE_COMPARISON_PLAN.md)、[重复性与几何](repeat_review.md)
