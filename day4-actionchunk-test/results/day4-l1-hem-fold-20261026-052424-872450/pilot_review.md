# Hem-v9: stable release, fold recoil

Stage geometry identifies both dragging and recoil. The source half's fraction beyond the initial fold line is .043 at crossing, .918 at transfer, .969 at place, .785 just after release, and 0 after the stationary period. The nominal stationary half moves in mean y by -0.083 m at place and -0.140 m at final. The selected hem vertex moves from y=-.197 at place to y=-.797 after release/settling (about .60 m recoil). Final PNG shows an unfolded garment.

Fixed particle friction configuration prevents the prior runaway in this run, but does not preserve the fold. These geometric observations do not uniquely identify stored elastic energy, bending resistance or contact mechanics as the cause. No formal Day4 success.

Next hem-v10-arc-fold changes the transfer trajectory only: sampled semicircle about the initial fold line, with gripper z interpolating from grasp height to .03 m underneath the circular lift component. Maximum nominal segment length .025 m. Same candidate material configuration, release, settle and provisional thresholds. The arc is a geometric path candidate, not guaranteed cloth isometry. It aims to reduce the dragging associated with the old vertical-lift/diagonal-transfer path.

Local checks: actual grasp snapshot used to check mirror endpoint, exact midpoint fold-line crossing, monotonic y, and segment lengths <=.025 m; Python 3.10 syntax passed. Physical reachability and fold retention still require the remote run.
