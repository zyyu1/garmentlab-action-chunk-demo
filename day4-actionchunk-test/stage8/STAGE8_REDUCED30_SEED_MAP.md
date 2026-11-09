# Stage 8 缩减版 30 例 Seed Map

父清单：`STAGE8_FROZEN_MANIFEST.json`，file sha256
`ae1b165376e1b6adc88288fdc3e2e9388ba23c1df74f7377d694f4a2c4dfc030`；
core `364c9b7e…`。缩减清单：
`STAGE8_REDUCED30_MANIFEST.json`，core `2c70026a…`。

| 档 | 顺序 | seed | 初态目录 | Stage4 | Stage5 expert | 最终 split | debug |
|---|---:|---:|---|---|---|---|---|
| flat | 1 | 4110 | `day4-square-initial-20261105-231449-197286` | yes | no | unused | no |
| flat | 2 | 4111 | `day4-square-initial-20261105-231810-103925` | yes | no | unused | no |
| flat | 3 | 4112 | `day4-square-initial-20261105-232137-703257` | yes | no | unused | no |
| flat | 4 | 4113 | `day4-square-initial-20261105-232453-404004` | yes | no | unused | no |
| flat | 5 | 4114 | `day4-square-initial-20261105-232818-196572` | yes | no | unused | no |
| perturbed | 1 | 4215 | `day4-square-initial-stripfold-20261106-003839-589444` | yes | no | unused | no |
| perturbed | 2 | 4216 | `day4-square-initial-stripfold-20261106-004840-096130` | no | no | unused | no |
| perturbed | 3 | 4217 | `day4-square-initial-stripfold-20261106-005909-291726` | no | no | unused | no |
| perturbed | 4 | 4218 | `day4-square-initial-stripfold-20261106-010842-989694` | no | no | unused | no |
| perturbed | 5 | 4219 | `day4-square-initial-stripfold-20261106-011855-796373` | no | no | unused | no |
| crumpled | 1 | 4313 | `day4-square-initial-stripfold-20261106-020101-494614` | yes | no | unused | no |
| crumpled | 2 | 4314 | `day4-square-initial-stripfold-20261106-021221-790718` | yes | no | unused | no |
| crumpled | 3 | 4315 | `day4-square-initial-stripfold-20261106-022321-900837` | yes | no | unused | no |
| crumpled | 4 | 4316 | `day4-square-initial-stripfold-20261106-023341-788882` | yes | no | unused | no |
| crumpled | 5 | 4317 | `day4-square-initial-stripfold-20261106-024436-496333` | no | no | unused | no |

- 15 seeds × 2 policies = **30 cases**。
- 两策略继承父 manifest 的**同一 initial_dir、result/geometry 哈希、checkpoint、
  stats、runner、Backend、预算、终端和计时方式**。
- H4 execute_k=4；single 单步。
- 4110–4114、4215、4313–4316 曾用于 **Stage 4 专家**，所以本缩减集不是全新
  未使用 test；它们未进入 Stage 5 train/val，也未用于 Stage 6/7 策略调试。
- 完整哈希见 `STAGE8_REDUCED30_MANIFEST.json`。
