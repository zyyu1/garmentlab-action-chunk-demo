# 第 6 步 6a：L2/L3 角点翻折初态生成（v3：prepared 单点锚点 + 扰动专用门限）

状态：v2 动态附件折角版机械上通过，但布料**从未移动**——动态 `Control` 在 3 cm `reach` 容差处就停止，grasp 悬在角点上方 2.9 cm，2 cm 动态附件没有覆盖到布。已改回 prepared 单点锚点（唯一被证明能抓住布的路径），并只在 `corner_prepared_control.py` 里把**持布阶段**的 EE 门限放宽到公共 3 cm 契约；块跟随 <5 mm、锚点 <10 mm、抓取前 10 mm 严格门限都不变。v3 已实现并更新清单，尚未运行。

## v2 动态附件为什么是空动作

`day4-square-initial-liftdrop-20261101-114359-549472`（4300，`passed=true`）：

- `cycle_00_settled` 与 `flat_settled` 最大差 **3.7e-8 m**；`cycle_01_settled` 与 `cycle_00` 差 **7.5e-9 m**；两层完全没动。
- 每个动作（包括无负载的 approach）EE 误差 **28–30 mm**，正好停在原始 `Control` 的 3 cm `reach` 容差边界：`robot_goto_position` 一进入 3 cm 就返回，不会收敛到毫米级。
- grasp 时 EE `z=0.0386`，角点 `z=0.0099`；辅助块中心在角点上方约 2.9 cm，超过 2 cm 动态附件重叠半径，夹爪在空气里闭合。
- 因此 v1 动态版（091429/095419）的“通过”也是空动作：0.4434/0.4464 的 extent 只是方巾旋转后的外接框（0.4×(cos yaw+sin yaw)），不是布料被拉伸。

## 只有 prepared 单点锚点真正抓住了布

v1 诊断 `day4-square-initial-liftdrop-20261101-110942-527451`（4300，prepared corner_3）：

- grasp 后 EE 误差 0.83 mm；块跟随最大 1.31 mm；单点锚点间隙最大 1.4 mm；角点确实被抬起 7.8 cm。
- lift 三段末 EE 误差 6.9 → 8.9 → 13.7 mm；第三段 240 步一直 ≥13.7 mm，关节速度 0.13–0.15 rad/s；误差几乎全是水平方向，z 只差 -3.1 mm。
- 离线 URDF 多解 IK：目标与卡住位置都可解（关节余量 0.111/0.196 rad）。
- 结论：不是块/锚点/运动学问题，是闭爪夹住布料后布张力把 EE 拉偏；prepared 折叠适配器的 EE<10 mm + 连续 6 步 + 末臂速<0.1 判据在近角高抬升下无法满足，公共 3 cm `reach` 契约满足。

## v3 设计

- 生成器回到 `CornerPoseBackend`（prepared 4 角点单点锚点，5 mm 重叠），`prepared_grasp=True`。
- `corner_prepared_control.py`（仅 L2/L3 生成器引用，正式折叠不引用）：
  - 每个 corner slot 的 `_drive` 在 `follow=False`（抓取前接近/下降）仍走原始 **10 mm** 严格门限。
  - `follow=True`（持布）改为 **EE 30 mm**、块 <5 mm、旋转 <0.03、连续 6 步；不再要求关节速度 <0.1。
  - `robot_goto_position` 持布时按 25 mm 分段执行，末段 60 步只检查 EE<30 mm + 块<5 mm，不因负载下的持续微动报错。
  - 首次 grasp 之后（`slot.used=True`），release 跟随和 home 也用放宽路径；抓取前的 approach 仍严格。4300 首次 v3 运行在 release 的严格末臂速检查失败（grasp/lift/fold 已完成），因此需要这一条。
- 每个周期动作：approach → grasp → lift → hold → **fold（一次对角下移：向内 `fold_over_m`、降到角点+2 cm）** → release → settle。v2 的“在抬升高度水平转移再下降”合并为一个对角 place，减少高张力段的水平拖拽。
- 判读不看 z extent：折角是单层对折后平放，两层几乎同高；看 `initial.png` 和二维重叠密度。外接矩形也基本不变，因为折线保留了相邻两条边的极值。

## v3 首次成功运行（122344-211131）：布料被刚性拖走

`day4-square-initial-liftdrop-20261101-122344-211131`（4300，`passed=true`）：

- grasp EE 0.83/0.93 mm；块跟随 ≤1.02 mm；锚点间隙最大 3.89 mm；grasp/lift/transfer/fold/release/home 全部完成。
- lift EE 误差 23.4/14.0 mm，fold 14.3/14.5 mm，release 4.2/4.1 mm，均在放宽后的 3 cm 内。
- 但 `cycle_00_settled` / `cycle_01_settled` 相对 `flat_settled` 的**二维刚性拟合残差最大 0.01 mm**：整块布只是刚性旋转/平移（cycle 0 转 +2.98°、平移 5.5 cm；cycle 1 再平移 8.9 cm），没有任何内部形变。`initial.png` 也是平整方巾。**没有折角，是整块布被拖走。**
- 原因：旧 fold 是从抬升点直接斜降到 2 cm 的直线，角点越过折线时 z 只有约 6 cm，布贴地拖行。L1 x-fold 在 90° 时把抓点抬到约 20 cm 再横移，布是被带过去的。

修正：fold 改回两段式——**先在 lift 高度水平内移到落点上方，再垂直下降**；并在 approach/grasp/lift/transfer/lower/release/settled 后各保存一份 `cycle_XX_after_*.npz`，用于判断折角是在哪一步形成/丢失。

## 参数与清单

`square-initial-plan.json`（`version=square-initial-v2`，参数未变）：L2 `fold_over_m` 0.07–0.09、L3 0.10–0.13；每周期保留原 `lift_height_m`、`hold_steps`、`settle_steps`，`release_clearance_m=0.02`；4300 第二周期为 corner 1。`square-difficulty.yaml` 的 L2/L3 数值不变，notes 为 fold-over 语义。

已更新清单（LF）：script `deed794a…`、corner control `15e6ce56…`、plan `4879e0af…`、yaml `cae00393…`；21 项预检待远端复核。

## 运行

先跑最差近角、两角翻折的 L3 4300：

```bash
SQUARE_LIFTDROP_DIAG=1 bash <remote-root>/run-square-initial-liftdrop.sh 4300
```

通过后跑 L2 4200：

```bash
SQUARE_LIFTDROP_DIAG=1 bash <remote-root>/run-square-initial-liftdrop.sh 4200
```

两者通过后再跑剩余 18 例（每例独立进程）：

```bash
for s in 4201 4202 4203 4204 4205 4206 4207 4208 4209 4301 4302 4303 4304 4305 4306 4307 4308 4309; do
  bash <remote-root>/run-square-initial-liftdrop.sh "$s" || break
done
```

## 判读

- 每例：`passed=true`、errors 为空、`initial.png` 480×640、`initial_geometry.npz` 可读。
- `initial.png` 能看到折角搭接；二维密度图中折角区域约为平铺的两倍。
- `cycle_00_settled` / `cycle_01_settled` 与 `flat_settled` 必须有明显差异（v2 是 3.7e-8 的完全无动作）。
- `action.block_error_m` <5 mm、`max_single_anchor_gap_m` <10 mm；持布阶段 EE 误差允许到 30 mm。
- L3 两个折角与 L2 单角在图像上可区分；L1 仍为平整 0.4 m 方巾。
- 若 fold 的 EE 超过 30 mm 导致 `robot did not reach target`，先降低 fold 的起始高度或把对角路径拆成两段。

## 历史：v1 角点 lift/drop（已证伪）

v1 用动态附件（2 cm）和 prepared 单点锚点（5 mm）执行 lift→原高度释放。两种方式静置后都平铺（z extent ≈6e-8），因为 `particle_friction_scale=0`，褶皱无法保留；动态版更严重：3 cm `reach` 容差使抓取悬空，布料完全没动。

- 2 cm 动态附件：L2 4200（091429-926167）、L3 4300 钳制后（095419-369850）通过状态检查，但都是空动作/平铺。
- prepared 单点锚点：L2 4200 通过（103938-206493）；L3 4300 在 lift 的 10 mm EE 门限超时（104852-657877），诊断 110942-527451 证明块和锚点正常、EE 被布张力拉偏 13.7 mm。
