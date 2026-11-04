"""Offline tests: formal preflight accepts new initials and rejects bad ones."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE / 'a5-rc2-pfs1-observation-v2-rc8b' / 'app'
sys.path.insert(0, str(APP))
import stage4_batch_preflight as p  # noqa: E402

NEW = HERE / 'results' / 'RC8B_INITIALS_20261105'
OLD_4100 = Path(r'E:\learning\project\thesis\day4-actionchunk-test\results\A5_RC2_AUDIT_20261103T194913Z\day4-square-initial-20261031-094446-203825')

valid = {
    4100: ('flat', NEW / 'day4-square-initial-20261105-014501-526555'),
    4202: ('perturbed', NEW / 'day4-square-initial-stripfold-20261105-015817-115841'),
    4302: ('crumpled', NEW / 'day4-square-initial-stripfold-20261105-020706-026048'),
}
for seed, (level, d) in valid.items():
    p.initial(d, level, seed)
    print('ACCEPT', seed, level)

tmp = Path(tempfile.mkdtemp(prefix='rc8b_preflight_'))
_counter = [0]


def copy_case(src):
    _counter[0] += 1
    dst = tmp / ('case%d' % _counter[0])
    shutil.copytree(src, dst)
    return dst


def expect_reject(label, d, level, seed):
    try:
        p.initial(d, level, seed)
    except ValueError as exc:
        print('REJECT_OK', label, '->', str(exc)[:80])
        return
    raise SystemExit('expected rejection: ' + label)


expect_reject('old_4100_no_protocol', OLD_4100, 'flat', 4100)

bad = copy_case(valid[4202][1])
r = json.loads((bad / 'result.json').read_text())
r['protocol']['particle_friction_scale_readback'] = 0.0
(bad / 'result.json').write_text(json.dumps(r))
expect_reject('wrong_scale', bad, 'perturbed', 4202)

bad = copy_case(valid[4202][1])
r = json.loads((bad / 'result.json').read_text())
r['protocol'].pop('material_binding')
(bad / 'result.json').write_text(json.dumps(r))
expect_reject('missing_binding', bad, 'perturbed', 4202)

bad = copy_case(valid[4202][1])
r = json.loads((bad / 'result.json').read_text())
r['protocol']['generator']['script_sha256'] = '0' * 64
(bad / 'result.json').write_text(json.dumps(r))
expect_reject('generator_mismatch', bad, 'perturbed', 4202)

bad = copy_case(valid[4202][1])
r = json.loads((bad / 'result.json').read_text())
r.pop('protocol')
(bad / 'result.json').write_text(json.dumps(r))
expect_reject('missing_protocol', bad, 'perturbed', 4202)

shutil.rmtree(tmp)
print('ALL_PROTOCOL_CHECKS_OK')
