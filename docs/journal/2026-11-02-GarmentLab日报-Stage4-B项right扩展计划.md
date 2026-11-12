# Stage 4 right 开发覆盖扩展 b-right-dev-v2（已登记；A1 预检完成，未运行）

日期 2026-11-02。本文件登记并说明 right 边开发覆盖的扩展：在 `b-right-dev-v1` 已验证 4200/4300 两个开发初态的基础上，把剩余全部开发 seed 纳入 right 的 single 表示验证。**没有运行任何仿真；held-out 未生成、未运行；正式批次仍暂停；正式 Stage 4 成功仍为 0。**

## 0. A1 预检完成（2026-11-02，仅离线）

`stage4_a1_right_v2_preflight.py` 的 48 项检查全部通过；未启动仿真、未生成 held-out、未产生正式成功。预检发现并修正一处**描述与实际采样不一致**：v2 配置原写 `settle(180 for perturbed, 240 for crumpled)`，但已登记 runner 对两档都在 fold OPEN 后执行 **30 release ticks + `settle(180)`**；`settle(240)` 只在 recovery 展开后，且 180/240 是初态生成时的 settle。配置已修正为 v2.1（仅描述字段，无行为改动），manifest 同步更新：

| 文件 | 旧哈希 | 新哈希 |
|---|---|---|
| `stage4-b-right-dev-v2.json` | `adf4c9a8…` | `91c0fe7f…` |
| `square-recovery-fold-right-v2-files.json` | `2fff0bf9…` | `c3e34c91…` |

入口 `run-recovery-fold-right-v2.sh`（`3822bd98…`）、批次驱动（`d4c00162…`）、21 项底层身份（`cb947b85…`）、初态生成 manifest（`70b1793b…`）均未变。B/C 新增文件不在 21/23 项身份中，登记 runner 也未导入它们。初态 registry 尚未在本地出现，A2 首次生成初态时在远端创建。

证据：[A1 预检报告](day4-actionchunk-test/results/STAGE4_A1_PREFLIGHT_20261102/review.md)、`preflight.json`、`preflight_stdout.txt`。下一步进入 A2；上传时必须使用修正后的 config/manifest，并在远端复核新哈希。

## 1. 为什么扩、扩到哪

v1 只在每档一个 seed（4200、4300）上验证了 right 的释放后保持，且每次尝试终态逐位可复现。这足以证明"right 在这两个初态上有效"，但不足以说明不是初态特定的巧合。因此按用户决定扩大到**全部剩余开发 seed**，不挑 seed：

| 档 | seed | 数量 | 初态生成 | 折叠 |
|---|---|---:|---|---|
| L2 perturbed | 4201–4209 | 9 | `run-square-initial-stripfold.sh <seed>`（首次运行生成并登记） | right，single |
| L3 crumpled | 4301–4309 | 9 | 同上 | right，single |

合计 18 个初态 + 18 次折叠尝试。**只跑 single**：single/arc4 在 4200/4300 上 12 个公开动作的目标、后端指令与终态顶点已逐位相同，表示等价不需要在每个 seed 上重复；本批不产生任何 H=4 收益结论。

不动的部分：21 项底层代码身份、12 个公开动作、物理、评价器、held gate、采样时序（OPEN + 30 release ticks + settle(180) for both levels；初态生成 settle 180/240 在 episode 之前）、left 的失败记录、默认折向定义。

## 2. 新增文件（已登记；21 项底层代码未改）

| 文件 | 作用 | SHA256（原始字节） |
|---|---|---|
| `stage4-b-right-dev-v2.json` | 变体配置：18 个 seed、single、right 目标参数；A1 v2.1 修正 sampling 描述 | `91c0fe7f12cf28cdab1a62d4d1a4b9a63c2418857744f0b0f7711b7cf095bff5` |
| `run-recovery-fold-right-v2.sh` | 只接受 registry 内初态的入口 | `3822bd98d3d05bc6cba3880ba756f3a438a6985b6abc19c19259a67b47091af3` |
| `square-recovery-fold-right-v2-files.json` | 独立 manifest：21 项底层 + 上述 2 项 = 23 项；A1 刷新 config 条目 | `c3e34c9149d75c56932873b4705ee996b808f61348ca0e700d3d49a505deff97` |
| `run-stage4-b-right-dev-v2-batch.sh` | 远端批次驱动（生成/复用初态、登记、折叠、记账） | `d4c0016202949a45ec6ff8a4edca746581f95832c5d528534c1be6f144231142` |
| 底层身份 | `square-recovery-fold-files.json` | `cb947b85c4d5acdaf2028cfcbde8eb3743158d3868e9ca082e85994beadb73b1` |

本地离线工具（不上传远端、不进入身份）：`stage4_b_right_dev_v2_audit.py`、`test_stage4_b_right_dev_v2_audit.py`（3 项合成数据测试通过）、`stage4_a1_right_v2_preflight.py`（A1 48 项预检通过，哈希 `9b777af8…`）。

## 3. 初态登记规则（本批的信任模型）

v1 把两个初态目录名写死在配置里；扩展批的目录要等生成后才有名字，因此改用**先登记后折叠**：

1. 批次为每个 seed 运行一次 `run-square-initial-stripfold.sh`，从输出取得结果目录；
2. 校验该目录的 `result.json`：`passed=true`、seed 与 level 等于登记值；
3. 计算 `result.json` 与 `initial_geometry.npz` 的 SHA256，追加写入 `<remote-root>/stage4-b-right-dev-v2-initials.json`（只追加，不改旧条目，原子替换写入）；
4. 折叠入口只接受 registry 中出现的目录，并在每次运行前重新核对这两个哈希；内容一变即拒绝运行。

因此初态身份在折叠发生之前就已固定并可复核，批次不能事后替换初态或挑选结果。已登记的 helper 行为已用合成目录离线验证：重复登记幂等、seed 不符拒绝、内容变化拒绝、lookup 与"已完成"判定正确。

## 4. 远端步骤（由用户执行）

**第一步：上传 4 个文件，原样（不做行尾转换）**。A1 修正后 config 为 LF、manifest 为 CRLF；四个文件均按原字节上传，任何行尾转换都会改变登记哈希：

```powershell
scp -P 23636 E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\run-recovery-fold-right-v2.sh E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\stage4-b-right-dev-v2.json E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\square-recovery-fold-right-v2-files.json E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test\run-stage4-b-right-dev-v2-batch.sh <server>:<remote-root>/
```

**第二步：核对身份**：

```bash
cd <remote-root> && <remote-root>/envs/isaac40/bin/python - <<'PY'
import json,hashlib
from pathlib import Path
m=json.loads(Path('square-recovery-fold-right-v2-files.json').read_text())
bad=[]
for n,v in m.items():
    p=Path(n)
    if not p.exists(): bad.append((n,'missing')); continue
    if hashlib.sha256(p.read_bytes()).hexdigest()!=v: bad.append((n,'mismatch'))
print('V2_MANIFEST_BAD',bad,len(m))
for f,want in [('square-recovery-fold-right-v2-files.json','c3e34c91'),
               ('stage4-b-right-dev-v2.json','91c0fe7f'),
               ('run-recovery-fold-right-v2.sh','3822bd98'),
               ('square-recovery-fold-files.json','cb947b85')]:
    h=hashlib.sha256(Path(f).read_bytes()).hexdigest()
    print('SHA',f,h,'MATCH',h.startswith(want))
PY
```

期望 `V2_MANIFEST_BAD [] 23`，四个 `MATCH True`。任何不匹配就停止，不要开批次。

**第三步：跑批次**：

```bash
cd <remote-root> && bash run-stage4-b-right-dev-v2-batch.sh dev-v2
```

- 状态与日志：`<remote-root>/stage4-b-right-dev-v2-dev-v2/`（`batch.log`、`attempts.jsonl`、`init-*.log`、`fold-*.log`）。
- 初态登记：`<remote-root>/stage4-b-right-dev-v2-initials.json`。
- 每个 seed 先确认/生成初态，再跑一次 single 折叠。
- 折叠失败（`passed=false`）只记一行 rejected，继续下一个 seed；**不会自动重试、不会覆盖旧结果**。
- 初态生成失败或缺结果目录视为基础设施错误，整批停止——此时剩余尝试不可比。
- 中断后重跑同一条命令会跳过 `attempts.jsonl` 中已有结果目录的 seed；要强制重跑用新 tag（旧 tag 的目录与记录不动）。

**第四步：下载并汇总**（全部跑完后）：

```powershell
scp -P 23636 -r <server>:<remote-root>/stage4-b-right-dev-v2-dev-v2 <server>:<remote-root>/stage4-b-right-dev-v2-initials.json E:\learning\project\thesis\day4-actionchunk-test\results\
```

```powershell
cd E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test
python -I stage4_b_right_dev_v2_audit.py --results E:\learning\project\thesis\day4-actionchunk-test\results --attempts E:\learning\project\thesis\day4-actionchunk-test\results\stage4-b-right-dev-v2-dev-v2\attempts.jsonl --out E:\learning\project\thesis\day4-actionchunk-test\results\B_RIGHT_DEV_V2_SUMMARY\audit.json
```

审计逐例核对 23 项变体身份、21 项底层身份、12 个动作、held gate，并从 `final.npz` 重算 crossed/extent/z_p95；输出每 seed 的 passed/rejected/error 与缺失 seed 列表，永不把开发 `passed` 升级为正式成功。

## 5. 本批不能支持的说法

- 不能当作每档 20 seeds 的正式结果，也不能计算正式成功率；held-out 集合仍未使用。
- 不能比较 single 与 arc4 的精度或收益：本批只有 single。
- 不能说明更长时间的保持：只有 OPEN 后 30 release ticks + settle(180)（两档相同）的终态，没有独立退让或第二个 retention 样本。
- 不能据此自动把 right 写进任务定义：是否采用 right、是否替换 left，需要按冻结文档 §0/§4.2 另行登记，并对 single/arc4 同时生效。
- 失败与拒绝全部保留在 `attempts.jsonl` 与结果目录中，不挑选、不重试替换。
