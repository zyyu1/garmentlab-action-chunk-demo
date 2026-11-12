# 2026-11-12 GarmentLab 日报 · 仓库文档规范化与日报补全

**结论：仓库历史版本命名、日报命名与 Stage 4 配套文档完成统一与归档；补齐 11-07 起日报。无仿真、无训练。**

## 1. 提交历史版本命名统一

- 全部 36 个 commit 主题由 `versionX.Y.Z: …` 改为 `vX.Y.Z: …`。
- 重写后重新打 tag：`v9.1.0`、`v9.1.3`（annotated 消息保留），force-push `main` 与 tags。
- 影响：所有 commit SHA 变化；重写前完整备份 `garmentlab-before-version-rename-20261112.bundle`。
- 校验：`origin/main` 中 `^version` 前缀提交为 **0**。

## 2. 日报命名统一

- 17 份日报统一为 `YYYY-MM-DD-GarmentLab日报-Stage<X>-<主题>.md`（分隔符统一为 `-`，主题内空格转 `-`）。
- Stage0 日志分隔符统一为 `2026-09-29-环境安装交接日志-Stage0.md`。
- 同步更新所有 Markdown 链接（含 `%20` 编码），专项校验“日报”链接 **0 broken**。

## 3. Stage 4 配套文档归档

16 份历史文档按日期并入日报序列，例如：

| 原文件 | 归档后 |
|---|---|
| `CHECKPOINT_20261031.md` | `2026-10-31-…日报-Stage4-checkpoint.md` |
| `DAY4_ROUTE_REASSESSMENT.md` | `2026-10-26-…日报-Stage4-路径与控制重评.md` |
| `STAGE4_SUCCESS_CRITERIA_V1.md` | `2026-11-02-…日报-Stage4-成功判据v1.md` |
| `STAGE4_A5_RC2.md` | `2026-11-03-…日报-Stage4-A5-RC2登记.md` |

- 无完全重复文件（sha256 核对），未删除内容。
- 活文档保留：`README.md`、`DAY4_ACCEPTANCE_TRACKER.md`、`DAY4_MINIMUM_PLAN.md`、`DAY4_NEXT_STEPS.md`、`Marian_…_plan.md`、`CHECKPOINT_MANIFEST.json`、`environment_log.md`。

## 4. 补全 11-07 起日报

| 日报 | 主题 |
|---|---|
| [2026-11-07](2026-11-07-GarmentLab日报-Stage5-正式采集与观测审计.md) | Stage 5 正式采集、观测审计、超时保护 |
| [2026-11-08](2026-11-08-GarmentLab日报-Stage5缩减版与Stage6-7.md) | 50/10/10、离线训练、Stage 6/7 |
| [2026-11-09](2026-11-09-GarmentLab日报-Stage8缩减30与Stage9-10展示.md) | Stage 8 缩减 30 例、Stage 9/10、v9.1.x |

## 5. 证据

- 备份：`E:\learning\project\garmentlab-before-version-rename-20261112.bundle`
- 提交：`aa679e6`（日报命名）、`559dfd6`（Stage0）、`715f2f4`（Stage 4 归档）、本日报提交。
- 远端：`https://github.com/zyyu1/garmentlab-action-chunk-demo`（main）。
