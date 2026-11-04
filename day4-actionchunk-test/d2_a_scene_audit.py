#!/usr/bin/env python3
"""D2-A: inspect the actual cloth/support physics scene used by D1-120.

This builds the same scene configuration as the diagnostic runner, performs no
episode and writes raw readbacks plus missing-item notes.
"""
import argparse
import importlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

APP = Path(__file__).resolve().parent


def jsonable(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, 'tolist'):
        return value.tolist()
    if isinstance(value, (tuple, list)):
        return [jsonable(x) for x in value]
    try:
        return [float(x) for x in value]
    except Exception:
        return repr(value)


def attr_rows(prim, needles=None):
    rows = {}
    for attr in prim.GetAttributes():
        name = attr.GetName()
        if needles and not any(n.lower() in name.lower() for n in needles):
            continue
        try:
            rows[name] = jsonable(attr.Get())
        except Exception as exc:
            rows[name] = {'read_error': repr(exc)}
    return rows


def material_rows(prim):
    rows = []
    try:
        from pxr import UsdShade
        api = UsdShade.MaterialBindingAPI(prim)
        for purpose in ('physics', 'all'):
            try:
                rel = api.GetDirectBindingRel(purpose) if purpose != 'all' else api.GetDirectBindingRel()
            except Exception:
                rel = None
            targets = []
            if rel:
                targets = [str(t) for t in rel.GetTargets()]
            if targets:
                rows.append({'purpose': purpose, 'relationship': str(rel.GetName()), 'targets': targets})
        for rel in prim.GetRelationships():
            if 'material' in rel.GetName().lower():
                targets = [str(t) for t in rel.GetTargets()]
                if targets:
                    rows.append({'relationship': str(rel.GetName()), 'targets': targets})
    except Exception as exc:
        rows.append({'error': repr(exc)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--app', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    os.environ['GARMENTLAB_ATTACHMENT_OVERLAP'] = '0.005'
    os.environ['GARMENTLAB_DISABLED_ATTACHMENT_PROBE'] = '0'
    app = args.app.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(app))
    sys.path.insert(0, '/root/autodl-tmp/garmentlab-action-chunk-demo')

    from backends.garmentlab_backend import _import_garmentlab
    from rc2_live_backend import LiveSquarePoseBackend as SquarePoseBackend
    from square_start import start_with_square
    from room_collision_control import install_room_collision_control

    class StripPoseBackend(SquarePoseBackend):
        def __init__(self, edges, *a, **k):
            self._strip_edges = list(edges)
            super().__init__(*a, **k)

        def _make_prepared_control(self, env):
            from strip_prepared_control import StripPreparedControl
            StripPreparedControl.output_directory = getattr(self, 'output_dir', None)
            return StripPreparedControl(env, self._strip_edges)

    _import_garmentlab()
    material_module = importlib.import_module('Env.Garment.Garment')
    original_material = material_module.ParticleMaterial
    original_cloth = material_module.ClothPrim
    restore_room = None
    b = None
    payload = {'created_utc': datetime.now(timezone.utc).isoformat(),
               'scope': 'D2-A actual scene readback; no episode',
               'readback': {}, 'missing': [], 'errors': []}
    try:
        restore_room = install_room_collision_control(out)

        def fixed_material(*a, **k):
            k['particle_friction_scale'] = 0.
            return original_material(*a, **k)

        def bend_cloth(*a, **k):
            k['bend_stiffness'] = 100.
            return original_cloth(*a, **k)

        material_module.ParticleMaterial = fixed_material
        material_module.ClothPrim = bend_cloth
        b = StripPoseBackend(['bottom', 'right'],
                             garment_usd=str(app / 'square_cloth_40cm.usda'),
                             prepared_grasp=True, max_action_steps=30000)
        start_with_square(b, out, .0001)
        world = b._env.world
        stage = world.stage
        garment = b._env.garment[0]
        ps = garment.particle_system
        pm = garment.particle_material
        cloth_view = garment.garment_mesh._cloth_prim_view

        def call(obj, name):
            try:
                value = getattr(obj, name)()
                return jsonable(value)
            except Exception as exc:
                return {'read_error': repr(exc)}

        payload['readback']['particle_system'] = {
            'prim_path': str(ps.prim_path),
            'particle_contact_offset': call(ps, 'get_particle_contact_offset'),
            'non_particle_collision_enabled': call(ps, 'get_non_particle_collision_enabled'),
            'global_self_collision_enabled': call(ps, 'get_global_self_collision_enabled'),
            'solver_position_iteration_count': call(ps, 'get_solver_position_iteration_count'),
            'enable_ccd': call(ps, 'get_enable_ccd'),
            'attrs': attr_rows(ps.prim, ('particle', 'collision', 'contact', 'offset', 'friction', 'filter')),
            'materials': material_rows(ps.prim),
        }
        try:
            pm_path = str(pm.prim_path)
            pm_prim = stage.GetPrimAtPath(pm_path)
            payload['readback']['particle_material'] = {
                'prim_path': pm_path,
                'prim_valid': bool(pm_prim and pm_prim.IsValid()),
                'friction': call(pm, 'get_friction'),
                'particle_friction_scale': call(pm, 'get_particle_friction_scale'),
                'damping': call(pm, 'get_damping') if hasattr(pm, 'get_damping') else 'method_missing',
                'attrs': attr_rows(pm_prim, ('friction', 'damping', 'restitution', 'material')) if pm_prim and pm_prim.IsValid() else {},
                'materials': material_rows(pm_prim) if pm_prim and pm_prim.IsValid() else [],
            }
        except Exception as exc:
            payload['errors'].append('particle_material: ' + repr(exc))
        try:
            payload['readback']['cloth_view'] = {
                'methods': [n for n in dir(cloth_view) if any(k in n.lower() for k in
                            ('contact', 'offset', 'friction', 'velocity', 'speed'))],
            }
        except Exception as exc:
            payload['errors'].append('cloth_view: ' + repr(exc))
        # All colliders and their actual material/filter/offset readbacks.
        from pxr import UsdPhysics
        colliders = []
        for prim in stage.Traverse():
            if not prim.HasAPI(UsdPhysics.CollisionAPI):
                continue
            row = {
                'path': str(prim.GetPath()), 'type': str(prim.GetTypeName()),
                'collision_enabled': None,
                'attrs': attr_rows(prim, ('collision', 'contact', 'offset',
                                          'friction', 'filter', 'particle')),
                'materials': material_rows(prim),
            }
            try:
                row['collision_enabled'] = UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()
            except Exception as exc:
                row['collision_error'] = repr(exc)
            colliders.append(row)
        payload['readback']['colliders'] = colliders
        # Cloth mesh prim and material binding.
        cloth_prim = stage.GetPrimAtPath(garment.garment_mesh_prim_path)
        payload['readback']['cloth_mesh'] = {
            'path': str(cloth_prim.GetPath()),
            'applied_schemas': [str(x) for x in cloth_prim.GetAppliedSchemas()],
            'attrs': attr_rows(cloth_prim, ('particle', 'collision', 'contact',
                                            'offset', 'friction', 'filter', 'mass')),
            'materials': material_rows(cloth_prim),
        }
        # Support surfaces: all colliders whose path looks like ground/table.
        payload['readback']['support_candidates'] = [
            r for r in colliders
            if any(k in r['path'].lower() for k in ('ground', 'table', 'floor'))
        ]
        # Explicit missing/unsupported items.
        if not payload['readback']['particle_material'].get('materials') and not payload['readback']['particle_material'].get('attrs'):
            payload['missing'].append('particle material has no readable material attrs/bindings')
        support = payload['readback']['support_candidates']
        if not support:
            payload['missing'].append('no ground/table collider found')
        if support and not any(r['materials'] for r in support):
            payload['missing'].append('support collider has no explicit physics material binding; PhysX default applies')
        if any('filter' not in json.dumps(r).lower() for r in colliders):
            payload['missing'].append('collision filter/group attrs not exposed on all colliders; inspect raw attrs')
        payload['readback']['default_ground_plane'] = [
            r for r in colliders if r['path'] == '/World/defaultGroundPlane/GroundPlane/CollisionPlane'
        ]
        payload['readback']['room_ground_plane'] = [
            r for r in colliders if r['path'].startswith('/World/Room/') and 'GroundPlane' in r['path']
        ]
    except Exception as exc:
        import traceback
        payload['errors'].append(repr(exc))
        payload['traceback'] = traceback.format_exc()
    finally:
        # Write before stopping Isaac; stop can close the process.
        try:
            (out / 'd2_a_scene_readback.json').write_text(
                json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        except Exception as exc:
            print('D2_A_WRITE_ERROR', repr(exc), flush=True)
        try:
            if b is not None:
                b.stop()
        except Exception as exc:
            payload['errors'].append('stop: ' + repr(exc))
        try:
            material_module.ParticleMaterial = original_material
            material_module.ClothPrim = original_cloth
        except Exception:
            pass
        if restore_room is not None:
            try:
                restore_room()
            except Exception:
                pass
    print('D2_A_DONE', out / 'd2_a_scene_readback.json')
    if payload['errors']:
        print('D2_A_ERRORS', payload['errors'])
    return 0 if not payload['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
