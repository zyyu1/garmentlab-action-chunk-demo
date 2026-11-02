# 第 6 步 6a：L2/L3 部分边折初态（最终版：L2 bottom 折条 + L3 left 半折）

状态（2026-11-02）：**6a 完成**。L1/L2/L3 各 10 张、共 30 张初态图全部 `passed=true`。最终方案：

- L1：平整方巾；
- L2：一条 **bottom** 折条，width 0.16–0.18（4200=0.174179），典型 extent 0.42×0.25、z 0.06；
- L3：一条 **left 半折**，width 0.20，典型 extent 0.25×0.43、z 0.06。

最终 plan `e2cfaebe…`（version square-initial-v3）、yaml `a42fec8a…`；生成器 `178ab10c…`、strip control `49075fb4…`、run script `33a4e142…`。30 张对比图：`results/initial30_sheet_v2.png`。

6b 暂停点：5 动作 recovery 冒烟脚本已写好、未运行（`day4-strip-recovery-smoke.py` `68781cf2…`、`run-strip-recovery-smoke.sh` `57bdfd68…`）；7 动作折叠压缩未实现。完整交接见根目录日报。

## 为什么放弃角点折

`day4-square-initial-liftdrop-20261102-003842-589989`（4300，两段式 transfer/lower）：

- `after_lift`：角点抬到 0.135 m，91 个粒子 >2 cm，形变残差最大 38.8 mm。
- `after_transfer` / `after_lower`：角点向内 10.3–11.8 cm、降到 0.026 m，形变残差最大 150–187 mm——**折角在持布时存在**。
- `after_release`：二维刚性拟合残差瞬间变成 **0.04 mm**，角点弹回初始位置外侧；`settled` 是平整方巾的刚性旋转。
- 布的自摩擦系数为 0，小三角形折角不是稳定平衡；L1 半折能保留是因为折叠面积大、重量压在另一半上、折线长。

## 设计：x-fold 弧线的缩小版

复用已验证的 x 轴半折机制，把折叠宽度从 20 cm 减到 8–12 cm：

- 抓取左边缘中点（`left_sleeve` 槽位）或下边缘中点（`hem` 槽位）的单点锚点。
- 在布料局部坐标系里构造半圆弧：折线距抓点 `width`，弧半径 `width`，四个公开目标 arc45/90/135/place 的局部坐标为
  `lateral*(width - width*cosθ) + [0,0, 0.02θ/π + width*sinθ]`，再经 `Rz(yaw)` 和当前抓点变换到世界。
- 动作序列：approach → descend → close → arc45 → arc90 → arc135 → place → StableHold 60 → release → 30 步静止 → retreat → settle。
- L2：一条 bottom 折条；L3：一条 left 半折（0.20，最终版；早期 bottom+top 方案因 top 边近基座不可达且区分弱已放弃）。
- 生成后机器人回 home EE，渲染 `initial.png`；逐条保存 `strip_XX_{grasp,arc45,arc90,arc135,place,release,retreat,settled}.npz`。

折条落在静止布面上，由自身重量压住，与 L1 半折同一稳定机制；理论上不会再松手弹平，但需要冒烟确认。

## 参数

`square-initial-plan.json`（`version=square-initial-v3`）：

- L2 `4200–4209`：`strips=[{edge:'bottom', width_m:0.16–0.18}]`。
- L3 `4300–4309`：`strips=[{edge:'left', width_m:0.20}]`（yaml：num_lift_drops=1、max_recovery_moves=1）。
- 保留每例 `translation_xy_m`、`yaw_rad`、`settle_steps`；移除 `lift_drop_cycles`。
- `square-difficulty.yaml`：L2 宽度范围 [0.16,0.18]、L3 [0.20,0.20]，notes 改为 strip-fold / left half-fold；`config_sha256` 已同步。

新文件：

- `strip_prepared_control.py`：在现有 prepared 方巾控制上，把用到的边缘槽位改成 5 mm 单点锚点；每步检查锚点间隙 <10 mm。
- `day4-square-initial-stripfold.py`：L2/L3 生成器；局部弧线、两段式动作、StableHold、逐条快照、`crossed_fraction` 和 `pick_displacement_m`。
- `run-square-initial-stripfold.sh`：预检 manifest/plan/config/asset/seed/strips，运行并校验 `initial.png`。

清单 `square-initial-stripfold-files.json`（LF，23 项）：script `178ab10c…`、strip control `49075fb4…`、run script `33a4e142…`、plan `e2cfaebe…`、yaml `a42fec8a…`；共享依赖沿用服务器已验证哈希。

## 11 cm 布条冒烟（012250-056840）：折过去但松手摊平

`day4-square-initial-stripfold-20261102-012250-056840`（4300，left 0.113 / bottom 0.110，`passed=true`）：

- EE/块/锚点跟随都很好：EE ≤4.3 mm、块 ≤0.55 mm、锚点 ≤2.02 mm；held_check accepted。
- `strip_00_place`：crossed 1.00，pick 内移 0.225 m，extent 缩到 0.312——折条真实存在。
- `strip_00_release`：仍 crossed 1.00。
- `strip_00_retreat`：crossed 0.00，pick 回到 -0.001 m，extent 回到 0.446，残差 0.0——**折条在释放后的静止/退让阶段完全展开**。
- 11 cm 布条只占整块布 27.5%，对折线的重量力矩约为 L1 半折（20 cm）的 1/4，压不住 bend=100 的折痕回弹。

修正：宽度提高到 0.16–0.18（接近已验证稳定的半折），L2 一条、L3 左+下两条；生成器宽度上限改为 0.21。需要重跑 4300 验证 0.165 布条是否能保持，以及第二条折是否稳定。

## 0.165 布条在 place 超时（014243-642852）

加宽到 0.16–0.18 后，arc45/90/135 通过，place 在严格 `Square waypoint velocity/position did not converge` 失败：布条负载把 EE 拉离目标，prepared 折叠适配器的 EE<10 mm + 关节速度<0.1 判据无法满足。

修正：给 `strip_prepared_control.py` 加与 corner 版相同的持布阶段放宽——EE 到公共 3 cm、块<5 mm、旋转<0.03、锚点<10 mm 不变；抓取前（follow=False）仍用 10 mm 严格门限。生成器的 `held_check` 也改为 EE<3 cm，其余不变。

## left 0.165 展开、bottom 0.169 保留（015828-793026）

加宽到 0.16–0.18 后的 4300（left 0.165、bottom 0.169，place 放宽后通过）：

- left：place 时 crossed 1.00、pick 内移 0.322 m；release 时 crossed 已降到 0.93；retreat/settled crossed 0.00、pick 回到 -0.001 m、extent 回到 0.446——仍完全展开。
- bottom：place crossed 1.00、pick 0.330 m；release/retreat/settled 均 crossed 1.00、pick 0.326 m、z 最高 0.072 m——**完整保留**。
- 两个方向宽度几乎相同，但 bottom（折叠方向与夹爪手指开合方向一致）稳定，left（垂直）不稳定。left 需要接近半折的宽度；bottom 的阈值在 0.11–0.169 之间。

修正：L2 改为一条 **bottom** 折条；L3 改为 **bottom + top** 两条对边折条（向中间折、重叠成褶皱）。为此给 `strip_prepared_control.py` 增加一个 top 边单点锚点槽位（新 PreparedRegion + 地面过滤），生成器 `EDGE_AXIS`/槽位映射加入 `top`。

## 运行

先跑 L3 4300 冒烟（两条布条）：

```bash
bash /root/autodl-tmp/run-square-initial-stripfold.sh 4300
```

通过后跑 L2 4200：

```bash
bash /root/autodl-tmp/run-square-initial-stripfold.sh 4200
```

两者通过后再跑剩余 18 例：

```bash
for s in 4201 4202 4203 4204 4205 4206 4207 4208 4209 4301 4302 4303 4304 4305 4306 4307 4308 4309; do
  bash /root/autodl-tmp/run-square-initial-stripfold.sh "$s" || break
done
```

## 判读

- `passed=true`、errors 为空、`initial.png` 480×640。
- 图像能看到布条折痕/搭接；L2 一条、L3 两条且在左下搭接。
- `strip_XX_settled.npz` 与 `flat_settled` 的刚性拟合残差必须明显大于 0（角点折的 `after_release` 是 0.04 mm 的完全弹平）。
- `crossed_fraction` 接近或超过 0.5；`pick_displacement_m` 接近 2×width。
- `held_check.accepted=true`，`anchor_gap_max_m` ≤10 mm，`block_error_m` <5 mm。
- 若 arc 阶段在严格 10 mm 门限超时，则给 `strip_prepared_control.py` 增加持布阶段的 3 cm 放宽（与 corner 版相同的做法）。

## 历史（角点折，已证伪）

- v1 lift→原高度释放：L2/L3 静置后完全平铺。
- v2 动态附件角点折：动态 `Control` 在 3 cm reach 容差处停止，抓取悬空，布料完全没动。
- v3 prepared 角点折（两段式）：持布时折角存在，释放瞬间整体弹平；刚性拟合残差 0.04 mm。详见 `SQUARE_INITIAL_LIFTDROP_V1.md`。
