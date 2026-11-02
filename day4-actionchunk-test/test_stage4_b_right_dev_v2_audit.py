#!/usr/bin/env python3
"""Offline smoke test for stage4_b_right_dev_v2_audit.py (synthetic data only)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUDIT = HERE / 'stage4_b_right_dev_v2_audit.py'
LABELS = ['rec_approach', 'rec_pick', 'rec_lift', 'rec_spread', 'rec_release',
          'fold_approach', 'fold_close', 'fold_arc45', 'fold_arc90',
          'fold_arc135', 'fold_place', 'fold_release']


def build_case(root, seed, level, passed=True, held=True):
    d = root / f'day4-recovery-fold-synthetic-{seed}'
    d.mkdir(parents=True)
    xs = np.linspace(-0.2, 0.2, 21)
    gx, gy = np.meshgrid(xs, xs)
    points = np.stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)], axis=1)
    pick_index = 230
    pick = points[pick_index].copy()
    final = points.copy()
    moving = points[:, 0] > points[pick_index, 0] - 0.2
    final[moving, 0] -= 0.35
    final[moving, 2] += 0.06
    np.savez_compressed(d / 'final.npz', vertices=final)
    np.savez_compressed(d / 'cloth_constructed.npz', points=points)
    lateral = np.array([-1.0, 0.0, 0.0])
    crossed = float((((final[moving] - pick) @ lateral) > 0.2).mean())
    base = json.loads((HERE / 'square-recovery-fold-files.json').read_text())
    manifest = json.loads((HERE / 'square-recovery-fold-right-v2-files.json').read_text())
    config = json.loads((HERE / 'stage4-b-right-dev-v2.json').read_text())
    result = {
        'passed': passed, 'errors': [], 'fold_edge': 'right', 'execution_mode': 'single',
        'action_count': 12, 'call_horizons': [1] * 12, 'action_labels': LABELS,
        'actions': [{'label': l, 'target_pose': [0, 0, 0, 0], 'command': 0} for l in LABELS],
        'records': [{'edge': 'right', 'pick_index': pick_index, 'pick_world': pick.tolist()}],
        'fold_yaw': 0.0,
        'initial_case': {'seed': seed, 'level': level},
        'fold_held_check': {'accepted': held, 'position_error_m': 0.01},
        'fold_metrics': {'moving_count': int(moving.sum()), 'crossed_fraction': crossed,
                         'extent': np.ptp(final, axis=0).tolist(),
                         'z_p95': float(np.percentile(final[:, 2], 95)),
                         'pick_index': pick_index},
        'code_files': base,
    }
    (d / 'result.json').write_text(json.dumps(result))
    (d / 'variant_identity.json').write_text(json.dumps({
        'code_files': manifest, 'base_code_files': base, 'config': config,
        'formal_stage4_success': False, 'initial_files': {}}))
    return d


def run(tmp):
    return subprocess.run(
        [sys.executable, '-I', str(AUDIT), '--results', str(tmp / 'results'),
         '--attempts', str(tmp / 'attempts.jsonl'), '--out', str(tmp / 'summary.json')],
        capture_output=True, text=True)


class AuditTest(unittest.TestCase):
    def test_passed_case(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            d = build_case(tmp / 'results', 4201, 'perturbed')
            (tmp / 'attempts.jsonl').write_text(json.dumps(
                {'seed': 4201, 'level': 'perturbed', 'execution': 'single',
                 'result_dir': '/root/autodl-tmp/' + d.name}) + '\n')
            proc = run(tmp)
            summary = json.loads((tmp / 'summary.json').read_text())
            self.assertEqual(summary['counts']['passed'], 1)
            self.assertEqual(summary['failed_checks'], 0)
            self.assertEqual(len(summary['missing_seeds']), 17)
            self.assertIn('SUMMARY', proc.stdout)

    def test_missing_result_is_error(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / 'results').mkdir()
            build_case(tmp / 'results', 4202, 'perturbed')
            (tmp / 'attempts.jsonl').write_text(json.dumps(
                {'seed': 4202, 'level': 'perturbed', 'execution': 'single',
                 'result_dir': '/root/autodl-tmp/day4-recovery-fold-not-downloaded'}) + '\n')
            proc = run(tmp)
            summary = json.loads((tmp / 'summary.json').read_text())
            self.assertEqual(summary['counts']['error'], 1)
            self.assertEqual(summary['counts']['passed'], 0)
            self.assertIn('ERROR', proc.stdout)

    def test_held_gate_failure_flagged(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            d = build_case(tmp / 'results', 4203, 'perturbed', held=False)
            (tmp / 'attempts.jsonl').write_text(json.dumps(
                {'seed': 4203, 'level': 'perturbed', 'execution': 'single',
                 'result_dir': '/root/autodl-tmp/' + d.name}) + '\n')
            run(tmp)
            summary = json.loads((tmp / 'summary.json').read_text())
            names = summary['failed_check_names']
            self.assertTrue(any(name.endswith(':held_gate') for name in names), names)


if __name__ == '__main__':
    unittest.main()
