"""Square-only constructor configuration, restored immediately after startup."""
import importlib
import json
from pathlib import Path
import numpy as np

def start_with_square(backend,output,particle_mass):
    config_module=importlib.import_module('Env.Config.GarmentConfig')
    module=importlib.import_module('Env.Garment.Garment')
    original_config=config_module.GarmentConfig
    original_cloth=module.ClothPrim
    output=Path(output);calls=[]
    class SquareConfig(original_config):
        def __init__(self,*args,**kwargs):
            kwargs.update(pos=np.array([0.,-.45,.08]),scale=np.ones(3),ori=np.zeros(3))
            super().__init__(*args,**kwargs)
    def make_cloth(*args,**kwargs):
        if 'particle_mass' in kwargs:raise RuntimeError('Unexpected mass override')
        kwargs['particle_mass']=particle_mass
        cloth=original_cloth(*args,**kwargs)
        prim=cloth._prim
        arrays={k:np.asarray(prim.GetAttribute(k).Get()) for k in ['points','faceVertexCounts','faceVertexIndices']}
        assert arrays['points'].shape==(441,3)
        assert np.allclose(np.ptp(arrays['points'],axis=0),[.4,.4,0],atol=1e-6)
        np.savez_compressed(output/'cloth_constructed.npz',**arrays)
        usd_mass=float(prim.GetAttribute('physics:mass').Get())
        assert np.isclose(usd_mass,441*particle_mass,rtol=1e-5)
        calls.append({'particle_mass':particle_mass,'total_mass':usd_mass,'vertices':441})
        return cloth
    config_module.GarmentConfig=SquareConfig;module.ClothPrim=make_cloth
    try:backend.start()
    finally:config_module.GarmentConfig=original_config;module.ClothPrim=original_cloth
    assert len(calls)==1
    data={'constructor':calls[0],'reads':{}}
    def capture(label):
        view=backend._env.garment[0].garment_mesh._cloth_prim_view
        assert view._physics_view is not None
        masses=backend._to_numpy(view.get_particle_masses(clone=True))
        np.save(output/('particle_masses_'+label+'.npy'),masses)
        assert masses.shape==(1,441) and np.isfinite(masses).all()
        assert np.allclose(masses,particle_mass,rtol=.001,atol=0)
        data['reads'][label]={'total_kg':float(masses.sum()),'min_kg':float(masses.min()),'max_kg':float(masses.max())}
        (output/'mass_audit.json').write_text(json.dumps(data,indent=2))
    capture('after_start')
    world=backend._env.control.rest_world
    assert np.allclose(np.ptp(world,axis=0),[.4,.4,0],atol=1e-5)
    assert np.allclose((world.min(axis=0)+world.max(axis=0))/2,[0,-.45,.08],atol=1e-5)
    return capture
