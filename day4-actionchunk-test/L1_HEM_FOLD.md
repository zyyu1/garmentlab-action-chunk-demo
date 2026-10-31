# L1 下摆对折候选 v2

目标：在当前单次抓取能力下尝试实际半折，不再将左袖口拉向右袖口。保留原 pilot 失败数据。

新脚本及模块：day4-l1-hem-fold.py、hem_fold_geometry.py、hem_prepared_grasp_control.py、hem_anchor_alignment_observer.py、run-l1-hem-fold.sh、l1-hem-files.json。沿用原 l1_fold_geometry.py 的暂定指标、mass_experiment.py 的轻质量设置和 anchor_observer.py。

hem 控制器只改初始抓点选取（最小 y 附近 1.5 cm 带内，选择 x 最接近衣物中心的顶点）；原开启跳变阈值、单进程一次抓取限制等均保留。替换仅发生在当前进程的 backend 类引用中，不覆盖正式 backend。观察器按实际 Nx3 锚点数组验证唯一原始顶点映射，仍在 attachment 关闭时执行 points1 对齐。

动作：既有分层下降→抓取→分段抬升 15 cm→跨 y 中线→下摆镜像目标→放置→实测末端位置目标保持 60 步→释放→退让→settle 180 步。长移动分成最大 2.5 cm 的目标段；这不是精确的机器人速度控制。相机提高到 2.8 m；新增 05b_released 和 05c_retreated 快照。

保持原暂定评价阈值，正式 Day4 验收仍为 false。此版本既没有随机 L1 批次，也没有证明独立 reset、多次抓取或 L2/L3 已完成。

本地语法、原始资产下摆选点、分段最大长度、末端目标一致性及镜像越线指标测试通过。GPU 验证尚待用户运行。
