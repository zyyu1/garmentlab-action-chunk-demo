# l2pose 单次诊断结果：中间行为，未重现 rc8b 4202 的持续滑移

**结论：** 位姿匹配的派生初态（旧折叠几何 + 新整体位姿）单次运行 **accepted**（质心 **0.7396 mm**、P95 **1.5397 mm**、stationary half **7.63 mm**、稳态质心 **0.418 mm/s**，无几何失败）。它既不是旧初态的 0.2642/0.3792，也远未达到新初态的 7.4809/11.5382；按预登记属于**中间行为**。因此：**2.8 mm 的整体位姿变化本身不足以重现失败**；不能据此认定“隐藏应力是关键”，也不能认定位姿无关。

## 1. 运行身份

| 项目 | 值 |
|---|---|
| 诊断候选 | `a5-rc2-pfs1-observation-v2-l2pose`（manifest `3a97a500…`；60/63 与 rc8b 逐字节相同） |
| rollout 源 | `a5_recovery.py` / `a5_capture.py` / `pfs1_observation_v2.py` / `stage4_success_v1.py` / 资产与 rc8b 相同（预检核对） |
| 派生初态 | `day4-square-initial-stripfold-20261104-202215-l2posecontrol`：旧 `final` 经 +0.2564° / (−1.94, +2.71) mm 变换到新位姿；`flat_settled` 不变；速度不恢复 |
| 初态审计 | 内部距离最大差 1.67e-16 m；与新初态对齐残差 P95 0.0672 / max 0.3019 mm；`flat_settled` 逐位相同；z 不变 |
| 运行 | tmux 单次 `day4-a5-rc2-pfs1-observation-v2-20261105-042455-646408`；无重试 |
| 下载/审计 | 111/111 哈希一致；`L2POSE_CASE_AUDIT` 全部通过（`initial_diagnostic=true`、材料 1.0、语义有效） |

## 2. 连续指标对照

| 指标 | old rc8（0.0 初态） | **l2pose（旧几何+新位姿）** | new rc8b（1.0 初态） |
|---|---:|---:|---:|
| 质量 | accepted | **accepted** | rejected |
| 质心 / P95 (mm) | 0.2642 / 0.3792 | **0.7396 / 1.5397** | 7.4809 / 11.5382 |
| stationary half (mm) | 7.24 | **7.63** | 29.91 |
| 释放后 0.5 s 质心 | 11.56 mm/s | **11.97 mm/s** | 4.08 mm/s |
| 1.5–8 s 稳态质心 | 0.595 mm/s | **0.418 mm/s** | 4.092 mm/s |
| 几何失败帧 | 无 | **无** | 82 帧（249–330） |
| fold extent (m) | 0.2283 × 0.4199 | **0.2211 × 0.4159** | 0.1958 × 0.4078 |

- l2pose 的稳定性质心/P95 约为 old 的 2.8×/4.1×，但仍在 1 mm / 3 mm 内；稳态速度甚至低于 old；没有进入 new 的持续 ~4 mm/s 滑移。
- 专家目标：l2pose vs new 最大差 **0.209 mm**、yaw 差 0.026°；l2pose vs old 最大差 2.755 mm。也就是说，专家跟随的是**新位姿的目标路径**，但结果仍接近旧行为——差异不在目标路径本身。

## 3. 派生初态与 new 的剩余差异

- 对齐后：P95 0.067 mm、max 0.302 mm；z 最大差 0.264 mm；pick/关键顶点差 0.02–0.05 mm。
- 除 `final` 的亚毫米几何外，`flat_settled`、`strip_records`（pick/world/width）、`initial_case` 均与 new 相同；速度不恢复、载入后清零。
- 因此 l2pose 与 new 的已知差异只剩**亚毫米级 `final` 几何**（以及由此带来的接触/层序差异）。在这套数据里，亚毫米初态差可以把结果从 accepted 推到 rejected，说明该例对初始几何高度敏感；但本对照不能把它拆成接触/层序/数值哪一项。

## 4. 判读（按修订后的预登记）

| 预登记结果 | 本次 |
|---|---|
| 重现持续滑移 | 否（无持续 ~4 mm/s，stationary 7.6 mm，未失败） |
| 保持旧行为 | 不完全（0.74/1.54 vs 0.26/0.38，约 3–4×） |
| **中间行为** | **是**：accepted 但明显退化，介于 old 与 new 之间 |

- **可以说的：** 2.8 mm 的整体位姿变化**不足以**单独重现失败；专家按新位姿重算的目标也不是充分原因；剩余亚毫米几何差与该例的失败**相关**。
- **不能说的：** “隐藏应力/接触是关键”（未测、无重复性）；“位姿无关”（l2pose 比 old 退化）；“具体释放机制已确定”。

## 5. 边界与下一步

- 只跑了一次；无重试、无扩批、未冻结；诊断初态不是正式 task-scoped 生成初态，不进入七例矩阵/held-out/正式批次。
- 未做重复性：单次 accepted 不能排除 run-to-run 差异；new 的失败也只有一次。
- 下一步可选（需明确指令，不自动执行）：
  1. **重复性**：在相同 l2pose/new 初态上各再跑一次，确认 0.74/1.54 与 7.48/11.54 是否可重复；这是区分“真实敏感性”与“单次分叉”的最低成本对照。
  2. **局部几何**：对 `final` 最大差顶点（#91，0.30 mm；z 差 0.26 mm）与折线附近层序做离线检查，判断亚毫米差是否落在接触/层叠敏感区。
  3. 不建议直接改初态生成协议或扫摩擦。

## 6. 产物

- [l2pose_compare.json](l2pose_compare.json)、[l2pose_bins.csv](l2pose_bins.csv)
- 运行目录：[l2pose_run/…042455-646408](l2pose_run/day4-a5-rc2-pfs1-observation-v2-20261105-042455-646408)
- 派生初态与审计：[day4-square-initial-stripfold-20261104-202215-l2posecontrol](day4-square-initial-stripfold-20261104-202215-l2posecontrol/transform_audit.json)
- 预登记：[SINGLE_COMPARISON_PLAN.md](SINGLE_COMPARISON_PLAN.md)
- 版本登记：[l2pose registration](../../a5-rc2-pfs1-observation-v2-l2pose/registration.json)
