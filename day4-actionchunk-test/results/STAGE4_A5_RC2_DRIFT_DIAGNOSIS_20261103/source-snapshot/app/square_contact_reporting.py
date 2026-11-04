"""Early PhysX contact-report setup for the square diagnostics.

v4 applied PhysxContactReportAPI after env.reset(); PhysX had already created
the rigid bodies, so the run recorded zero events even though the assist blocks
were ground-supported.  This module authors the API at slot-creation time,
before reset, verifies it after reset, and creates an early RigidPrimView for
net-contact-force readback as an independent positive control.
"""
import numpy as np


def _apply(stage, path, threshold=0.0):
    from pxr import PhysxSchema
    prim = stage.GetPrimAtPath(path)
    record = {'path': path, 'prim_valid': bool(prim.IsValid())}
    if not prim.IsValid():
        record['error'] = 'missing prim'
        return record
    api = PhysxSchema.PhysxContactReportAPI.Apply(prim)
    attr = api.CreateThresholdAttr()
    if not attr.IsValid():
        record['error'] = 'threshold attribute missing'
        return record
    if not attr.Set(float(threshold)):
        record['error'] = 'threshold set failed'
        return record
    record['api'] = bool(prim.HasAPI(PhysxSchema.PhysxContactReportAPI))
    record['threshold'] = float(attr.Get())
    return record


def setup_early_contact_reporting(stage, block_paths, threshold=0.0):
    """Apply contact-report APIs before env.reset() initializes physics."""
    from pxr import UsdPhysics
    report = {'scope': 'authored before env.reset(); v4 authored after reset and saw zero events',
              'threshold': float(threshold), 'blocks': [], 'robot_bodies': [],
              'ground_colliders': [], 'errors': [],
              'applied_before_reset': True}
    for path in block_paths:
        record = _apply(stage, path, threshold)
        report['blocks'].append(record)
        if 'error' in record:
            report['errors'].append('block ' + path + ': ' + record['error'])
    for prim in stage.Traverse():
        path = str(prim.GetPath())
        if path.startswith('/World/Franka/') and prim.HasAPI(UsdPhysics.RigidBodyAPI):
            record = _apply(stage, path, threshold)
            report['robot_bodies'].append(record)
            if 'error' in record:
                report['errors'].append('robot ' + path + ': ' + record['error'])
        elif path.startswith('/World/defaultGroundPlane') and prim.HasAPI(UsdPhysics.CollisionAPI):
            report['ground_colliders'].append(path)
    return report


def verify_early_contact_reporting(stage, report):
    """Check that the early attributes survived env.reset()."""
    from pxr import PhysxSchema, UsdPhysics
    result = {'blocks': [], 'robot_bodies': [], 'ground_colliders': [],
              'all_ok': True}
    if not report:
        return {'all_ok': False, 'error': 'no early setup report'}
    if report.get('error'):
        result['all_ok'] = False
        result['error'] = report['error']
    if not report.get('blocks'):
        result['all_ok'] = False
        result['error'] = 'no early block report'
    for group in ('blocks', 'robot_bodies'):
        for record in report.get(group, []):
            path = record['path']
            prim = stage.GetPrimAtPath(path)
            api_ok = bool(prim.IsValid() and prim.HasAPI(PhysxSchema.PhysxContactReportAPI))
            threshold = None
            if api_ok:
                attr = prim.GetAttribute('physxContactReport:threshold')
                if attr.IsValid():
                    threshold = float(attr.Get())
            ok = bool(api_ok and threshold is not None and abs(threshold) <= 1e-12)
            if not ok:
                result['all_ok'] = False
            result[group].append({'path': path, 'api': api_ok,
                                  'threshold': threshold, 'ok': ok})
    result['ground_colliders'] = list(report.get('ground_colliders', []))
    # A block pair is the pre-registered block-ground positive control.
    result['blocks_ok'] = bool(result['blocks']) and all(x['ok'] for x in result['blocks'])
    result['robot_ok'] = all(x['ok'] for x in result['robot_bodies'])
    return result


def create_block_contact_force_view(world):
    """Create a pre-reset RigidPrimView over the three assist blocks.

    The view is initialized manually after env.reset(), so a failure in the
    contact-force path cannot abort the physics reset.  ``disable_stablization=False``
    preserves the experiment's original physics settings.  Construction also
    applies PhysxContactReportAPI to the blocks, which is the early-authoring
    fix by itself.
    """
    from omni.isaac.core.prims import RigidPrimView
    info = {'created': False, 'prim_paths': [], 'count': 0, 'error': None,
            'added_to_scene': False}
    view = None
    try:
        view = RigidPrimView(
            prim_paths_expr='/World/Attachment/attach.*/block',
            name='attachment_block_contact_view',
            track_contact_forces=True,
            prepare_contact_sensors=True,
            disable_stablization=False,
            max_contact_count=0,
        )
        info['prim_paths'] = list(view.prim_paths)
        info['count'] = len(info['prim_paths'])
        if info['count'] != 3:
            raise RuntimeError('Expected 3 attachment blocks, got %d' % info['count'])
        info['created'] = True
    except Exception as exc:
        info['error'] = repr(exc)
        view = None
    info['view'] = view
    return info
