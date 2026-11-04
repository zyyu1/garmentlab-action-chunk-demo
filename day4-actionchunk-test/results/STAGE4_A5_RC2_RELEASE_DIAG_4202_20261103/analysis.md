# RC2 release-window diagnostic: 4202 single

Source: `E:\learning\project\thesis\day4-actionchunk-test\results\day4-a5-rc2-drift-diag-20261104-053151-197013`

## Phase table

| phase | steps | duration s | centroid mm | rotation deg | P95 mm | max mm | rigid RMS mm | speed P95 / max mm/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| anchor_1943_to_release_1944 | 1943-1944 | 0.0167 | 0.1361 | 0.0012 | 0.7420 | 10.9082 | 0.2672 | 44.5207 / 654.4936 |
| opening_1944_to_released_1953 | 1944-1953 | 0.1500 | 0.7287 | 0.0676 | 12.1159 | 24.4464 | 1.7287 | 80.7730 / 162.9758 |
| released_1953_to_command_1954 | 1953-1954 | 0.0167 | 0.1943 | -0.0566 | 0.6956 | 1.0855 | 0.2284 | 41.7385 / 65.1312 |
| command_1954_to_1mm_1955 | 1954-1955 | 0.0167 | 0.1946 | -0.0519 | 0.9485 | 1.8848 | 0.2492 | 56.9107 / 113.0850 |
| retreat_1955_to_end_2097 | 1955-2097 | 2.3667 | 2.2770 | -0.8035 | 4.8870 | 5.4199 | 0.0943 | 2.0649 / 2.2901 |
| opening_total_1943_to_1953 | 1943-1953 | 0.1667 | 0.8483 | 0.0689 | 13.8310 | 25.6191 | 1.8936 | 82.9862 / 153.7143 |
| retreat_total_1953_to_2097 | 1953-2097 | 2.4000 | 2.4849 | -0.9119 | 5.4034 | 6.2806 | 0.4136 | 2.2514 / 2.6169 |
| total_1943_to_2097 | 1943-2097 | 2.5667 | 2.9999 | -0.8438 | 14.2201 | 26.0817 | 1.8419 | 5.5403 / 10.1617 |

## Events

| id | event | step | sim s |
|---|---|---:|---:|
| A | anchor / last pre-release hold state | 1943 | 32.416668 |
| B | attachment release / opening starts | 1944 | 32.433335 |
| C | released snapshot / retreat not yet commanded | 1953 | 32.583335 |
| D | retreat command start | 1954 | 32.600002 |
| E | retreat reaches 1 mm upward | 1955 | 32.616668 |
| F | retreat end / success-trace t0 | 2097 | 34.983335 |

## Findings

- The release/opening phase (1943→1953) is a **local, non-rigid** transient: aperture opens 0→80 mm, EE z stays at ~46.8 mm, centroid peaks ~1.24 mm at 1948 and recoils to 0.85 mm by 1953; P95 grows to ~13.8 mm and max to ~25.6 mm.
- The retreat phase (1955→2097) is **nearly rigid**: centroid 2.28 mm, rotation -0.80°, P95 4.89 mm, rigid RMS 0.094 mm; the local release deformation persists but the retreat adds a rigid translation/rotation.
- The formal 210–330 window then continues the rigid sliding/rotation and fails the 1 mm / 3 mm limits; the release transient is the local-deformation source, the retreat/window the rigid-motion source.
- Contact channel: subscription created, 0 events. This is not evidence of no contact. EE distance is 3.8 mm at the anchor, 14.7 mm after release, 21.1 mm at the released snapshot, and 166.0 mm at the retreat end. Finger-link distance is unavailable (0 finite values); only EE distance is reported.
- v1.1 run: the anchor is emitted as `release_anchor` (non-state) and action targets are compared at float32; the diagnostic is complete and no physics/control/action change occurred. v1 had `complete=False` because `release_diag_action_target` compared the float32 recorded target to the float64 result target with atol 1e-9 (float32 cast is exactly equal; max float64 diff 1.26e-8 m) and `evidence continuous_steps` saw the anchor as a duplicate `state` at step 1943. Neither was a physics/action change.
