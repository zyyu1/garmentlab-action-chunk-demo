# RC2 drift localisation: 4202 single and 4302 single

Generated from existing RC2 evidence only; no simulation was run.

## Event table

| case | id | event | observed step | world step | sim time (s) | source |
|---|---|---|---:|---:|---:|---|
| 4202 single | E1 | last pre-release hold frame | 1942 | 1944 | 32.400002 | pre_release_hold.npz; step inferred from action_begin |
| 4202 single | E2 | release action begin (public OPEN command) | 1943 | 1945 | 32.416668 | evidence timeline action_begin |
| 4202 single | E3 | attachment release / gripper effective open | 1944 | 1946 | 32.433335 | first state with holding=false, attached=false, all enables=false |
| 4202 single | E4 | released snapshot (pre-retreat) | 1953 | 1955 | 32.583335 | evidence sample released |
| 4202 single | E5 | retreat command start | 1954 | 1956 | 32.600002 | first state with command_holding=false |
| 4202 single | E6 | retreat reaches 1 mm upward | 1955 | 1957 | 32.616668 | first state with EE z > released EE z + 1 mm |
| 4202 single | E7 | retreat end / success-trace t=0 | 2097 | 2099 | 34.983335 | evidence action_end; success_meta.absolute_step |
| 4202 single | E8 | hold_3s sample (trace step 180) | 2277 | 2279 | 37.983335 | evidence sample hold_3s; trace step 180 |
| 4202 single | E9 | formal evaluation window start (trace step 210) | 2307 | 2309 | 38.483335 | success_meta.absolute_step + 210 |
| 4202 single | E10 | hold_4s sample (trace step 240) | 2337 | 2339 | 38.983335 | evidence sample hold_4s; trace step 240 |
| 4202 single | E11 | formal evaluation window end (trace step 330) | 2427 | 2429 | 40.483335 | success_meta.absolute_step + 330 |
| 4202 single | E12 | finger / gripper to cloth contact record | missing | missing | missing | missing in RC2 evidence |
| 4302 single | E1 | last pre-release hold frame | 2359 | 2361 | 39.350002 | pre_release_hold.npz; step inferred from action_begin |
| 4302 single | E2 | release action begin (public OPEN command) | 2360 | 2362 | 39.366669 | evidence timeline action_begin |
| 4302 single | E3 | attachment release / gripper effective open | 2361 | 2363 | 39.383335 | first state with holding=false, attached=false, all enables=false |
| 4302 single | E4 | released snapshot (pre-retreat) | 2370 | 2372 | 39.533335 | evidence sample released |
| 4302 single | E5 | retreat command start | 2371 | 2373 | 39.550002 | first state with command_holding=false |
| 4302 single | E6 | retreat reaches 1 mm upward | 2372 | 2374 | 39.566669 | first state with EE z > released EE z + 1 mm |
| 4302 single | E7 | retreat end / success-trace t=0 | 2517 | 2519 | 41.983336 | evidence action_end; success_meta.absolute_step |
| 4302 single | E8 | hold_3s sample (trace step 180) | 2697 | 2699 | 44.983336 | evidence sample hold_3s; trace step 180 |
| 4302 single | E9 | formal evaluation window start (trace step 210) | 2727 | 2729 | 45.483336 | success_meta.absolute_step + 210 |
| 4302 single | E10 | hold_4s sample (trace step 240) | 2757 | 2759 | 45.983336 | evidence sample hold_4s; trace step 240 |
| 4302 single | E11 | formal evaluation window end (trace step 330) | 2847 | 2849 | 47.483336 | success_meta.absolute_step + 330 |
| 4302 single | E12 | finger / gripper to cloth contact record | missing | missing | missing | missing in RC2 evidence |

## Adjacent-event segment metrics

| case | segment | duration s | centroid mm | rotation deg | P95 mm | max mm | rigid RMS mm | per-step vertices | contact | EE dist start/end mm |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|
| 4202 single | hold_last_60 | 0.9833 | 0.0745 | -0.0324 | 0.2024 | 0.2414 | 0.0391 | True | missing | 3.804 / 3.802 |
| 4202 single | hold_end_to_released | 0.1833 | 0.8483 | 0.0689 | 13.8310 | 25.6191 | 1.8936 | False | missing | 3.802 / 21.075 |
| 4202 single | released_to_retreated | 2.4000 | 2.4849 | -0.9119 | 5.4034 | 6.2806 | 0.4136 | False | missing | 21.075 / 165.997 |
| 4202 single | retreated_to_trace0 | 0.0000 | 0.0000 | -0.0000 | 0.0000 | 0.0000 | 0.0000 | True | missing | 165.997 / 165.997 |
| 4202 single | trace0_to_60 | 1.0000 | 1.0235 | -0.3616 | 2.2149 | 2.4276 | 0.0016 | True | missing | 165.997 / 166.059 |
| 4202 single | trace0_to_hold3 | 3.0000 | 3.0713 | -1.0853 | 6.6442 | 7.2819 | 0.0012 | True | missing | 165.997 / 166.215 |
| 4202 single | hold3_to_window_start | 0.5000 | 0.5145 | -0.1816 | 1.1124 | 1.2185 | 0.0006 | True | missing | 166.215 / 166.261 |
| 4202 single | trace0_to_window_start | 3.5000 | 3.5858 | -1.2669 | 7.7576 | 8.5003 | 0.0013 | True | missing | 165.997 / 166.261 |
| 4202 single | window_start_to_hold4 | 0.5000 | 0.5110 | -0.1806 | 1.1057 | 1.2112 | 0.0009 | True | missing | 166.261 / 166.310 |
| 4202 single | hold4_to_window_end | 1.5000 | 1.5319 | -0.5398 | 3.3083 | 3.6267 | 0.0014 | True | missing | 166.310 / 166.471 |
| 4202 single | window_210_330 | 2.0000 | 2.0429 | -0.7204 | 4.4141 | 4.8379 | 0.0011 | True | missing | 166.261 / 166.471 |
| 4202 single | trace0_to_end | 5.5000 | 5.6285 | -1.9873 | 12.1710 | 13.3378 | 0.0008 | True | missing | 165.997 / 166.471 |
| 4302 single | hold_last_60 | 0.9833 | 0.0696 | -0.0436 | 0.2552 | 0.3093 | 0.0506 | True | missing | 2.047 / 2.040 |
| 4302 single | hold_end_to_released | 0.1833 | 0.9810 | 0.0737 | 15.0313 | 27.6487 | 2.0852 | False | missing | 2.040 / 21.595 |
| 4302 single | released_to_retreated | 2.4500 | 2.4384 | -0.9432 | 5.4901 | 6.4528 | 0.5180 | False | missing | 21.595 / 166.567 |
| 4302 single | retreated_to_trace0 | 0.0000 | 0.0000 | -0.0000 | 0.0000 | 0.0000 | 0.0000 | True | missing | 166.567 / 166.567 |
| 4302 single | trace0_to_60 | 1.0000 | 0.9506 | -0.3350 | 2.0556 | 2.2506 | 0.0016 | True | missing | 166.567 / 166.636 |
| 4302 single | trace0_to_hold3 | 3.0000 | 2.8628 | -1.0093 | 6.1884 | 6.7800 | 0.0011 | True | missing | 166.567 / 166.804 |
| 4302 single | hold3_to_window_start | 0.5000 | 0.4754 | -0.1673 | 1.0273 | 1.1235 | 0.0011 | True | missing | 166.804 / 166.852 |
| 4302 single | trace0_to_window_start | 3.5000 | 3.3382 | -1.1766 | 7.2166 | 7.9033 | 0.0012 | True | missing | 166.567 / 166.852 |
| 4302 single | window_start_to_hold4 | 0.5000 | 0.4768 | -0.1678 | 1.0290 | 1.1263 | 0.0010 | True | missing | 166.852 / 166.902 |
| 4302 single | hold4_to_window_end | 1.5000 | 1.4334 | -0.5041 | 3.0939 | 3.3906 | 0.0008 | True | missing | 166.902 / 167.067 |
| 4302 single | window_210_330 | 2.0000 | 1.9102 | -0.6719 | 4.1231 | 4.5169 | 0.0009 | True | missing | 166.852 / 167.067 |
| 4302 single | trace0_to_end | 5.5000 | 5.2483 | -1.8485 | 11.3397 | 12.4200 | 0.0010 | True | missing | 166.567 / 167.067 |

## Missing adjacent-event segments

The release/retreat interval has only sparse snapshots. The following adjacent event pairs cannot be computed per physical step; only E1->E4 (hold last frame to released snapshot) and E4->E7 (released to retreated) are available at snapshot level:

- 4202 single E1->E2: no per-step cloth vertices at the release action begin
- 4202 single E2->E3: no per-step cloth vertices at attachment release
- 4202 single E3->E4: no per-step cloth vertices at E3; only the E4 snapshot
- 4202 single E4->E5: no per-step cloth vertices at the retreat command start
- 4202 single E5->E6: no per-step cloth vertices at E5/E6
- 4202 single E6->E7: no per-step cloth vertices during the retreat
- 4302 single E1->E2: no per-step cloth vertices at the release action begin
- 4302 single E2->E3: no per-step cloth vertices at attachment release
- 4302 single E3->E4: no per-step cloth vertices at E3; only the E4 snapshot
- 4302 single E4->E5: no per-step cloth vertices at the retreat command start
- 4302 single E5->E6: no per-step cloth vertices at E5/E6
- 4302 single E6->E7: no per-step cloth vertices during the retreat

## Original evaluator cross-check

| case | metric | recomputed | original | abs delta | match |
|---|---|---:|---:|---:|---|
| 4202 single | centroid_drift_max_m | 0.00204288421498 | 0.00204288421498 | 0 | True |
| 4202 single | vertex_drift_p95_max_m | 0.00441411895649 | 0.00441411895649 | 0 | True |
| 4202 single | vertex_drift_max_m | 0.00483791060135 | 0.00483791060135 | 0 | True |
| 4202 single | vertex_speed_p95_max_m_s | 0.00344471238246 | 0.00344471238246 | 0 | True |
| 4202 single | vertex_speed_max_m_s | 0.0164683856734 | 0.0164683856734 | 0 | True |
| 4302 single | centroid_drift_max_m | 0.00191023287345 | 0.00191023287345 | 0 | True |
| 4302 single | vertex_drift_p95_max_m | 0.00412314717758 | 0.00412314717758 | 0 | True |
| 4302 single | vertex_drift_max_m | 0.00451694723545 | 0.00451694723545 | 0 | True |
| 4302 single | vertex_speed_p95_max_m_s | 0.00352269063377 | 0.00352269063377 | 0 | True |
| 4302 single | vertex_speed_max_m_s | 0.0165762479472 | 0.0165762479472 | 0 | True |

## Findings and missing evidence

- The pre-release hold is stable; the motion starts at/after release.
- The observed release-to-retreat interval has only the released and retreated snapshots. Per-physical-step cloth vertices and gripper opening amount are missing, so the exact onset step inside that interval cannot be localised.
- The formal 210..330 window motion is nearly rigid translation plus rotation (small rigid-fit RMS), i.e., whole-cloth sliding/rotation rather than local relaxation.
- No finger/gripper-cloth contact force or impulse trace exists in RC2. The EE-to-nearest-vertex distance is a geometric proxy, not contact. Hypotheses about robot contact remain to be tested by D1/D2.
- The original verify-dev exit code 1 is a stability rejection of the positive smoke case 4202 arc4; the RGB/video/holding evidence checks pass for all seven cases.

## Plots

- `plots/drift_4202_single.png`
- `plots/drift_4302_single.png`
