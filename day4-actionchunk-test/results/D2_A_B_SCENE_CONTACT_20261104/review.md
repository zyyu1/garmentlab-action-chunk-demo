# D2-A/B：实际场景、释放速度与接触通道核查

日期：2026-11-04。D2-A 为场景实际读回 + D1 轨迹速度分析；D2-B 为独立小场景已知接触测试。**没有改变释放条件、摩擦或碰撞配置，没有重跑完整 episode。**

## D2-A：实际读回

### 支撑面与碰撞

| 项目 | 实际值 |
|---|---|
| 实际支撑 collider | `/World/defaultGroundPlane/GroundPlane/CollisionPlane`（Plane） |
| collisionEnabled | **true** |
| 室内地面 collider | `/World/Room/room/FlatGrid/GroundPlane/CollisionPlane`，collisionEnabled **false** |
| ground contactOffset / restOffset | `-Infinity` / `-Infinity`（PhysX 默认，未显式设置） |
| ground 物理材质 | **没有显式 physics material binding**；`material:binding:physics` 为空，PhysX 默认材质生效 |
| ground collision/filter group | 没有 `physics:collisionGroup` 或 `physxCollision:filterGroup` 属性可读 |
| 机器人 collider | 7 个 arm link + hand：contactOffset 0.02 m、restOffset 0；finger：contactOffset/restOffset 为默认 `-Infinity` |
| 附件 block（3 个） | 有显式 `physics_material_1/2/3`；contactOffset 0.10 m、restOffset 0；不是支撑面 |

**缺失项：** 支撑地面没有显式物理材质绑定；无法从 USD 读回它的摩擦值，只能知道 PhysX 默认生效。地面/布料没有可读的 filter group；目前只能确认默认 group 0 和 collider 未禁用，不能声称碰撞过滤已被独立验证。`ParticleSystem.solver_position_iteration_count` 的读取方法在该版本报错，属性也未暴露，solver iteration 实际值缺失。

### 布料

| 项目 | 实际值 |
|---|---|
| cloth prim | `/World/Garment/garment/mesh`，441 顶点 |
| applied schemas | `PhysxParticleClothAPI`, `PhysxParticleAPI`, `PhysxAutoParticleClothAPI`, `PhysicsMassAPI` |
| mass | 0.04410 kg（441 × 0.0001） |
| stiffness / damping | stretch 10000、bend 100、shear 100、spring damping 0.2 |
| particle group / self collision | group 0；selfCollision true、selfCollisionFilter true |
| particle system | `/World/Garment/particleSystem`；particleContactOffset **0.01 m**；nonParticleCollisionEnabled **true**；globalSelfCollision true；CCD true |
| particle material | `/World/Garment/particleMaterial`，正确绑定到 particle system |
| particle friction | `friction=0.3000000119`；**`particleFrictionScale=0.0`**；damping 0；adhesion/cohesion 0 |

`particleFrictionScale=0.0` 不是“材质未绑定”：particle material 确实绑定，friction .3 也可读；但 particle friction scale 为 0，且 initial protocol 明确断言这一 profile。它是实际生效的参数，不是未发现的绑定错误。

### 释放前后速度

D1 `release_diag`：附着在 **1944** 变为 `holding=false / attached=false / 三个 slot 全 false`；但 `command_holding=true`、`gripper_state=2` 一直持续到 1953，1954 才变为 `command_holding=false`、`gripper_state=0`。`ungrasp_return` 事件在 1953。**附件关闭（1944）早于 gripper open（1954）10 步。**

| 区间 | 粒子平均速度 mm/s | 质心速度 mm/s | 角速度 deg/s |
|---|---:|---:|---:|
| prehold 最后 5 步 | 0.262 | 0.055 | 0.020 |
| prehold 最后 30 步 | 0.278 | 0.080 | 0.028 |
| 附着解除 1943→1944 | **17.420** | **11.040** | 0.069 |
| 释放后前 5 步 | **35.950**（max 44.251） | **19.418**（max 27.786） | **2.124**（max 4.122） |
| 释放后前 10 步 | 28.555 | 16.753 | 2.586 |
| 释放后前 30 步 | 15.016 | 9.247 | 1.574 |
| 等待前 30 步 | 6.688 | 4.461 | 0.889 |
| 等待最后 30 步 | 1.287 | 1.024 | 0.359 |

- 释放前持布阶段几乎静止（0.26 mm/s 粒子平均、0.055 mm/s 质心）。
- **附着解除的 1 步内速度跳增到 17.4 / 11.0 mm/s，前 5 步达到 36 / 19 mm/s**。这说明释放瞬间确实给整块布一个冲量，而不是单纯的持续接触滑移。
- 速度在等待中衰减，但等待最后 30 步仍有约 1.0 mm/s 的质心滑移；与步骤 8 的持续 ~1 mm/s 一致。
- 布料最低点约 **0.009876 m**，particle contact offset 0.01 m；与布料落在默认地面上一致。不是悬空。

## D2-B：接触通道验证

### 已知 rigid contact

独立小场景：默认地面 + 立方体从 z=0.5 m 落到地面。

| 配置 | 结果 |
|---|---|
| 原 `ContactRecorder`（只在 reset 后给 `/World/Franka/TestCube` 加 API、只订阅 `/World/Franka`） | 立方体落到 z≈0.025 m，实际接触；**callback/event = 0** |
| API 同时加到 cube **和 ground**、且在 `world.reset()` **之前** | **callback/event = 166**；actors 为 cube + ground；接触点最大 impulse 约 **0.0233** |

结论：**rigid contact 通道本身可以工作，但当前 `ContactRecorder` 的配置方式不能通过已知接触验证**；它对 `/World/Franka` 之外的对象不订阅，而且只在 reset 后给机器人 prim 加 API。A5/D1 中的 0 事件不能解释为“无接触”。

### 当前布料—地面接触

独立小场景：`square_cloth_40cm.usda` 粒子布料从 z≈0.20 m 落到默认地面；API 加到 ground、particle system 和 cloth mesh 三者。

- 布料最低点从 **0.18365 m** 降至 **0.00988 m**（particle contact offset 0.01 m），说明布料确实接触/落在支撑面上。
- **callback/event = 0**，`apply_errors=[]`。
- 因此：**当前 PhysX contact-report 通道不支持/未触发粒子布料—地面接触报告**。这不是“无接触”；是观测方法不支持该布料类型。
- 现有 `ContactRecorder` 的 scope 也只包含机器人 rigid body，天然不覆盖 cloth-ground。

**D2-B 结论：** 需要更换布料—地面的观测方法。可用的替代是：
- 逐粒子最低高度/穿透量（相对 ground z=0 与 particle contact offset 0.01）；
- 粒子/质心速度、角运动、分层高度；
- 明确标注“无接触力/冲量”；不得把距离/高度当作接触力。

## 对 D2-C 的含义

- **没有发现“材质未绑定”类错误**：particle material 已绑定，friction .3、particleFrictionScale 0 可读且与 initial protocol 一致。支撑地面没有显式材质，只有 PhysX 默认材质；这是一个缺失的显式配置，但不能直接断定应提高摩擦。
- **释放瞬间有明确的整体速度跳变**（prehold 0.26 mm/s → 前 5 步 36 mm/s），符合“减少释放冲量”的单变量对照前提。
- 但 cloth-ground 接触力/冲量通道不可用；D2-C 若只改释放条件，仍只能用高度/速度/穿透作为比较指标，不能声称接触力变化。
- 按用户规则，当前**不直接提高摩擦**，也不直接把“改变释放动作”当成已定方案；需要先确定一个单变量：
  - 候选 A（推荐优先评估）：只改**附件释放与 gripper open 的顺序/时刻**（当前 1944 断开附件、1954 才报告 gripper open），保持目标/动作数不变，预期降低 1944 的释放冲量；
  - 候选 B：只修**支撑面的显式物理材质绑定**（若团队确认“无显式 ground material”是配置缺陷），但这不是当前证据能直接推出的“提高摩擦”。
- D2-C 尚未运行；原 1 mm / 3 mm 阈值、正式批次暂停、无 held-out 不变。

## 产物

- D2-A 实际读回：[d2_a_scene_summary.json](d2_a_scene_summary.json)、[d2_a_scene_readback.json](d2_a_scene_readback.json)、[d2_a_room_collision_audit.json](d2_a_room_collision_audit.json)、[d2_a_mass_audit.json](d2_a_mass_audit.json)、[d2_a_console.log](d2_a_console.log)
- D2-A 释放速度：[release_kinematics.json](release_kinematics.json)、[release_kinematics.csv](release_kinematics.csv)、[attachment_timing.csv](attachment_timing.csv)、[d2_a_release_speeds.png](d2_a_release_speeds.png)
- D2-B rigid 原始：[d2_b_rigid_contact_report.json](d2_b_rigid_contact_report.json)、[d2_b_rigid_contacts.jsonl](d2_b_rigid_contacts.jsonl)、[d2_b_rigid_console.log](d2_b_rigid_console.log)
- D2-B rigid 修正验证：[d2_b_rigid_contact_variant.json](d2_b_rigid_contact_variant.json)、[d2_b_rigid_variant_console.log](d2_b_rigid_variant_console.log)
- D2-B cloth：[d2_b_cloth_contact_report.json](d2_b_cloth_contact_report.json)、[d2_b_cloth_console.log](d2_b_cloth_console.log)
- 脚本：[d2_a_scene_audit.py](../../d2_a_scene_audit.py)、[d2_a_release_kinematics.py](../../d2_a_release_kinematics.py)、[d2_b_rigid_contact_test.py](../../d2_b_rigid_contact_test.py)、[d2_b_rigid_contact_test2.py](../../d2_b_rigid_contact_test2.py)、[d2_b_cloth_contact_test.py](../../d2_b_cloth_contact_test.py)
