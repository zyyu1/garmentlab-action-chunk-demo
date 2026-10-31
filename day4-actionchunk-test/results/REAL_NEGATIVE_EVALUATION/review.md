# Real negative examples — development metrics

| Example | Alignment mm | Particle IoU | Reflection error mm | Fixed-half drift mm |
|---|---:|---:|---:|---:|
| flat_seed_4100 | 115.238 | 0.0000 | 219.997 | 0.000 |
| flat_seed_4101 | 115.238 | 0.0000 | 219.999 | 0.000 |
| flat_seed_4102 | 115.238 | 0.0000 | 220.000 | 0.000 |
| flat_seed_4103 | 115.238 | 0.0000 | 220.000 | 0.000 |
| flat_seed_4104 | 115.238 | 0.0000 | 220.000 | 0.000 |
| flat_seed_4105 | 115.238 | 0.0000 | 220.000 | 0.000 |
| flat_seed_4106 | 115.238 | 0.0000 | 220.000 | 0.000 |
| flat_seed_4107 | 115.238 | 0.0000 | 220.000 | 0.000 |
| flat_seed_4108 | 115.238 | 0.0000 | 220.000 | 0.000 |
| flat_seed_4109 | 115.238 | 0.0000 | 220.000 | 0.000 |
| held_before_release | 115.235 | 0.0000 | 217.315 | 10.571 |
| after_release_and_30_steps | 115.238 | 0.0000 | 217.279 | 10.170 |

All success fields remain null. These examples are excluded from formal attempts.
Ten flat states are evaluated against themselves to characterize the unfolded baseline, not independent rollouts.
The two grasp snapshots share one run and are not independent episodes.
No real successful fold exists here; classification accuracy and thresholds remain unvalidated.
