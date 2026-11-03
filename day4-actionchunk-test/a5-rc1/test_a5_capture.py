"""Exercise the real C recorder, A5 bridge, B evaluator and evidence acceptance gate."""
from pathlib import Path
from types import SimpleNamespace as NS
import json
import sys
import tempfile
import unittest

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from episode_evidence import EpisodeEvidence
from test_episode_evidence import FakeBackend
from test_stage4_success_v1 import fixture
from a5_capture import release_window, finish_metadata
from a5_entry import assess, read, MANIFEST


class Backend(FakeBackend):
    def __init__(self, vertices, skip_step=None):
        super().__init__()
        self.vertices = vertices
        self.skip_step = skip_step
        self._gripper_state = 0
        self.world.current_time_step_index = 0
        self._env.control.slots = [NS(attachment_enabled=lambda: False) for _ in range(3)]
        self._env.control.robot_goto_position = self.move

    def move(self, pos, *args):
        self.ee = np.asarray(pos[0])
        self.world.step()

    def step(self, **kwargs):
        super().step(**kwargs)
        self.world.current_time_step_index += 2 if self.world.current_time_step_index==self.skip_step else 1

    def _garment_world_positions(self):
        return self.vertices

    def execute(self, chunk):
        for a in chunk.actions:
            self._env.control.robot_goto_position([a.target_pose[:3]])
        return {'executed_steps':len(chunk.actions),'done':False}


def exercise(path, level, mode, skip=None):
    flat=level=='flat'; task='A_l1_overfold' if flat else 'B_nominal'; edge='left' if flat else 'right'
    meta, arrays=fixture(task,edge)
    b=Backend(arrays['vertices'][0],skip)
    evidence=EpisodeEvidence(b,path,[__file__],synthetic=True); evidence.install()
    case={'level':level,'seed':4100 if flat else 4202}
    initial=path/'input';initial.mkdir();(initial/'result.json').write_text('{}')
    np.savez_compressed(initial/'initial_geometry.npz',vertices=arrays['initial'])
    np.savez_compressed(path/'cloth_constructed.npz',points=arrays['local_points'])
    n=7 if flat else 12; h=[1]*n if mode=='single' else [1]*(n-5)+[4,1]
    r={'passed':False,'initial_case':case,'initial_dir':str(initial),'execution_mode':mode,
       'actions':[],'errors':[],'code_files':read(MANIFEST),'call_horizons':h}
    r['held_check' if flat else 'fold_held_check']=meta['held_check']
    def call(target, count, label):
        action=NS(target_pose=np.r_[target,0.],gripper_command=0)
        b.execute(NS(actions=[action]*count))
        r['actions'].extend({'label':label} for _ in range(count))
    try:
        for index,count in enumerate(h[:-1]):
            call(b.ee.copy(),count,'rec_release' if not flat and index==4 else 'waypoint')
        final=release_window(b,evidence,path,r,arrays['initial'],meta['pick_index'],0.,
                             lambda t:call(t,1,'release_retreat'))
        np.savez_compressed(path/'final.npz',vertices=final)
        r['action_count']=len(r['actions']);r['passed']=True
    finally:
        evidence.finish(r)
    finish_metadata(path,r,case,mode)
    (path/'result.json').write_text(json.dumps(r))
    return assess(path)


class CaptureTests(unittest.TestCase):
    def test_tasks_and_representations(self):
        for level in ('flat','perturbed','crumpled'):
            for mode in ('single','arc4'):
                with self.subTest(level=level,mode=mode),tempfile.TemporaryDirectory() as t:
                    verdict=exercise(Path(t),level,mode)
                    self.assertTrue(verdict['criteria']['success'])
                    self.assertEqual([k for k,v in verdict['evidence_checks'].items() if not v],['actual_sim'])
                    self.assertIsNone(verdict['success'])
                    with np.load(Path(t)/'success_trace.npz') as z:
                        self.assertEqual(z['vertices'].shape,(331,441,3))
                        self.assertEqual(z['attachment_enabled'].shape,(331,3))

    def test_clock_gap_saves_only_partial(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(RuntimeError,'physics sample'):
                exercise(Path(t),'perturbed','arc4',skip=50)
            self.assertTrue((Path(t)/'partial_trace.npz').exists())
            self.assertFalse((Path(t)/'success_trace.npz').exists())


if __name__=='__main__': unittest.main()
