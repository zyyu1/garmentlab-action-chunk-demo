# Stage 6 L1 最小开发评估结果

日期：2026-11-08。**开发评估，不是独立 test 泛化结果；不宣称统计显著或 Stage 6 自动通过。**
本轮未重训、未追加采集、未运行 L2/L3、未重跑 learned 6120、未自动 rollout。

## 1. 固定身份与 5 个初态

- checkpoint：`best_val.pt` epoch 498，sha256 `ade6013141cfa3b114fe6583602da4b14486b96d736ffe5bbfd104cc3e517208`
- stats：`cbc4d711b2341b7ab786ca345ccb490bb32de1ebf93fb1eacc59de22d61a9ae9`，holding identity
- 初态：manifest 冻结的 5 个 flat/val seed，按 seed 升序：

`6120, 6121, 6122, 6148, 6151`

- 6120 使用当前模型此前的 recheck 结果，**未重跑**；旧模型首例不并入当前模型分母。
- 4 个新增 learned 使用原 runner `562386ee…`；random 使用仅新增 `--policy random` 分支的 runner
  `81510841…`；Backend、物理、7 动作预算和判据未改。
- `--skip-identity-check` 已核对：只跳过 checkpoint/stats 两个旧 byte 常量检查；
  initial/material/candidate/code-files 核验仍执行，未补回其他被跳过的身份检查。

冻结清单与预检：

- `<remote-root>/stage6_runs/evals/l1_dev_budget500_20261108/manifest.json`
- `.../precheck.json`
- `.../summary.json`

random 定义（manifest 已登记）：每 action 依次抽 `dx,dy,dz~U(-.05,.05)`、
`dyaw~U(-.2,.2)`、`gripper~{0,1,2}`；每 episode 使用
`np.random.default_rng([0, seed])`，与运行顺序无关；yaw 用当前实际 EE 四元数
按 `R.from_euler("xyz",[pi,0,yaw])` 同一约定反解；不读专家目标、不吸附 region、不自动释放。

## 2. 成功数与配对结果

| 指标 | learned | random |
|---|---:|---:|
| accepted / 5 | **2/5** | **0/5** |
| 6120 | failure | failure |
| 6121 | failure | failure |
| 6122 | **accepted** | failure |
| 6148 | **rejected** | failure |
| 6151 | **accepted** | failure |

| seed | learned status | learned class | learned first failure | learned CLOSE distance | random status | random class | random first failure | random CLOSE distance |
|---:|---|---|---|---:|---|---|---|---:|
| 6120 | execution_error | prepared_region_reject | bc_grasp_01 / pred 1 | 0.040755 | execution_error | prepared_region_reject | bc_grasp_01 / pred 1 | 0.424724 |
| 6121 | execution_error | waypoint_timeout | bc_grasp_01 / pred 1 | 0.027320（在 0.03 内，但 timeout） | execution_error | prepared_region_reject | bc_grasp_01 / pred 2 | 0.505003 |
| 6122 | accepted | success | — | 0.011491 | execution_error | prepared_region_reject | bc_grasp_01 / pred 1 | 0.414138 |
| 6148 | rejected | physical_rejected | —（7 动作完成，评价拒绝） | 0.008865 | execution_error | prepared_region_reject | bc_grasp_01 / pred 5 | 0.400505 |
| 6151 | accepted | success | — | 0.012811 | execution_error | prepared_region_reject | bc_grasp_01 / pred 1 | 0.389775 |

分类计数：

- learned：success 2、prepared-region 1、waypoint timeout 1、physical rejected 1；
- random：prepared-region reject 5、success 0。

random 的 5 次 CLOSE 都远超 0.03 m；learned 的 6122/6148/6151 CLOSE 进入 0.03 m，
其中 6148 完成 331 帧但几何评价拒绝。

## 3. 完整评价例的原物理指标

只有完成 331 帧的 6122、6151（accepted）和 6148（rejected）有完整评价；
6120、6121 和全部 random 因提前失败无完整 331 帧，指标记为**不可用**，不是 0。

| seed | status | held | released_cont | geometry | stable | upward (m) | held pos err (m) | arm speed (rad/s) | anchor gap (m) | failed geom frames |
|---:|---|---|---|---|---|---:|---:|---:|---:|---:|
| 6122 | accepted | true | true | true | true | 0.166009 | 0.001668 | 0.094156 | 0.002041 | 0 |
| 6148 | rejected | true | true | **false** | true | 0.155720 | 0.000471 | 0.095456 | 0.002512 | **121（210–330）** |
| 6151 | accepted | true | true | true | true | 0.162508 | 0.000122 | 0.096178 | 0.003856 | 0 |

稳定性：

- 6122：centroid drift max `8.96e-5 m`，vertex drift p95 max `1.65e-4 m`，
  vertex speed p95 max `2.56e-3 m/s`；
- 6148：centroid `1.54e-8 m`，vertex drift p95 max `4.90e-7 m`，
  speed p95 max `3.75e-6 m/s`（稳定，但 geometry 全窗口失败）；
- 6151：centroid `9.71e-5 m`，vertex drift p95 max `1.49e-4 m`，
  speed p95 max `2.25e-3 m/s`。

6122/6151 的 `expert_target_consistency=false`（OPEN target 与专家 `EE+0.15` 不同），
但按约定不是 BC 成功门槛；实际 `upward_displacement`、detached、held、331、geometry、
stable 均通过。6120/6121/random 没有 `success_meta`/`success_trace` 或完整窗口，
不报告物理成功/失败指标。

## 4. 证据与视频

汇总：

- [summary.json](stage6_l1_dev_20261108/summary.json)
- [summary.md](stage6_l1_dev_20261108/summary.md)
- [manifest.json](stage6_l1_dev_20261108/manifest.json)
- [precheck.json](stage6_l1_dev_20261108/precheck.json)

远程结果根目录：

`<remote-root>/stage6_runs/results/`

| policy | seed | result dir | video |
|---|---:|---|---|
| learned | 6120 | `day4-a5-bc-recheck-budget500-20261109-030302-075279` | [mp4](stage6_l1_dev_20261108/videos/l1dev-learned-6120.mp4) |
| learned | 6121 | `day4-a5-l1dev-learned-6121-20261109-031647-178257` | [mp4](stage6_l1_dev_20261108/videos/l1dev-learned-6121.mp4) |
| learned | 6122 | `day4-a5-l1dev-learned-6122-20261109-032931-765591` | [mp4](stage6_l1_dev_20261108/videos/l1dev-learned-6122.mp4) |
| learned | 6148 | `day4-a5-l1dev-learned-6148-20261109-035350-594500` | [mp4](stage6_l1_dev_20261108/videos/l1dev-learned-6148.mp4) |
| learned | 6151 | `day4-a5-l1dev-learned-6151-20261109-040820-173419` | [mp4](stage6_l1_dev_20261108/videos/l1dev-learned-6151.mp4) |
| random | 6120 | `day4-a5-l1dev-random-6120-20261109-042317-214114` | [mp4](stage6_l1_dev_20261108/videos/l1dev-random-6120.mp4) |
| random | 6121 | `day4-a5-l1dev-random-6121-20261109-042650-473271` | [mp4](stage6_l1_dev_20261108/videos/l1dev-random-6121.mp4) |
| random | 6122 | `day4-a5-l1dev-random-6122-20261109-043104-120426` | [mp4](stage6_l1_dev_20261108/videos/l1dev-random-6122.mp4) |
| random | 6148 | `day4-a5-l1dev-random-6148-20261109-043438-820775` | [mp4](stage6_l1_dev_20261108/videos/l1dev-random-6148.mp4) |
| random | 6151 | `day4-a5-l1dev-random-6151-20261109-044011-122985` | [mp4](stage6_l1_dev_20261108/videos/l1dev-random-6151.mp4) |

视频均来自各 result 的 `evidence/episode.mp4`；每个 result 还有
`result.json`、`bc-verdict.json`、`failure.json`、`partial_trace.npz` 或
`success_trace.npz`/`success_meta.json`、`bc_observations.npz`。

## 5. 结论

- **learned 2/5 accepted；random 0/5 accepted。**
- learned 的两个成功例是 6122、6151；6148 完成 7 动作和 331 帧但因 geometry 拒绝；
  6120 第二轮 CLOSE 仍超出 prepared region；6121 CLOSE 在 0.03 m 内但 waypoint timeout。
- random 五次都在 CLOSE prepared-region 校验失败（0.39–0.51 m），无终端/331。
- 这是 5 个固定 flat/val 初态的开发评估，不是独立 test；样本量不足以宣称统计显著，
  也不构成 Stage 6 自动通过。
- 不自动扩展 L2/L3，不自动 rollout。
