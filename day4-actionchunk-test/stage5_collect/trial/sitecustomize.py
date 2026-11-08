"""Stage 5 trial overlay: read-only snapshot before each public action.

Activated only when STAGE5_OBS_DIR is set.  Patches EpisodeEvidence.emit so that
immediately after an ``action_begin`` record is written (i.e. before the action
executes) it saves one observation:

    obs/action_<call_id>_obs.npz  (vertices 441x3, ee 3, joints N)
    obs/action_<call_id>_obs.json (call_id, backend_step, sim_time_s, holding,
                                   targets, commands, horizon)

Nothing here steps physics, calls control, or writes cloth state.
"""
import builtins
import json
import os
from pathlib import Path

if os.environ.get('STAGE5_DEMO') == '1':
    import hashlib

    import a5_entry as _ae

    DEMO_DIR = Path(os.environ.get('STAGE5_DEMO_DIR',
                                   '/root/autodl-tmp/stage5-trial/collect/demo'))
    PFS = {'flat': 0.0, 'perturbed': 1.0, 'crumpled': 1.0}
    GEN = {'flat': 'day4-square-initial-demo.py',
           'perturbed': 'day4-square-initial-stripfold-demo.py',
           'crumpled': 'day4-square-initial-stripfold-demo.py'}

    def _read(p):
        return json.loads(Path(p).read_text(encoding='utf-8'))

    def _sha(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    def _demo_authorize(initial, split, execution, runner):
        _ae.preflight()
        result = _read(Path(initial) / 'result.json')
        case = result['initial_case']
        seed, level = int(case['seed']), case['level']
        if result.get('passed') is not True:
            raise ValueError('Demo initial not passed')
        if ('l1' if level == 'flat' else 'recovery') != runner:
            raise ValueError('Demo runner/task mismatch')
        lo, hi = _read(DEMO_DIR / 'stage5-demo-seeds.json')['ranges'][level]
        if not (int(lo) <= seed <= int(hi)):
            raise ValueError('Seed outside demo range')
        plan = _read(DEMO_DIR / 'stage5-demo-initial-plan.json')['episodes']
        if sum(row == case for row in plan) != 1:
            raise ValueError('Demo initial differs from registered plan')
        proto = result.get('protocol') or {}
        if proto.get('version') != 'stage4-initial-v2-task-scoped':
            raise ValueError('Demo initial protocol version')
        task = 'A_l1_overfold' if level == 'flat' else 'B_nominal'
        if (proto.get('task'), proto.get('level'), proto.get('seed')) != (task, level, seed):
            raise ValueError('Demo initial protocol identity')
        for key in ('particle_friction_scale_expected', 'particle_friction_scale_readback'):
            if abs(float(proto.get(key)) - PFS[level]) > 1e-6:
                raise ValueError('Demo initial pfs mismatch: ' + key)
        binding = proto.get('material_binding') or {}
        if binding.get('particle_material') != '/World/Garment/particleMaterial' \
                or not binding.get('particle_system'):
            raise ValueError('Demo initial material binding')
        gen = proto.get('generator') or {}
        script = GEN[level]
        if gen.get('script') != script or gen.get('script_sha256') != _sha(DEMO_DIR / script):
            raise ValueError('Demo generator identity')
        if gen.get('files_manifest') != 'stage5-demo-initial-files.json' \
                or gen.get('files_manifest_sha256') != _sha(DEMO_DIR / 'stage5-demo-initial-files.json'):
            raise ValueError('Demo files manifest identity')
        for name in ('result.json', 'initial_geometry.npz', 'initial.png'):
            if not (Path(initial) / name).is_file():
                raise ValueError('Demo initial artifact missing: ' + name)
        return {'demo': True, 'seed': seed, 'level': level}

    _ae.authorize_initial = _demo_authorize

if os.environ.get('STAGE5_OBS_DIR'):
    OBS = Path(os.environ['STAGE5_OBS_DIR'])

    def _log(obj):
        try:
            OBS.mkdir(parents=True, exist_ok=True)
            with (OBS / 'errors.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(obj) + '\n')
        except Exception:
            pass

    def _snap(evidence, row):
        import numpy as np
        b = evidence.b
        # Same-moment real holding/attachment state.  Missing holding is an
        # explicit error; never silently write false.
        state = evidence.state()
        if 'holding' not in state or not isinstance(state['holding'], bool):
            raise RuntimeError('Stage5 snapshot missing boolean holding state')
        holding = bool(state['holding'])
        # namespace per episode by the result directory name: evidence.out is
        # <result_dir>/evidence, so its parent is unique per episode.
        ep_dir = OBS / Path(str(getattr(evidence, 'out', 'unknown'))).parent.name
        vertices = np.asarray(b._garment_world_positions(), dtype=float)
        ee, quat = b._env.robots[0].get_cur_ee_pos()
        ee = np.asarray(ee, dtype=float).reshape(-1)
        quat = np.asarray(quat, dtype=float).reshape(-1)
        joints = b._env.robots[0]._robot.get_joint_positions()
        if hasattr(joints, 'detach'):
            joints = joints.detach().cpu().numpy()
        joints = np.asarray(joints, dtype=float).reshape(-1)
        cid = int(row.get('call_id') or 0)
        ep_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(ep_dir / ('action_%03d_obs.npz' % cid),
                            vertices=vertices, ee=ee, quat=quat, joints=joints)
        meta = {'call_id': cid,
                'backend_step': int(state.get('backend_step',
                                              row.get('backend_step') or -1)),
                'sim_time_s': float(row.get('sim_time_s') or 0.0),
                'holding': holding,
                'attached': bool(state.get('attached')),
                'enabled_slots': state.get('enabled_slots'),
                'logical_attached': bool(state.get('logical_attached')),
                'command_holding': bool(state.get('command_holding')),
                'state_source': 'evidence.state() immediately before action',
                'targets': row.get('targets'),
                'commands': row.get('commands'),
                'horizon': row.get('horizon'),
                'vertices_shape': list(vertices.shape),
                'quat_order': 'wxyz',
                'joints_shape': list(joints.shape),
                'episode_dir': ep_dir.name}
        with (ep_dir / ('action_%03d_obs.json' % cid)).open('w', encoding='utf-8') as f:
            json.dump(meta, f)

    def _patch(mod):
        cls = mod.EpisodeEvidence
        original_emit = cls.emit

        def emit(self, kind, **data):
            row = original_emit(self, kind, **data)
            if kind == 'action_begin':
                try:
                    _snap(self, row)
                except Exception as exc:  # never break the episode
                    _log({'error': repr(exc), 'call_id': row.get('call_id')})
            return row

        cls.emit = emit
        cls._stage5_patched = True

    _orig_import = builtins.__import__

    def _hook(name, globals=None, locals=None, fromlist=(), level=0):
        mod = _orig_import(name, globals, locals, fromlist, level)
        if (name == 'episode_evidence' or name.endswith('.episode_evidence')) \
                and hasattr(mod, 'EpisodeEvidence') \
                and not getattr(mod, '_stage5_patched', False):
            _patch(mod)
        return mod

    builtins.__import__ = _hook
