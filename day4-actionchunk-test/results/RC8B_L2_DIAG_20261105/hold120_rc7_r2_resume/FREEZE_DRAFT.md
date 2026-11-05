# hold120 rc7 冻结材料草稿（未执行 freeze）

**状态：** 七例开发 RC 通过（六阳性 accepted，4201 有效 rejected）。本文件仅为草稿；**未执行 freeze、未写 `verified-dev.json`/`E_RELEASE.json`**，正式 Stage 4 成功仍为 0。

## 1. 候选身份

| 项目 | 值 |
|---|---|
| 原候选 | `a5-rc8b-recovery-hold120-rc7` |
| 原 manifest | `41db790f256396e07df079e511090d14a9852c1f55197afa36ea847a9403c2df` |
| 修订候选 | `a5-rc8b-recovery-hold120-rc7-r2` |
| 修订 manifest | `40858efc1a5840ab2bf51e025f823382e8586bc037fbe41bf1d1de5b21dee86a`（63 项；相对原仅 config） |
| a5_recovery | `5055931dc4cecc27e205204ea10cb87fb0236c8f59144c341524283bbf7548ac`（两版相同） |
| 审计 | 原 `813da5ce…`；修订 `0d4a9d74…`；`hold_contract.py` |
| 继承记录 | `a9a106c202178d859b3d4b4bf9e9e4102f091aeebaef3328709e75b0c0bb9210`（仅 slot1） |
| 采样/评价 | 原 evaluator、阈值、release step 0、窗口不变 |

## 2. 七槽结果

| 槽 | seed/mode | 质量 | 质心/P95 (mm) |
|---:|---|---|---:|
| 1 | 4100 single | accepted | 0.1435 / 0.2072 |
| 2 | 4100 arc4 | accepted | 0.1435 / 0.2072 |
| 3 | 4202 single | accepted | 0.2374 / 0.3484 |
| 4 | 4202 arc4 | accepted | 0.2374 / 0.3484 |
| 5 | 4302 single | accepted | 0.2386 / 0.3468 |
| 6 | 4302 arc4 | accepted | 0.2386 / 0.3468 |
| 7 | 4201 single | rejected（有效） | 7.2583 / 11.0030 |

## 3. 门禁草稿

- 六阳性全部 accepted；4201 有效评价。
- 三组配对目标差 0.0；L2/L3 hold 均 120 步 / 121 帧 / 2.0 s。
- 七例证据完整；下载 118 + 664 文件哈希一致；本地复算 7/7；来源兼容验证 exit 0。
- 原版 verify-dev 未使用（单一 manifest 限制）；使用登记后的 `verify_rc7_sources.py`，不称原版通过。

## 4. 未做

- freeze、gate、释放回执、held-out、正式批次、任何成功计数增加。
- slot1 原 audit exit 5、暂停账本、复审计记录全部保留。
