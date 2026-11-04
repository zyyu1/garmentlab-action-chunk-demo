# D2-E 步骤 2：支撑面与摩擦配置核查

日期：2026-11-04。**离线核查，没有启动新 episode，没有修改物理参数。** 数据来源为 D2-A 场景实际读回、D2-C 已保存轨迹/几何和现有源码。目标：先确定布料实际承托在哪里、材料绑定到哪里，再决定是否需要新增观测实验。

## 0. 结论摘要

1. **唯一与布料存在有效碰撞候选的表面是默认地面** `/World/defaultGroundPlane/GroundPlane/CollisionPlane`：z=0、水平、50 m 平面、collision enabled。
2. **室内地面 collider 已禁用**；它不是支撑面。
3. **三个附件块碰撞体存在且释放后仍保留，但与布料、机器人、刚体均被碰撞组过滤，且与地面加了 FilteredPairs**；它们不能承托或碰撞布料。
4. **机器人手/指与布料也被碰撞组过滤**；接触记录器只覆盖机器人刚体，不能用于布料—地面接触。
5. **布料材料绑定在粒子系统上**：`/World/Garment/particleSystem -> /World/Garment/particleMaterial`；粒子材料 `friction=0.3`、**`particleFrictionScale=0.0`**。布料 mesh 本身没有直接物理材质绑定。
6. **默认地面没有直接物理材质绑定**。Isaac 的 `add_default_ground_plane` 创建了 0.5/0.5/0.8 的材质，但 `GroundPlane` 的应用分支被 `physics_material is None` 守卫挡住；读回确认 CollisionPlane `materials=[]`。因此 0.5/0.5/0.8 不能当作实际生效值。
7. **几何证据：** 布料最低点约 **9.876 mm**，高于地面约 **9.876 mm**，比 `particleContactOffset=10 mm` 低约 **0.123–0.124 mm**。这只是几何关系，不是接触力/冲量证据。
8. **当前不选择修正。** 支撑/过滤拓扑已足够明确；有效摩擦仍无法由读回确定，需要后续单变量敏感性对照。是否补一次纯读回观测见 §6。

## 1. 证据等级

| 标记 | 含义 |
|---|---|
| **C** | 代码/配置设置值：源码或配置明确写出，但不等于运行时生效 |
| **R** | 场景读回值：D2-A 在同一构造场景中实际读回，未运行 episode |
| **D** | 由 D2-C 已保存轨迹/几何推导 |
| **U** | 未能确认，或“有效值”无法由现有读回确定 |

D2-A 读回使用与 D1-120/D2-C 相同的场景构造、粒子尺寸/接触偏移/摩擦覆盖；D2-C 只改变末次释放顺序，不改变场景构建。

## 2. 核查表（对象／prim）

### 2.1 布料与粒子材料

| 对象／prim | 碰撞状态 | 世界位置／顶面 | 材料绑定 | 摩擦相关读回值 | 待确认项 |
|---|---|---|---|---|---|
| 布料 `/World/Garment/garment/mesh` | particle cloth：`PhysxParticleClothAPI`、`PhysxParticleAPI`、`PhysxAutoParticleClothAPI`；`selfCollision=true`、`selfCollisionFilter=true`；无 rigid CollisionAPI **[R]** | 初始 x[-0.1959,0.2449] y[-0.6712,-0.2304] z≈0.009900 m；释放前 x[-0.1922,0.0321] y[-0.6702,-0.2531] z[0.009877,0.072324] m；正式窗口 z[0.009876,0.069983] m **[D]** | mesh `materials=[]`；粒子系统 `material:binding:physics -> /World/Garment/particleMaterial` **[R]** | 粒子材料 `friction=0.3000000119`、`particleFrictionScale=0.0`、`damping=0.0`、`adhesion/cohesion=0` **[R]** | 布料—地面有效摩擦；`particleFrictionScale=0` 的 PhysX 实际语义 **[U]**；无布料—附件块或布料—机器人碰撞（过滤）**[C]** |
| 粒子系统 `/World/Garment/particleSystem` | `particleSystemEnabled=true`、`nonParticleCollisionEnabled=true`、`globalSelfCollisionEnabled=true`、`enableCCD=true` **[R]** | 附着于布料，无独立世界变换 | 绑定 `/World/Garment/particleMaterial`（读回有两条关系，同一目标）**[R]** | 通过粒子材料：`friction=0.3`、`particleFrictionScale=0.0` **[R]** | `solver_position_iteration_count` 读取报错；代码值 16 **[C/U]**；`get_non_particle_collision_enabled` 方法缺失，但属性为 true **[R]** |
| 粒子材料 `/World/Garment/particleMaterial` | 非碰撞体 | 不适用 | 由粒子系统绑定；mesh 无直接绑定 **[R]** | `friction=0.3000000119`；`particleFrictionScale=0.0`；`damping=0.0`；`adhesion/cohesion/adhesionOffsetScale=0.0`；`cflCoefficient=1.0`；`density=0.0` **[R]** | `particleFrictionScale=0` 后的有效摩擦系数无法直接读回 **[U]** |
| 布料自碰撞 | `selfCollision=true`、`selfCollisionFilter=true`、`particleGroup=0` **[R]** | 随布料 | 粒子材料 **[R]** | 同上 **[R]** | 自接触力不可观测；不是外部支撑 |

### 2.2 地面与室内地面

| 对象／prim | 碰撞状态 | 世界位置／顶面 | 材料绑定 | 摩擦相关读回值 | 待确认项 |
|---|---|---|---|---|---|
| 默认地面 `/World/defaultGroundPlane/GroundPlane/CollisionPlane` | CollisionAPI `enabled=true`；type `Plane` **[R]**；`contactOffset=-Infinity`、`restOffset=-Infinity`（PhysX 默认，未显式设置）**[R]** | **z=0 m、水平 Z 平面、size=50 m [C]**；实际 world transform/size 未在已有读回中保存 **[U]**；若 50 m 代码尺寸成立，覆盖布料 x/y 范围（余量 >24 m）**[D/U]** | CollisionPlane `materials=[]`：**无直接物理材质绑定 [R]**；`add_default_ground_plane` 创建 `/World/Physics_Materials/physics_material`（static 0.5 / dynamic 0.5 / restitution 0.8）**[C]**，但 `GroundPlane` 的应用分支被 `physics_material is None` 守卫挡住 **[C]**；祖先绑定未捕获 **[U]** | 没有显式地面摩擦读回；**0.5/0.5/0.8 未确认绑定/生效 [U]**；不能把该刚体值当作布料有效摩擦 | 祖先/地面材质绑定；精确 world transform/size；布料—地面有效摩擦 **[U]** |
| 默认地面材质 prim `/World/Physics_Materials/physics_material` | 非碰撞体 | 不适用 | 由 `add_default_ground_plane` 创建并传给 `GroundPlane`；读回未捕获该 prim，CollisionPlane 无直接绑定 **[C/U]** | `static_friction=0.5`、`dynamic_friction=0.5`、`restitution=0.8` **[C]**；运行时数值/绑定 **[U]** | prim 是否存在、数值是否保留、是否绑定 **[U]** |
| 室内地面 `/World/Room/room/FlatGrid/GroundPlane/CollisionPlane` | **CollisionAPI `enabled=false`**，由 `room_collision_control.py` 禁用 **[R]** | room pos [0,0,0]、ori [0,0,0]、scale [1,1,1] **[C]**；顶面高度未读 **[U]**；已禁用 | `materials=[]` **[R]** | 无显式材料读回；禁用状态下不适用 | 不需要作为支撑；不要在没有登记的情况下重新启用 |

### 2.3 附件块与机器人

| 对象／prim | 碰撞状态 | 世界位置／顶面 | 材料绑定 | 摩擦相关读回值 | 待确认项 |
|---|---|---|---|---|---|
| 附件块 A（right sleeve fold）`/World/Attachment/attach/block` | CollisionAPI `enabled=true`；Cube **[R]**；属于 `/World/attach_group`；与 garment、robot、rigid **过滤 [C]**；FilteredPairsAPI 将默认地面加入过滤 **[C]**，构造函数会验证 block-ground 过滤 **[C，错则中止]** | 初始中心 [0.2,-0.45,0.08] m、边长 0.03 m、顶面 z=0.095 m **[D/C]**；释放时近似中心 [-0.1743,-0.4723,0.0299] m、顶面 z≈0.0449 m **[D/U 精确值]** | `physics:physics_material_1` **[R]**；视觉材质另绑 **[R]** | 刚体默认 static=0.2、dynamic=1.0、restitution=0.0 **[C]**；运行时数值 **[U]**；**因碰撞过滤，不能作为布料有效摩擦** | 精确 build/release/post-release world transform；材质数值；过滤对运行时读回 **[U]**；释放后块仍存在 **[C]** |
| 附件块 B（left sleeve，未用）`/World/Attachment/attach_1/block` | `enabled=true`；Cube **[R]**；同样组过滤和 ground FilteredPairs **[C]** | 初始中心 [-0.2,-0.45,0.08] m、边长 0.03 m、顶面 z=0.095 m **[D/C]**；本 episode 未抓取，精确 pose **[U]** | `physics_material_2` **[R]**；视觉材质 **[R]** | 刚体默认 0.2/1.0/0.0 **[C/U]**；不是布料有效摩擦 | 精确 pose、材质数值 **[U]**；释放后仍存在 **[C]** |
| 附件块 C（bottom hem recovery）`/World/Attachment/attach_2/block` | `enabled=true`；Cube **[R]**；同样组过滤和 ground FilteredPairs **[C]** | 初始中心 [0,-0.65,0.08] m、边长 0.03 m、顶面 z=0.095 m **[D/C]**；释放时近似中心 [0.0476,-0.6417,0.0433] m、顶面 z≈0.0583 m **[D/U 精确值]** | `physics_material_3` **[R]**；视觉材质 **[R]** | 刚体默认 0.2/1.0/0.0 **[C/U]**；不是布料有效摩擦 | 精确 build/release/post-release transform；材质数值；过滤对运行时读回 **[U]**；释放后仍存在 **[C]** |
| 机器人碰撞体 `/World/Franka/panda_*/geometry/*`（12 个） | 7 个臂 link、hand、两指均 `enabled=true` **[R]**；臂 link contactOffset=0.02 / restOffset=0；finger 为默认 -Infinity **[R]** | 动态，不是支撑面 | 所有机器人碰撞体 `materials=[]` **[R]**；PhysX 默认材质 | 没有显式机器人摩擦读回；不是布料有效摩擦 | 运行时 robot-garment 过滤对读回 **[C/U]**；0 contact events 不能证明无布料接触 |

## 3. 可能承托布料的表面

| 表面 | 与布料有有效碰撞？ | 几何 | 判断 |
|---|---|---|---|
| 默认地面 `/World/defaultGroundPlane/.../CollisionPlane` | **是（唯一候选）** | z=0、50 m 平面；布料 z_min≈0.009876 m；覆盖布料 x/y | **最可能的唯一外部支撑**；但只有几何接近证据，没有接触力 |
| 室内地面 `/World/Room/.../CollisionPlane` | 否；collision disabled | room [0,0,0]，顶面未读 | 不是支撑 |
| 附件块 `/World/Attachment/attach*` | 否；garment/robot/rigid 组过滤 + ground FilteredPairs | 3 cm 立方；初始顶面 0.095 m；释放时约 0.0449/0.0583 m；未用左块 0.095 m | 不能承托或碰撞布料；释放后仍存在 |
| 机器人手/指 | 否；robot-garment 组过滤 | finger contact offset 默认；hand/link 0.02 m | 不能承托；接触记录器只覆盖机器人刚体 |
| 布料自碰撞 | 仅自碰撞 | 441 粒子；selfCollision=true | 不是外部支撑 |
| 附件约束 | 释放前保持布料；释放后 `enabled=false` | PhysxAutoAttachment | 不是碰撞体/支撑面 |

## 4. 高度、穿透与接触证据

| 量 | 值 | 来源/说明 |
|---|---:|---|
| 地面顶面 | z=0 m | 代码设置；精确读回 **[U]** |
| 粒子接触偏移 | 0.010 m | `garmentlab_backend.py` 显式设置；读回 0.0099999998 **[C/R]** |
| 布料最低点（初始） | 0.00989996 m | **[D]** |
| 布料最低点（释放前） | 0.00987676 m | **[D]** |
| 布料最低点（preopen 末态） | 0.00987682 m | **[D]** |
| 布料最低点（正式窗口） | 0.00987584 m | **[D]** |
| 布料最低点距地面 | 9.876 mm | 几何计算 **[D]** |
| 布料最低点相对 particleContactOffset | **低约 0.123–0.124 mm** | 几何计算 **[D]**；**不是穿透力/接触力** |

布料最低点始终在 z≈9.876 mm，地面 z=0；没有地面穿透（z_min>0），但低于 10 mm 粒子接触偏移约 0.123–0.124 mm。这个量只能说明布料处于地面接触偏移附近，不能说明存在接触力、法向力或摩擦冲量。

## 5. 代码设置、场景读回与有效值

| 参数 | 代码设置 **[C]** | 场景读回 **[R]** | 有效值判断 |
|---|---|---|---|
| 布料摩擦 `friction` | `GarmentConfig.friction=0.3` | 粒子材料 0.3000000119 | 材质属性已读回；有效摩擦仍取决于粒子接触模型 |
| `particleFrictionScale` | `a5_recovery_diag.py:243` 设为 0.0 | 0.0 | **显式生效的材质属性**；其物理效果未测量 |
| 粒子接触偏移 | `garmentlab_backend.py` 设 0.01 | 0.0099999998 | 已读回 |
| `nonParticleCollisionEnabled` | 默认 true | 属性 true；方法缺失 | 属性层面为 true |
| 自碰撞 / CCD | 默认 true / true | true / true | 已读回 |
| 地面高度/尺寸 | z=0、size=50 m | 未保存 transform/size | 代码值，精确读回 **[U]** |
| 地面默认材质 | 0.5/0.5/0.8 | CollisionPlane `materials=[]` | **未绑定/未确认生效 [U]** |
| 附件块尺寸/质量 | 0.03 m、mass 1000、visible=false | 未保存 size/mass | 代码值；精确读回 **[U]** |
| 附件块材质 | 刚体默认 0.2/1.0/0.0 | 绑定 physics_material_1/2/3 | 绑定已读回；数值/有效性 **[U]**；且与布料碰撞被过滤 |
| 地面/附件块过滤 | ground FilteredPairs；组过滤 | 未保存 pair 列表 | 构造函数验证 block-ground；组过滤仅代码 **[C/U]** |
| 室内地面 | 禁用 | enabled=false | 已读回，确定禁用 |
| solver position iterations | 16 | 读取报错 | **[C/U]** |

**参数来源（显式／默认／继承）：**

| 参数 | 值 | 来源类型 | 位置/说明 |
|---|---|---|---|
| 布料 `friction` | 0.3 | **显式** | `GarmentConfig.friction=0.3` |
| `particleFrictionScale` | 0.0 | **显式** | `a5_recovery_diag.py:243` monkeypatch |
| `particleContactOffset` | 0.01 m | **显式** | `garmentlab_backend.py:131` |
| 地面 z / size | 0 m / 50 m | **默认** | `add_default_ground_plane` 默认参数；实际变换 **[U]** |
| 地面 `physics_material` 0.5/0.5/0.8 | 创建但未绑定 | **默认** | Isaac 默认材质；`GroundPlane` 应用守卫导致未绑定 **[R/U]** |
| 地面 contact/rest offset | -Infinity | **默认** | PhysX 默认，未显式设置 **[R]** |
| 附件块尺寸 / mass | 0.03 m / 1000 | **显式** | `Control.py:48`（尺寸）；mass 同处 |
| 附件块材质 0.2/1.0/0.0 | 绑定 `physics_material_1/2/3` | **默认** | Isaac `DynamicCuboid` 默认材质；数值运行时 **[U]** |
| 附件块—地面过滤 | ground 加入 FilteredPairs | **显式** | `square_proxy_ground_control.py:20-31` |
| robot/garment/attach 碰撞组过滤 | 组间互斥 | **显式** | `Control.py:139-150` |
| 室内地面禁用 | collision=false | **显式** | `room_collision_control.py` |
| 布料材质链 | particleSystem → particleMaterial | **继承** | mesh 无直接绑定；粒子系统绑定 **[R]** |

**关键区分：**

- `particleMaterial` 的 0.3/0.0 是布料粒子材质的实际绑定属性；`0.0` 不是“材质未绑定”。
- 附件块的 0.2/1.0 是 **刚体** 材质默认值；布料与附件块被碰撞组过滤，不能用它解释布料摩擦。
- 地面的 0.5/0.5/0.8 只存在于代码创建路径，CollisionPlane 没有直接绑定；不能把它当作布料有效摩擦。
- 布料网格没有直接 physics material；材质继承链是 **粒子系统 → particleMaterial**，不是 mesh。

## 6. 是否需要步骤 3 的运行时读回

**不需要为了建立支撑/过滤拓扑再跑完整 episode。** 现有证据已足够确定：

- 只有默认地面与布料存在有效碰撞候选；
- 室内地面禁用；
- 附件块/机器人与布料过滤；
- 布料材质绑定在粒子系统。

仍无法确认、但属于低影响或读回不能解决的项目：

1. 地面/附件块的精确 world transform、尺寸和祖先材质绑定；
2. `physics_material`/`physics_material_1/2/3` 的运行时数值；
3. robot-garment/attach 和 block-ground 的运行时 FilteredPairs 完整列表；
4. `solver_position_iteration_count` 的有效值；
5. 附件块精确的 build/release/post-release pose（本报告用动作/材料目标推导，非读回）。

其中 **有效布料—地面摩擦不能由读回确定**：即使补读回，仍只能知道材质属性和绑定，不知道 `particleFrictionScale=0` 的实际摩擦效果。因此下一步若要改变摩擦，必须在步骤 5 做单变量敏感性对照；步骤 4 可先离线复用 D2-C/D1 轨迹检查持续滑移特征。

如果团队要求表内所有“**[U]**”都变成读回值，可登记一次**纯读回观测实验**（不修改物理参数，只跑 4202 single），但这不是选择修正的前置条件。**当前不选择修正。**

### 6.1 下一候选的基线约束

基线/对照索引见 [baseline_index.md](baseline_index.md)。

- 下一候选默认从 **RC2 原流程**派生；**不默认保留 120 步等待，也不默认保留 D2-C 释放顺序**。
- D1-120 和 D2-C 都是诊断改动，不是中性基线：D1 改变了等待时序，D2-C 改变了释放顺序。若保留其诊断记录，必须先核对它们没有改变控制/目标；不能把 D2-C 的 10 步 preopen 或 D1 的 120 步等待直接带入新候选。
- 新候选登记时必须记录父 RC2 版本、manifest/config、初态哈希和独立输出目录；4202 single 通过前不重跑完整七例。
- 步骤4已离线完成：[持续滑移报告](../D2_E_STEP4_SLIP_20261104/review.md)；步骤5决定为 `particleFrictionScale 0.0→1.0` 敏感性对照，见 [预登记草案](../D2_E_STEP4_SLIP_20261104/step5_decision.md)。

## 7. 源码位置

| 设置 | 位置 |
|---|---|
| 布料接触偏移 0.01 | `garmentlab-action-chunk-demo/backends/garmentlab_backend.py:131` |
| `particleFrictionScale=0` | `a5-rc2-d2c-release-order/app/a5_recovery_diag.py:243` |
| 附件块尺寸 0.03 m | `day4/upstream/current/Env/env/Control.py:48` |
| 碰撞组过滤 robot/garment/attach | `day4/upstream/current/Env/env/Control.py:139-150` |
| 释放后保留 block/constraint | `a5-rc2-d2c-release-order/app/multi_prepared_grasp_control.py:116-123` |
| 附件块—地面 FilteredPairs | `a5-rc2-d2c-release-order/app/square_proxy_ground_control.py:20-31` |
| 室内地面禁用 | `a5-rc2-d2c-release-order/app/room_collision_control.py` |
| 默认地面材质 0.5/0.5/0.8 与 `physics_material is None` 守卫 | Isaac `omni.isaac.core/.../objects/ground_plane.py`、`scenes/scene.py:230-237` |
| 附件块刚体默认材质 0.2/1.0/0.0 | Isaac `omni.isaac.core/.../objects/cuboid.py:217-222` |

## 8. 产物与来源

- [support_material_audit.json](support_material_audit.json)：结构化核查表、候选支撑面、几何事实、未确认项
- [support_material_table.csv](support_material_table.csv)：同表 CSV
- [build_audit.py](build_audit.py)：从已保存证据生成上述文件，不启动仿真
- 原始读回：[D2-A 报告](../D2_A_B_SCENE_CONTACT_20261104/review.md)、[d2_a_scene_readback.json](../D2_A_B_SCENE_CONTACT_20261104/d2_a_scene_readback.json)、[d2_a_scene_summary.json](../D2_A_B_SCENE_CONTACT_20261104/d2_a_scene_summary.json)
- 轨迹/几何：[D2-D 对照](../D2_D_COMPARE_20261104/review.md)、D2-C 运行 `day4-a5-rc2-d2c-release-order-20261104-090032-412133`
- 源码：`garmentlab-action-chunk-demo/backends/garmentlab_backend.py`、`a5-rc2-d2c-release-order/app/a5_recovery_diag.py`、`multi_prepared_grasp_control.py`、`square_proxy_ground_control.py`、`room_collision_control.py`，以及 Isaac `GroundPlane/scene.py`、`cuboid.py` 默认值
