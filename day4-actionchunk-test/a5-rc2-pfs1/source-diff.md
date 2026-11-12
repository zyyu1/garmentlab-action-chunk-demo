# a5-rc2-pfs1 source differences vs RC2

Generated 2026-11-04. Parent manifest `39dc5055e2c2ce3a9deb406f1f5e73baf55a9aec3c115619fef598f6aef0122d`. Candidate manifest `bad4b59a0baecd08bd814bc98cfc28e7a0197fb9fed2effd21282ef40563c51b` (63 entries).

**Runtime note (added after the run):** the source below calls `ClothPrimView.get_velocities()` and stores its raw output. The completed run showed that this readback is not consistent with the world-position finite difference (formal readback particle mean 28.76 mm/s vs position derivative 1.29 mm/s; vector correlation about −0.006). The source identity is unchanged, but the readback is **unvalidated** and is not used for physical speeds. See [pfs1 comparison](../results/D2_E_PFS1_COMPARE_20261104/review.md) and [velocity_readback_diagnostic](../results/D2_E_PFS1_COMPARE_20261104/velocity_readback_diagnostic.json).

## Classification

| Category | Files | Change |
|---|---|---|
| Physics parameter (one variable) | `a5_recovery.py` | `particle_friction_scale` 0.0 -> 1.0 in the active ParticleMaterial wrapper. |
| Observation / metadata | `a5_capture.py`, `pfs1_observation.py`, `a5_recovery.py` | Passive stage/per-step reads of vertices, actual particle velocities via ClothPrimView.get_velocities, EE, joints, gripper and attachment; output prefix `day4-a5-rc2-pfs1-`. No action/physics change. |
| Candidate identity | `a5-rc2-pfs1.json`, `a5-manifest.json`, `a5-rc2-pfs1-files.json`, `run-a5-rc2-pfs1.sh` | New config/manifests/runner; 63-entry deployment identity; 4202 single only; incomplete-attempt guard. |
| Unchanged | 58 base files, `a5_l1.py`, `a5-candidate.json`, evaluator, thresholds, initial | `a5_l1.py` remains RC2 and is not run; evaluator/initial/thresholds byte-identical. |

Changed base files: `a5_capture.py`, `a5_recovery.py`.

New files: `pfs1_observation.py`, `a5-rc2-pfs1.json`, `run-a5-rc2-pfs1.sh`.

## Full diffs for changed base files

### a5_recovery.py
```diff
--- RC2/a5_recovery.py
+++ a5-rc2-pfs1/a5_recovery.py
@@ -29,6 +29,8 @@
 
 import numpy as np
 from scipy.spatial.transform import Rotation
+import pfs1_observation
+
 
 sys.path.insert(0, '<remote-root>/garmentlab-action-chunk-demo')
 from backends.garmentlab_backend import GarmentLabBackend, _import_garmentlab
@@ -94,7 +96,7 @@
     raise ValueError('Unexpected initial geometry')
 fold_edges = ['left'] if args.fold_edge == 'left' else ['right']
 edges = list(dict.fromkeys([s['edge'] for s in strips] + fold_edges))
-out = Path('<remote-root>') / ('day4-a5-rc2-recovery-' +
+out = Path('<remote-root>') / ('day4-a5-rc2-pfs1-' +
                                   datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
 out.mkdir()
 result = {'probe_version': 'recovery-fold-episode-v1', 'passed': False,
@@ -238,7 +240,8 @@
         material_module.ClothPrim = bend_cloth
 
         def fixed_material(*a, **k):
-            k['particle_friction_scale'] = 0.
+            # a5-rc2-pfs1: only the particle inter-friction scale changes.
+            k['particle_friction_scale'] = 1.
             return original_material(*a, **k)
 
         material_module.ParticleMaterial = fixed_material
@@ -262,6 +265,7 @@
     if not np.allclose(b._garment_world_positions(), folded, atol=1e-5, rtol=0):
         raise RuntimeError('Folded state readback mismatch')
     b._settle(30)
+    pfs1_observation.record_stage(b, out, 'initial_loaded')
     yaw = float(case['yaw_rad'])
     # ---- recovery (5 actions) ----
     rec = strip_records[0]
@@ -279,6 +283,7 @@
     action(grasp_to_ee(flat_pick + [0., 0., .03], yaw), yaw, GripperCommand.HOLD, 'rec_spread', 12)
     action(grasp_to_ee(flat_pick + [0., 0., .03], yaw), yaw, GripperCommand.OPEN, 'rec_release', 12)
     b._settle(240)
+    pfs1_observation.record_stage(b, out, 'after_recovery')
     recovered = b._garment_world_positions().copy()
     res_flat = rigid_residual(flat, recovered)
     R_rec, _ = rigid_fit(flat[:, :2], recovered[:, :2])
@@ -349,6 +354,7 @@
                float(np.max(np.abs(b._to_numpy(robot._robot.get_joint_velocities())[:7]))) < .1 and
                orientation_reached and
                fold_slot.max_single_anchor_gap_m <= .01)
+    pfs1_observation.record_stage(b, out, 'pre_release')
     result['fold_held_check'] = {
         'position_error_m': held_error,
         'arm_speed_rad_s': float(np.max(np.abs(
```

### a5_capture.py
```diff
--- RC2/a5_capture.py
+++ a5-rc2-pfs1/a5_capture.py
@@ -4,6 +4,8 @@
 from pathlib import Path
 
 import numpy as np
+
+import pfs1_observation
 
 
 def release_window(backend, recorder, out, result, initial, pick, yaw, release):
@@ -28,9 +30,32 @@
         return original(*args, **kwargs)
 
     control.robot_goto_position = measure_detachment
+    # Passive observation of every step in the release action, including the
+    # opening and retreat.  The wrapper only calls the original step and reads
+    # state afterwards; it adds no physics step and no control call.
+    release_records = []
+    original_step = world.step
+
+    def observed_step(*args, **kwargs):
+        value = original_step(*args, **kwargs)
+        release_records.append(pfs1_observation.snapshot(
+            backend, 'release_step_%03d' % len(release_records)))
+        return value
+
+    world.step = observed_step
     try:
         release(target)
+    except BaseException:
+        try:
+            if release_records:
+                pfs1_observation.save_records(
+                    out, 'pfs1_release_steps_partial', release_records,
+                    {'failed': True, 'scope': 'release action partial'})
+        except Exception as exc:
+            print('PFS1_PARTIAL_SAVE_ERROR', repr(exc), flush=True)
+        raise
     finally:
+        world.step = original_step
         control.robot_goto_position = original
 
     zero = int(world.current_time_step_index)
@@ -46,6 +71,8 @@
     with np.load(out/'cloth_constructed.npz', allow_pickle=False) as grid:
         points = grid['points'].copy()
     vertices, holding, enabled, opened, times, absolute = [], [], [], [], [], []
+    trace_records = []
+    trace_start = len(release_records)
     try:
         for step in range(331):
             if step:
@@ -64,6 +91,8 @@
             opened.append(int(backend._gripper_state) == 0)
             absolute.append(tick)
             times.append(now)
+            trace_records.append(pfs1_observation.snapshot(
+                backend, 'trace_%03d' % step))
             if step in (180, 240):
                 recorder.sample('hold_3s' if step == 180 else 'hold_4s')
     finally:
@@ -72,6 +101,52 @@
                             steps=np.arange(len(times)), absolute_steps=absolute, sim_time_s=times,
                             holding=np.asarray(holding, bool), attachment_enabled=np.asarray(enabled, bool),
                             gripper_open=np.asarray(opened, bool))
+        all_records = list(release_records) + trace_records
+        if all_records:
+            pfs1_observation.save_records(
+                out, 'pfs1_release_steps', all_records,
+                {'release_records': len(release_records),
+                 'trace_records': len(trace_records),
+                 'trace_start_index': trace_start,
+                 'formal_saved': len(trace_records) >= 331})
+            boundary_index = next(
+                (i for i, rec in enumerate(all_records)
+                 if not rec['holding'] and not rec['attachment_enabled_any']), None)
+            if boundary_index is not None:
+                boundary = all_records[boundary_index]
+                pfs1_observation.save_stage(out, 'release_boundary', boundary)
+                index_path = out / 'pfs1_stage_index.json'
+                index = json.loads(index_path.read_text()) if index_path.is_file() else []
+                pre = next((x for x in index if x['label'] == 'pre_release'), None)
+                released = recorder.samples.get('released')
+                clock = {
+                    't0_definition': 'pre-release last-attached state; first detached physics step is the boundary sample; no zero-step post-disable sample in the RC2 original flow',
+                    'pre_release': pre,
+                    'release_boundary': {
+                        'label': boundary['label'],
+                        'sim_time_s': boundary['sim_time_s'],
+                        'absolute_step': boundary['absolute_step'],
+                        'holding': boundary['holding'],
+                        'attachment_enabled_any': boundary['attachment_enabled_any'],
+                    },
+                    'released_sample': released,
+                    'sampling_error_steps': (None if pre is None else
+                                             boundary['absolute_step'] - pre['absolute_step']),
+                    'definition_note': 'The actual attachment disable is between the pre-release state and the first detached step; report the step/time interval, not an exact instant.',
+                }
+                (out / 'pfs1_release_clock.json').write_text(
+                    json.dumps(clock, indent=2, allow_nan=False) + '\n')
+                first = [rec for rec in all_records
+                         if boundary['sim_time_s'] - 1e-9 <= rec['sim_time_s']
+                         <= boundary['sim_time_s'] + 0.5 + 1e-9]
+                if first:
+                    pfs1_observation.save_records(
+                        out, 'pfs1_first_0_5s', first,
+                        {'scope': 'release boundary + 0.5 s', 'boundary_index': boundary_index})
+            if len(trace_records) >= 331:
+                pfs1_observation.save_records(
+                    out, 'pfs1_formal_210_330', trace_records[210:331],
+                    {'scope': 'success_trace frames 210..330 inclusive'})
     return vertices[-1]
 
 
```

## New files

| File | SHA256 | Purpose |
|---|---|---|
| `pfs1_observation.py` | `9482847357eade07b27799134379fdf611b5e9db3dbd5fa3dea8df0acb40ed04` | Passive stage/per-step observation; actual ClothPrimView.get_velocities readback; no step/control. |
| `a5-rc2-pfs1.json` | `2d72a40565b3f63269fff861231255a45318618ed969bc7cf132bd041c34d32c` | Candidate pre-registration/config. |
| `run-a5-rc2-pfs1.sh` | `3f9e38e3dde535d754ab01f3319d1914872bd669d1ebf3d62e6cef6c625dfa80` | 4202 single one-shot runner/preflight/ledger with incomplete-attempt guard. |

## Manifest hash changes
| File | RC2 | candidate |
|---|---|---|
| `a5_capture.py` | `a6cf0b41510b923f714eb9cddf6531cd1b20614be590645a034f5d1314592ee0` | `c67ea7bd8486892c56bacbd9bcb5e84f99d8f8c38c9a4d4625eb7720c8ec0e5a` |
| `a5_recovery.py` | `e06f814fa6079399c0b9c14c626b4126ebcdc27eeed4b1f465d7b96e704ae43c` | `632a7e3f49d918f876c96b1818bfcb85b620f5564854047479983c47470f4b53` |
