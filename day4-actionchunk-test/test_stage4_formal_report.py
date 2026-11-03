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
        output = self.root / ('out-' + str(len(list(self.root.glob('out-*.json')))) + '.json')
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

    def test_legacy_formal_claim_is_not_formal_evidence(self):
        path = self.result()
        r = json.loads((path / 'result.json').read_text())
        r['formal_day4_success'] = True
        (path / 'result.json').write_text(json.dumps(r))
        data = self.run_report()
        self.assertTrue(data['rows'][0]['legacy_formal_claim'])
        self.assertIsNone(self.cell(data)['formal_success_rate'])

    def test_corrupt_result_retains_logged_denominator(self):
        path = self.result()
        (path / 'result.json').write_text('{broken')
        data = self.run_report([self.attempt(result=path)])
        self.assertEqual(self.cell(data)['error'], 1)
        self.assertFalse(data['denominator_complete'])

    def test_started_attempt_is_error_until_finished(self):
        start = dict(self.attempt(), attempt_id='one', event='started', initial_dir='/initial')
        data = self.run_report([start])
        self.assertEqual(self.cell(data)['error'], 1)
        path = self.result()
        end = dict(start, event='finished', result_dir='/remote/' + path.name, exit_code=0)
        data = self.run_report([start, end])
        self.assertEqual((self.cell(data)['attempts'], self.cell(data)['passed']), (1, 1))

    def test_unattempted_are_not_errors(self):
        self.result()
        data = self.run_report()
        self.assertEqual(data['planned_attempts'], 8)
        self.assertEqual(len(data['not_attempted']), 7)
        self.assertEqual(self.cell(data)['error'], 0)

    def test_existing_report_is_not_overwritten(self):
        self.run_report()
        output = self.root / 'out-0.json'
        original = output.read_bytes()
        p = subprocess.run([sys.executable, str(REPORT), '--seeds', str(self.seeds),
                            '--root', str(self.results), '--out', str(output)], capture_output=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(output.read_bytes(), original)

    def test_runner_error_cannot_count_as_development_pass(self):
        path = self.result()
        row = self.cell(self.run_report([dict(self.attempt(result=path), exit_code=2)]))
        self.assertEqual((row['passed'], row['error']), (0, 1))


if __name__ == '__main__':
    unittest.main()
