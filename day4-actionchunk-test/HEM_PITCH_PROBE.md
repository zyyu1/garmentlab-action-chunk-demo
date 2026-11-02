# hem-v12-pitch-arc-probe

## Motivation and limits

Inspection found HemPreparedGraspControl._tick always commanded zero block angular velocity while following position. Multiple paired anchors constrain a finite cloth patch. This can oppose the local orientation reversal required by a fold; it is a hypothesis, not a proven cause of v11 recoil.

The new pilot retains v11 low arc, fixed material configuration and geometry thresholds. After grasp it records the measured wrist and block reference rotations. Each arc waypoint requests world-X rotation -pi*i/N relative to the reference wrist; MyFranka.move/reach accept the wxyz quaternion through the repository's Env.Utils.transforms wrapper (four-component input passes through unchanged).

The block follows the **measured** wrist rotation relative to its reference, preserving its initial relative orientation. It does not rotate ahead to the commanded wrist angle. Angular velocity uses a world rotation-vector error divided by dt, capped at 1 rad/s. Existing linear velocity cap .3 m/s and positional tolerances remain. Holding convergence also requires block rotation error <.03 rad; existing robot rotation check is <.1 rad. Existing 1000-step timeout remains. Reachability is not established locally.

Final wrist pitch is retained during release/retreat to avoid an unplanned wrist reset. The block stays after constraint removal as before. No particle positions/velocities, springs or mass are modified during actions.

## Interface restriction

set_fold_angle is a pilot-only side channel, outside the current CartesianAction XYZ+yaw schema. Each action and pending failed action records pilot_fold_angle_rad; snapshots include actual wrist/block quaternions and block tracking error. This run is diagnostic only, never a policy demonstration or formal Stage 4 success. If full pitch proves necessary, the action representation and public backend require an explicit design/update before data collection.

## Validation

Python 3.10 syntax passed. Extracted pure rotation methods were tested with nonidentity initial wrist/block quaternions: zero/90/180-degree target composition, no block command before the measured wrist moves, correct world-X error, and zero error when block catches up. This is not Isaac physics testing. Source inspection verified the quaternion passthrough in MyFranka's conversion helper. Dependency manifest refreshed.

Upload day4-l1-hem-fold.py, hem_prepared_grasp_control.py, run-l1-hem-fold.sh, l1-hem-files.json; other dependencies are unchanged. Run the existing runner. Save failures rather than loosening angle or reach tolerances.
