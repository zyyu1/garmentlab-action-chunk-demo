# rc8b 开发初态生成审查（新协议）

**范围：** 按 task-scoped 协议生成开发初态：4100（L1，0.0）、4201/4202（L2，1.0）、4302（L3，1.0）。每 seed 一次、独立保存、不挑选、无自动重试。4100 也重新生成，因为旧结果缺少新协议要求的 `protocol` 块（材料绑定与生成器身份）；新几何与旧初态逐位相同。

## 1. 运行

| seed | 命令 | 结果 |
|---:|---|---|
| 4100 | `bash run-square-initial.sh 4100` | exit 0，`day4-square-initial-20261105-014501-526555` |
| 4201 | `bash run-square-initial-stripfold.sh 4201` | exit 0，`day4-square-initial-stripfold-20261105-014825-318974` |
| 4202 | 同上 4202 | exit 0，`day4-square-initial-stripfold-20261105-015817-115841` |
| 4302 | 同上 4302 | exit 0，`day4-square-initial-stripfold-20261105-020706-026048` |

## 2. 协议字段（每个初态）

| 字段 | 4100 | 4201/4202 | 4302 |
|---|---|---|---|
| `protocol.version` | `stage4-initial-v2-task-scoped` | 同 | 同 |
| `task` | `A_l1_overfold` | `B_nominal` | `B_nominal` |
| `particle_friction_scale_expected` | 0.0 | 1.0 | 1.0 |
| `particle_friction_scale_readback` | 0.0 | 1.0 | 1.0 |
| `material_binding.particle_material` | `/World/Garment/particleMaterial` | 同 | 同 |
| `material_binding.particle_system` | `/World/Garment/particleSystem` | 同 | 同 |
| `generator.script` / hash | `day4-square-initial.py` / 绑定 | `day4-square-initial-stripfold.py` / 绑定 | 同 |
| `generator.files_manifest` / hash | `square-initial-files.json` / 绑定 | `square-initial-stripfold-files.json` / 绑定 | 同 |

`initial_case` 与 `square-initial-plan.json` 的对应行逐字段相同（plan 中包含 1 次）；`initial_geometry.npz` 与 `initial.png` 均存在。

## 3. 任务定义核对

| seed | 初态族 | 折条/宽度 | extent (m) | z_p95 (m) | 旧 extent (m) |
|---:|---|---|---|---|---|
| 4100 | flat | — | 0.4129 × 0.4129 | ~0 | 同值（逐位相同） |
| 4201 | perturbed | bottom 0.1793（范围 0.1615–0.1793） | 0.4283 × 0.2669 | 0.0675 | 0.4286 × 0.2678 |
| 4202 | perturbed | bottom 0.1714 | 0.4213 × 0.2558 | 0.0680 | 0.4206 × 0.2541 |
| 4302 | crumpled | left 0.2000 | 0.2674 × 0.4315 | 0.0693 | 0.2847 × 0.4357 |

- L2 条宽在冻结范围内；L3 为 width 0.20 的 left 折条；两档的 z_p95 都在 ~0.07 m，说明条带仍折起、未摊平。
- **L3 的 x extent 比旧初态窄约 17 mm**（0.285→0.267）。这是 1.0 下重新 settle 的结果，不是生成失败；任务定义只固定折条边与宽度，未固定 extent。已记录该差异，不默认与旧初态相同。
- 4100 的新 `initial_geometry.npz` 的 before/applied/settled 与旧初态逐位相同（max|Δ|=0）；只有 result.json 多了 protocol 元数据，因此哈希变化是预期的。

## 4. 哈希与登记

新初态的 `result.json` / `initial_geometry.npz` 哈希已写入 `a5-candidate.json` 与 `registration.json`；`manifest` 由 `build_manifest.py` 生成。正式 preflight 会用这些哈希和 `protocol.generator` 逐项核对；旧初态（无 protocol）会被拒绝。

## 5. 限制

- 生成只做一次，没有重试或挑选；若七例出现阳性失败，保留失败并停止冻结，不回退旧初态、不沿用 rc8 结果。
- L2/L3 的初态在 1.0 下生成，与 rc8 使用的 0.0-settled 初态不同；两套结果不可混用。
