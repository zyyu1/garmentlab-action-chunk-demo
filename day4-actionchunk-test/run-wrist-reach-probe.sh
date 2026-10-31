#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
"$python_bin" - <<'PY'
import hashlib,json
from pathlib import Path
for name,digest in json.loads(Path('wrist-reach-files.json').read_text()).items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:
        raise RuntimeError('Uploaded file mismatch: '+name)
PY
"$python_bin" -u day4-wrist-reach-probe.py --allow-root
