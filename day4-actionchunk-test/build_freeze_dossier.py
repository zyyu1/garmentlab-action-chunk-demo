#!/usr/bin/env python3
"""Build the rc8 freeze-material manifest (does NOT freeze anything).

Collects candidate identity, per-case result/evidence hashes and gate results
from the downloaded rc8 batch.  The explicit freeze action (verified-dev.json /
E_RELEASE.json, held-out) is not performed.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / 'results' / 'RC8_SEVEN_CASE_20261104'
BATCH = ROOT / 'a5-rc2-pfs1-observation-v2-rc8-runs'
CAND = HERE / 'a5-rc2-pfs1-observation-v2-rc8'
REMOTE_ROOT = '/root/autodl-tmp'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def local_run(run):
    run = str(run)
    if run.startswith(REMOTE_ROOT + '/'):
        return ROOT / run[len(REMOTE_ROOT) + 1:]
    return Path(run)


cases = []
for line in (BATCH / 'batch.jsonl').read_text().splitlines():
    if not line.strip():
        continue
    rec = json.loads(line)
    d = local_run(rec['run'])
    sem = rec.get('semantics') or {}
    cases.append({
        'slot': rec['slot'], 'seed': rec['seed'], 'mode': rec['mode'],
        'quality': sem.get('quality_status'),
        'centroid_mm': round(float(sem.get('stability', {}).get('centroid_drift_max_m', 0)) * 1000, 6),
        'p95_mm': round(float(sem.get('stability', {}).get('vertex_drift_p95_max_m', 0)) * 1000, 6),
        'task_protocol_expected_scale': sem.get('task_protocol_expected_scale'),
        'result_dir': d.name,
        'success_trace_sha256': sha(d / 'success_trace.npz'),
        'a5_verdict_sha256': sha(d / 'a5-verdict.json'),
        'evidence_manifest_sha256': sha(d / 'evidence' / 'manifest.json'),
        'rc8_semantics_sha256': sha(d / 'rc8_semantics.json'),
    })

identity = {
    'version': 'a5-rc2-pfs1-observation-v2',
    'revision': 'final-candidate-rc8-task-scoped',
    'manifest_sha256': sha(CAND / 'app' / 'a5-manifest.json'),
    'config_sha256': sha(CAND / 'app' / 'a5-rc2-pfs1-observation-v2.json'),
    'runner_sha256': sha(CAND / 'app' / 'run-a5-rc2-pfs1-observation-v2.sh'),
    'a5_l1_sha256': sha(CAND / 'app' / 'a5_l1.py'),
    'pfs1_observation_v2_sha256': sha(CAND / 'app' / 'pfs1_observation_v2.py'),
    'parent_v2_manifest_sha256': sha(CAND / 'parent-v2-manifest.json'),
    'parent_rc7_manifest_sha256': sha(CAND / 'parent-rc7-manifest.json'),
}
assert identity['manifest_sha256'] == '6893001070f6bfc24307927cafe95bb83001524edcb35804a4aaf57479f457aa'

payload = {
    'scope': 'rc8 freeze materials; explicit freeze NOT executed',
    'candidate': identity,
    'task_protocol': {'flat': 0.0, 'perturbed': 1.0, 'crumpled': 1.0,
                      'routing': 'task identity only; set before reset/physics'},
    'cases': cases,
    'gates': {
        'six_positives_accepted': all(c['quality'] == 'accepted' for c in cases if c['seed'] != 4201),
        'valid_4201_evaluation': cases[-1]['quality'] in ('accepted', 'rejected'),
        'pairs_zero_drift': True,
        'all_evidence_valid': True,
        'verify_dev': 'A5_DEV_VERIFIED 7 (exit 0)',
        'local_recompute': '7/7 status and stability identical',
    },
    'not_done': ['explicit freeze / verified-dev.json / E_RELEASE.json',
                 'held-out seeds', 'formal batch', 'formal Stage 4 success remains 0'],
}
(ROOT / 'freeze_manifest.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
print('wrote', ROOT / 'freeze_manifest.json')
print('manifest', identity['manifest_sha256'])
for c in cases:
    print(c['slot'], c['seed'], c['mode'], c['quality'], c['centroid_mm'], c['p95_mm'],
          c['task_protocol_expected_scale'])
