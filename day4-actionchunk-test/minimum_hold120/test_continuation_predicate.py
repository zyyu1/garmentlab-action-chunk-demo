"""Offline check of the registered continuation predicate on the 4112 record."""
import json
import sys
from pathlib import Path

sys.path.insert(0, '/root/autodl-tmp/stage4-minimum-hold120')
import minimum_driver_v2 as d  # noqa: E402

D = Path('/root/autodl-tmp/day4-a5-rc2-l1-20261106-033055-623326')
verdict = json.loads((D / 'a5-verdict.json').read_text())
print('verdict_status', verdict.get('status'))
print('is_continuation_class', d._waypoint_non_convergence(verdict, D))
res = json.loads((D / 'result.json').read_text())
print('passed', res.get('passed'), 'errors', res.get('errors'))
# negative controls
print('neg_missing_dir', d._waypoint_non_convergence(verdict, Path('/tmp/does-not-exist')))
print('neg_wrong_status', d._waypoint_non_convergence({'status': 'accepted'}, D))
