#!/usr/bin/env python3
"""D2-B: known particle-cloth/ground contact test for the contact channel."""
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
    from Env.Config.GarmentConfig import GarmentConfig
    from Env.Garment.Garment import Garment
    from pxr import PhysxSchema, PhysicsSchemaTools, UsdPhysics
    from omni.physx import get_physx_simulation_interface

    world = World(stage_units_in_meters=1.0, backend='torch', device='cuda')
    world.get_physics_context().enable_gpu_dynamics(True)
    world.scene.add_default_ground_plane()
    config = GarmentConfig(
        usd_path=str(app / 'square_cloth_40cm.usda'),
        pos=np.array([0., 0., .20]), ori=np.zeros(3), scale=np.ones(3),
        visual_material_usd=None, particle_contact_offset=.01)
    garment = Garment(world, config)
    added_to_scene = False
    try:
        world.scene.add(garment.garment_mesh)
        added_to_scene = True
    except Exception as exc:
        # The cloth may already be registered; keep the error for the report.
        scene_add_error = repr(exc)
    paths = ['/World/defaultGroundPlane/GroundPlane/CollisionPlane',
             '/World/Garment/particleSystem',
             '/World/Garment/garment/mesh']
    applied = []
    apply_errors = []
    for path in paths:
        prim = world.stage.GetPrimAtPath(path)
        if not prim or not prim.IsValid():
            apply_errors.append([path, 'missing'])
            continue
        try:
            api = PhysxSchema.PhysxContactReportAPI.Apply(prim)
            api.CreateThresholdAttr(0.0)
            applied.append(path)
        except Exception as exc:
            apply_errors.append([path, repr(exc)])
    world.reset()
    events = []
    meta = {'applied': applied, 'apply_errors': apply_errors,
            'added_to_scene': added_to_scene,
            'scene_add_error': locals().get('scene_add_error'),
            'callback_count': 0, 'event_count': 0, 'errors': []}

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
    zmin = []
    for _ in range(180):
        world.step(render=False)
        try:
            pos = garment.garment_mesh._cloth_prim_view.get_world_positions()
            if hasattr(pos, 'detach'):
                pos = pos.detach().cpu().numpy()
            pos = np.asarray(pos, dtype=float).reshape(-1, 3)
            zmin.append(float(pos[:, 2].min()))
        except Exception as exc:
            meta['errors'].append('zmin: ' + repr(exc))
            zmin.append(None)
    meta['zmin_first'] = zmin[0]
    meta['zmin_last'] = zmin[-1]
    meta['zmin_min'] = min(x for x in zmin if x is not None) if any(x is not None for x in zmin) else None
    meta['events'] = events[:200]
    meta['expected'] = 'particle cloth at z=0.20 m falls to default ground'
    (out / 'd2_b_cloth_contact_report.json').write_text(
        json.dumps(meta, indent=2) + '\n', encoding='utf-8')
    print('D2_B_CLOTH callbacks=%s events=%s zmin=%s applied=%s errors=%s' % (
        meta['callback_count'], meta['event_count'], meta['zmin_min'],
        applied, meta['errors']))
    sim.close()
    return 0 if meta['event_count'] > 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
