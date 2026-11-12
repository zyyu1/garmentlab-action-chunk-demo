# A1：b-right-dev-v2 开发覆盖预检（2026-11-02，仅离线）

本报告对应 A1“固定实验版本与预检”。只做本地只读核对并修正一处登记描述；**未启动仿真、未生成或运行任何 held-out、未产生正式 Stage 4 成功**。正式成功仍为 0。

## 1. 结论

- `stage4_a1_right_v2_preflight.py` 共 48 项检查，**48/48 通过**（输出见 `preflight_stdout.txt`，结构化结果见 `preflight.json`）。
- 发现并修正一处**配置描述与实际采样时序不一致**，登记为 v2.1；只改描述字段，runner 行为、21 项底层代码和 12 动作协议均未变。
- B/C 的新增文件不在 21/23 项身份中，登记 runner 未导入它们；B/C 的离线交付不改变 A2 将要运行的代码身份。
- 初态 registry 本地不存在，符合预期；A2 首次生成初态时在远端创建并登记。
- 远端部署尚未核对；A2 上传修正后的 4 个文件后，必须先通过远端 manifest 核对，再启动批次。

## 2. 发现与修正

原 `stage4-b-right-dev-v2.json` 的 `sampling` 字段写的是：

```
OPEN + 30 release ticks + settle(180 for perturbed, 240 for crumpled); final.npz only
```

已登记 runner 的实际时序（`day4-recovery-fold-episode.py`）：

| 位置 | 代码 | 含义 |
|---|---|---|
| 第 274–275 行 | `rec_release` → `b._settle(240)` | recovery 展开后的 settle，两档相同；不是 fold 终态 |
| 第 343–345 行 | `fold_release` → `for _ in range(30)` | fold OPEN 后 30 个 release tick |
| 第 346 行 | `b._settle(180)` | **两档共用的 fold 终态 settle** |

初态生成侧 `day4-square-initial-stripfold.py` 才使用 `case['settle_steps']`（perturbed 180 / crumpled 240），发生在 episode 之前。因此原字段把“初态 settle / recovery settle”误写成了“release 后 settle”。

修正后字段：

```
OPEN + 30 release ticks + settle(180) for both levels; final.npz only;
initial-state settle 180 (perturbed) / 240 (crumpled) occurs before the fold episode
```

同时增加 `revision: v2.1`、`revised_utc`、`revision_note`。**这是登记版本变更，不是行为变更**；runner、目标、评价器和动作预算均未改。

| 文件 | 修正前 SHA256 | 修正后 SHA256 |
|---|---|---|
| `stage4-b-right-dev-v2.json` | `adf4c9a834f4aa407ed1bb393da30622eff6742aadb1486d25309335c477d4c1` | `91c0fe7f12cf28cdab1a62d4d1a4b9a63c2418857744f0b0f7711b7cf095bff5` |
| `square-recovery-fold-right-v2-files.json` | `2fff0bf9335ebf079921577aee4ebe312c9796e39f3e3fcc0087d832575392fd` | `c3e34c9149d75c56932873b4705ee996b808f61348ca0e700d3d49a505deff97` |

修正前的配置未参与任何运行；旧哈希保留在此表用于追溯。21 项底层身份、入口、批次驱动、初态 manifest 均未变。

## 3. 身份核对

### 3.1 23 项变体身份

- manifest 条目数 23；集合严格等于 21 项底层 + `run-recovery-fold-right-v2.sh` + `stage4-b-right-dev-v2.json`。
- 23 项全部能在本地解析；逐项匹配原始字节或 LF 归一化字节。匹配模式：raw 9 项、LF 14 项（Windows 检出与远端 LF 的已知差异，不是内容变化）。
- `stage4-b-right-dev-v2.json` 的 manifest 条目等于修正后的配置哈希。
- `square-recovery-fold-files.json` 的哈希等于配置中的 `base_manifest_sha256`（`cb947b85…`）。

### 3.2 21 项底层身份

- 21 项全部在本地解析并匹配（raw 7 项、LF 14 项），无缺失、无 mismatch。
- 冻结的 runner `day4-recovery-fold-episode.py` 原始哈希为 `ddad4116…`；入口 `run-recovery-fold-episode.sh` 为 `41026c91…`；二者与 base manifest 一致。
- `strip_prepared_control.py`、`multi_prepared_grasp_control.py`、`square_start.py`、backend/schema、USD 等均在 21 项内且匹配。

### 3.3 入口与批次驱动

| 文件 | SHA256 | 状态 |
|---|---|---|
| `run-recovery-fold-right-v2.sh` | `3822bd98d3d05bc6cba3880ba756f3a438a6985b6abc19c19259a67b47091af3` | 未变 |
| `run-stage4-b-right-dev-v2-batch.sh` | `d4c0016202949a45ec6ff8a4edca746581f95832c5d528534c1be6f144231142` | 未变 |
| `square-recovery-fold-files.json` | `cb947b85c4d5acdaf2028cfcbde8eb3743158d3868e9ca082e85994beadb73b1` | 未变 |
| `square-initial-stripfold-files.json` | `70b1793b5a87f69e9a4cbde5f6b40b047120eed798bdd895dee27e33072477f0` | 未变 |

入口的 registry-only、初态哈希复核、base manifest 断言、right 与 12 动作断言均在源码中确认；批次驱动的 `registry_append` / `registry_lookup` / `already_done` / `attempts.jsonl` 流程和 `RECOVERY_FOLD_EXECUTION=single` 均确认。

## 4. Seed 矩阵与初态

`stage4-b-right-dev-v2.json` 登记 18 个开发 seed：

| 档 | seed | 数量 | 初态 settle | 折条 | 折叠 |
|---|---|---:|---:|---|---|
| perturbed | 4201–4209 | 9 | 180 | bottom，宽度 0.161505–0.179284 | right single |
| crumpled | 4301–4309 | 9 | 240 | left，宽度 0.20 | right single |

核对结果：

- `development_cases` 与 4201–4209 / 4301–4309 完全一致；`attempt_order` 与固定顺序一致。
- 与 held-out 4210–4229 / 4310–4329 无交集。
- `square-initial-plan.json` 共 90 条；18 个 A2/A3 seed 均有唯一条目，level、settle、折条边和宽度与登记一致。
- 初态 manifest 的 23 项全部匹配；plan 的 LF 哈希为 `32e61d57…`；初态 runner 接受 4200–4229 / 4300–4329；初态脚本哈希为 `178ab10c…`。
- 本地 `stage4-b-right-dev-v2-initials.json` 不存在；这是预期的。A2 的批次驱动会在首次生成初态后原子追加 `result.json` 与 `initial_geometry.npz` 的哈希，入口在每次折叠前复核。

## 5. B/C 隔离

- 21/23 项身份中没有任何 B 或 C 文件；`episode_evidence.py`、`stage4_success_v1.py`、`stage4-success-v1.json`、`day4-c-*` 均不在 manifest。
- 登记 runner 源码不含 `episode_evidence`、`stage4_success_v1`、`day4-c-`、`success_trace` 引用；其 import 仍全部指向 21 项底层模块。
- 因此 B 的成功判据层和 C 的采集层是独立交付；A2/A3 不会因它们存在而改变已登记的 12 动作轨迹身份。A4 若要按 B 判据评价，仍需明确 B v1 的 331 帧协议不在 A2/A3 采样中（见 §7）。

## 6. A2 交接

A2 必须按以下顺序开始，不得跳过远端核对：

1. **上传修正后的 4 个 v2 文件**（按原字节，不做行尾转换；config 为 LF、manifest 为 CRLF）：
   `run-recovery-fold-right-v2.sh`、`stage4-b-right-dev-v2.json`、`square-recovery-fold-right-v2-files.json`、`run-stage4-b-right-dev-v2-batch.sh`。
2. **远端核对**：使用 `2026-11-02-GarmentLab日报-Stage4-B项right扩展计划.md` §4 的 heredoc；期望：
   - `V2_MANIFEST_BAD [] 23`
   - `square-recovery-fold-right-v2-files.json` 自哈希 `c3e34c91…`
   - `stage4-b-right-dev-v2.json` `91c0fe7f…`
   - `run-recovery-fold-right-v2.sh` `3822bd98…`
   - `square-recovery-fold-files.json` `cb947b85…`
   四项均 `MATCH True` 才继续。
3. **运行批次**：`bash run-stage4-b-right-dev-v2-batch.sh dev-v2`。批次按 4201→4209、4301→4309 固定顺序；初态先登记后折叠；`passed=false` 记 rejected 并继续；基础设施错误停止整批。
4. **下载**：批次状态目录、`stage4-b-right-dev-v2-initials.json`、18 个初态目录和 18 个折叠结果目录；下载后先跑 `stage4_b_right_dev_v2_audit.py`，再跑 `stage4_b_right_dev_v2_supplement.py`。
5. **禁止**：不跑 arc4、不生成/运行 held-out、不因失败调参重跑替换；失败原样保留。

**同一 tag 重跑注意**：批次驱动会把没有结果目录的 seed 视为未完成并重试；若此前已写入一行基础设施错误记录，重跑会产生同 seed 的重复行，而 `stage4_b_right_dev_v2_audit.py` 会以 `duplicate_attempt_row` 拒绝。发生基础设施错误时应先诊断，再用新 tag 重跑，不要在原 tag 上强行重试。

## 7. 限制与后续

- 本报告只证明本地登记身份与代码/配置/采样描述一致；**远端文件尚未核对**，A2 第一步必须完成。
- 初态 registry 尚未生成；A2/A3 的结果目录必须与 registry 一起下载，不能只用 D 索引中仅含图片的历史副本。
- A2/A3 的采样是 OPEN + 30 release ticks + settle(180) 的 `final.npz`，**不是 B v1 的 0..330 逐物理步 `success_trace.npz`**。A4 可以按 B 的终态几何阈值做“质量通过”分类，但不能据此宣称正式成功或 3.5–5.5 s 稳定窗口。
- C 的退让动作使 L1 为 8 动作、recovery 为 13 动作，超过 B v1 的 12 动作预算；A5 若要接入 C，必须二选一：保留 12 动作正式路径，或按 §0 重新登记动作预算与采样时钟。
- 本报告不改变 right 的采用状态：right 仍是独立开发变体，不是默认折向；正式成功仍为 0。

## 8. 产物与哈希

| 文件 | SHA256 |
|---|---|
| `stage4_a1_right_v2_preflight.py` | `9b777af840612441d3aab6af962a56000ebc7306c4c2cfe32990269e3c9e409b` |
| `preflight.json` | `b3897407a0869aeb44e9da030d7452ffaa7825f35d043d148f5eda2f3abe68ee` |
| `preflight_stdout.txt` | `b6aa853d1de1a5d85f7ae9becc76bad566f000f84d853bbde330aa8c655b72b8` |
| `stage4-b-right-dev-v2.json`（v2.1） | `91c0fe7f12cf28cdab1a62d4d1a4b9a63c2418857744f0b0f7711b7cf095bff5` |
| `square-recovery-fold-right-v2-files.json`（v2.1） | `c3e34c9149d75c56932873b4705ee996b808f61348ca0e700d3d49a505deff97` |
| `run-recovery-fold-right-v2.sh` | `3822bd98d3d05bc6cba3880ba756f3a438a6985b6abc19c19259a67b47091af3` |
| `run-stage4-b-right-dev-v2-batch.sh` | `d4c0016202949a45ec6ff8a4edca746581f95832c5d528534c1be6f144231142` |
| `square-recovery-fold-files.json` | `cb947b85c4d5acdaf2028cfcbde8eb3743158d3868e9ca082e85994beadb73b1` |
| `square-initial-stripfold-files.json` | `70b1793b5a87f69e9a4cbde5f6b40b047120eed798bdd895dee27e33072477f0` |
| `square-initial-plan.json`（LF） | `32e61d575d77eae0943cb2251d10c25b12d7f0d9f8f962ddd96dc1a4d4d2ab85` |

`preflight.json` 含 `generated_utc`，复跑会更新该字段和文件哈希；上表对应 2026-11-02 的最终一次运行。其余冻结文件的哈希不受复跑影响。

复跑预检：

```powershell
cd E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test
python -I stage4_a1_right_v2_preflight.py --out results\STAGE4_A1_PREFLIGHT_20261102\preflight.json
```
