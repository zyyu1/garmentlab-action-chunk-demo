"""Verify a downloaded result directory against a remote sha256sum listing."""
import hashlib
import sys
from pathlib import Path

run = Path(sys.argv[1]).resolve()
listing_path = Path(sys.argv[2]).resolve()
listing = listing_path.read_text(encoding='utf-8-sig').splitlines()

remote = {}
for line in listing:
    if not line.strip():
        continue
    h, p = line.split(maxsplit=1)
    remote[p.strip().lstrip('./')] = h

local = {}
for p in run.rglob('*'):
    if p.is_file():
        local[str(p.relative_to(run)).replace('\\', '/')] = hashlib.sha256(p.read_bytes()).hexdigest()

missing = sorted(set(remote) - set(local))
extra = sorted(set(local) - set(remote))
bad = sorted(k for k in set(remote) & set(local) if remote[k] != local[k])
print('remote_files', len(remote), 'local_files', len(local))
print('missing', missing)
print('extra', extra)
print('hash_mismatch', bad)
print('VERIFIED' if not (missing or extra or bad) else 'MISMATCH')
