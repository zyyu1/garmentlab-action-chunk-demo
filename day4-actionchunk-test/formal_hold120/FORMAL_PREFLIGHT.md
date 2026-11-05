# hold120 正式 expert 批次：离线预检与运行清单

**状态：** 开发候选已冻结；正式批次待运行；正式 Stage 4 成功 **0**。本轮未启动仿真、未生成 held-out 初态、未运行正式 episode。

## 1. 冻结身份核对

| 项目 | 完整 SHA256 |
|---|---|
| 候选 manifest | `40858efc1a5840ab2bf51e025f823382e8586bc037fbe41bf1d1de5b21dee86a` |
| 验证 manifest | `7d328159b72a2bd55be0254fd6844cb94408e1efa67e973148b67e8ffa3dcdae` |
| `verified-dev.json` | `67c64a55b74db10ac85818cb0ed6ca1d00600e8b4ba326e5af4d6f01109cbbad` |
| `E_RELEASE.json` | `9042e88ed8b4d082917151023705276230c1a4ba5c8e65b3c602337fa68ab66a` |
| formal slots | `628a9242a5d32dc6b9432cd797da9145bd055b8d901d90e1da7f3e9d04885315` |
| deployment manifest | `1a36b8c44811352b9bfdfb4a20fbdb54161b6e1415043ace7cd11777d20c7eb9` |

- `gate_rc7_sources.py` 重新运行 → **exit 0**（`A5_GATE_OK_SOURCE 7`）。
- verification manifest 83/83 条目匹配；`check_vm_entries.py` exit 0。
- 回执绑定：E_RELEASE → verified-dev → verification manifest → 候选/父 manifest。
- 无当前正式批次锁或活跃 tmux；`stage4-b-right-dev-v2-L2/L3.lock` 属旧 B-right 开发，不是本批次锁，未删除。

## 2. 固定正式矩阵

| 档 | seeds | 初态数 | 槽数（single+arc4） |
|---|---|---:|---:|
| L1 flat | 4110–4129 | 20 | 40 |
| L2 perturbed | 4210–4229 | 20 | 40 |
| L3 crumpled | 4310–4329 | 20 | 40 |
| **合计** | | **60** | **120** |

- seed 清单与 `stage4-heldout-seeds.json` 逐项一致；与 dev seeds 无重叠。
- `formal_slots.json` 固定顺序：每个 seed 先生成一次初态，再 single、arc4；两模式共享同一初态文件/哈希。
- 不因失败换 seed、不挑选初态；本清单未生成任何初态。

## 3. 正式入口与部署层

- 部署驱动：`formal_hold120/formal_driver.py`；配置 `formal_config.json`。
- **生成任何初态前**先执行 `gate_rc7_sources.py`；gate 失败直接退出，不生成、不 rollout。
- 初态：冻结的 `run-square-initial.sh` / `run-square-initial-stripfold.sh`。
- episode：冻结的 `a5_entry.py run --split formal`；audit：修订 `audit_hold120_case.py`。
- 不使用共享根目录旧副本；config 指向冻结候选的 `app/`。
- 冻结 `a5_entry.py` 内部仍有其 receipt 检查；批次 gate 是来源兼容 `gate_rc7_sources.py`，内部检查只作为 frozen code 的附加校验，不作为批次 gate。
- 协议：L1 pfs=0 无 hold；L2/L3 pfs=1，原 240 settle + 120 hold 后再观测计算 fold；single/arc4 同位置同时长。
- 初态 preflight 继续拒绝错误 scale、缺失 protocol/材料绑定/生成器身份。

## 4. 评价链

每槽记录：
- `entry_exit`、`runner_exit`（来自 `a5-verdict.json`）、`audit_exit`；
- `file_complete`、`observation_semantics_valid`、`quality_status`、`overall_valid`；
- `hold_applicable`、`recovery_hold`；
- 最终是否 accepted/rejected，不用 `passed=true` 代替成功判定。

- 原 `stage4_success_v1`、阈值、release step 0、窗口不变。
- 位置差分速度为物理量；原始 API 读回保持 `unvalidated` 标记。
- cloth-ground 力/冲量与 solver 内部值不可得，继续注明；不新增物理验收门槛。

## 5. 部署 manifest

`deployment_manifest.json` 绑定 18 项：driver、config、slots、测试/日志、launch/download、候选 manifest、gate/freeze/audit/hold_contract、verification manifest、两份回执、seed 清单与 plan。哈希 `5dbc0d31…`；所有新增入口均在部署身份内。

## 6. 离线测试结果

`test_formal_driver.py` 使用临时目录与桩 backend，不调用 Isaac Sim；**10/10 通过**：
gate 失败不生成/不 rollout；身份/缺结果暂停；同 seed 两模式复用初态；质量 rejected 保存并继续；审计异常暂停；未完成 attempt 暂停不重跑；锁阻止并发；配对/hold 时序不一致暂停；已完成失败重跑时跳过；零尝试 summary 的 rejection_rate=null。

统计：`rejection_rate=(rejected+error)/attempts`；空分母 null；未开始槽单列；按 level/mode 分组；同 seed 配对不重复计初态。

## 7. 容量与机时估算（来自开发实测）

| 项目 | 实测/估算 |
|---|---|
| episode 总大小 | 15.6–20.1 MB；均值 18.44 MB；最大 20.1 MB |
| 120 episodes | 均值约 **2.21 GB**；最坏约 **2.41 GB** |
| 60 初态 | flat 0.36、L2 0.55、L3 0.48 MB/份 → 约 **28 MB** |
| 日志/部分结果/余量 | +20% ≈ 0.5 GB |
| 合计预留 | **约 2.9 GB** |
| 远端磁盘 | 50G，已用 37G，可用 **14G**；余量约 11G |
| 单槽 wall time | L1 13.8 min；L2 17.8 min；L3 18.2 min |
| 120 槽 | 约 **33.2 h**；加 60 初态约 1.5 h → **约 35 h** |

本轮不删除数据、不扩容。若空间不足，按 level 分段下载归档；未核验备份前不得删原始结果。

## 8. 远端启动 / 进度 / 续跑命令

```bash
# 上传部署层（如尚未上传）
scp -P 23636 formal_hold120.tar.gz root@connect.nmb2.seetacloud.com:/root/autodl-tmp/
ssh -p 23636 root@connect.nmb2.seetacloud.com \
  'mkdir -p /root/autodl-tmp/stage4-formal-hold120 && cd /root/autodl-tmp/stage4-formal-hold120 && tar -xzf /root/autodl-tmp/formal_hold120.tar.gz && chmod +x launch_formal.sh'

# 预检（不启动仿真）
ssh -p 23636 root@connect.nmb2.seetacloud.com \
  'cd /root/autodl-tmp/stage4-formal-hold120 && /root/autodl-tmp/envs/isaac40/bin/python formal_driver.py --preflight'

# 启动（tmux；仅一次）
ssh -p 23636 root@connect.nmb2.seetacloud.com \
  'tmux new-session -d -s formal_hold120 /root/autodl-tmp/stage4-formal-hold120/launch_formal.sh'

# 查看进度
ssh -p 23636 root@connect.nmb2.seetacloud.com \
  'tail -5 /root/autodl-tmp/stage4-formal-hold120/formal_run.log; wc -l /root/autodl-tmp/stage4-formal-hold120-formal-v1/attempts.jsonl; cat /root/autodl-tmp/stage4-formal-hold120-formal-v1/summary.json 2>/dev/null'

# 续跑：先确认无活跃 tmux/锁、检查 attempts 中是否有 started；同一条启动命令即可，已完成槽自动跳过
# 若 started 未完成，驱动会暂停，不自动重试；需人工检查现场后再决定。
```

## 9. 下载核验与汇总

```bash
ssh -p 23636 root@connect.nmb2.seetacloud.com \
  'cd /root/autodl-tmp/stage4-formal-hold120 && /root/autodl-tmp/envs/isaac40/bin/python download_formal.py --state /root/autodl-tmp/stage4-formal-hold120-formal-v1 --out /root/autodl-tmp/formal_hold120_archive.tar.gz'
scp -P 23636 root@connect.nmb2.seetacloud.com:/root/autodl-tmp/formal_hold120_archive.tar.gz ./
# 远端哈希清单 + 本地 verify_rc7_download.py（generic）逐文件核验
# summary 以 state/summary.json 为准；不修改原始 ledger。
```

## 10. 停止条件

立即暂停：gate/身份失败；缺结果；entry/runner/audit 非零；file/观测语义不完整；配对目标 >1e-6；hold 时序不一致；未完成 attempt；锁冲突；磁盘不足。质量 rejected 但证据完整则保存继续。4201 类负例允许有效 accepted/rejected（本正式矩阵无负例）。

## 11. 剩余阻塞项

- **正式批次与 held-out 未运行**；正式 Stage 4 成功仍为 0。
- 生产驱动尚未在 GPU 上实际跑过（本轮仅离线/桩测试与不启动仿真的 preflight）。
- 冻结 `a5_entry.py` 的内部 receipt 检查仍在；不视为批次 gate。
