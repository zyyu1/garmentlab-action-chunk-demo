"""Synthetic offline fixture for release_diag.py; no Isaac/GPU/cv2 required."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np

from release_diag import DiagnosticEpisodeEvidence, REQUIRED_EVENTS


class FakeRobot:
    def __init__(self):
        self.ee = np.array([0., 0., .2])
        self.q = np.array([1., 0., 0., 0.])
        self.jp = np.array([0., 0., 0., 0., 0., 0., 0., .02, .03])
        self.dof_names = ['panda_joint%d' % i for i in range(1, 8)] + \
                         ['panda_finger_joint1', 'panda_finger_joint2']
        self.link_names = ['panda_link%d' % i for i in range(8)] + \
                          ['panda_leftfinger', 'panda_rightfinger']
        self.links = np.zeros((len(self.link_names), 3))
        self.links[-2] = [0., 0., .2]
        self.links[-1] = [.02, 0., .2]
        self._robot = NS(
            get_joint_positions=lambda: self.jp.copy(),
            dof_names=self.dof_names,
            link_names=self.link_names,
            get_link_positions=lambda: self.links.copy())

    def get_cur_ee_pos(self):
        return self.ee.copy(), self.q.copy()


class FakeBackend:
    def __init__(self):
        self._holding = False
        self._command_holding = False
        self._step_count = {'n': 0}
        x, y = np.meshgrid(np.linspace(-.2, .2, 21), np.linspace(-.2, .2, 21))
        self.vertices = np.column_stack([x.ravel(), y.ravel(), np.zeros(441)])
        self.world = NS(current_time=0., current_time_step_index=0,
                        get_physics_dt=lambda: 1 / 60,
                        render=lambda: None, step=lambda **k: None)
        self.robot = FakeRobot()
        self._env = NS(
            world=self.world,
            control=NS(attachlist=[None],
                       slots=[NS(attachment_enabled=lambda: False)]),
            robots=[self.robot],
            camera=NS(camera=NS(get_rgb=lambda: np.zeros((120, 320, 3), np.uint8))))

    def _garment_world_positions(self):
        return self.vertices.copy()

    def execute(self, chunk):
        return {'executed_steps': len(chunk.actions), 'done': False}


class ReleaseDiagTests(unittest.TestCase):
    def test_release_window_arrays(self):
        with tempfile.TemporaryDirectory() as temp:
            b = FakeBackend()
            recorder = DiagnosticEpisodeEvidence(
                b, temp, [__file__, Path('episode_evidence.py'),
                          Path('release_diag.py')], synthetic=True)
            recorder.start_release_diag()
            recorder.emit('action_begin', targets=[[0., 0., .35, 0.]],
                          commands=[0], horizon=1)
            recorder.record_event('ungrasp_return')
            recorder.record_event('delay_begin')
            b.world.current_time += 1 / 60
            recorder.steps += 1
            recorder.emit('state', phase='delay', **recorder.state())
            recorder.record_event('delay_end')
            recorder.record_event('retreat_begin')
            b.world.current_time += 1 / 60
            recorder.steps += 1
            recorder.emit('state', phase='retreat', **recorder.state())
            recorder.emit('sample', label='released', **recorder.state())
            recorder.emit('sample', label='retreated', **recorder.state())
            recorder.record_event('retreat_end')
            recorder.emit('action_end', executed_steps=1, **recorder.state())
            doc = recorder.finish_release_diag()
            recorder.finish({'passed': True, 'errors': []})
            ev = Path(temp) / 'evidence'
            with np.load(ev / 'release_diag.npz', allow_pickle=False) as z:
                self.assertEqual(z['vertices'].shape[1:], (441, 3))
                self.assertGreaterEqual(z['joint_positions'].shape[1], 9)
                self.assertTrue(np.isfinite(z['gripper_aperture_m']).all())
                self.assertTrue(np.isfinite(z['ee_min_vertex_distance_mm']).all())
                self.assertTrue(np.isfinite(z['finger_min_vertex_distance_mm']).all())
                self.assertAlmostEqual(float(z['gripper_aperture_m'][0]), .05, places=6)
                labels = [str(x) for x in z['sample_label'] if str(x)]
                self.assertIn('released', labels)
                self.assertIn('retreated', labels)
                state = np.asarray(z['sample_label']) == ''
                times = np.asarray(z['sim_time_s'])[state]
                steps = np.asarray(z['observed_step'])[state]
                self.assertTrue(np.allclose(np.diff(times), 1 / 60, atol=1e-6))
                self.assertTrue(np.array_equal(np.diff(steps),
                                               np.ones(len(steps) - 1, dtype=int)))
            j = json.loads((ev / 'release_diag.json').read_text())
            self.assertEqual(j['physics_control_actions']['mode'],
                             'passive post-step reads only')
            self.assertEqual(len(j['action_begin']['targets']), 1)
            self.assertAlmostEqual(j['action_begin']['targets'][0][2], .35, places=6)
            self.assertIn('released', j['sample_labels'])
            self.assertIn('retreated', j['sample_labels'])
            self.assertEqual([e['event'] for e in j['events']], REQUIRED_EVENTS)
            self.assertTrue(j['events_complete'])
            self.assertTrue((ev / 'release_diag_events.csv').is_file())
            self.assertEqual(j['count'], doc['count'])
            self.assertGreaterEqual(doc['count'], 4)


if __name__ == '__main__':
    unittest.main()
