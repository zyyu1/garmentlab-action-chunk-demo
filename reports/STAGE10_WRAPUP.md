# Stage 10 wrap-up · v9.1.0

## English

The reduced demo and offline figure reproduction package are complete. The full 120-episode evaluation and clean-environment simulation reproduction remain future work. This packaging update launched no simulation, GPU training or remaining evaluation episodes.

- Stage 8: 15 paired seeds / 30 episodes; single 0/15, H4 2/15 (flat seeds 4111 and 4113). L2/L3 both 0/5 for each policy.
- 27/30 episodes lack a complete 331-frame window; geometry/stability remain unavailable.
- Stage 6/7 development results are excluded. Initial-state reuse and unequal training budgets prevent stronger comparison claims.
- The original Stage 9 PDF and CSV are preserved. v9.1.0 figures use portable English labels and derive failure counts from archived error records.

### Offline reproduction

From the repository root:

```bash
python -m pip install matplotlib==3.10.1
python scripts/reproduce_figures.py
```

Output: `figures_reproduced/`; use `--out` with a fresh directory to repeat. See [checks](../results/checks.json), [raw CSV](../results/raw_results.csv) and [summary](../results/summary.json). The script validates paired initial hashes, denominators, success counts and all 28 failure records. Expected failure counts (single/H4): grasp region 3/1; CLOSE region 7/2; waypoint 1/5; release order 1/0; complete rejected 1/0; incomplete 2/5.

### Environment and deployment boundary

Historical simulation: Isaac Sim 4.0.0.0, Python 3.10.8, RTX 3090 24 GB, GarmentLab commit `f2988b169ec3f1471b46f963ceba58f56179ef0d`. See [environment/model identities](../docs/ENVIRONMENT_IDENTITY.md), [migration](../docs/MIGRATION.md) and [architecture](../assets/architecture.png). Real-robot methods remain stubs; no real deployment or clean-environment simulation rerun is claimed. Licensing gaps are recorded in the identity document.

[Stage 9 report](STAGE9_REPORT.pdf) · [Success rate](../assets/fig1_success_rate.png) · [Failure types](../assets/fig2_failure_types.png) · [README](../README.md)

## 中文

缩减版 demo 与离线图表复现材料已完成；完整 120 例评估及干净环境仿真复现仍待后续。本次整理没有启动仿真、GPU 训练或补跑剩余评估。

- Stage 8 共 15 个配对 seed、30 例：single 0/15，H4 2/15，成功为 flat 4111、4113；两种策略在 L2/L3 均为 0/5。
- 27/30 无完整 331 帧窗口，几何/稳定性保持不可用。
- Stage 6/7 开发结果不并入分母；初态复用和训练预算不同限制结论范围。
- 保留原始 Stage 9 PDF 和 CSV；v9.1.0 图表使用跨平台英文标签，失败数量从归档错误记录逐例推导。

### 离线复现

在仓库根目录运行上方两条命令，输出到 `figures_reproduced/`；重复运行用 `--out` 指定新目录。校验内容包括配对初态哈希、分母、成功数及全部 28 例失败记录。失败数（single/H4）：抓取区域 3/1；CLOSE 区域 7/2；waypoint 1/5；释放顺序 1/0；完整 rejected 1/0；incomplete 2/5。

### 环境与部署边界

历史仿真环境为 Isaac Sim 4.0.0.0、Python 3.10.8、RTX 3090 24 GB；完整 commit、模型和 stats 身份见上方环境文档。真机方法仍为接口占位；没有完成真机部署或干净环境仿真重跑。许可缺口保留在环境身份文档中。原始联系材料仍是未发送草稿，不属于本次展示入口。
