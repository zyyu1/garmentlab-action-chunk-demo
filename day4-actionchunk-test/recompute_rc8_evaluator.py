#!/usr/bin/env python3
"""Local recomputation of rc8 evaluator results from downloaded artifacts.

Runs the unchanged stage4_success_v1.evaluate on each case's success_meta.json
and success_trace.npz (paths resolved from the batch ledger) and compares
status/stability with the remote verdict.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--batch', type=Path, required=True)
ap.add_argument('--app', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
ap.add_argument('--remote-root', default='/root/autodl-tmp')
args = ap.parse_args()

batch = args.batch.resolve()
app = args.app.resolve()
out = args.out.resolve()
sys.path.insert(0, str(app))
import stage4_success_v1  # noqa: E402

local_root = batch.parent


def local_run(run):
    run = str(run)
    if run.startswith(args.remote_root.rstrip('/') + '/'):
        return local_root / run[len(args.remote_root.rstrip('/')) + 1:]
    return Path(run)


rows = []
for line in (batch / 'batch.jsonl').read_text().splitlines():
    if not line.strip():
        continue
    rec = json.loads(line)
    d = local_run(rec['run'])
    meta = json.loads((d / 'success_meta.json').read_text())
    with np.load(d / 'success_trace.npz', allow_pickle=False) as z:
        data = {k: z[k].copy() for k in z.files}
    local = stage4_success_v1.evaluate(meta, data)
    remote = json.loads((d / 'a5-verdict.json').read_text())['criteria']
    same_status = local['status'] == remote['status']
    same_stability = all(
        abs(float(local['stability'][k]) - float(remote['stability'][k])) <= 0
        for k in remote['stability'])
    rows.append({'slot': rec['slot'], 'seed': rec['seed'], 'mode': rec['mode'],
                 'local_status': local['status'], 'remote_status': remote['status'],
                 'status_match': same_status, 'stability_match': same_stability,
                 'local_stability': local['stability']})
    print(rec['slot'], local['status'], 'status_match', same_status,
          'stability_match', same_stability)

summary = {'cases': rows,
           'all_match': all(x['status_match'] and x['stability_match'] for x in rows),
           'evaluator': 'stage4_success_v1.evaluate unchanged; config stage4-success-v1.json'}
out.mkdir(parents=True, exist_ok=True)
(out / 'local_recompute.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print('ALL_MATCH', summary['all_match'])
raise SystemExit(0 if summary['all_match'] else 1)
