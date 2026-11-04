"""Verify the rc7 seven-case download against a remote sha256sum listing.

The listing paths are relative to the download root (result dirs and the batch
ledger directory at top level).
"""
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
listing = Path(sys.argv[2]).read_text(encoding='utf-8-sig').splitlines()
remote = {}
for line in listing:
    if not line.strip():
        continue
    h, p = line.split(maxsplit=1)
    remote[p.strip()] = h

missing, extra, bad = [], [], []
seen = set()
for p, want in remote.items():
    local = root / p
    if not local.is_file():
        missing.append(p)
        continue
    have = hashlib.sha256(local.read_bytes()).hexdigest()
    if have != want:
        bad.append(p)
    seen.add(p)

for p in root.rglob('*'):
    if p.is_file():
        rel = str(p.relative_to(root)).replace('\\', '/')
        if rel not in remote and rel != 'remote_hashes.txt':
            extra.append(rel)

print('remote_files', len(remote), 'local_files', len(seen))
print('missing', missing[:10], 'count', len(missing))
print('extra', extra[:10], 'count', len(extra))
print('hash_mismatch', bad[:10], 'count', len(bad))
print('VERIFIED' if not (missing or extra or bad) else 'MISMATCH')
