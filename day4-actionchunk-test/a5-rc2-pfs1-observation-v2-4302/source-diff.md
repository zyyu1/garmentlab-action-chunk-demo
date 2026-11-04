# 源码差异：a5-rc2-pfs1-observation-v2 → 4302 扩展

本扩展**没有修改任何仿真/控制/观测源码**。63 项 manifest 中 61 项与 v2 逐字节相同；差异只存在于两个登记/编排文件。

## 1. manifest 差异

| 类别 | 数量 | 说明 |
|---|---:|---|
| 相同 | 61 | 物理、控制、观测、资产、evaluator、初态 plan 等 |
| 变化 | 2 | `a5-rc2-pfs1-observation-v2.json`、`run-a5-rc2-pfs1-observation-v2.sh` |
| 新增/删除 | 0 | 文件集合与 v2 完全相同 |

`a5_recovery.py`、`a5_capture.py`、`pfs1_observation_v2.py`、`stage4_success_v1.py`、`a5_entry.py`、`a5_l1.py`、`square-initial-plan.json`、`square_cloth_40cm.usda` 等全部未变。因此 4302 与 4202 的结果差异只能来自 seed/初态，不来自候选代码。

## 2. `a5-rc2-pfs1-observation-v2.json`（登记/范围）

- `revision`：`candidate-registered-observation-v2` → `candidate-registered-observation-v2-extension-4302`；
- `status`：`candidate_registered_not_run` → `extension_registered_not_run`；
- 新增 `extension` 块：`id=4302-single`、`scope.seeds=[4302]`、`new_lock=a5-rc2-pfs1-observation-v2-4302-runs`、`changed_files_vs_v2`、`unchanged_manifest_entries_vs_v2=61`；
- `initial` / `subject` 改为 4302 的预登记初态与 `level=crumpled`；
- `physical_invariance`、`observation_revision`、`comparison` 与 v2 同义（新增 `sticking` 检查项）；
- `run`：`seed=4302`、新锁、`retry=false`。

**该 JSON 不被仿真代码读取**（`grep` 全部 py 无引用），只作为登记与 runner 断言输入。

## 3. `run-a5-rc2-pfs1-observation-v2.sh`（编排）

完整 diff 见 [runner-v2-to-4302.diff](runner-v2-to-4302.diff)。变化类别：

| 类别 | v2 | 4302 扩展 |
|---|---|---|
| 远端目录 | `.../a5-rc2-pfs1-observation-v2/app` | `.../a5-rc2-pfs1-observation-v2-4302/app` |
| 默认 seed / 范围断言 | 4202 | 4302（其他 seed/mode 直接 exit 2） |
| 锁/账本 | `a5-rc2-pfs1-observation-v2-runs` | `a5-rc2-pfs1-observation-v2-4302-runs` |
| 重跑开关 | `PFS1_OBS_V2_ALLOW_RERUN` | `PFS1_V2_EXT_ALLOW_RERUN` |
| 预检父 manifest | pfs1 `bad4b59a…` | v2 `d97bf349…` |
| 预检身份逻辑 | 58 项对 base 相同 | 61 项对 v2 相同；2 项必须变化 |
| 预检初态 | 4202 / perturbed | 4302 / crumpled |
| 账本 seed | 4202 | 4302 |
| 运行入口 | `a5_entry.py run --initial … --mode single` | 相同（未改参数、未改采样） |

后处理块（文件完整性、观测语义、材料值 0.3/1.0、contact 能力、ledger）与 v2 相同，只把记录的 seed 改为 4302。

## 4. 未改动的运行语义

- `a5_recovery.py` 仍写 `day4-a5-rc2-pfs1-observation-v2-<timestamp>` 输出前缀（候选版本名不变），journal 目录区分扩展；
- 12 个公开动作、动作目标表达式、call horizon、退让目标、evaluator 与 1 mm / 3 mm 阈值未改；
- 4202 初态与结果不重生、不覆盖；4302 复用原登记初态 `day4-square-initial-stripfold-20261103-094143-137994`。
