#!/usr/bin/env bash
# Stage 5 demo initial-state generator (on-demand, single seed).
# Reuses the frozen generator logic via the -demo runners; writes the same
# task-scoped protocol block (stage4-initial-v2-task-scoped).
set -euo pipefail
cd "$(dirname "$0")"
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
seed=${1:-6100}

"$python_bin" - "$seed" <<'PY'
import sys, json, hashlib
from pathlib import Path
seed = int(sys.argv[1])
seeds = json.loads(Path('stage5-demo-seeds.json').read_text())
ranges = seeds['ranges']
match = [k for k, (a, b) in ranges.items() if a <= seed <= b]
assert len(match) == 1, 'Seed outside Stage 5 demo ranges'
level = match[0]
plan = json.loads(Path('stage5-demo-initial-plan.json').read_text())
rows = [r for r in plan['episodes'] if r['seed'] == seed]
assert len(rows) == 1 and rows[0]['level'] == level, 'Seed not in demo plan'
for name, digest in json.loads(Path('stage5-demo-initial-files.json').read_text()).items():
    p = Path(name)
    assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == digest, name
app = Path('/root/autodl-tmp/stage5-trial/app')
assert hashlib.sha256((app / 'square-difficulty.yaml').read_bytes()).hexdigest() == plan['config_sha256']
assert hashlib.sha256((app / 'square_cloth_40cm.usda').read_bytes()).hexdigest() == plan['asset_sha256']
print('DEMO_INITIAL_PREFLIGHT_OK', seed, level, flush=True)
PY

level=$("$python_bin" -c "import json;r=json.load(open('stage5-demo-initial-plan.json'));print([x['level'] for x in r['episodes'] if x['seed']==$seed][0])")
if [ "$level" = "flat" ]; then runner=day4-square-initial-demo.py; else runner=day4-square-initial-stripfold-demo.py; fi

log=$(mktemp /root/autodl-tmp/day4-demo-initial-log-XXXXXXXX.log)
set +e
SQUARE_INITIAL_SEED="$seed" GARMENTLAB_ATTACHMENT_OVERLAP=0.005 GARMENTLAB_DISABLED_ATTACHMENT_PROBE=0 \
  "$python_bin" -u "$runner" --allow-root 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e
"$python_bin" - "$log" <<'PY'
import sys, json
from pathlib import Path
import cv2
log = Path(sys.argv[1])
paths = [s[12:] for s in log.read_text(errors='replace').splitlines() if s.startswith('RESULT_FILE ')]
assert len(paths) == 1, 'Missing result; retain ' + str(log)
p = Path(paths[0])
(p.parent / 'runner.log').write_bytes(log.read_bytes())
r = json.loads(p.read_text())
assert r['passed'], r['errors']
im = cv2.imread(str(p.parent / 'initial.png'))
assert im is not None and im.shape == (480, 640, 3)
print('DOWNLOAD_DIR', p.parent, flush=True)
print('DEMO_INITIAL_DIR', p.parent, flush=True)
print('DEMO_INITIAL_SAVED', r['initial_case']['seed'], r['initial_case']['level'], flush=True)
PY
if [ "${statuses[0]}" -ne 0 ] || [ "${statuses[1]}" -ne 0 ]; then exit 1; fi
