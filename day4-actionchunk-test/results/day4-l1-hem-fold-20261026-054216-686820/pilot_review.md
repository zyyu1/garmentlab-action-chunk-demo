# Hem-v10: garment turnover rather than folding

Viewed 04_transfer, 05_place and 06_final images. Final garment is broadly unfolded with sleeves on the opposite side from their initial position. Source-half centroid y ends at -.2534 m but nominal stationary-half centroid y ends at -.4897 m (initial -.2873): stationary-half mean displacement [-.03856,-.20241,.00249] m. Their final y ranges are respectively [-.3907,-.1187] and [-.6259,-.3651] m, explaining little overlap despite source-half crossing fraction 1.0.

The major stationary-half displacement appears between crossing and transfer: mean y drift -.0287 -> -.1571 m; at place -.1932 m. This is not simply a metric false negative. Existing overlap/alignment checks correctly reject whole-garment turnover. No formal success.

Next hem-v11-low-arc-fold keeps horizontal arc samples, endpoint, material and acceptance thresholds unchanged but lowers the arc lift component from radius about .234 m to .12 m (absolute apex z about .145 m). Hypothesis: reduce lifting/dragging of the nominal stationary half. Not a proven correction. Stage summaries now report its centroid displacement alongside source crossing fraction.

Local checks on actual grasp snapshot: horizontal samples and endpoint unchanged; path segments <=.025 m; maximum absolute z <.15 m; Python 3.10 syntax passes. Remote behavior pending.
