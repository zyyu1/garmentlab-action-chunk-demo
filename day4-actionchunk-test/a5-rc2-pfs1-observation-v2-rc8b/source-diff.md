# 源码差异：rc8 → rc8b（初态协议补齐）

文件集合不变（63 项）。相对 rc8 有 **11 项变化、52 项逐字节相同**；rollout 物理逻辑未改，变化集中在初态生成、正式入口绑定与初态协议元数据。

| 文件 | 变化 | 角色 |
|---|---|---|
| `day4-square-initial.py` | L1 初态：保持 pfs=0；新增 `protocol` 块（task/level/seed/expected/readback/binding/generator/generated_utc） | 初态生成 |
| `day4-square-initial-stripfold.py` | L2/L3 初态：pfs **0→1**；断言读回 1.0；新增同结构 `protocol` 块；physics_profile 文案 | 初态生成 |
| `square-initial-files.json` / `square-initial-stripfold-files.json` | 更新生成器与 runner 哈希 | 依赖清单 |
| `stage4_batch_preflight.py` | `initial()` 新增协议校验：version/task/level/seed、expected+readback scale、材料绑定、生成器脚本与 files manifest 哈希；缺失/不符/旧协议直接拒绝 | 正式预检 |
| `run-square-initial.sh` / `run-square-initial-stripfold.sh` | `cd "$(dirname "$0")"`，从候选 app 目录执行，不再读共享根目录旧副本 | 初态入口 |
| `run-stage4-formal-batch.sh` | `cd "$here"`；生成调用 `bash "$here/$runner"`，绑定候选 app | 正式入口 |
| `a5-candidate.json` | 4100/4201/4202/4302 指向本次新初态及哈希 | 登记 |
| `a5-rc2-pfs1-observation-v2.json` | rc8b 协议、初态清单、矩阵、账本 | 登记 |
| `run-a5-rc2-pfs1-observation-v2.sh` | rc8b 七槽编排、初态协议预检、账本 | 编排 |

## 未改

- `a5_recovery.py`、`a5_capture.py`、`a5_entry.py`、`pfs1_observation_v2.py`、`stage4_success_v1.py`、`square-initial-plan.json`、资产与资产哈希。
- 7/12 公开动作、命令、horizon、目标构造、held gate、阈值、评价器。

## 协议语义

- 初态生成、reset、rollout 使用同一任务配置：flat 0.0，perturbed/crumpled 1.0。
- 初态结果自带任务、材料绑定（material + particle system）、scale 读回、生成器身份；正式 preflight 拒旧/拒错，禁止回退。
- 4100 的新初态几何与旧初态逐位相同；L2/L3 新初态在 1.0 下重新 settle，几何可能变化，已在 `results/RC8B_INITIALS_20261105/review.md` 记录。
