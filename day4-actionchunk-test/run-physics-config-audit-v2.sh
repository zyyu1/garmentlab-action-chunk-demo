#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
"$python_bin" - <<'PY'
import hashlib
from pathlib import Path
p = Path('/root/autodl-tmp/day4-physics-config-audit-v2.py')
expected = 'a852d7eb2d0d5e44f9fd695f387f81198403e10474f44c6359ebcf0583af8b63'
if hashlib.sha256(p.read_bytes()).hexdigest() != expected:
    raise RuntimeError('Wrong audit v2 file: stopped before simulation startup')
print('AUDIT_V2_PREFLIGHT_OK', flush=True)
PY
log=$(mktemp /root/autodl-tmp/day4-physics-config-run-XXXXXXXX.log)
GARMENTLAB_ATTACHMENT_OVERLAP=0.005 \
GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
"$python_bin" -X faulthandler -u day4-physics-config-audit-v2.py --allow-root 2>&1 | tee "$log"
"$python_bin" - "$log" <<'PY'
import json
import sys
from pathlib import Path
log = Path(sys.argv[1])
lines = log.read_text(errors='replace').splitlines()
if 'PHYSICS_CONFIG_AUDIT_OK' not in lines:
    raise RuntimeError('Missing audit success marker')
paths = [line[len('RESULT_FILE '):] for line in lines if line.startswith('RESULT_FILE ')]
if len(paths) != 1:
    raise RuntimeError('Expected one result path')
path = Path(paths[0])
r = json.loads(path.read_text())
assert r.get('audit_version') == 2, 'Expected audit_version=2'
assert r['passed'] is True and r['no_steps_during_capture'] is True and r['attachment_disabled'] is True
assert r['baseline_source_checks'] and all(r['baseline_source_checks'].values())
for name in ('cloth', 'cloth_view', 'particle_system', 'particle_material'):
    assert (path.parent / 'source' / ('sdk__' + name + '.py')).is_file(), name
prims = json.loads((path.parent / 'physics_attributes.json').read_text())
assert any(p['type'] == 'PhysxParticleSystem' and p['attributes'] for p in prims)
(path.parent / 'runner.log').write_bytes(log.read_bytes())
print('PHYSICS_CONFIG_V2_RESULT_VERIFIED', flush=True)
print('DOWNLOAD_DIR', path.parent, flush=True)
PY
