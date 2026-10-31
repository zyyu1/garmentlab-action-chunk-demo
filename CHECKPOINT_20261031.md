# Day4 checkpoint — 2026-10-31

Current state: formal Day4 successes = 0. Do not interpret pipeline completion as fold success.

The latest square grasp pose candidate has been prepared, uploaded and statically checked, but has NOT run in simulation at this checkpoint. Next manual command: `bash /root/autodl-tmp/run-square-grasp-pose.sh`.

Start with DAY4_NEXT_STEPS.md and DAY4_SQUARE_FRAME_AUDIT.md. Existing failures and compact review/result files are preserved under day4-actionchunk-test/results. Experimental scripts include historical versions; use only the current plan for next actions.

## Provenance and coverage

- Current server project snapshot, including unpushed commit 233771e changes and uncommitted Backend/prepared control updates.
- GitHub parent main: 23077703586fdcae432aa683671ba49517466811.
- GarmentLab changes are preserved as day4/upstream/garmentlab-adaptation.patch plus three current source files; patch base f2988b169ec3f1471b46f963ceba58f56179ef0d.
- Local Day4 scripts, manifests, plans, handoff reports, offline audits and procedural square USDA.
- Large raw result directories (videos, images, particle arrays, logs), environments, external garment assets and downloaded SDK meshes are not uploaded. They remain in the local thesis directory and/or AutoDL data disk. This is a code/documentation checkpoint, not a complete environment/data backup.
- Runtime scripts expect their dependencies directly in /root/autodl-tmp and the existing GarmentLab/Isaac environment. Repository paths are archival layout; transfer the active manifest files before running.

The square pose Backend is a development candidate. Original shared Backend still lacks yaw mapping. The new candidate adds world yaw and fixed downward orientation with the URDF fingertip midpoint proxy; no formal Backend integration or physical pinch calibration is claimed.
