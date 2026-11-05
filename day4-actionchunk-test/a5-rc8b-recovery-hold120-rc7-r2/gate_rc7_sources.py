"""Gate for the source-inherited hold120 rc7 release."""
import json
import sys
from pathlib import Path

import freeze_rc7_sources as f


def main():
    if not f.VERIFIED.is_file() or not f.RELEASE.is_file():
        raise SystemExit('E BLOCKED: missing verified-dev.json or E_RELEASE.json')
    v = json.loads(f.VERIFIED.read_text())
    r = json.loads(f.RELEASE.read_text())
    assert r['manifest_sha256'] == f.sha(f.APP / 'a5-manifest.json')
    assert r['parent_manifest_sha256'] == f.sha(f.PARENT) == f.PARENT_SHA
    assert r['verification_sha256'] == f.sha(f.VERIFIED)
    assert r['verification_manifest_sha256'] == f.sha(f.VERIFY_MANIFEST)
    assert v['manifest_sha256'] == r['manifest_sha256']
    assert v['parent_manifest_sha256'] == r['parent_manifest_sha256']
    assert v['verification_manifest_sha256'] == r['verification_manifest_sha256']
    vm = json.loads(f.VERIFY_MANIFEST.read_text())
    assert vm['candidate_manifest_sha256'] == f.sha(f.APP / 'a5-manifest.json')
    assert vm['parent_manifest_sha256'] == f.sha(f.PARENT)
    cases = f.verify_all()
    by_slot = {c['slot']: c for c in v['cases']}
    assert sorted(by_slot) == list(range(1, 8))
    for slot, c in cases.items():
        assert by_slot[slot]['status'] == c['status']
        assert by_slot[slot]['result_dir'] == c['result_dir']
        assert by_slot[slot]['trace_sha256'] == c['trace_sha256']
    assert v['all_six_positives_accepted'] is True
    assert cases[7]['status'] in ('accepted', 'rejected')
    print('A5_GATE_OK_SOURCE', len(cases), 'manifest', r['manifest_sha256'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
