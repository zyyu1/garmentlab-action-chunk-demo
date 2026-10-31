# Hem-v8: release stabilized, folding still fails

Readback: material friction remains 0.3000000119; particle friction scale changes 1 -> 0 immediately before release. Initial and 05_place vertex arrays exactly match hem-v6. This isolates the material's particle-particle friction scale intervention at matched observed pre-release geometry.

End of released_stationary centroid speed: 0.000596 m/s. Final 60 steps centroid speed mean 0.000963 m/s, max 0.002076 m/s. Centroid ranges across these samples: [0.000151,0.0000901,0.0000404] m. These are centroid measures, not proof of all-particle equilibrium. Final centroid approximately [0.005112,-0.309360,0.020863] m. Unlike v6/v7, the cloth does not continue to escape.

Viewed 05_place, 05b_stationary, 06_final. The garment unfolds after opening and stays on the surface. Alignment about 0.13994 m, IoU about 0.0370, crossed fraction about 0.34748; no fold success or formal Day4 acceptance.

Evidence strongly implicates particle-particle friction interactions in the observed runaway under this setup. It does not identify the solver's internal defect or establish real material fidelity.

Next hem-v9-fixed-particle-friction applies scale=0 in the ParticleMaterial constructor before first reset and retains friction=.3 throughout. No release-time parameter switch. Keep existing trajectory for this validation; initial geometry may differ, so do not claim a matched-state comparison. This remains a development candidate. If stable, subsequent work returns to grasp/path and fold retention rather than more broad physics scans.

Local validation of v9: Python 3.10 syntax; constructor keyword checked against installed SDK source captured locally. Remote physical validation pending.
