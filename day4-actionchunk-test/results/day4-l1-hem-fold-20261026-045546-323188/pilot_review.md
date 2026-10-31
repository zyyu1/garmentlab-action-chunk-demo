# Hem-v7 release-friction comparison

Compared with hem-v6 (day4-l1-hem-fold-20261026-044315-574384), vertices at 00_initial, 01_grasp and 05_place are exactly identical (maximum vertex displacement zero). Result records material friction 0.3000000119 -> 0.0 immediately before release. This is a matched pre-release geometry comparison; no claim that all hidden solver states have been compared.

V6 stops after 74 release samples with centroid speed about 2.780 m/s. V7 completes 613 samples; peak centroid speed about 0.781 m/s, final speed about 0.411 m/s. V7 stationary-period end speed is about 0.099 m/s, but later motion continues. Final centroid (1.71846,-1.20349,0.02265) m. Speeds are adjacent centroid differences divided by 1/60 s. Different run durations mean their peaks should not be interpreted as a controlled fixed-window effect size.

Viewed 05_place and 06_final PNGs. Final garment is outside the camera image. Pipeline completion is not stability or fold success: alignment mean 0.1342 m, occupancy IoU 0.0358, crossed fraction 0. No formal Day4 acceptance.

Material friction zero affects both rigid contacts and particle-particle contacts; it cannot attribute the change uniquely to ground or self-contact friction. Do not adopt zero total friction as a successful expert configuration.

Next hem-v8-particle-friction-probe uses the captured installed SDK's set_particle_friction_scale(0.0) immediately before release, keeping material friction at .3. Verify both readbacks and pre-release geometry. This remains a diagnostic intervention, not a formally eligible episode. No particle velocity resets or acceptance-threshold changes. Locally syntax checked, not physically validated.
