import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from test_a5_capture import Backend
from episode_evidence import EpisodeEvidence


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.b = Backend(np.zeros((441, 3)))

    def test_first_invalid_buffer_is_not_written_and_physics_is_unchanged(self):
        frames = iter([None, np.zeros((120,320,3), dtype=np.uint8)])
        self.b._env.camera.camera.get_rgb = lambda:next(frames)
        rec = EpisodeEvidence(self.b,self.root,[__file__],synthetic=True)
        rec.install()
        self.assertEqual((rec.frames, rec.steps, self.b.world.current_time_step_index),(1,0,0))
        self.assertEqual(rec.errors,[])
        self.b._env.camera.camera.get_rgb=self.b.rgb
        rec.finish({'passed':True})
        rows=list(map(json.loads,(self.root/'evidence/timeline.jsonl').read_text().splitlines()))
        self.assertEqual([r['kind'] for r in rows[:4]],['start','camera_prime_pending','frame','camera_ready'])

    def test_persistently_empty_buffer_stops_before_actions(self):
        self.b._env.camera.camera.get_rgb=lambda:None
        rec=EpisodeEvidence(self.b,self.root,[__file__],synthetic=True)
        with self.assertRaisesRegex(RuntimeError,'No valid startup RGB'):
            rec.install()
        self.assertEqual(rec.actions,0)
        rec.finish({'passed':False})
        self.assertTrue(rec.errors)

if __name__=='__main__':unittest.main()
