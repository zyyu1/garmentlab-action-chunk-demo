"""Deterministic synthetic integration fixture; no Isaac/GPU experiments."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
from episode_evidence import EpisodeEvidence
from audit_episode_evidence import audit


class FakeBackend:
    def __init__(self):
        self._holding = False
        self._step_count = {'n': 0}
        self.ee = np.array([0., 0., .2])
        self.world = NS(current_time=0., get_physics_dt=lambda: 1 / 60,
                        render=lambda: None, step=self.step)
        self._env = NS(world=self.world, control=NS(attachlist=[None]),
                       robots=[NS(get_cur_ee_pos=lambda: (self.ee.copy(), None))],
                       camera=NS(camera=NS(get_rgb=self.rgb)))

    def step(self, **kwargs):
        self.world.current_time += 1 / 60
        self._step_count['n'] += 1

    def rgb(self):
        import cv2
        image = np.zeros((120, 320, 3), np.uint8)
        cv2.putText(image, 'SYNTHETIC TEST ONLY', (5, 40), 0, .65, (255, 255, 255), 1)
        cv2.putText(image, 'step %d' % self._step_count['n'], (5, 80), 0, .6, (0, 255, 0), 1)
        return image

    def _garment_world_positions(self):
        return np.array([[0., 0., 0.], [.1, 0., 0.], [0., .1, 0.]])

    def execute(self, chunk):
        for action in chunk.actions:
            self.ee = np.asarray(action.target_pose[:3], dtype=float)
            self.world.step()
        return {'executed_steps': len(chunk.actions), 'done': False}


def fixture(root, failure=False):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    b = FakeBackend()
    recorder = EpisodeEvidence(b, root, [__file__, Path(__file__).with_name('episode_evidence.py')], synthetic=True)
    recorder.install()
    def retreat():
        b.execute(NS(actions=[NS(target_pose=[0., 0., .35, 0.], gripper_command=0)]))
    result = {'passed': False, 'formal_day4_success': False, 'errors': []}
    try:
        if failure:
            b.world.step()
            raise RuntimeError('Intentional failure before retreat')
        recorder.retention(retreat)
        result['passed'] = True
    except RuntimeError as exc:
        result['errors'].append(str(exc))
    finally:
        recorder.finish(result)
        (root / 'result.json').write_text(json.dumps(result, indent=2))
    report = audit(root / 'evidence')
    (root / 'audit.json').write_text(json.dumps(report, indent=2))
    return report


class EvidenceTests(unittest.TestCase):
    def test_complete_and_tampered(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertTrue(fixture(temp)['evidence_complete'])
            p = Path(temp) / 'evidence' / 'hold_4s.npz'
            p.write_bytes(b'tampered')
            self.assertFalse(audit(Path(temp) / 'evidence')['checks']['file_hashes'])

    def test_failure_saved_and_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            report = fixture(temp, failure=True)
            self.assertFalse(report['evidence_complete'])
            self.assertTrue(report['checks']['terminal_saved'])
            self.assertTrue(report['checks']['video_decodes'])


if __name__ == '__main__':
    unittest.main()
