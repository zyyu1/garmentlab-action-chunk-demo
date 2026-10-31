# Robot-only delayed pitch: failure near joint boundaries

delayed_pitch_18 fails after 240 steps: position error .088568 m; rotation error .003349 rad (~.192 degrees). Last passing waypoint 17 position error .007108 m. Neither run grasps the garment, so the observed pose tracking failure does not require cloth loading.

At failure q4=-3.0254765 rad (~-173.347 deg), q6=3.6995265 rad (~211.967 deg). Prior captured scene audit gives q4 lower limit -176.001 deg and q6 upper limit 215.002 deg. Margins are about 2.65 and 3.04 degrees. This supports a near-boundary controller configuration; it does not prove the requested Cartesian pose has no other IK solution. Limits are from the saved scene audit, not a fresh runtime limit query from this run.

Next empty-gripper check: opposite-delayed-pitch-v2 reverses world-X pitch sign on the same XYZ path and timing schedule. +pi and -pi have the same final rotation but different intermediate poses/configurations. Preserve 10 mm position, .1 rad orientation, six consecutive reached steps, and 240-step screening budget. Save current scene revolute-joint limits for comparison. Passing this probe does not validate cloth motion or wrist retreat, and does not make the XYZ+yaw action interface support pitch.
