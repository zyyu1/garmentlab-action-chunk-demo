"""Local evaluator recomputation for the seven hold120 rc7 cases."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
APP = HERE / 'a5-rc8b-recovery-hold120-rc7-r2' / 'app'
BASE = HERE / 'results' / 'RC8B_L2_DIAG_20261105'
RUNS = [
    (1, 4100, 'single', BASE / 'hold120_rc7' / 'day4-a5-rc2-l1-20261105-081311-735952'),
    (2, 4100, 'arc4', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-l1-20261105-083859-341524'),
    (3, 4202, 'single', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-pfs1-observation-v2-20261105-085248-353214'),
    (4, 4202, 'arc4', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-pfs1-observation-v2-20261105-091038-643466'),
    (5, 4302, 'single', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-pfs1-observation-v2-20261105-092821-242307'),
    (6, 4302, 'arc4', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-pfs1-observation-v2-20261105-094700-143205'),
    (7, 4201, 'single', BASE / 'hold120_rc7_r2_resume' / 'day4-a5-rc2-pfs1-observation-v2-20261105-100445-893957'),
]
sys.path.insert(0, str(APP))
import stage4_success_v1  # noqa: E402

rows = []
for slot, seed, mode, d in RUNS:
    meta = json.loads((d / 'success_meta.json').read_text())
    with np.load(d / 'success_trace.npz', allow_pickle=False) as z:
        data = {k: z[k].copy() for k in z.files}
    local = stage4_success_v1.evaluate(meta, data)
    remote = json.loads((d / 'a5-verdict.json').read_text())['criteria']
    status = local['status'] == remote['status']
    stab = all(abs(float(local['stability'][k]) - float(remote['stability'][k])) <= 0
               for k in remote['stability'])
    rows.append({'slot': slot, 'seed': seed, 'mode': mode,
                 'local_status': local['status'], 'remote_status': remote['status'],
                 'status_match': status, 'stability_match': stab})
    print(slot, seed, mode, local['status'], 'status', status, 'stab', stab)

out = {'all_match': all(r['status_match'] and r['stability_match'] for r in rows), 'cases': rows}
(BASE / 'hold120_rc7_r2_resume' / 'local_recompute.json').write_text(
    json.dumps(out, indent=2) + '\n', encoding='utf-8')
print('ALL_MATCH', out['all_match'])
raise SystemExit(0 if out['all_match'] else 1)
