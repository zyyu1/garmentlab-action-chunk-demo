"""Build Stage 5 demo layer manifests (initial files + deployment identity)."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = Path('/root/autodl-tmp/stage5-trial/app')
CAND = Path('/root/autodl-tmp/a5-rc8b-recovery-hold120-rc7-r2')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    initial_files = {
        'make_demo_plan.py': sha(HERE / 'make_demo_plan.py'),
        'stage5-demo-initial-plan.json': sha(HERE / 'stage5-demo-initial-plan.json'),
        'run-demo-initial.sh': sha(HERE / 'run-demo-initial.sh'),
        'day4-square-initial-demo.py': sha(HERE / 'day4-square-initial-demo.py'),
        'day4-square-initial-stripfold-demo.py': sha(HERE / 'day4-square-initial-stripfold-demo.py'),
        str(APP / 'square-difficulty.yaml'): sha(APP / 'square-difficulty.yaml'),
        str(APP / 'square_cloth_40cm.usda'): sha(APP / 'square_cloth_40cm.usda'),
    }
    (HERE / 'stage5-demo-initial-files.json').write_text(
        json.dumps(initial_files, indent=2) + '\n', encoding='utf-8')
    deployment = {
        'schema': 'stage5-demo-deployment-v1',
        'frozen_candidate_manifest': sha(APP / 'a5-manifest.json'),
        'frozen_candidate_manifest_sha256': '40858efc1a5840ab2bf51e025f823382e8586bc037fbe41bf1d1de5b21dee86a',
        'stage4_frozen_files_unchanged': True,
        'demo_layer': {
            'seeds': 'stage5-demo-seeds.json',
            'plan': 'stage5-demo-initial-plan.json',
            'initial_files_manifest': 'stage5-demo-initial-files.json',
            'initial_generator': 'run-demo-initial.sh',
            'entry': 'a5_entry_demo.py',
            'authorization': 'split=demo (demo registry + task-scoped protocol + file hashes)',
        },
        'entries': {
            str(HERE.parent / 'collect_demos.py'): sha(HERE.parent / 'collect_demos.py'),
            str(HERE.parent / 'verify_export.py'): sha(HERE.parent / 'verify_export.py'),
            str(HERE.parent / 'phase_map.json'): sha(HERE.parent / 'phase_map.json'),
            str(APP / 'sitecustomize.py'): sha(APP / 'sitecustomize.py'),
            'stage5-demo-seeds.json': sha(HERE / 'stage5-demo-seeds.json'),
            'stage5-demo-initial-plan.json': sha(HERE / 'stage5-demo-initial-plan.json'),
            'stage5-demo-initial-files.json': sha(HERE / 'stage5-demo-initial-files.json'),
            'a5_entry_demo.py': sha(HERE / 'a5_entry_demo.py'),
            'run-demo-initial.sh': sha(HERE / 'run-demo-initial.sh'),
        },
    }
    (HERE / 'stage5_demo_manifest.json').write_text(
        json.dumps(deployment, indent=2) + '\n', encoding='utf-8')
    print('DEMO_MANIFESTS_WRITTEN', len(initial_files), len(deployment['entries']))


if __name__ == '__main__':
    main()
