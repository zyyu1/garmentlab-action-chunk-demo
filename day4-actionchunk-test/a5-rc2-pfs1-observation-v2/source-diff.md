# a5-rc2-pfs1-observation-v2 source differences vs a5-rc2-pfs1

Generated 2026-11-04. Parent pfs1 manifest `bad4b59a0baecd08bd814bc98cfc28e7a0197fb9fed2effd21282ef40563c51b` (63 entries). V2 candidate manifest `d97bf349dc8a7813ab274da52c4a16c69a11b9135717a6851abbd6192cf3b73f` (63 entries).

## Classification

| Category | Files | Change |
|---|---|---|
| Physics / control | none | `particleFrictionScale=1.0`, `friction=0.3`, ground, collision, material binding, 12 actions, targets logic, horizons, retreat target, evaluator and thresholds are unchanged from pfs1. |
| Observation | `a5_recovery.py`, `a5_capture.py`, `pfs1_observation_v2.py` | Raw API velocity readback is now explicitly unvalidated; release records add world-vertex backward finite-difference velocities; material readbacks are added at construction/reset/settle/recovery/pre-release; first-0.5 edge tolerance corrected 1e-9 -> 1e-6. No extra `world.step` or control call. |
| Identity | `a5-rc2-pfs1-observation-v2.json`, `a5-manifest.json`, `a5-rc2-pfs1-observation-v2-files.json`, `run-a5-rc2-pfs1-observation-v2.sh` | New version, manifest, one-shot lock and semantic ledger; 4202 single only. |
| Unchanged | 58 parent base entries, `a5_l1.py`, evaluator, thresholds, initial | Byte-identical to pfs1 for the 58 non-changed/non-pfs1-specific entries. |

Changed base files: `a5_capture.py`, `a5_recovery.py`.
New files: `pfs1_observation_v2.py`, `a5-rc2-pfs1-observation-v2.json`, `run-a5-rc2-pfs1-observation-v2.sh`.

## Physics/control diff review

`a5_recovery.py` diff contains only:

- import `pfs1_observation` -> `pfs1_observation_v2`;
- output prefix `day4-a5-rc2-pfs1-` -> `day4-a5-rc2-pfs1-observation-v2-`;
- material object comment and construction-time readback after `original_material(...)`;
- material stage readbacks after reset, initial settle, recovery and pre-release;
- stage snapshot module name.

No action call, target expression, horizon, retreat target, attachment/release call or particle parameter changed.

`a5_capture.py` diff contains only:

- observation module import/name;
- first-0.5 window comparison tolerance `1e-9` -> `1e-6` (includes the frame at boundary+0.500000026 s);
- no action/attachment/release sequence change.

## Observation semantics

- `pfs1_observation_v2.py` keeps `ClothPrimView.get_velocities(clone=True)` output as `readback_velocities`, with `readback_velocity_validated=false` and `readback_velocity_status=unvalidated; not used as physical velocity`.
- Per-step records store `fd_velocities`, `fd_velocity_valid`, `fd_interval_s`, `fd_method=backward_difference_world_vertices`, and `fd_time_source=world.current_time at each passive post-step snapshot`.
- Single-frame stage snapshots store raw readback but explicitly mark `physical_velocity_method=not_computed_single_frame`; they do not fabricate a velocity.
- Material readback records the material prim/path and raw attrs, particle-system binding, friction/particleFrictionScale, global self-collision, non-particle collision, contact offset, particle group and raw filter attrs, support collider bindings.
- `solver_effective` is recorded as `unverified; scene/USD readback only` for every material stage. This is not a solver-effective proof.
- `contact_capability.json` records robot-rigid scope, cloth-ground force/impulse unavailable, zero events != no contact, and `required_for_acceptance=false`.

## Identity hashes

| File | SHA256 |
|---|---|
| `a5_recovery.py` | `b9993097980379fb72cf0feadb4c42d5ea254c758e19488bc518898adb4d3eda` |
| `a5_capture.py` | `c5651dc80a137115730a1ae6d6f9c1d8e48e3c4b76c70ef3e14c164f03f23f28` |
| `pfs1_observation_v2.py` | `abd459feb7adcddf4f1adf45d925e710ca65fb0ef0e7af41437222b4adef6d35` |
| `a5-rc2-pfs1-observation-v2.json` | `bce2d51dd16b50f97653e8436e444a9fd3da927e80d7e56ea053b1ed6c63e9b9` |
| `run-a5-rc2-pfs1-observation-v2.sh` | `25c57699c8eef22d8bfe2ba02c1b99e8f51e51891b8fc3dfb2c73d831128a69e` |

Old pfs1 source, manifest, registration, result and invalid-attempt evidence remain untouched. This revision does not replace the old pfs1 result; it is a new observation revalidation.
