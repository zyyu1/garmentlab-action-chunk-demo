# Stage 4 第 7 步：正式批次准备（已登记，未运行）

## 当前 E 交接 · 2026-11-03

正式入口已统一指向 A5 候选，启动前必须校验与该 manifest 绑定的真实开发复验回执。当前没有签发回执。按 [A5 交接清单](STAGE4_A5_E_HANDOFF.md) 运行开发复验；下文旧 left、旧阈值和旧运行命令为历史登记。

> 2026-11-02 工作包 D 更新：批次预检、运行前尝试登记、续跑与不覆盖保护、开发/正式统计分离、30 张初态及 reset 索引见 [D 交付报告](STAGE4_D_OFFLINE_REVIEW.md)。20 项离线测试通过，未运行 held-out。下文历史执行命令现在默认被暂停闸门阻止；A–C 收敛后由 E 冻结与部署。18 个初态的 result/geometry 本地缺失已列入索引。

日期 2026-11-02。本文件按 [冻结文档 §0 的变更规则](STAGE4_TASK_DEFINITION_FREEZE.md) 登记第 7 步的 seed 集合与初态生成改动，并给出远端执行顺序。**本步没有运行任何仿真，正式 Stage 4 成功仍为 0。**

两件事必须先分清：

1. **本文件完整提供的是“批次基础设施”**：60 个 held-out 初态、120 次折叠尝试的驱动脚本、拒绝率口径与汇总工具。
2. **正式成功判据的数值阈值仍未冻结**（冻结文档 §0 明确列为后续步骤）。因此这批数据即使跑完，也只能给出脚本开发门槛 `passed` 与拒绝率，**不能自行变成正式成功**；阈值冻结必须先单独登记。

## 1. 本次登记的改动

| 项目 | 内容 | 理由 |
|---|---|---|
| held-out seed 集合 | L1 `4110–4129`、L2 `4210–4229`、L3 `4310–4329`，每档 20 个 | 冻结文档 §5 要求 20 个/档、与开发集（4100–4109 / 4200–4209 / 4300–4309）不重叠、批次前一次性固定。取各档紧邻的下一段连续区间，在任何结果出现前确定，不能事后重抽。 |
| 初态参数 | 平移 dx、dy 与 yaw 仍是 `default_rng(seed)` 的前三次抽样，范围取自 `square-difficulty.yaml` | 该规则对全部 30 个开发条目逐位复现（容差 1e-15，已用 `stage4_heldout_register.py --check` 验证），因此 held-out 沿用同一规则。 |
| L2 条宽 | `[0.16, 0.18]` 的第 4 次抽样，四舍五入 6 位小数，逐条写入 plan | 开发集 L2 条宽是人工写入值（0.161505–0.179284），无法从 seed 流复现；held-out 改用同一 seed 流的第 4 次抽样，范围不变。这是**已声明的程序选择**，不依赖任何结果。 |
| L3 条宽 | 固定 0.20 | 与开发集一致。 |
| `square-initial-plan.json` | 由 30 条扩展到 90 条（纯追加，开发条目逐条不变） | 生成 held-out 初态的前置条件。 |
| `run-square-initial.sh` | seed 断言 `4100–4109` → `4100–4129` | 原脚本写死开发区间，held-out 无法生成。 |
| `run-square-initial-stripfold.sh` | seed 断言 `4200–4309` → `4200–4229` 或 `4300–4329`；level 映射同步改为 `4200–4229` 为 perturbed | 同上。 |
| 新增工具 | `stage4_heldout_register.py`（登记与自检）、`run-stage4-formal-batch.sh`（远端驱动）、`stage4_formal_report.py`（离线汇总） | 均为批次基础设施；**不进入两份折叠 manifest**，折叠代码身份不变。 |
| `square-initial-files.json` 的三项旧条目 | `square_start.py` `b6a98831`→`d2b47783`；`multi_prepared_grasp_control.py` `3a18f36d`→`579de3d6`；`square-difficulty.yaml` `82ab6771`→`a42fec8a` | 该 manifest 自 6a 起未同步。新值**不是**本地仓库文件哈希（本地这两个 .py 与远端本就不同），而是两份折叠 manifest 与条带初态 manifest 已共同钉住、并在远端逐条核对通过的值。因此这是把 L1 初态生成对齐到当前已部署的栈，不是把未验证版本写进身份清单。代价：L1 开发初态当初用旧依赖生成，held-out 初态用当前依赖，两者初态生成的依赖身份不同（折叠路径不受影响）。 |

新的 LF 归一化 SHA256（manifest 用）：

| 文件 | 原值 | 新值 |
|---|---|---|
| `square-initial-plan.json` | `e2cfaebe597e…`（条带 manifest） | `32e61d575d77eae0943cb2251d10c25b12d7f0d9f8f962ddd96dc1a4d4d2ab85` |
| `run-square-initial.sh` | `9fc648a5d006…` | `b22f848ee995c88b48d550ba83687ee6d804b9a2731fabb054fa143687bc4637` |
| `run-square-initial-stripfold.sh` | `33a4e142ca81…` | `1116550f65b9282c2a0e85f321c9ceb863cf8f1fe152c36bc48e387ebc34b631` |

两份初态 manifest 刷新后的 LF 归一化 SHA256：

| manifest | 新值 |
|---|---|
| `square-initial-files.json` | `bccf3e157d96a53c4afba154194ddb652880f7634bedca912b9b5e4127ec5940` |
| `square-initial-stripfold-files.json` | `70b1793b5a87f69e9a4cbde5f6b40b047120eed798bdd895dee27e33072477f0` |

**发现的既有问题**：`square-initial-files.json` 有 5 项落后于远端（plan、runner 加上述三项依赖），所以 `run-square-initial.sh` 的 preflight 在本次更新前必然失败。2026-11-02 的远端核对已确认：除本次新上传的 3 个文件外，条带 manifest 的全部条目与远端一致，因此那三项依赖可以直接取条带 manifest 的值。这是必须记录在案的版本变更，不是顺手的无关修改。

## 2. 远端更新状态与下一步（由用户执行）

**已完成（2026-11-02）**：4 个文件已转 LF 上传，远端完整 SHA256 与本地一致（plan `32e61d57…`、L1 runner `b22f848e…`、条带 runner `1116550f…`）。远端核对输出确认：条带 manifest 除本次两个新文件外全部条目一致；L1 manifest 有 3 项依赖不匹配（`square_start.py`、`multi_prepared_grasp_control.py`、`square-difficulty.yaml`），已在本地按条带 manifest 的值刷新。

**下一步（两条命令）**：上传刷新后的两份 manifest（LF），然后做一次完整核对。**（2026-11-02 已完成：两份 manifest 上传后无排除项核对通过，`bad` 均为空，哈希 `bccf3e15…` / `70b1793b…`。下面的命令保留为重新核对的入口。初态生成与折叠均未运行。）**

```powershell
cd E:\learning\project\garmentlab-action-chunk-demo\day4-actionchunk-test
python -c "import pathlib; src=pathlib.Path('.'); dst=pathlib.Path('../upload-20261102'); dst.mkdir(exist_ok=True); [ (dst/f).write_bytes((src/f).read_bytes().replace(b'\r\n', b'\n')) for f in ['square-initial-files.json','square-initial-stripfold-files.json'] ]"
scp -P 23636 ..\upload-20261102\square-initial-files.json ..\upload-20261102\square-initial-stripfold-files.json root@connect.nmb2.seetacloud.com:/root/autodl-tmp/
```

```bash
cd /root/autodl-tmp && /root/autodl-tmp/envs/isaac40/bin/python - <<'PY'
import json,hashlib
from pathlib import Path
for mf in ('square-initial-files.json','square-initial-stripfold-files.json'):
    d=json.loads(Path(mf).read_text())
    bad=[]
    for name,digest in d.items():
        p=Path(name) if Path(name).exists() else Path('garmentlab-action-chunk-demo')/name
        if not p.exists(): bad.append((name,'missing')); continue
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest: bad.append((name,'mismatch'))
    print('MANIFEST',mf,'bad',bad)
print('EXPECT_MANIFEST_SHA256',
      hashlib.sha256(Path('square-initial-files.json').read_bytes()).hexdigest(),
      hashlib.sha256(Path('square-initial-stripfold-files.json').read_bytes()).hexdigest())
PY
```

期望：两份 manifest 的 `bad` 都为空，且两个文件哈希分别等于 `bccf3e15…`、`70b1793b…`。若有任何不匹配，停止并贴回输出，不要开始批次。

**可选但建议的桥接核对（任务 A）**：L1 开发初态当初用旧依赖生成，held-out 初态将用当前依赖。若要确认依赖差异不影响初态，可在远端先只生成一次 seed 4100 的初态（`bash run-square-initial.sh 4100`），下载后由我把它与历史 4100 初态的 441 点几何做对比；差异在容差内才继续批次。这一步不改变任何已登记内容，只是补齐可比性证据。

**注意**：不要刷新 manifest 里其它本地与远端内容不同的文件（例如本地这两份 `.py` 的哈希就不是远端值）。本次三项依赖之所以刷新，是因为它们已在两份折叠 manifest 与条带 manifest 中钉住、并在远端逐条核对通过，而不是把仓库当前副本直接写进去。

## 3. 批次矩阵与命令

**当前暂停**：按冻结文档 `b-right-dev-v1` 登记，先用开发 seeds 4200/4300 验证 right 的释放后保持；在此之前不得生成或运行任何一个 held-out 初态（`4110–4129` / `4210–4229` / `4310–4329`）。本节命令仅作为登记在案的批次定义保留，right 变体结论出来后再决定是否启用、以及是否按其登记同步改动。

每档 20 seeds，single 与 arc4 共用同一 seed 列表和同一初态目录：

| 任务 | 档 | seeds | 初态生成 | 折叠 | 尝试数 |
|---|---|---|---:|---|---:|
| A（L1 过折，overhang 0.02） | flat | 4110–4129 | `run-square-initial.sh` | `run-l1-xfold-yaw-aware.sh` | 20×2 |
| B（nominal 20/20） | perturbed | 4210–4229 | `run-square-initial-stripfold.sh` | `run-recovery-fold-episode.sh … left` | 20×2 |
| B（nominal 20/20） | crumpled | 4310–4329 | `run-square-initial-stripfold.sh` | 同上 | 20×2 |

合计 60 个初态、120 次折叠尝试。驱动脚本按 seed 生成/复用初态，再依次跑 single、arc4；折叠失败不中断批次、不覆盖旧结果，**没有结果目录则视为基础设施错误并停止**（其余数据不可比）。

```bash
cd /root/autodl-tmp
bash run-stage4-formal-batch.sh stage4-heldout-seeds.json formal-v1
```

`stage4-heldout-seeds.json` 已在第 2 节的上传列表中；批次状态写 `/root/autodl-tmp/stage4-formal-batch-formal-v1/`：`attempts.jsonl`（每次尝试一行）、`init_dirs.txt`、逐例日志。

## 4. 拒绝率与汇总口径

- 每档拒绝率 = `(rejected + error) / 总尝试`；**空批次报空，不能写成 0%**（依据 [评价与记录工具](day4-actionchunk-test/DAY4_EVALUATION_RECORDING.md)）。
- 本项目里 `rejected` = 有完整 `result.json` 但 `passed=false` 的尝试；`error` = 批次记录里尝试了却没有结果目录的情况。
- 汇总：`python -I stage4_formal_report.py --seeds stage4-heldout-seeds.json --root <下载根目录> --attempts <批次目录>/attempts.jsonl --out <输出>`，按档、按表示分别输出尝试数、通过数、拒绝率、重复尝试与未冻结代码目录。
- 工具不会把 `passed` 升级为正式成功；正式判据见第 5 节。

## 5. 正式成功判据仍未冻结（硬前置）

计划 §5 要求“用开发成功/失败样例冻结 alignment、overlap、success 定义、测量时刻及阈值”。目前的开发数据能把两类结果完全分开，可作为冻结依据，但**本步不做决定**：

| 指标 | 失败例（L1 基线、L2/L3 left） | 通过例（L1 过折、L2/L3 right） |
|---|---|---|
| crossed | 0.000 | 1.000 |
| IoU | 0.015 | 0.365–0.423（L1）/ 0.559–0.563（right） |
| 对齐 | 115.2 mm | 13.8 mm（L1）/ 8.49 mm（right） |
| 反射误差 | 222–225 mm | 39.9–45.0 mm（L1）/ 19.4–20.0 mm（right） |
| z_p95 | 9.9 mm | 67.5–69.1 mm |

冻结阈值时必须同时写明：适用的档、测量时刻（释放后静置结束）、是否要求 held gate、以及“阈值一旦冻结即对两种表示与所有 seed 同时生效”。建议在任何正式批次启动前完成这一步并登记。

## 6. 必须先做的判断：现在是否值得跑

冻结版 left 的失败是确定性的：L2/4200 与 L3/4300 在两种表示、两个代码版本下都重复为释放后回弹摊平（crossed 0、extent 0.442–0.458、z_p95 9.9 mm）。任务 B 的 40 个 held-out 初态若沿用 left，预期仍接近全失败。两条路：

- **A. 先跑基线批次**：得到一份完整的正式拒绝率基线（120 次尝试），代价是约 60 次初态生成 + 120 次折叠的远端机时，且按现状几乎不会产生正式成功。
- **B. 先解决 B 的释放后保持**（例如按 §4.2 的规则新建 right 变体并单独冻结），再跑正式批次。

无论选哪条，都不得在批次中途改折向或更换 seed；选 B 时 right 变体必须按冻结文档 §0 重新登记并同时适用于 single/arc4。

## 7. 本步未覆盖

- 折叠脚本不录视频；正式验收要求的成功/失败视频需要另行接入录制并单独登记。
- 10 次 reset 批次由已有工具（`day4-prepared-square-backend-reset.py`）执行，尚未并入本批次脚本。
- 接口隔离检查、30 张验收图（现在每档 20 个初态各有一张 `initial.png`，共 60 张）尚未整理成验收材料。
- 正式成功仍为 0。


## 2026-11-02 汇总器修复与 right 开发验证登记（尚未运行）

stage4_formal_report.py 已把缺失结果转换为 error 尝试，按档/表示/任务计入 attempts 和 (rejected+error)/attempts；空批次保持 null。新增 test_stage4_formal_report.py，8 项纯离线测试通过（一次通过+一次缺失结果得到2次尝试、50%拒绝率）。已有结果与日志不重复计数，非 held-out 日志不纳入，重试独立计数。

按冻结文档最新 b-right-dev-v1 条目，仅以开发 seeds 4200/4300 各运行 single/arc4 验证 right 的释放后保持；独立 manifest 与目录白名单在任何新结果前登记。held-out 与正式批次暂停，正式成功仍为0。检查范围仅现有 OPEN+30ticks+180settle 的终态，不宣称第二时刻保持或长期稳定。


## 2026-11-02 b-right-dev-v1 开发复验与移交后审计完成

汇总器缺失结果分母修复与8项离线测试已通过；原项目代码与已测试副本SHA256一致（9a757d34…）。一次通过+一次无结果error的合成回归输出2次尝试、50%拒绝率；空批次保持null。

L2 4200的right single/arc4由本聊天在移交前完成；L3 4300采用另一聊天产出的最早外部single/arc4，按目录启动时间选择而非passed。两对均通过原版PAIRS_COMPARABLE，四份选定结果held gate通过、crossed=1.0，L2 IoU=0.559091、L3 IoU=0.562997；各对目标差及五项指标差值精确为0。底层21项代码不变，四份结果的独立23项变体manifest、配置和初态文件哈希均核对一致。

共下载核验66个远端文件，包含6份完整开发结果：选定4份配对结果与2份额外L3 single重复尝试。额外尝试原样保留，不增加独立seed覆盖，不计算正式成功率。用户移交后本聊天仅下载审计，未再提交GPU仿真，未终止已在途远端进程。

结论仅为每档一个开发seed在OPEN后30 release ticks+settle(180)终态保持；没有独立退让、第二retention样本或长期稳定性验证，不能外推整个开发集/held-out，更不能解释为BC策略或H=4性能提升。right为独立变体，不替换left失败或默认定义。held-out与正式批次保持暂停，正式Stage 4成功仍为0。

完整报告：[right开发复验与移交后审计](../thesis/day4-actionchunk-test/results/TASK_B_RIGHT_DEV_V1_20261102-183740/review.md)。
