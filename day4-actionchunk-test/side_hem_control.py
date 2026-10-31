"""Fixed-asset oracle candidate: single right hem side-edge grasp, development only."""
import numpy as np
from pxr import UsdGeom
import multi_prepared_grasp_control as multi
from single_anchor_hem_control import SingleAnchorHemControl

class SideHemControl(SingleAnchorHemControl):
    def __init__(self,env):
        mesh=UsdGeom.Mesh(env.world.stage.GetPrimAtPath(env.garment[0].garment_mesh_prim_path))
        points=np.asarray(mesh.GetPointsAttr().Get(),dtype=float)
        expected=np.array([14.765658378601074,57.31283187866211,2.6692309379577637])
        if points.shape!=(9945,3) or not np.allclose(points[1547],expected,rtol=0,atol=1e-5):
            raise RuntimeError('Side-hem oracle asset guard failed; do not guess another index')
        counts=np.asarray(mesh.GetFaceVertexCountsAttr().Get())
        faces=np.asarray(mesh.GetFaceVertexIndicesAttr().Get())
        if not np.all(counts==3):raise RuntimeError('Expected triangle mesh')
        faces=faces.reshape(-1,3)
        neighbors=set(faces[np.any(faces==1547,axis=1)].ravel().tolist())
        if neighbors!={1546,1547,1548,1567,1673}:
            raise RuntimeError('Side-hem topology guard failed')
        original=multi.select_regions
        def selected(world):
            regions=original(world)
            regions[2]=('hem',1547)
            if any(np.linalg.norm(world[1547]-world[i])<.05 for _,i in regions[:2]):
                raise RuntimeError('Side-hem region too close to sleeve slot')
            return regions
        multi.select_regions=selected
        try:super().__init__(env)
        finally:multi.select_regions=original
