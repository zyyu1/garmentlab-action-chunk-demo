#!/usr/bin/env python3
"""D2-B: known rigid-contact validation of the existing ContactRecorder."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--app', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    app = args.app.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(app))
    sys.path.insert(0, '/root/autodl-tmp/garmentlab-action-chunk-demo')

    from backends.garmentlab_backend import _import_garmentlab
    sim = _import_garmentlab()[1]
    from omni.isaac.core import World
    from omni.isaac.core.objects import DynamicCuboid
    from square_contact_recorder import ContactRecorder

    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()
    cube = world.scene.add(DynamicCuboid(
        prim_path='/World/Franka/TestCube', name='d2b_test_cube',
        position=np.array([0., 0., .5]), scale=np.array([.05, .05, .05]),
        color=np.array([1., 0., 0.])))
    world.reset()
    rec = ContactRecorder(world, out, lambda: 'd2b_known_contact')
    positions = []
    for _ in range(180):
        world.step(render=False)
        positions.append(np.asarray(cube.get_world_pose()[0], dtype=float).tolist())
    report = rec.save()
    report['cube_start_m'] = [0., 0., .5]
    report['cube_final_m'] = positions[-1] if positions else None
    report['steps'] = 180
    report['expected'] = 'cube falls from z=0.5 m onto default ground; contact report expected'
    (out / 'd2_b_rigid_contact_report.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('D2_B_RIGID event_count=%s callback_count=%s final=%s' % (
        report.get('event_count'), report.get('callback_count'), report.get('cube_final_m')))
    sim.close()
    return 0 if report.get('event_count', 0) > 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
