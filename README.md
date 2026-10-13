# Garment Folding with Action Chunking

比较 single-step behavior cloning 与 H=4 action-chunk BC，
在 Flat、Perturbed、Crumpled 三种衣物初态下的折叠成功率和推理开销。

## 当前状态

环境准备阶段，尚无仿真、训练或评估结果。

- SSH 与 VS Code Remote SSH 已配置。
- Isaac Sim 4.0.0.0 已安装，实际启动待验证。
- PyTorch 2.2.2、NumPy 1.26.4、Open3D 0.18.0 导入通过。
- pip check 通过。
- 衣物和场景文件已准备，资产引用完整性待验证。
- 等待 GPU 后进行无头仿真与渲染测试。

## Upstream code reused

计划复用 GarmentLab 的 FoldDemo、FoldEnv 和控制接口。
上游代码单独存放。

- Repository: https://github.com/GarmentLab/GarmentLab
- Commit: 6ee0620fddb8083d5eab554fa343cdc966c61d5f

## Our additions

当前包含环境记录和真机迁移假设。
数据生成、策略、统一 Backend 和评估尚未实现。

## 文档

- [环境记录](environment_log.md)
- [真机迁移假设](docs/sim2real_assumptions.md)