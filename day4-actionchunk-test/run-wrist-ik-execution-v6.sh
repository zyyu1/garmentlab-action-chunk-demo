#!/usr/bin/env bash
set -euo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
"$python_bin" - <<'PY'
import json,hashlib
from pathlib import Path
for name,digest in json.loads(Path('wrist-ik-execution-v6-files.json').read_text()).items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:
        raise RuntimeError('File mismatch: '+name)
PY
"$python_bin" -u day4-wrist-ik-execution-v6.py --allow-root
