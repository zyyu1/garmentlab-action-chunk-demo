# D1-120 步骤 6：两次调用均在 runner 预检/启动阶段失败

日期：2026-11-04（远端容器 `autodl-container-ac0a41b2f7-bc28942d`）。两次都在 Isaac 启动前失败，**没有执行任何物理步，没有生成结果目录**。

## 第一次：mode 未传入

命令：

```bash
cd /root/autodl-tmp/a5-rc2-d1-120/app
bash run-a5-rc2-d1-120.sh 4202 single
```

日志：[console.log](console.log)

```text
Traceback (most recent call last):
  File "<stdin>", line 33, in <module>
NameError: name 'mode' is not defined
```

原因：runner 的第一个 heredoc 只传入 `"$seed"`，但 Python 预检使用 `mode`。修复为 `"$python_bin" - "$seed" "$mode"`，并在 Python 中读 `sys.argv[2]`。

影响：预检在 attempt ledger 之前失败；`runs` 为空，没有 `attempts.jsonl`/`completed`/结果目录。

## 第二次：initial 未赋值

修复 mode 后再次调用；日志：[console-run.log](console-run.log)

```text
D1_PREFLIGHT_OK 66 39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d /root/autodl-tmp/day4-square-initial-stripfold-20261103-062710-242560
run-a5-rc2-d1-120.sh: line 123: initial: unbound variable
D1_ABORT no result directory; retain log /root/autodl-tmp/a5-rc2-d1-120-log-cttxxcWx.log
D1_LOG_RETAINED /root/autodl-tmp/a5-rc2-d1-120-log-cttxxcWx.log
```

原因：预检 Python 计算了局部 `initial`，但 shell 没有给 `$initial` 赋值；`set -u` 在调用 `a5_recovery_diag.py` 前中止。修复为在预检前从 `a5-candidate.json` 设置 `initial`，并增加 `D1_PREFLIGHT_ONLY=1` 的无仿真预检出口。

影响：已写入一条 `started` attempt 记录（[attempts.jsonl](attempts.jsonl)，manifest `1a273026…`），但没有 `completed`、没有结果目录、没有 Isaac/物理步。该记录保留，不删除。

## 当前修复状态

- runner SHA256 `bb30e814c13cfec9b7ab763260827b8ca5b2c11fa5853a2e1cdb84db120aa817`
- manifest SHA256 `cd1d7f83d065974e12191486eddbf722edd4a1b7392ec78543966483434b25a6`
- 本地离线预检 **65/65 通过**（[D1_120_PREFLIGHT](../D1_120_PREFLIGHT_20261103/review.md)）
- 新增静态预检：`runner_preflight_args`、`runner_initial_resolution`、`runner_preflight_only_guard`
- `bash -n` 通过

修复只影响 runner 的参数/初态解析，不改变物理、控制、动作目标、120 步等待或事件记录。正式 Stage 4 成功仍为 0；RC2 与 v1.1 目录未修改。
