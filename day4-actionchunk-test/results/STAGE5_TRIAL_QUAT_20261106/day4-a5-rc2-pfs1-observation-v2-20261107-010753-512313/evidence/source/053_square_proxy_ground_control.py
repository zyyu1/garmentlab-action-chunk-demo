"""Development v6: exclude only auxiliary proxies from the ground plane."""
from pxr import UsdPhysics
from square_probe_control import SquareProbeControl

GROUND = '/World/defaultGroundPlane/GroundPlane/CollisionPlane'


class SquareProxyGroundControl(SquareProbeControl):
    def __init__(self, env):
        super().__init__(env)
        stage = self.world.stage
        ground = stage.GetPrimAtPath(GROUND)
        if not ground.IsValid() or not ground.HasAPI(UsdPhysics.CollisionAPI):
            raise RuntimeError('Expected ground collider missing')
        self.proxy_ground_before = {}
        for slot in self.slots:
            prim = stage.GetPrimAtPath(slot.block.block_path)
            if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
                raise RuntimeError('Expected auxiliary rigid body missing')
            api = UsdPhysics.FilteredPairsAPI.Apply(prim)
            relation = api.CreateFilteredPairsRel()
            self.proxy_ground_before[slot.block.block_path] = [str(p) for p in relation.GetTargets()]
            if not relation.AddTarget(ground.GetPath()):
                raise RuntimeError('Could not filter proxy-ground pair')
        self.proxy_ground_authored = self.verify_proxy_ground()

    def verify_proxy_ground(self):
        rows = []
        for slot in self.slots:
            prim = self.world.stage.GetPrimAtPath(slot.block.block_path)
            targets = [str(p) for p in UsdPhysics.FilteredPairsAPI(prim).GetFilteredPairsRel().GetTargets()]
            expected = set(self.proxy_ground_before[slot.block.block_path]) | {GROUND}
            enabled = UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()
            if set(targets) != expected or enabled is not True:
                raise RuntimeError('Proxy pair filter or collision enable readback mismatch')
            rows.append({'body': slot.block.block_path, 'filtered_pairs': targets, 'collision_enabled': enabled})
        return rows

    def initialize(self):
        super().initialize()
        self.proxy_ground_after_reset = self.verify_proxy_ground()
