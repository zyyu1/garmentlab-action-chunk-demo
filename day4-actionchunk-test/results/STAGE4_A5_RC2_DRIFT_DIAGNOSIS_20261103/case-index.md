# RC2 baseline: seven pre-registered cases

Source audit: `E:\learning\project\thesis\day4-actionchunk-test\results\A5_RC2_AUDIT_20261103T194913Z`

| case | verdict | failed check | centroid max mm | P95 max mm | geometry frames failed | video frames | evidence all true |
|---|---|---|---:|---:|---:|---|---|
| 4100 arc4 | accepted | accepted | 0.143531 | 0.207200 | 0 | 843-904 (62) | True |
| 4100 single | accepted | accepted | 0.143531 | 0.207200 | 0 | 843-904 (62) | True |
| 4201 single | rejected | geometry: 121/121 window frames fail; runtime gate: RuntimeError('Fold did not cross the fold line') | 0.000243 | 0.002573 | 121 | 1298-1359 (62) | True |
| 4202 arc4 | rejected | stability: centroid_max=0.002043 m (limit 0.001), vertex_p95_max=0.004414 m (limit 0.003) | 2.042884 | 4.414119 | 0 | 1157-1218 (62) | True |
| 4202 single | rejected | stability: centroid_max=0.002043 m (limit 0.001), vertex_p95_max=0.004414 m (limit 0.003) | 2.042884 | 4.414119 | 0 | 1157-1218 (62) | True |
| 4302 arc4 | rejected | stability: centroid_max=0.001910 m (limit 0.001), vertex_p95_max=0.004123 m (limit 0.003) | 1.910233 | 4.123147 | 0 | 1367-1428 (62) | True |
| 4302 single | rejected | stability: centroid_max=0.001910 m (limit 0.001), vertex_p95_max=0.004123 m (limit 0.003) | 1.910233 | 4.123147 | 0 | 1367-1428 (62) | True |

## Roles

- 4100 single/arc4: positive L1 regression.
- 4202 single/arc4: positive task-B, rejected by stability; 4202 single is the first diagnostic subject.
- 4302 single/arc4: positive task-B, rejected by stability; 4302 single is the later revalidation subject.
- 4201 single: negative control, rejected by geometry/runtime gate.

## Verification baseline

- RC2 manifest: `39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d` (60 entries, verified).
- Original verify-dev: exit_code=1, release_exists=False.
- RGB/video/holding evidence checks: all seven true.
- Freeze: not frozen; formal Stage 4 success remains 0.
