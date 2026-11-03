# D：批次与离线汇总交付（2026-11-02）

本次仅执行本地离线工作；没有运行、生成或部署任何 held-out 初态/折叠。正式批次仍暂停。D 的工具和证据索引已交付，原始材料缺口保留给 A 的采集/下载补齐；不能把 D 交付解释为 E 已具备启动条件。

## 已完成

- 固定 seeds：每档 20 个，合计 60 个 held-out、120 个 seed×表示槽位；开发集 30 个与之不重叠。校验唯一性及完整 plan 条目（包括条带方向/宽度），原登记随机生成规则 `stage4_heldout_register.py --check` 通过。
- 批次运行前登记 started，运行后追加 finished；中断的 started 保留为 error 分母，不自动重试。完成的失败尝试也跳过；没有结果、身份错配、结果哈希变更或损坏日志时停止续跑。历史无身份绑定的批次不自动迁移。
- 批次绑定 seeds、plan、基础设施和 manifest 字节哈希；恢复时变更即停止。进程锁阻止同批次并发；初态 result/PNG/NPZ 验证身份并绑定哈希，single/arc4 复用同一初态。锁遗留时先检查运行进程与日志，不能自动清除。
- 汇总按档、表示、任务区分 development_passed、rejected、error。拒绝率 `(rejected+error)/attempts`；空批次为 null。未开始的计划槽位单列 not_attempted，不虚构为失败。缺失/损坏结果和未结束尝试计入 error；runner 非零退出不能凭 passed=true 计通过。
- 不信任 legacy formal_day4_success/fold_success_accepted 标记；保留 legacy_formal_claim 供追溯。目前 formal_evaluated=0、formal_success=0、formal_success_rate=null，明确等待独立冻结评价器审计，不能解释为正式评估失败率 100%。代码哈希存在也不等于已核验冻结身份。
- 输出报告使用独占创建，拒绝覆盖已有结果；原实验数据未修改。已有日志格式兼容，新日志以 attempt_id 合并 started/finished。

## 证据与验证

- [最终证据索引](day4-actionchunk-test/results/STAGE4_D_OFFLINE_20261102/evidence/index.md)：最终登记的 30 张初态图全部找到并可解码，逐文件路径、SHA256 和 NPZ 结构见同目录 index.json。
- L1 的两份 result.json 原始字节不同，但 JSON 内容逐项一致；保留两个哈希，不覆盖副本。可用的语义完整初态包共 12 个（L1 10 个，L2/L3 各 1 个）。严格字节一致的完整包为 2 个。
- 4201–4209、4301–4309 的 18 个登记初态目录本地只有图片，缺 result.json 与 initial_geometry.npz；索引逐项标明。这些是原始材料缺口，不推断为实验失败，也不以其他版本目录替代。
- 10 次 reset 原始 result、cycle/reset JSON、PNG、NPZ 均已读回；10/10 状态检查通过。只有 1 次完整折叠，其余为生命周期短程 rollout；不能写成 10 次完整折叠成功。
- [离线 held-out 汇总](day4-actionchunk-test/results/STAGE4_D_OFFLINE_20261102/heldout_offline_report.json)：已提供的两个本地结果根目录内 0 次 held-out 尝试，120 个计划槽位未开始；没有提供正式批次日志，因此 denominator_complete=false，不声称远端全量证明。
- [测试记录](day4-actionchunk-test/results/STAGE4_D_OFFLINE_20261102/tests.txt)：20 项离线测试通过，覆盖缺失/损坏结果、失败分母、重试、日志起止、断点续跑、身份变更、不覆盖和旧正式标记拒绝。Git Bash 对 LF 传输内容的 `bash -n` 通过；未执行 GPU runner，也未进行远端端到端测试。
- [预检结果](day4-actionchunk-test/results/STAGE4_D_OFFLINE_20261102/preflight.json)与[交付文件哈希](day4-actionchunk-test/results/STAGE4_D_OFFLINE_20261102/delivery_hashes.json)。外层初版 index 保留，正式阅读入口为 evidence/index.md（补充了 L1 的语义一致判定）。

## 离线使用

在 day4-actionchunk-test 目录运行（均不启动仿真）：

```powershell
python stage4_batch_preflight.py check
python -m unittest test_stage4_formal_report test_stage4_batch_preflight -v
python -I stage4_formal_report.py --seeds stage4-heldout-seeds.json --root <下载结果根目录> --attempts <批次目录>/attempts.jsonl --out <新的报告路径.json>
python stage4_acceptance_index.py --root <主结果根目录> --root <原始结果根目录> --out <不存在的新索引目录>
```

## 移交 E 的约束

本次不刷新折叠 manifest、不选择 right、不修改控制/采样时序。现有正式 driver 仍保留已登记的 left 入口；A 的采用结论、B 的冻结评价、C 的采集复验收敛后，由 E 统一固定任务入口、评价器和 manifest，并接入正式离线判定输出。当前汇总不会自动把任何开发通过升级为正式成功。

driver 新增暂停闸门，只有 E 显式设置 STAGE4_FORMAL_RELEASE=A_B_C_FROZEN 才会进入执行逻辑；该变量是操作性闸门，不是 A–C 验收证明。不得仅为绕过暂停而设置。部署时必须同时传输 stage4_batch_preflight.py，shell 按 LF 传输并核对哈希。新的批次基础设施和报告工具尚未部署远端。需要重试时保留失败账本，先登记原因与新 attempt_id；本版不提供隐式自动重试。
