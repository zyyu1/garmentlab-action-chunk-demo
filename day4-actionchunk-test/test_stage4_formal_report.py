"""Offline CLI regression tests. All seeds and results are synthetic fixtures."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPORT = Path(__file__).with_name('stage4_formal_report.py')


class FormalReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.results = self.root / 'results'
        self.results.mkdir()
        self.seeds = self.root / 'seeds.json'
        held = [('flat', 4110), ('flat', 4111), ('perturbed', 4210), ('crumpled', 4310)]
        self.seeds.write_text(json.dumps({'heldout': [{'level': l, 'seed': s} for l, s in held]}))

    def result(self, level='flat', seed=4110, mode='single', passed=True, suffix='a'):
        prefix = 'day4-l1-xfold-yaw-aware-' if level == 'flat' else 'day4-recovery-fold-'
        path = self.results / (prefix + str(seed) + '-' + mode + '-' + suffix)
        path.mkdir()
        (path / 'result.json').write_text(json.dumps({
            'initial_case': {'level': level, 'seed': seed}, 'execution_mode': mode,
            'passed': passed, 'code_files': {'fixture': 'fixture'}, 'action_count': 7,
            'fold_success_accepted': False}))
        return path

    def attempt(self, level='flat', seed=4110, mode='single', result=None):
        return {'level': level, 'seed': seed, 'execution': mode,
                'result_dir': '' if result is None else '/remote/' + result.name,
                'exit_code': 1 if result is None else 0}

    def run_report(self, attempts=(), repeated_args=False):
        log = self.root / 'attempts.jsonl'
        log.write_text(''.join(json.dumps(r) + '\n' for r in attempts))
        output = self.root / 'out.json'
        cmd = [sys.executable, '-I', str(REPORT), '--seeds', str(self.seeds),
               '--root', str(self.results), '--attempts', str(log), '--out', str(output)]
        if repeated_args:
            cmd += ['--root', str(self.results), '--attempts', str(log)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(output.read_text())
        for row in data['summary']:
            self.assertEqual(row['attempts'], row['passed'] + row['rejected'] + row['error'])
            self.assertEqual(row['formal_success'], 0)
        return data

    def cell(self, data, level='flat', mode='single'):
        return next(r for r in data['summary'] if r['level'] == level and r['execution'] == mode)

    def test_pass_and_missing_result_is_two_attempts_and_half_rejected(self):
        path = self.result()
        data = self.run_report([self.attempt(result=path), self.attempt(seed=4111)])
        row = self.cell(data)
        self.assertEqual((row['attempts'], row['passed'], row['rejected'], row['error']), (2, 1, 0, 1))
        self.assertEqual(row['rejection_rate'], .5)
        self.assertEqual(data['tasks']['A_l1']['rejection_rate'], .5)
        self.assertEqual(len(data['missing']), 1)

    def test_rejected_and_missing_result_is_fully_rejected(self):
        path = self.result(passed=False)
        row = self.cell(self.run_report([self.attempt(result=path), self.attempt(seed=4111)]))
        self.assertEqual((row['attempts'], row['rejected'], row['error']), (2, 1, 1))
        self.assertEqual(row['rejection_rate'], 1.)

    def test_error_only_cell_and_task_b_total(self):
        data = self.run_report([self.attempt('perturbed', 4210), self.attempt('crumpled', 4310, 'arc4')])
        for level, mode in [('perturbed', 'single'), ('crumpled', 'arc4')]:
            row = self.cell(data, level, mode)
            self.assertEqual((row['attempts'], row['error'], row['rejection_rate']), (1, 1, 1.))
        self.assertEqual((data['tasks']['B_l2l3']['attempts'], data['tasks']['B_l2l3']['error']), (2, 2))
        self.assertEqual(data['tasks']['B_l2l3']['rejection_rate'], 1.)

    def test_empty_cell_remains_empty(self):
        data = self.run_report()
        self.assertTrue(all(r['attempts'] == 0 and r['rejection_rate'] is None for r in data['summary']))
        self.assertIsNone(data['tasks']['B_l2l3']['rejection_rate'])

    def test_existing_result_and_repeated_inputs_are_not_double_counted(self):
        path = self.result()
        data = self.run_report([self.attempt(result=path), self.attempt(seed=4111)], repeated_args=True)
        self.assertEqual(self.cell(data)['attempts'], 2)
        self.assertEqual(data['logged_attempts'], 2)

    def test_non_heldout_attempts_and_results_are_excluded(self):
        self.result(seed=4100)
        data = self.run_report([self.attempt(seed=4100)])
        self.assertEqual(self.cell(data)['attempts'], 0)
        self.assertEqual(data['missing'], [])
        self.assertEqual(data['logged_attempts'], 0)

    def test_retries_are_separate_but_two_modes_are_not_duplicate_attempts(self):
        self.result()
        self.result(mode='arc4')
        data = self.run_report([self.attempt()])
        self.assertEqual(self.cell(data)['attempts'], 2)
        self.assertEqual(self.cell(data)['duplicate_attempts'], [4110])
        self.assertEqual(self.cell(data, mode='both')['attempts'], 3)
        other = self.result(level='perturbed', seed=4210)
        self.result(level='perturbed', seed=4210, mode='arc4')
        data = self.run_report([self.attempt(result=other, level='perturbed', seed=4210)])
        self.assertEqual(self.cell(data, 'perturbed', 'both')['duplicate_attempts'], [])

    def test_named_result_not_downloaded_is_an_error(self):
        missing = Path('day4-recovery-fold-not-downloaded')
        data = self.run_report([self.attempt('crumpled', 4310, 'arc4', missing)])
        row = self.cell(data, 'crumpled', 'arc4')
        self.assertEqual((row['attempts'], row['error'], row['rejection_rate']), (1, 1, 1.))
        error = data['rows'][0]
        self.assertEqual(error['outcome'], 'error')
        self.assertEqual(error['attempt_line'], 1)
        self.assertEqual(row['non_frozen_code'], [])


if __name__ == '__main__':
    unittest.main()
