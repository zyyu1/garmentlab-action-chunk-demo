"""Standalone capability probe, not a garment rollout or calibrated grasp."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import traceback
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--case', choices=['rigid', 'disabled', 'enabled'], required=True)
parser.add_argument('--output', required=True)
args, _ = parser.parse_known_args()
out = Path(args.output) / args.case
out.mkdir(parents=True, exist_ok=False)
shutil.copy2(__file__, out / Path(__file__).name)
result = {'probe_version': 'attachment-canary-mass-v2', 'case': args.case, 'completed': False, 'formal_day4_success': False,
          'dt': 1/120, 'pre_release_steps': 120, 'post_release_steps': 60,
          'errors': [], 'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
app = None
trace = []
try:
    from isaacsim import SimulationApp
    app = SimulationApp({'headless': True})
    from pxr import UsdGeom, UsdPhysics, PhysxSchema, Gf, Sdf, Vt
    from omni.isaac.core import World
    from omni.physx.scripts import particleUtils
    import omni.physics.tensors as tensors
    from scipy.spatial.transform import Rotation

    world = World(stage_units_in_meters=1., physics_dt=1/120, rendering_dt=1/120,
                  backend='torch', device='cuda:0')
    stage = world.stage
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    scene_path = world.get_physics_context().prim_path
    scene = UsdPhysics.Scene.Get(stage, scene_path)
    scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0, 0, -1))
    scene.CreateGravityMagnitudeAttr().Set(9.81)
    phys = PhysxSchema.PhysxSceneAPI.Apply(scene.GetPrim())
    phys.CreateEnableGPUDynamicsAttr().Set(True)
    phys.CreateBroadphaseTypeAttr().Set('GPU')
    phys.CreateSolverTypeAttr().Set('TGS')
    carrier = UsdGeom.Sphere.Define(stage, '/World/Carrier')
    carrier.CreateRadiusAttr().Set(.01)
    carrier.AddTranslateOp().Set(Gf.Vec3d(0, 0, 1))
    carrier.AddOrientOp().Set(Gf.Quatf(1))
    # No CollisionAPI: attachment is the only cloth-to-carrier coupling.
    rigid = UsdPhysics.RigidBodyAPI.Apply(carrier.GetPrim())
    rigid.CreateRigidBodyEnabledAttr().Set(True)
    rigid.CreateKinematicEnabledAttr().Set(False)
    rigid.CreateVelocityAttr().Set(Gf.Vec3f(0))
    rigid.CreateAngularVelocityAttr().Set(Gf.Vec3f(0))
    mass = UsdPhysics.MassAPI.Apply(carrier.GetPrim())
    mass.CreateMassAttr().Set(.02)
    mass.CreateDiagonalInertiaAttr().Set(Gf.Vec3f(.0001))
    mass.CreateCenterOfMassAttr().Set(Gf.Vec3f(.05 if args.case == 'rigid' else 0, 0, 0))
    joint = UsdPhysics.SphericalJoint.Define(stage, '/World/Pivot')
    # Empty body0 = world; no angular drives or cone limits authored.
    joint.CreateBody1Rel().SetTargets([carrier.GetPath()])
    joint.CreateLocalPos0Attr().Set(Gf.Vec3f(0, 0, 1))
    joint.CreateLocalPos1Attr().Set(Gf.Vec3f(0))
    joint.CreateJointEnabledAttr().Set(True)
    points = np.array([[.08 + .02*i, -.02 + .02*j, 1.] for j in range(3) for i in range(7)])
    ids = np.array([0, 14])
    attachment = None
    if args.case != 'rigid':
        system_path = Sdf.Path('/World/Particles')
        particleUtils.add_physx_particle_system(stage, system_path, simulation_owner=Sdf.Path(scene_path),
            contact_offset=.003, rest_offset=.001, particle_contact_offset=.003,
            solid_rest_offset=.001, solver_position_iterations=16,
            global_self_collision_enabled=False, non_particle_collision_enabled=False)
        mesh = UsdGeom.Mesh.Define(stage, '/World/Cloth')
        mesh.CreatePointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*map(float,p)) for p in points]))
        faces = []
        for j in range(2):
            for i in range(6):
                a = j*7+i
                faces.extend([a,a+1,a+7,a+1,a+8,a+7])
        mesh.CreateFaceVertexCountsAttr().Set([3]*24)
        mesh.CreateFaceVertexIndicesAttr().Set(faces)
        mesh.CreateSubdivisionSchemeAttr().Set('none')
        mesh.CreateVelocitiesAttr().Set(Vt.Vec3fArray([Gf.Vec3f(0)]*len(points)))
        particleUtils.add_physx_particle_cloth(stage, mesh.GetPath(), None, system_path,
            spring_stretch_stiffness=10000., spring_bend_stiffness=100.,
            spring_shear_stiffness=100., spring_damping=.2, self_collision=False,
            self_collision_filter=True)
        UsdPhysics.MassAPI.Apply(mesh.GetPrim()).CreateMassAttr().Set(.021)
        attachment = PhysxSchema.PhysxPhysicsAttachment.Define(stage, '/World/Attachment')
        attachment.CreateActor0Rel().SetTargets([mesh.GetPath()])
        attachment.CreateActor1Rel().SetTargets([carrier.GetPath()])
        attachment.CreatePoints0Attr().Set(Vt.Vec3fArray([Gf.Vec3f(*map(float,p)) for p in points[ids]]))
        attachment.CreatePoints1Attr().Set(Vt.Vec3fArray([Gf.Vec3f(*map(float,p)) for p in points[ids]-[0,0,1]]))
        attachment.CreateAttachmentEnabledAttr().Set(args.case == 'enabled')
    stage.GetRootLayer().Export(str(out/'authored.usda'))
    world.reset()
    view = tensors.create_simulation_view('torch')
    view.set_subspace_roots('/')
    body = view.create_rigid_body_view('/World/Carrier')
    cloth = view.create_particle_cloth_view('/World/Cloth') if attachment else None
    def array(x):
        return x.detach().cpu().numpy().copy()
    result['runtime_mass'] = array(body.get_masses()).tolist()
    result['runtime_inertia'] = array(body.get_inertias()).tolist()
    assert body.count == 1
    if cloth is not None:
        assert cloth.count == 1
        assert array(cloth.get_positions()).size == len(points)*3
    particle_masses = None
    if cloth is not None:
        result['cloth_mass_readbacks'] = {}
        result['cloth_authored_total_mass_kg'] = float(UsdPhysics.MassAPI(mesh.GetPrim()).GetMassAttr().Get())
    def capture_mass(step):
        masses = array(cloth.get_masses()).reshape(-1)
        if masses.shape != (len(points),) or not np.isfinite(masses).all() or not (masses > 0).all():
            raise RuntimeError('Invalid runtime cloth particle masses')
        result['cloth_mass_readbacks'][str(step)] = {
            'particle_masses_kg': masses.tolist(), 'total_kg': float(masses.sum()),
            'min_kg': float(masses.min()), 'max_kg': float(masses.max()),
            'matches_authored_total_rtol_0_002': bool(np.isclose(masses.sum(), .021, rtol=.002, atol=0)),
            'unchanged_from_start': particle_masses is None or bool(np.array_equal(masses, particle_masses))}
        return masses
    if cloth is not None:
        particle_masses = capture_mass(0)
    def record(step):
        t = array(body.get_transforms()).reshape(-1,7)[0]  # tensor API quaternion xyzw
        velocity = array(body.get_velocities()).reshape(-1,6)[0]
        rot = Rotation.from_quat(t[3:])
        pivot_error = np.linalg.norm(t[:3]-[0,0,1])
        row = {'step':step, 'transform_xyzw':t.tolist(), 'velocity':velocity.tolist(),
               'angle_rad':float(rot.magnitude()), 'rotvec':rot.as_rotvec().tolist(),
               'pivot_error_m':float(pivot_error)}
        if cloth is not None:
            v = array(cloth.get_positions()).reshape(-1,3)
            if step in (120, 180):
                capture_mass(step)
            center = np.average(v, axis=0, weights=particle_masses)
            # External gravity moment of the entire cloth, NOT attachment reaction torque.
            gravity_moment = np.cross(v-[0,0,1], particle_masses[:,None]*np.array([0.,0.,-9.81])).sum(axis=0)
            row.update(cloth_mass_centroid_m=center.tolist(),
                       cloth_gravity_moment_about_pivot_Nm=gravity_moment.tolist())
            desired = rot.apply(points[ids]-[0,0,1])+t[:3]
            row.update(vertices=v.tolist(), anchor_error_m=float(np.linalg.norm(v[ids]-desired,axis=1).max()),
                       anchor_z_mean=float(v[ids,2].mean()),
                       enabled=bool(attachment.GetAttachmentEnabledAttr().Get()))
            assert np.isfinite(v).all()
        assert np.isfinite(t).all() and np.isfinite(velocity).all()
        trace.append(row)
    record(0)
    for step in range(1,181):
        if step == 121 and attachment is not None:
            assert attachment.GetAttachmentEnabledAttr().Set(False)
        world.step(render=False)
        record(step)
        if trace[-1]['pivot_error_m'] > .02:
            raise RuntimeError('Pivot error exceeded 20mm diagnostic stop')
    result['completed'] = True
except Exception:
    result['errors'].append(traceback.format_exc())
    print(result['errors'][-1], flush=True)
finally:
    (out/'trace.json').write_text(json.dumps(trace,indent=2), encoding='utf8')
    (out/'result.json').write_text(json.dumps(result,indent=2), encoding='utf8')
    print('CASE_RESULT',out/'result.json',flush=True)
    if app is not None:
        app.close()
if not result['completed']:
    raise SystemExit(1)
