"""Process-local room collision isolation before first physics reset.

Hypothesis test only: duplicate support geometry is not yet confirmed.
"""
import json
from pathlib import Path


def install_room_collision_control(output):
    from Env.env.BaseEnv import BaseEnv
    from pxr import Usd, UsdPhysics
    original = BaseEnv.import_room
    report = {'scope': 'Disable imported room colliders; retain default ground',
              'room_colliders': [], 'outside_room_colliders': []}
    path = Path(output) / 'room_collision_audit.json'

    def wrapped(env, config):
        value = original(env, config)
        root = env.stage.GetPrimAtPath(env.room_prim_path)
        if not root.IsValid():
            raise RuntimeError('Imported room prim missing')
        for prim in Usd.PrimRange(root):
            if not prim.HasAPI(UsdPhysics.CollisionAPI):
                continue
            attr = UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr()
            before = attr.Get()
            row = {'path': str(prim.GetPath()), 'type': prim.GetTypeName(),
                   'enabled_before': before, 'disabled_by_test': False}
            if before is not False:
                if not UsdPhysics.CollisionAPI(prim).CreateCollisionEnabledAttr().Set(False):
                    raise RuntimeError('Could not disable room collider')
                row['disabled_by_test'] = True
            row['enabled_after'] = attr.Get()
            report['room_colliders'].append(row)
        prefix = str(root.GetPath()) + '/'
        for prim in env.stage.Traverse():
            name = str(prim.GetPath())
            if name == str(root.GetPath()) or name.startswith(prefix):
                continue
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                report['outside_room_colliders'].append({
                    'path': name, 'type': prim.GetTypeName(),
                    'enabled': UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()})
        path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        changed = [r for r in report['room_colliders'] if r['disabled_by_test']]
        ground = [r for r in report['outside_room_colliders']
                  if r['path'].startswith('/World/defaultGroundPlane/') and r['enabled'] is not False]
        if not changed:
            raise RuntimeError('No enabled room colliders: isolation hypothesis not applicable; inspect audit')
        if not ground or any(r['enabled_after'] is not False for r in changed):
            raise RuntimeError('Ground preservation or collision-disable check failed; inspect audit')
        print('ROOM_COLLISION_ISOLATION', json.dumps(report), flush=True)
        return value

    BaseEnv.import_room = wrapped

    def restore():
        BaseEnv.import_room = original
    return restore
