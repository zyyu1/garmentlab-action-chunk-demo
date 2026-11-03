"""No GPU calls: fixed seeds, mutation detection, journal interruption/resume."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from stage4_batch_preflight import validate, journal, append

HERE = Path(__file__).resolve().parent


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_real_registration_without_simulation(self):
        r = validate(HERE / 'stage4-heldout-seeds.json', HERE / 'square-initial-plan.json')
        self.assertEqual(r['planned_fold_attempts'], 120)

    def test_duplicate_seed_and_strip_mutation_rejected(self):
        seeds = json.loads((HERE / 'stage4-heldout-seeds.json').read_text())
        p = self.root / 'seeds.json'
        seeds['heldout'][-1] = seeds['heldout'][0]
        p.write_text(json.dumps(seeds))
        with self.assertRaises(ValueError):
            validate(p, HERE / 'square-initial-plan.json')
        seeds = json.loads((HERE / 'stage4-heldout-seeds.json').read_text())
        next(r for r in seeds['heldout'] if r['level'] == 'perturbed')['strips'][0]['width_m'] += .001
        p.write_text(json.dumps(seeds))
        with self.assertRaises(ValueError):
            validate(p, HERE / 'square-initial-plan.json')

    def cli(self, command, *extra):
        return subprocess.run([sys.executable, str(HERE / 'stage4_batch_preflight.py'), command,
                               '--state', str(self.root), '--level', 'flat', '--seed', '4110',
                               '--execution', 'single', '--initial-dir', '/initial', *extra],
                              capture_output=True, text=True)

    def test_interrupted_attempt_blocks_resume_and_duplicate_start(self):
        self.assertEqual(self.cli('status').stdout.strip(), 'pending')
        self.assertEqual(self.cli('start').returncode, 0)
        self.assertNotEqual(self.cli('status').returncode, 0)
        self.assertNotEqual(self.cli('start').returncode, 0)
        self.assertEqual(len(journal(self.root / 'attempts.jsonl')), 1)

    def test_rejected_completed_attempt_is_skipped(self):
        result = self.root / 'failed-result'; result.mkdir()
        (result / 'result.json').write_text(json.dumps({'passed': False,
            'initial_case': {'level': 'flat', 'seed': 4110}, 'execution_mode': 'single'}))
        self.assertEqual(self.cli('start').returncode, 0)
        self.assertEqual(self.cli('finish', '--result-dir', str(result), '--exit-code', '1').returncode, 0)
        self.assertEqual(self.cli('status').stdout.strip(), 'done')
        self.assertEqual(len(journal(self.root / 'attempts.jsonl')), 1)
        (result / 'result.json').write_text('{}')
        self.assertNotEqual(self.cli('status').returncode, 0)

    def test_corrupt_or_conflicting_journal_fails_closed(self):
        log = self.root / 'attempts.jsonl'
        log.write_text('{truncated')
        with self.assertRaises(ValueError): journal(log)
        log.write_text('')
        append(log, {'event': 'finished', 'attempt_id': 'missing'})
        with self.assertRaises(ValueError): journal(log)

    def test_batch_identity_is_bound_across_resume(self):
        source = self.root / 'source'; source.mkdir()
        for name in ('stage4-heldout-seeds.json', 'square-initial-plan.json',
                     'run-stage4-formal-batch.sh', 'stage4_batch_preflight.py'):
            (source / name).write_bytes((HERE / name).read_bytes())
        cmd = [sys.executable, str(HERE / 'stage4_batch_preflight.py'), 'bind',
               '--state', str(self.root / 'state'), '--seeds', str(source / 'stage4-heldout-seeds.json'),
               '--plan', str(source / 'square-initial-plan.json')]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        (source / 'run-stage4-formal-batch.sh').write_text('changed')
        self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
