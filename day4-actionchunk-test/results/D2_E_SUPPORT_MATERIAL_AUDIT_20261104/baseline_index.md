# 基线索引与对照记录（步骤 1）

日期：2026-11-04。仅索引既有版本/证据；不运行新实验。

| 版本 | 角色 | 版本目录 | manifest | config / candidate | 4202 初态 | 结果目录 |
|---|---|---|---|---|---|---|
| **RC2** `stage4-a5-rc2` | 原始基线；下一候选默认父版本 | [a5-rc2](../../a5-rc2/) | `39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d`（60 项） | `a5-candidate.json` canonical LF SHA256 `10a6cb452b9fafd5907f245b68fd02d49c7af1e12fa6cb0f755f1791a5af27a5`；原始 RC2 文件为 CRLF，raw SHA256 `fbbb633c…`，规范化后与 10a6 相同 | `day4-square-initial-stripfold-20261103-062710-242560`；`result.json` `4472f4df…`，`initial_geometry.npz` `a6646d66…` | RC2 4202 single `022718-388270`；4302 single `025702-598075`（详见 [STAGE4_A5_RC2](../../../STAGE4_A5_RC2.md)） |
| **D1-120** `a5-rc2-d1-120` | 延迟退让诊断（已运行一次，无改善） | [a5-rc2-d1-120](../../a5-rc2-d1-120/) | `cd1d7f83d065974e12191486eddbf722edd4a1b7392ec78543966483434b25a6`（66 项） | config `a6884eab8ae4bf6d703b0321415cfc2cd501f878472068109addba564ba4d471` | 同上 | `day4-a5-rc2-d1-120-20261104-071602-499516` |
| **D2-C** `a5-rc2-d2c-release-order` | 释放顺序诊断（已运行一次，quality rejected） | [a5-rc2-d2c-release-order](../../a5-rc2-d2c-release-order/) | `778935ab6ec62a093470a8485a86e241884ba4f867c1be6d0f57c4f3f9eda537`（66 项） | config `96acc5fa4a0a318c876437c236a5c9260497a00028adb6db280784ed1725be27` | 同上 | `day4-a5-rc2-d2c-release-order-20261104-090032-412133` |

## 对照事实

- **D1-120：** 120 步等待没有改善。等待 2.0783/4.5603 mm、退让 2.4590/5.3214 mm、正式窗口 2.0409/4.4134 mm；D1 与基线布料在相同 elapsed 时间点 486 点逐位相同。延迟只改变相位，不改变滑移率。
- **D2-C：** 释放顺序改变后正式窗口 1.9823/4.3426 mm，仍超 1 mm / 3 mm，quality rejected；释放一步速度 17.4197 vs 17.4223 mm/s，free 0–30 基本不变。释放顺序不是该例漂移的主要因素。
- 两例都是 4202 single 诊断，不是正式验收；正式 Stage 4 成功仍为 0。

## 下一候选约束

- 下一候选默认从 **RC2 原流程**派生；不默认保留 120 步等待，也不默认保留 D2-C 的 preopen/释放顺序。
- 若保留 D1/D2-C 的诊断记录，必须先核对它们**没有改变控制**；D1 改变了等待时序，D2-C 改变了释放顺序，均不是中性基线。
- 新候选登记必须写明父 RC2 manifest/config、初态哈希、唯一修改项、新 manifest/config 和独立输出目录。
- 4202 single 通过前不重跑完整七例；正式批次和 held-out 保持暂停。

## 关联

- [D2-E 步骤 2 支撑/摩擦审查](review.md)
- [D2-D 对照](../D2_D_COMPARE_20261104/review.md)
- [D1-120 分析](../D1_120_STEP8_ANALYSIS_20261104/review.md)
