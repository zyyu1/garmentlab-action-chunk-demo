# Hem-v12 failure: positional tracking

Failed target fold_arc_7: xyz [-.0084406,-.5983278,.1027229] m, requested pitch 42 degrees. Measured xyz [-.0091882,-.6195217,.1226858] m. Position error 29.125 mm, exceeding the existing 10 mm check. Wrist orientation error about 1.5604 degrees relative to the grasp reference; below robot's .1 rad tolerance. Block position error relative to measured wrist offset about .05859 mm; block rotation error magnitude about .000104 rad, both within existing tolerances.

This is evidence of controller failure to reach this pose combination, not proof of absolute IK infeasibility, joint limits, or an attachment tracking failure. Do not increase timeout or relax position tolerance based on this record.

Next: standalone robot-only delayed-pitch feasibility probe, no grasp. Retain low elliptical xyz path, hold initial wrist orientation through the first half and rotate across the second half. Record position/orientation errors and joints for every waypoint; stop at first failing target. Uses the saved v12 grasp pose as a reproducible reference. 240 steps per target for screening (shorter than full pilot); failure does not prove absolute unreachability. Even a pass does not validate a loaded cloth fold or retreat.
