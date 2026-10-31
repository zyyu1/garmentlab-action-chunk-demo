# Hem-v6 room collision isolation review

room_collision_audit.json confirms one imported collider disabled:
/World/Room/room/FlatGrid/GroundPlane/CollisionPlane (Plane, true -> false).
The default /World/defaultGroundPlane/GroundPlane/CollisionPlane remained enabled.

The release trace has 74 frames and stops during released_stationary. The centroid starts at approximately (-0.00633,-0.25108,0.03836) m and ends at (-0.22298,-1.83014,0.03627) m. The robot and attachment block remain essentially stationary. Removing the duplicated room collider did not eliminate the runaway motion. Initial/contact states changed, so this is not a matched-release-state comparison with hem-v5.

Official background (not proof of this run's root cause): NVIDIA Omni Physics 107.2 known limitations lists particle drift on flat surfaces due to solver ghost forces, and notes that particle friction uses the particle actor's material rather than friction combine modes:
https://docs.omniverse.nvidia.com/kit/docs/omni_physics/107.2/dev_guide/guides/current_limitations.html
This documentation is not a version-specific diagnosis of the installed Isaac Sim 4.0 stack.

Next bounded diagnostic: hem-v7-release-friction-probe repeats v6 up to 05_place and changes only particle material friction from 0.3 to 0 immediately before release, using the setter/getter in the locally captured SDK. It does not reset particle velocity. It retains the single ground configuration, recorded release trace and 2 m stop bound. Material friction affects particle-rigid and particle-particle contacts: a positive result would implicate this material's friction interactions, not uniquely identify ground friction. Actual matched pre-release geometry must be verified from NPZ after running.

This diagnostic is not an eligible Day4 expert episode regardless of provisional geometry checks. No physical result yet. Local Python 3.10 syntax validation only.
