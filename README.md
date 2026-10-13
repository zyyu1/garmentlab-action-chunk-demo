# Garment Folding with Action Chunking

比较 single-step behavior cloning 与 H=4 action-chunk BC，在 Flat、Perturbed、Crumpled
三种衣物初态下的折叠成功率、恢复能力和推理开销。

> Preliminary action-representation study for fast and robust garment-folding VLA policies.
> Not a complete VLA model.

## 研究问题

How do initial garment-state difficulty and temporal action representation affect folding
success, recovery behavior, and inference cost?

## 当前状态（Day 2 结束，2026-10-13）

已完成：环境、场景、动作序列、每阶段状态导出。

- Isaac Sim 4.0.0.0 headless 在 AutoDL RTX 4080 32GB 上启动通过。
- GarmentLab 已适配 AutoDL，改动见 `third_party/autodl_adaptations.patch`。
- 12 步折叠动作序列（grasp → move → release × 3）执行完成，退出码 0。
- 第三次抓取诊断 D00–D04 执行完成，退出码 0。
- 每阶段导出顶点数据，最终顶点数 9945。
- 证据目录：`runs/2026-10-13-third-grasp/`。

未完成 / 已知限制：

- 折叠质量未验收：末态倾斜、一角翘起。
- 主视角被机械臂遮挡约 30–40 %，无法判定袖子/领口对齐。
- 无 mp4 视频，仅有 PNG 序列。
- 仅运行 1 次，未测重复性。
- 尚无 demonstrations、策略训练和正式评估。

## Upstream code reused

- Repository: https://github.com/GarmentLab/GarmentLab
- Base commit: `6ee0620fddb8083d5eab554fa343cdc966c61d5f`（grafted）
- 复用模块：`FoldEnv.py`、`BaseEnv.py`、`Control.py`、`SceneConfig.py`、`Recording_Camera.py`、
  `FoldDemo.py` 的控制逻辑。
- AutoDL 适配改动已提交，patch 见 `third_party/autodl_adaptations.patch`。

## Our additions

- `backends/`、`schemas/`、`envs/`、`experts/`、`policies/`、`evaluation/`：目录已建，
  Day 3 起逐步填充。
- `scripts/fold-action-test.py`、`scripts/fold-third-grasp-debug.py`：临时测试脚本，
  用于验证 GarmentLab 折叠动作序列。
- `runs/2026-10-13-third-grasp/`：Day 2 证据（PNG + 每阶段顶点 npy + log）。
- `docs/2026-10-13_day2_report.md`：Day 2 报告。
- `third_party/autodl_adaptations.patch`：对上游的三处最小适配改动。

## Roadmap

- Day 3：`GarmentLabBackend` + 统一 observation/action schema + 侧视图相机。
- Day 4：三档 difficulty protocol + 参数化 expert。
- Day 5：生成 demonstrations 与 dataset。
- Day 6：single-step BC。
- Day 7：H=4 action-chunk BC。
- Day 8：正式实验（2 policies × 3 difficulties × 20 seeds）。
- Day 9：分析、图、视频、mini report。
- Day 10：干净复现 + 联系材料。

## Environment

- AutoDL container: `autodl-container-5d974b909f-0ac9998e`
- GPU: RTX 4080 32GB, driver 580.105.08
- Isaac Sim 4.0.0.0
- Python venv: `/root/autodl-tmp/envs/isaac40`
- 详见 [环境记录](environment_log.md)

## 文档

- [环境记录](environment_log.md)
- [真机迁移假设](docs/sim2real_assumptions.md)
- [Day 2 报告](docs/2026-10-13_day2_report.md)

## Citation

GarmentLab (NeurIPS 2024): https://github.com/GarmentLab/GarmentLab
