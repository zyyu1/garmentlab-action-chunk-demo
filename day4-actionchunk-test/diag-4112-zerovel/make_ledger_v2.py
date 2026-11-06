"""Ledger for the v2 zerovel attempt (single run, no retry)."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/root/autodl-tmp/stage4-4112-zerovel')
APP = ROOT / 'app'
SCRIPT = ROOT / 'diagnose_arc135_zerovel_v2.py'
LEDGER = ROOT / 'ledger_v2.json'
INITIAL = Path('/root/autodl-tmp/day4-square-initial-20261105-232137-703257')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def app_digest(root):
    rows = []
    for p in sorted(root.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            rows.append(p.relative_to(root).as_posix() + '\0' + sha(p))
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(), len(rows)


def main():
    if LEDGER.exists():
        print('LEDGER_EXISTS', LEDGER)
        return 2
    digest, count = app_digest(APP)
    rec = {
        'attempt': 'zerovel-4112-2',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'supersedes': 'zerovel-4112-1 (overlay wrapper signature bug; aborted at grasp/close, no window tick)',
        'purpose': 'arc135 final 120-tick window: zero arm joint velocity targets (DOF 0-6)',
        'scope': {
            'window_only': True,
            'arm_dof': [0, 1, 2, 3, 4, 5, 6],
            'positions': 'unchanged from same RMP output',
            'joint_indices': 'unchanged',
            'other_fields': 'unchanged',
        },
        'app': {'path': str(APP), 'files': count, 'digest': digest},
        'app_identity_manifest_sha256': sha(APP / 'a5-manifest.json'),
        'script': str(SCRIPT),
        'script_sha256': sha(SCRIPT),
        'initial_dir': str(INITIAL),
        'initial_result_sha256': sha(INITIAL / 'result.json'),
        'initial_geometry_sha256': sha(INITIAL / 'initial_geometry.npz'),
        'runs': 1,
        'retry': False,
        'queue': 'minimum acceptance paused; this run is diagnostic only',
    }
    LEDGER.write_text(json.dumps(rec, indent=2) + '\n', encoding='utf-8')
    print('LEDGER_WRITTEN', json.dumps({'files': count, 'digest': digest[:12],
                                        'script': rec['script_sha256'][:12]}))


if __name__ == '__main__':
    sys.exit(main())
