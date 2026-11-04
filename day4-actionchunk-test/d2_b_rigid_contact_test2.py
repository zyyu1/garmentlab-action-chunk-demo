#!/usr/bin/env python3
"""D2-B variant: apply contact-report APIs before reset and record all actors."""
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
    from pxr import PhysxSchema, PhysicsSchemaTools
    from omni.physx import get_physx_simulation_interface

    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()
    cube = world.scene.add(DynamicCuboid(
        prim_path='/World/TestCube', name='d2b_test_cube',
        position=np.array([0., 0., .5]), scale=np.array([.05, .05, .05]),
        color=np.array([1., 0., 0.])))
    paths = ['/World/TestCube', '/World/defaultGroundPlane/GroundPlane/CollisionPlane']
    applied = []
    for path in paths:
        prim = world.stage.GetPrimAtPath(path)
        if prim and prim.IsValid():
            api = PhysxSchema.PhysxContactReportAPI.Apply(prim)
            api.CreateThresholdAttr(0.0)
            applied.append(path)
    world.reset()
    events = []
    meta = {'applied': applied, 'callback_count': 0, 'event_count': 0, 'errors': []}

    def callback(headers, data):
        meta['callback_count'] += 1
        try:
            for h in headers:
                actors = [str(PhysicsSchemaTools.intToSdfPath(h.actor0)),
                          str(PhysicsSchemaTools.intToSdfPath(h.actor1))]
                colliders = [str(PhysicsSchemaTools.intToSdfPath(h.collider0)),
                             str(PhysicsSchemaTools.intToSdfPath(h.collider1))]
                pts = []
                for j in range(h.contact_data_offset,
                               h.contact_data_offset + h.num_contact_data):
                    c = data[j]
                    pts.append({'position': [float(v) for v in c.position],
                                'normal': [float(v) for v in c.normal],
                                'impulse': [float(v) for v in c.impulse]})
                events.append({'step': int(world.current_time_step_index),
                               'actors': actors, 'colliders': colliders,
                               'contacts': pts})
                meta['event_count'] += 1
        except Exception as exc:
            meta['errors'].append(repr(exc))

    sub = get_physx_simulation_interface().subscribe_contact_report_events(callback)
    meta['subscription_created'] = sub is not None
    positions = []
    for _ in range(180):
        world.step(render=False)
        positions.append(np.asarray(cube.get_world_pose()[0], dtype=float).tolist())
    meta['cube_final_m'] = positions[-1] if positions else None
    meta['events'] = events[:200]
    (out / 'd2_b_rigid_contact_variant.json').write_text(
        json.dumps(meta, indent=2) + '\n', encoding='utf-8')
    print('D2_B_RIGID_VARIANT callbacks=%s events=%s applied=%s final=%s' % (
        meta['callback_count'], meta['event_count'], applied, meta['cube_final_m']))
    sim.close()
    return 0 if meta['event_count'] > 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
