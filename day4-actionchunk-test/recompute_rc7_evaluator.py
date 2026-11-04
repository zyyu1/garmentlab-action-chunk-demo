#!/usr/bin/env python3
"""Local recomputation of the rc7 evaluator results from downloaded artifacts.

Runs the unchanged stage4_success_v1.evaluate on each case's success_meta.json
and success_trace.npz and compares status/stability with the remote verdict.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
APP = HERE / 'a5-rc2-pfs1-observation-v2-rc7' / 'app'
sys.path.insert(0, str(APP))

import stage4_success_v1  # noqa: E402

CASES = [
    ('slot1', 'day4-a5-rc2-l1-20261104-210923-025602'),
    ('slot2', 'day4-a5-rc2-l1-20261104-212326-225911'),
    ('slot3', 'day4-a5-rc2-pfs1-observation-v2-20261104-213547-226507'),
    ('slot4', 'day4-a5-rc2-pfs1-observation-v2-20261104-215152-043317'),
    ('slot5', 'day4-a5-rc2-pfs1-observation-v2-20261104-220859-844555'),
    ('slot6', 'day4-a5-rc2-pfs1-observation-v2-20261104-222840-723114'),
    ('slot7', 'day4-a5-rc2-pfs1-observation-v2-20261104-224843-941246'),
]

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / 'results' / 'RC7_SEVEN_CASE_20261104'
out = []
for tag, name in CASES:
    d = root / name
    meta = json.loads((d / 'success_meta.json').read_text())
    with np.load(d / 'success_trace.npz', allow_pickle=False) as z:
        data = {k: z[k].copy() for k in z.files}
    local = stage4_success_v1.evaluate(meta, data)
    remote = json.loads((d / 'a5-verdict.json').read_text())['criteria']
    same_status = local['status'] == remote['status']
    same_stability = all(abs(float(local['stability'][k]) - float(remote['stability'][k])) <= 0
                         for k in remote['stability'])
    out.append({'case': tag, 'dir': name, 'local_status': local['status'],
                'remote_status': remote['status'], 'status_match': same_status,
                'stability_match': same_stability,
                'local_stability': local['stability']})
    print(tag, local['status'], 'status_match', same_status, 'stability_match', same_stability)

summary = {'cases': out,
           'all_match': all(x['status_match'] and x['stability_match'] for x in out),
           'evaluator': 'stage4_success_v1.evaluate unchanged; config stage4-success-v1.json'}
(root / 'local_recompute.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print('ALL_MATCH', summary['all_match'])
raise SystemExit(0 if summary['all_match'] else 1)
