# 环境记录

更新日期：2026-09-30

## 已验证
- 系统：Ubuntu 22.04.1
- 远程连接：SSH 和 VS Code Remote SSH 可用
- 数据盘：150 GB
- Python：3.10.8
- 虚拟环境：<remote-root>/envs/isaac40
- Isaac Sim：4.0.0.0（包安装完成，尚未验证启动）
- PyTorch：2.2.2+cu121，导入成功
- NumPy：1.26.4，导入成功
- Open3D：0.18.0，导入成功
- pip check：No broken requirements found.
- GarmentLab commit：6ee0620fddb8083d5eab554fa343cdc966c61d5f

## 已准备资产
- TNLC_Dress057：衣物 USD、border USD 和纹理已解压
- FlatGrid.usd：已上传，二进制 USD
- 资产外部引用完整性：待验证

## 待验证
- 当前为无卡模式，等待 GPU
- GPU 模式下的显卡、驱动和 PyTorch CUDA
- Isaac Sim 无头启动、有限步仿真和渲染帧保存
- GarmentLab FoldDemo 运行

## 文件位置
- 上游代码：<remote-root>/garmentlab_workspace/GarmentLab
- 依赖清单：<remote-root>/isaac40-requirements.txt
- 安装日志：<remote-root>/isaac40-install.log
- Open3D 日志：<remote-root>/open3d-install.log