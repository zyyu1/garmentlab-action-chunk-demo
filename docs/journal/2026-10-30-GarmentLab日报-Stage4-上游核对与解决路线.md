# Stage 4：上游核对与具体解决路线（2026-10-30）

## 结论与范围

已通过 GitHub 插件检索 GarmentLab/GarmentLab 的 main、README、FoldDemo、FoldEnv、Control、GarmentConfig、Garment、BaseEnv 和相关 issues，并核对本地 Stage 4 源码/结果。上游 main 本次解析为 `6ee0620fddb8083d5eab554fa343cdc966c61d5f`，与本地原先选定版本一致。

当前主要阻塞是完整释放后没有保持 half-fold。不是尚未实现动作流程，也没有证据把根因唯一归为 IK、腕部、弯曲刚度或锚点数量。本轮只做检索和离线审查，没有启动远端仿真、修改正式 Backend 或增加成功样本。新实例的实际代码与环境仍需核验。

## 1. 上游不能直接作为完整释放成功的基准

- [FoldDemo.py](https://github.com/GarmentLab/GarmentLab/blob/6ee0620fddb8083d5eab554fa343cdc966c61d5f/demo/FoldDemo.py) 最后调用 `ungrasp([True])`。
- [Control.py](https://github.com/GarmentLab/GarmentLab/blob/6ee0620fddb8083d5eab554fa343cdc966c61d5f/Env/env/Control.py) 的 `ungrasp` 仅在 `not flag[i]` 时打开夹爪并 detach。因此末次 True 不会释放；后续 robot_goto_position 也没有调用附件跟随更新，最后下摆仍受附件约束。
- 前两次 `ungrasp([False])` 才是释放。不能由官方演示图或最后一帧证明完整释放后的整衣折叠保持。
- 官方 `move()` 将辅助块角速度设为零，demo 的姿态参数为 None。180°腕部翻转不是官方路径的必要前提。
- 官方抓取本身是附件辅助模型，不能写成已经验证真实夹爪接触抓取。

因此保留你的显式 OPEN、退让和释放后测量要求，不通过保留附件来制造成功，也不再把三阶段原轨迹当作已验证答案。

## 2. 已有证据与排除项

|证据|具体结果|对下一步的约束|
|---|---|---|
|三阶段开发试验|102 个公开动作；最终投影 IoU 约 0.0361；各阶段均有回弹|不能纳入≤12动作正式示范，也没有必要继续整衣三阶段|
|首袖单点对照|回移 564.7→473.6 mm，仍展开；最大边长比 1.621→1.967|换成当前单点方案不足以修复，不继续锚点数扫描|
|低弧线末段|源半片高度中位约70 mm；与固定半片垂向间隔中位约46 mm；抓点离最近固定材料投影约24.75 mm|“已越过折线”不等于“已铺在下层上”；先修终段放置|
|历史质量审计|9945×默认0.01 kg≈99.45 kg；现候选采用0.0001 kg/点≈0.9945 kg|整合时必须显式传质量，不能只移植路径后退回默认值|
|多槽位代码|每槽一次性 used；robot_reset 只打开夹爪|同回合三次不同区域抓取通过，不等于同一抓点重用或独立episode reset通过|

证据入口：`day4-actionchunk-test/minimum_hem_review/review.md`、`results/day4-official-three-fold-20261027-000627-746461/pilot_review.md`、`results/day4-single-anchor-sleeve-20261027-004413-549160/pilot_review.md`、`results/day4-physics-config-20261025-053727-962061/physics_config_v2_review.md`。

## 3. 第一优先级：运行已有的单次终段支撑放置候选

采用 `day4-actionchunk-test/day4-minimum-half-fold.py`，不要再从头写另一套实验。其 manifest 中9个依赖已在本轮核对，全部匹配；本地未发现该候选的结果目录，不代表远端一定未运行。

执行前先核对新实例中：

1. `<remote-root>/envs/isaac40/bin/python`、GarmentLab资产及 `<remote-root>/garmentlab-action-chunk-demo/backends/garmentlab_backend.py` 是否存在。
2. 实际 Isaac Sim 版本为4.0系列；不要把升级Isaac Sim当成本轮修复。
3. `<remote-root>/day4-minimum-half-fold-*` 是否已有完整结果，有则先取回审查。
4. 将 `minimum-half-fold-files.json` 指定的9个文件、manifest自身及 `run-minimum-half-fold.sh` 一并传到 `<remote-root>`。不要只传主脚本。

远端前置条件满足且不存在待审结果后运行：

```bash
bash <remote-root>/run-minimum-half-fold.sh
```

候选维持质量、摩擦、机器人、低弧线前缀，只修改释放前的材料目标：

```text
p_ee_goal = p_ee_now + (p_material_goal - p_material_now)
```

目标取当前固定半片的邻近低平区域，XY修正不超过60 mm；保持目标60步，然后完整释放、原地60步、退让，再测量3 s与4 s保持情况。旧快照中可行目标约为材料点 `[-0.00894,-0.22217,0.02990]`，对应末端 `[-0.00917,-0.21521,0.02041]`；这些仅说明旧数据上可行，不能作为所有episode的硬编码坐标。

现有20 mm层间距是几何代理，不是已验证的接触距离。不要声称“附近有点”就已经有支撑力。运行时同时看材料目标误差、源半片高度/层间距、末段速度、局部边长比，以及释放后的真实保持。

判读与停止规则：

- `passed=True` 只代表流程产物完整。必须检查 `06_supported_place`、`08_release_stationary`、`10_final_3s`、`11_retention_4s` 的视频和材料点。
- 材料点仍未到目标、下层被拖走或明显悬高：继续定位路径/放置误差，不能据此判定弯曲刚度有问题。
- 放置已收敛、附件确实关闭，但释放后仍恢复展开：才进入一次物理可折性对照。
- 完整释放、退让、静置后保持明显重叠：同配置独立重复一次。两次都是开发验证，之后再冻结正式评价。

## 4. 如果仍回弹：只做一次有依据的弯曲对照

上游 [GarmentConfig.py](https://github.com/GarmentLab/GarmentLab/blob/6ee0620fddb8083d5eab554fa343cdc966c61d5f/Env/Config/GarmentConfig.py) 使用 stretch=10000、bend=100、shear=100、damping=0.2；[Garment.py](https://github.com/GarmentLab/GarmentLab/blob/6ee0620fddb8083d5eab554fa343cdc966c61d5f/Env/Garment/Garment.py) 把这些值传入 ClothPrim。不能仅凭100这个数值判定错误。

只有上一节证明放置基本有效时，建议预注册两分支：A保留bend=100；B构造时bend=10，其余保持同一参考配置。这是十倍敏感性诊断，不是已知修复值或真实布料标定。各分支都记录初始settled状态及运行时弹簧刚度；不能假装改变构造参数后初态仍严格相同。

若B明显改善保持且无新增穿透/局部过伸长，才独立重复并考虑采用为明确标注的仿真配置。若两者都回弹，不继续网格搜索；重新检查布料支撑、自碰撞间距及固定半片拖动。当前 particle_friction_scale=0 是既有稳定性候选，不代表物理布料层间摩擦已校准；不能同时恢复摩擦、改质量和弯曲再声称找到了原因。

## 5. Backend 必须补齐的具体项

1. **稳定附件生命周期**：保留预建块/约束与points1对齐。OPEN应零速度、禁用附件、打开夹爪，不删除运行中的块。[上游issue #9](https://github.com/GarmentLab/GarmentLab/issues/9) 也报告删除block导致tensor simulationView失效；该issue没有回复或已验证补丁，不能当作官方解决方案。
2. **再次抓取**：`PreparedRegion.used` 与 `choose_unused_region` 当前只允许未使用区域。正式recovery若重抓下摆，必须增加该槽安全复用：关闭状态重新对齐当前材料，清理activation记录，验证启用跳变和释放后状态。不能仅把used改回False。
3. **独立reset**：恢复衣物位置/速度、机器人状态、附件禁用状态、used/holding/phase及随机数状态。现导出Backend的reset只robot_reset、settle、施加difficulty，不足以证明布料恢复。连续10次reset/rollout中核对初态可复现和无前回合残留。
4. **统一坐标与yaw**：现hem_plan使用world x/y，Backend导出版本又没有接入yaw。三档若随机旋转衣物，固定世界折线和固定夹爪方向不能直接推广。用衣物规范坐标定义折线与材料对应点，再变换到世界；需要yaw则在公共接口真正接入并验证，未接入就明确限制实验范围，禁止悄悄忽略非零yaw。
5. **预算**：先保留密集路径验证几何，再用公开waypoint表达实际必要阶段；普通servo插值留在Backend。所有改变目标的expert决策和recovery都计数。≤12要求针对主流程+实际recovery总和；不能把整条折叠轨迹塞进一个CLOSE，也不能把H=4的chunk当成单动作。

## 6. 完成Stage 4的顺序

单次释放保持成功 → 独立开发重复 → 整合Backend/安全重抓/动作预算 → 固定三档与30张初态截图 → 验证评价能拒绝未折叠、整体搬移、回弹样例并冻结阈值 → 每档至少5条正式成功，保存全部尝试和拒绝率分母 → 合并完成10次reset/rollout与接口隔离检查 → Day5。

不要把位置到达、流程passed、附件仍启用的折叠形状或仅越线比例视为成功。冻结评价应同时覆盖释放状态、对应材料对齐、两半投影重叠及固定时刻的保持；数值阈值应在开发成功/失败样例上确定，本轮没有凭空指定正式阈值。

## 7. 暂不推荐的路线

- 重启180°翻腕、增益/惯量/迭代数扫描。
- 重跑已经失败的三阶段102动作或当前单锚点对照。
- 因官方demo“看起来折了”而保留最后附件或缩短释放后测量。
- 立刻迁移DexGarmentLab：作者在 [issue #7](https://github.com/GarmentLab/GarmentLab/issues/7#issuecomment-2878550405) 指向基于Isaac Sim 4.5的双灵巧手后续项目，但这不是当前Franka Stage 4的即插即用修复。

本轮结论：优先验证已经准备好的终段支撑放置候选；把官方末次未释放的语义差异作为评估边界明确记录。尚无证据承诺这一候选必然修复回弹，但它是当前证据最充分、改动最小的下一步。
