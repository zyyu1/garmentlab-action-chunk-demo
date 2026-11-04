import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def reg(name, parent_name, parent_manifest, initial_dir, result_dir, quality, centroid, p95, stationary, steady, failures, review):
    d = root / name
    data = {
        'version': 'a5-rc2-pfs1-observation-v2',
        'revision': 'diagnostic-repeat1',
        'stage': 'repeat1_completed',
        'kind': 'diagnostic_single_case_repeat',
        'parent': parent_name,
        'parent_manifest_sha256': parent_manifest,
        'identity': {
            'manifest_sha256': sha(d / 'app' / 'a5-manifest.json'),
            'manifest_entries': 63,
            'changed_vs_parent': ['a5-rc2-pfs1-observation-v2.json', 'run-a5-rc2-pfs1-observation-v2.sh'],
            'unchanged_vs_parent': 61,
            'config_sha256': sha(d / 'app' / 'a5-rc2-pfs1-observation-v2.json'),
            'runner_sha256': sha(d / 'app' / 'run-a5-rc2-pfs1-observation-v2.sh'),
        },
        'initial': initial_dir,
        'run': {'seed': 4202, 'mode': 'single', 'attempts': 1, 'retry': False,
                'result_dir': result_dir, 'quality': quality,
                'centroid_mm': centroid, 'p95_mm': p95,
                'stationary_drift_mm': stationary, 'steady_centroid_mm_s': steady,
                'geometry_failure_frames': failures,
                'download_verified': '111/111 files'},
        'comparison': {'vs_original': 'bit-identical at all stages, targets and success_trace (max diff 0.0)',
                       'review': review},
        'boundaries': ['single repeat, no retry, no expansion, no freeze',
                       'diagnostic repeat, not part of the seven-case matrix or formal success'],
    }
    (d / 'registration.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(name, data['identity']['manifest_sha256'], quality)


reg('a5-rc2-pfs1-observation-v2-l2pose-repeat1',
    'a5-rc2-pfs1-observation-v2-l2pose',
    '3a97a5000ac856b758b65a78d15d1f31fe826048ab59f79714c99b7fb89667f0',
    'day4-square-initial-stripfold-20261104-202215-l2posecontrol',
    'results/RC8B_L2_DIAG_20261105/l2pose_repeat1/day4-a5-rc2-pfs1-observation-v2-20261105-050830-340362',
    'accepted', 0.739646, 1.539675, 7.6258, 0.418, 0,
    'results/RC8B_L2_DIAG_20261105/repeat_review.md')
reg('a5-rc2-pfs1-observation-v2-rc8b-repeat1',
    'a5-rc2-pfs1-observation-v2-rc8b',
    'cce573ddd626715b15818467290152a4c68502bafc9595b11780fe1dd601bc8e',
    'day4-square-initial-stripfold-20261105-015817-115841',
    'results/RC8B_L2_DIAG_20261105/rc8b_repeat1/day4-a5-rc2-pfs1-observation-v2-20261105-052531-038610',
    'rejected', 7.480913, 11.538153, 29.9144, 4.092, 82,
    'results/RC8B_L2_DIAG_20261105/repeat_review.md')

# annotate the two source registrations
for p, status, extra in (
        (root / 'a5-rc2-pfs1-observation-v2-l2pose' / 'registration.json',
         'repeat1_bit_identical_accepted',
         {'repeat_candidate': 'a5-rc2-pfs1-observation-v2-l2pose-repeat1',
          'repeat_result': 'accepted 0.739646/1.539675; max stage/target/trace diff 0.0'}),
        (root / 'a5-rc2-pfs1-observation-v2-rc8b' / 'registration.json',
         'repeat1_bit_identical_rejected',
         {'repeat_candidate': 'a5-rc2-pfs1-observation-v2-rc8b-repeat1',
          'repeat_result': 'rejected 7.480913/11.538153; max stage/target/trace diff 0.0'})):
    d = json.loads(p.read_text())
    d['repeat1'] = dict({'status': status, **extra})
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('annotated')
