# 4202 L2 位姿匹配单次对照：预登记（修订版，未运行）

**目的（修正后）：** 检验**整体位姿变化是否足以重现** rc8b 4202 的持续滑移。它不能区分隐藏接触、应力或速度的因果贡献。

**命名修正：** 该派生初态只提供**旧初态几何 + 新整体位姿**。`a5_recovery.py` 只读取并设置 `flat_settled` 与 `final` 顶点位置（`_set_garment_world_positions`）并清零速度；不恢复接触缓存、应力或求解器状态。因此不得称其为“旧内部状态”。

## 1. 刚体变换定义（从初态计算，不看 rollout）

| 项目 | 定义 |
|---|---|
| 旋转轴 | 全局 +z（竖直轴），仅平面内旋转 |
| 拟合顶点范围 | 旧、新初态 `initial_geometry.npz['final']` 的全部 **441** 个顶点（xy） |
| 旋转中心 | 旧 `final` 的顶点质心（xy） |
| 平移 | 使变换后的旧 `final` 质心与新 `final` 质心重合（xy） |
| 高度 | z 保持不变（地面关系：平面平移 + 绕竖直轴旋转） |
| 拟合方法 | 2D Kabsch（旋转+平移，无缩放） |
| 计算时点 | 仅用两个初态文件计算；不根据任何 rollout 结果调整 |

记录：4×4 齐次矩阵、θ、旋转中心、平移、拟合顶点范围、拟合残差。

## 2. 变换对象（实际载入的状态）

`a5_recovery.py` 实际读取：
- `flat_settled`：**保持不变**。旧/新初态的 `flat_settled` 逐位相同；两次 rollout 使用同一 flat 参考。
- `final`：**施加上述刚体变换**（旧折叠几何 → 新位姿）。
- 速度：运行时不恢复，载入后清零；因此**没有速度向量需要旋转**，如实记录。
- `before` / `applied`：rollout 不读取，原样保留。
- `initial.png`：复制源旧图，标注“未重新渲染”，不作为变换后状态的视觉证据。

## 3. 初态审计（派生时保存）

- 变换矩阵、θ、中心、平移、拟合顶点范围；
- 源文件哈希（旧 `result.json`、`initial_geometry.npz`、`initial.png`）；
- 派生文件哈希；
- 内部距离保持：变换前后 `final` 的全部顶点对距离最大差（应 ~1e-12 m）；
- 与新初态对齐残差：变换后旧 `final` vs 新 `final` 的 P95/max（预期 ~0.04 mm）；
- `flat_settled` 与新初态逐位相等的核对；
- z 不变的最大差。

## 4. 运行身份

- 独立诊断候选 `a5-rc2-pfs1-observation-v2-l2pose` 与独立账本 `…-l2pose-runs`；只跑 **4202 single 一次**，无重试。
- rollout 源与 rc8b **逐字节相同**（`a5_recovery.py`、`a5_capture.py`、`pfs1_observation_v2.py`、`stage4_success_v1.py`、资产等；预检逐项核对 manifest）。
- 派生初态标记为 `diagnostic-l2-pose-control-v1`，**不得冒充** `stage4-initial-v2-task-scoped` 的正式生成初态；不进入七例矩阵、held-out 或正式 preflight 的 task-scoped 初态检查。

## 5. 控制与评价

- 专家按当前观测正常重算 pick/yaw/目标；记录与 old/new 的实际差异。
- 沿用 `stage4_success_v1`、1 mm / 3 mm 阈值、held gate 与正式窗口；不改七例矩阵、不改 rc8b。
- 证据检查与七例相同（文件、FD 速度、材料读回、release clock、contact 能力），另加诊断初态审计。

## 6. 判读（修正版）

| 结果 | 解释 | 不允许的推断 |
|---|---|---|
| 重现持续滑移（~4 mm/s、~7/11 mm、stationary half ~30 mm） | 整体位姿变化**足以在本例触发失败** | 不等于确定具体释放接触机制 |
| 保持旧行为（~0.26/0.38 mm、无持续滑移） | 该刚体变换**不足以**重现失败；需检查剩余几何差异、载入状态与重复性 | 不能直接认定“隐藏应力是关键” |
| 中间行为 | 记录连续指标（滑移速率、首次失败时刻、stationary half、fold extent） | 不强行二选一 |

## 7. 执行清单

1. 生成派生初态并保存审计（矩阵/哈希/距离/对齐残差）；
2. 建诊断候选与账本，预检 rollout 源与 rc8b 一致、初态身份正确；
3. 跑一次 4202 single；
4. 下载核验、本地复算，与 old/new 4202 对照；
5. 按上表判读；不扩批、不重试、不冻结。
