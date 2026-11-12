# hold120 rc7-r2 冻结归档（开发候选已冻结，正式批次未运行）

**状态：** 开发候选已冻结；正式 Stage 4 成功计数仍为 **0**；held-out/正式批次未运行。

## 1. 候选身份

| 项目 | 值 |
|---|---|
| 候选 | `a5-rc8b-recovery-hold120-rc7-r2` |
| manifest | `40858efc1a5840ab2bf51e025f823382e8586bc037fbe41bf1d1de5b21dee86a`（63 项） |
| 父 manifest | `41db790f256396e07df079e511090d14a9852c1f55197afa36ea847a9403c2df`（rc7，slot1 来源） |
| a5_recovery | `5055931dc4cecc27e205204ea10cb87fb0236c8f59144c341524283bbf7548ac` |
| 来源模式 | slot1 parent + slots2-7 revised；继承记录仅 slot1 |
| 审计 | 修订 `0d4a9d74…` + `hold_contract.py` |

## 2. 冻结回执与验证清单

| 文件 | SHA256 |
|---|---|
| `verified-dev.json` | `67c64a55b74db10ac85818cb0ed6ca1d00600e8b4ba326e5af4d6f01109cbbad` |
| `E_RELEASE.json` | `9042e88ed8b4d082917151023705276230c1a4ba5c8e65b3c602337fa68ab66a` |
| `verification-manifest.json` | `7d328159b72a2bd55be0254fd6844cb94408e1efa67e973148b67e8ffa3dcdae` |
| `verification-manifest-check.json` | `9debc341d27a0355130f222b338af29d9f2b02b367f971168e01f94c54c16d56`，83/83 条目匹配 |
| `FINAL_SEVEN_CASE_SUMMARY.json` | `6dae3d9bae07adeac12eeb0be80dfefb90db610644e57cb85e7dc2e0648ccf6d` |

回执路径（远端）：`<remote-root>/a5-rc8b-recovery-hold120-rc7-r2/{verified-dev.json,E_RELEASE.json,verification-manifest.json}`。

## 3. 实际命令与退出码

| 步骤 | 命令 | 退出码 |
|---|---|---:|
| 冻结 | `python freeze_rc7_sources.py --execute` | **0** |
| gate | `python gate_rc7_sources.py` | **0** |
| 验证清单逐项 | `python check_vm_entries.py` | **0**（83/83） |
| 临时副本负测 | `python test_freeze_rc7.py` | **0**（10/10） |

- 未使用仅支持单一 manifest 的旧 freeze 入口；使用来源兼容冻结/门禁工具。
- 回执以独占方式创建；测试用临时副本，未触碰真实回执。

## 4. 七例与审计历史

- 六阳性 accepted；4201 有效 rejected（7.2583/11.0030）；配对 0.0；hold 120/121/2.0。
- **slot1 首次审计退出 5，同结果经修订审计通过；slots2–7 在修订版下续跑。**
- 原版 verify-dev 未使用；使用 `verify_rc7_sources.py` + `freeze_rc7_sources.py` 的来源兼容入口。
- 本地复算 7/7；下载 118+664 哈希一致；视频审查通过。

## 5. 剩余阻塞项

- 正式批次/held-out 未运行；正式 Stage 4 成功仍为 0。
- 冻结仅针对开发候选；不构成正式成功或 held-out 放行。
