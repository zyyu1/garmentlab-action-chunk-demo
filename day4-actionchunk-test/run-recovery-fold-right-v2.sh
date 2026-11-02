#!/usr/bin/env bash
# Registered development-only coverage expansion (b-right-dev-v2).
# The underlying engine and the 21-entry base identity are unchanged.
# Only initial directories recorded by run-stage4-b-right-dev-v2-batch.sh are accepted.
set -uo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
initial_dir=${1:?usage: RECOVERY_FOLD_EXECUTION=single bash run-recovery-fold-right-v2.sh <registered-dev-initial>}
execution=${RECOVERY_FOLD_EXECUTION:-single}
"$python_bin" - "$initial_dir" "$execution" <<'PY' || exit 2
import hashlib,json,sys
from pathlib import Path
config=json.loads(Path('stage4-b-right-dev-v2.json').read_text())
manifest=json.loads(Path('square-recovery-fold-right-v2-files.json').read_text())
for name,digest in manifest.items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
assert hashlib.sha256(Path('square-recovery-fold-files.json').read_bytes()).hexdigest()==config['base_manifest_sha256']
assert sys.argv[2] in config['execution_modes'],'Only the registered execution modes are allowed'
registry=json.loads(Path(config['initial_registry']).read_text())
row=next((r for r in registry['seeds'] if r['initial_dir']==sys.argv[1]),None)
assert row is not None,'Only initial directories recorded by the v2 batch driver are allowed'
assert row['seed'] in [c['seed'] for c in config['development_cases']],'Seed not registered for v2'
for name,digest in row['files'].items():
    assert hashlib.sha256((Path(sys.argv[1])/name).read_bytes()).hexdigest()==digest,('initial file changed',name)
r=json.loads((Path(sys.argv[1])/'result.json').read_text())
assert r['passed'] and r['initial_case']['seed']==row['seed'] and r['initial_case']['level']==row['level']
print('RIGHT_V2_PREFLIGHT_OK',row['seed'],sys.argv[2],flush=True)
PY
log=$(mktemp /root/autodl-tmp/stage4-b-right-v2-log-XXXXXXXX.log)
RECOVERY_FOLD_EXECUTION="$execution" bash run-recovery-fold-episode.sh "$initial_dir" right 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
"$python_bin" - "$log" "$initial_dir" "$execution" "${statuses[0]}" <<'PY' || exit 3
import hashlib,json,sys
from pathlib import Path
log,initial,mode,rc=sys.argv[1:]
paths=[x[12:] for x in Path(log).read_text(errors='replace').splitlines() if x.startswith('RESULT_FILE ')]
assert len(paths)==1,'Missing or ambiguous result directory'
result_path=Path(paths[0]);r=json.loads(result_path.read_text())
config=json.loads(Path('stage4-b-right-dev-v2.json').read_text())
manifest=json.loads(Path('square-recovery-fold-right-v2-files.json').read_text())
base=json.loads(Path('square-recovery-fold-files.json').read_text())
assert r['code_files']==base and r['initial_dir']==initial
assert r['fold_edge']=='right' and r['execution_mode']==mode
assert r['initial_case']['seed'] in [c['seed'] for c in config['development_cases']]
assert r['action_count']==12 and sum(r['call_horizons'])==12
payload={'variant_id':config['variant_id'],'fold_edge':'right','execution_mode':mode,
         'code_files':manifest,'base_code_files':base,'config':config,
         'base_runner_exit':int(rc),'formal_stage4_success':False,
         'initial_files':{name:hashlib.sha256((Path(initial)/name).read_bytes()).hexdigest()
                          for name in ('result.json','initial_geometry.npz')}}
(result_path.parent/'variant_identity.json').write_text(json.dumps(payload,indent=2))
print('RIGHT_V2_EVIDENCE_SAVED',result_path.parent,flush=True)
PY
if [ "${statuses[1]}" -ne 0 ]; then exit 4; fi
exit "${statuses[0]}"
