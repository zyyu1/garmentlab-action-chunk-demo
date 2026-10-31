"""Day 4: three difficulty levels, 5 seeds each, screenshot initial state.

One Isaac Sim launch. Saves:
    runs/2026-10-14-difficulty/level_seed.png
And prints world-frame particle extents for sanity check.
"""

import sys, os, time, traceback
from pathlib import Path
from datetime import datetime

ROOT = Path("/root/autodl-tmp/garmentlab-action-chunk-demo")
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import numpy as np

def log(m): print(m, flush=True)

outdir = Path("/root/autodl-tmp") / (
    "difficulty-" + datetime.now().strftime("%Y%m%d-%H%M%S")
)
outdir.mkdir(parents=True, exist_ok=True)
log("OUTPUT_DIR=" + str(outdir))

from backends.garmentlab_backend import GarmentLabBackend
import imageio.v3 as iio

b = GarmentLabBackend()
log("CONSTRUCT_OK")

t0 = time.time()
b.start()
log(f"START_OK elapsed={time.time()-t0:.1f}s")

LEVELS = ["flat", "perturbed", "crumpled"]
SEEDS = [0, 1, 2, 3, 4]

try:
    for lvl in LEVELS:
        log(f"==== LEVEL {lvl} ====")
        for seed in SEEDS:
            log(f"RESET lvl={lvl} seed={seed}")
            try:
                obs = b.reset(seed=seed, difficulty=lvl)
            except Exception as e:
                log(f"RESET_FAILED lvl={lvl} seed={seed}: {e}")
                traceback.print_exc()
                continue

            # Move arm out of the view for a clean initial-state shot.
            try:
                b._env.control.robot_reset()
                for _ in range(60):
                    b._env.step()
            except Exception as e:
                log(f"ARM_RESET_WARN {e}")

            # Snapshot.
            try:
                rgb = np.asarray(b._env.camera.get_rgb_graph())
                assert rgb.ndim == 3 and rgb.shape[2] == 3 and rgb.size > 0
                name = f"{lvl}_seed{seed:02d}.png"
                iio.imwrite(outdir / name, rgb)
                log(f"SAVED {name} shape={rgb.shape}")
            except Exception as e:
                log(f"SNAPSHOT_FAILED lvl={lvl} seed={seed}: {e}")
                traceback.print_exc()

            # Report world-frame extent from observation.
            kp = obs.garment_keypoints
            center = obs.garment_center
            extent = kp.max(0) - kp.min(0)
            log(
                f"  center={center.tolist()} "
                f"kp_extent={extent.tolist()} "
                f"valid={obs.valid_keypoint_count}"
            )

    log("DIFFICULTY_SMOKE_OK")
except BaseException:
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    raise
finally:
    log("STOP_BEGIN")
    b.stop()
    log("STOP_OK")
