# a5-rc2-pfs1-observation-v2-l2pose：4202 位姿匹配诊断（已完成，中间行为）

**目的（修正后）：** 检验**整体位姿变化是否足以重现** rc8b 4202 的持续滑移。它不能区分隐藏接触、应力或速度的因果贡献。

**结果：accepted，中间行为。** 质心 **0.7396 mm**、P95 **1.5397 mm**、stationary half **7.63 mm**、稳态质心 **0.418 mm/s**、无几何失败；介于 old（0.2642/0.3792）与 new（7.4809/11.5382）之间。位姿变化本身**不足以**重现失败；专家目标跟随新位姿（与 new 差 0.209 mm），但不是失败原因。完整报告：[l2pose_review](../results/RC8B_L2_DIAG_20261105/l2pose_review.md)。

**命名：** 派生初态只提供**旧初态几何 + 新整体位姿**。rollout 只读取/设置 `flat_settled` 与 `final` 顶点位置并清零速度；不恢复接触缓存、应力或求解器状态，因此不是“旧内部状态”。

## 1. 身份

| 项目 | 值 |
|---|---|
| 版本 | `a5-rc2-pfs1-observation-v2`（`l2pose` diagnostic） |
| 父版本 | rc8b（manifest `cce573dd…`） |
| 新 manifest | `3a97a500…`（63 项；**60 项与 rc8b 逐字节相同**） |
| 变化项 | `a5-candidate.json`、登记 JSON、runner |
| rollout 身份 | `a5_recovery.py` / `a5_capture.py` / `pfs1_observation_v2.py` / `stage4_success_v1.py` / 资产与 rc8b 逐字节相同 |
| 新账本 | `/root/autodl-tmp/a5-rc2-pfs1-observation-v2-l2pose-runs` |

## 2. 派生初态（旧几何 + 新位姿）

| 项目 | 值 |
|---|---|
| 派生目录 | `day4-square-initial-stripfold-20261104-202215-l2posecontrol` |
| 源 | 旧 4202 初态 `…20261103-062710-242560` |
| 位姿参考 | 新 4202 初态 `…20261105-015817-115841` |
| 旋转轴 / 中心 | +z / 旧 `final` 质心 |
| 旋转 / 平移 | **+0.256377° / (−1.9414, +2.7075) mm** |
| 拟合范围 | 旧、新 `final` 的全部 441 顶点（xy） |
| 变换对象 | `final`（折叠几何）→ 新位姿；`flat_settled` 不变（与新旧初态逐位相同）；`before/applied` 不变；**速度不恢复** |
| 地面关系 | 平面平移 + 绕竖直轴旋转；z 不变 |
| 内部距离保持 | 最大差 **1.67e-16 m** |
| 与新初态对齐残差 | P95 **0.0672 mm**、max **0.3019 mm** |
| 派生哈希 | `result.json` `b051737a…`、`initial_geometry.npz` `32e76868…`、`initial.png` `8b9469ed…` |

## 3. 运行与评价

- 只跑 **4202 single 一次**，无重试、不扩批、不冻结；不改七例矩阵。
- 专家按当前观测正常重算目标；沿用 `stage4_success_v1`、1 mm / 3 mm 阈值与正式窗口。
- 证据检查与七例相同（文件、FD 速度、材料读回、release clock、contact 能力），另加诊断初态审计（矩阵、哈希、内部距离、对齐残差、flat 相等、z 不变）。
- 派生初态标记为 `diagnostic-l2-pose-control-v1`，不得冒充 `stage4-initial-v2-task-scoped` 的正式初态。

## 4. 判读

| 结果 | 解释 |
|---|---|
| 重现持续滑移（~4 mm/s、~7/11 mm、stationary half ~30 mm） | 整体位姿变化**足以在本例触发失败**；不等于确定具体释放接触机制 |
| 保持旧行为（~0.26/0.38 mm、无持续滑移） | 该刚体变换**不足以**重现失败；需检查剩余几何差异、载入状态与重复性，不能直接认定“隐藏应力” |
| 中间行为 | 记录连续指标，不强行二选一 |

## 5. 边界

- 诊断控制，不是正式任务协议；不能作为冻结或正式批次依据。
- 不改 rc8b 失败结论；正式 Stage 4 成功仍为 0。
