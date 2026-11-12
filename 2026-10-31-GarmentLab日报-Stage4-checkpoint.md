# Stage 4 checkpoint — 2026-10-31

Current state: formal Stage 4 successes = 0. Do not interpret pipeline completion as fold success.

Updated through v5: short grasp/hold/release and contact positive controls passed. Finger-ground events remain under geometry review; detailed contact vectors are all zero. Formal fold successes remain 0. Work is paused; read the latest 2026-10-31 handoff before resuming. No automatic experiment is scheduled.

Start with DAY4_NEXT_STEPS.md and 2026-10-31-GarmentLab日报-Stage4-方巾末端接口审查.md. Existing failures and compact review/result files are preserved under day4-actionchunk-test/results. Experimental scripts include historical versions; use only the current plan for next actions.

## Provenance and coverage

- Current server project snapshot, including unpushed commit 233771e changes and uncommitted Backend/prepared control updates.
- GitHub parent main: 23077703586fdcae432aa683671ba49517466811.
- GarmentLab changes are preserved as day4/upstream/garmentlab-adaptation.patch plus three current source files; patch base f2988b169ec3f1471b46f963ceba58f56179ef0d.
- Local Stage 4 scripts, manifests, plans, handoff reports, offline audits and procedural square USDA.
- Large raw result directories (videos, images, particle arrays, logs), environments, external garment assets and downloaded SDK meshes are not uploaded. They remain in the local thesis directory and/or AutoDL data disk. This is a code/documentation checkpoint, not a complete environment/data backup.
- Runtime scripts expect their dependencies directly in /root/autodl-tmp and the existing GarmentLab/Isaac environment. Repository paths are archival layout; transfer the active manifest files before running.

The square pose Backend is a development candidate. Original shared Backend still lacks yaw mapping. The new candidate adds world yaw and fixed downward orientation with the URDF fingertip midpoint proxy; no formal Backend integration or physical pinch calibration is claimed.
