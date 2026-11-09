# Stage 10 environment / identity

日期：2026-11-09。本文件为离线核对记录；本轮**未启动 GPU、未仿真、未重训**。

## 运行环境

| 项 | 值 |
|---|---|
| Isaac Sim | **4.0.0.0**（pip `isaacsim==4.0.0.0`、`isaacsim-rl==4.0.0.0`） |
| Python | 3.10.8（`/root/autodl-tmp/envs/isaac40/bin/python`） |
| GPU（历史运行环境） | RTX 3090 24 GB；本轮未启动 |
| GarmentLab 远端 | `https://github.com/GarmentLab/GarmentLab.git` |
| GarmentLab commit | **`f2988b169ec3f1471b46f963ceba58f56179ef0d`** |
| commit 日期/说明 | 2026-10-13，`Autodl adaptation: headless, multi_gpu typo, local paths, Control.step fix` |

## 固定候选身份

| 项 | single | H4 |
|---|---|---|
| checkpoint | `ade6013141cfa3b114fe6583602da4b14486b96d736ffe5bbfd104cc3e517208` | `ff8c694516eb8940e089aeb0a380daab6da0d84e9ab53aeaa6cd302c9a6c21d5` |
| stats | `cbc4d711b2341b7ab786ca345ccb490bb32de1ebf93fb1eacc59de22d61a9ae9` | `fe5df5c45fb29f0c96d38a7d6cae8b8f19464c51884ae6631bdaa3dc16d553fb` |
| updates | 2000 | 500 |
| execute_k | 1 | 4 |

- single：budget500 best_val；H4：best_val epoch 389。
- stats 的 obs_mean/obs_std/cont_mean/cont_std 逐元素相同；训练更新数不同，不能称相同计算预算。
- 父 manifest `STAGE8_FROZEN_MANIFEST.json` file sha256
  `ae1b165376e1b6adc88288fdc3e2e9388ba23c1df74f7377d694f4a2c4dfc030`，
  core `364c9b7e…`；缩减 manifest file sha256 `14532f7a…`，core `2c70026a…`。

## 上游 license / citation

- **GarmentLab**：NeurIPS 2024，论文标题
  *GarmentLab: A Unified Simulation and Benchmark for Garment Manipulation*，
  arXiv:2411.01200（README 中给出）。
- **License 缺口**：当前 checkout `f2988b1` 的根目录没有 `LICENSE` 或 `CITATION`
  文件；未核实到可再分发许可。不得把上游代码/资产当作已获再分发授权；
  对外分享前需向上游确认 license。
- **Isaac Sim**：NVIDIA Proprietary Software（pip metadata）；不是开源许可。
- 本仓库 `garmentlab-action-chunk-demo` 根目录也没有 `LICENSE` 文件；这是交付前待补项。

## schema / Backend / RealRobotBackend

- `schemas/action.py`：公共动作固定为 `[x,y,z,yaw] + gripper(0/1/2)`；策略不输出关节角/速度/力矩。
- `schemas/observation.py`：公共观测；与策略解耦。
- `backends/base.py`：唯一设备边界，`get_observation / execute / stop`。
- `backends/real_robot_backend_stub.py`：**仅接口占位**；`start/stop/get_observation/execute`
  均 `raise NotImplementedError`，没有连接硬件。
- 统一 schema、Backend 边界和 stub 已存在；真实感知、标定、IK、控制器、安全与真机数据
  **未实现**，不能声称支持真机部署。

## 缺失清单

1. RGB-D → 布料关键点/顶点的真实感知、遮挡/噪声处理。
2. 相机内参/手眼标定、布料模板/对应关系。
3. Cartesian waypoint → IK/轨迹/控制器；夹爪时序。
4. 碰撞、工作空间、力/电流、急停等安全限制。
5. 真机数据采集、回放和评估协议。
