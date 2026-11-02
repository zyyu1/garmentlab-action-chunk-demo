#!/usr/bin/env bash
# b-right-dev-v2 coverage batch driver (runs on the remote GPU host; do not run locally).
#
#   bash run-stage4-b-right-dev-v2-batch.sh [tag]
#
# For each registered development seed (4201-4209 perturbed, 4301-4309 crumpled):
#   1. generate the stripfold initial state if it is not yet recorded in the
#      variant registry, and record its content hashes in stage4-b-right-dev-v2-initials.json;
#   2. run one right-edge single-representation fold with run-recovery-fold-right-v2.sh.
# Every fold attempt is appended to attempts.jsonl.  A rejected fold never aborts
# the batch, never replaces an earlier result and is never retried automatically.
# A missing initial state or a missing result directory is an infrastructure
# error and stops the batch, because the remaining attempts would not be comparable.
#
# Seeds already recorded with a result directory are skipped (resume).  Use a new
# tag to force a clean run.
set -uo pipefail
cd /root/autodl-tmp
python_bin=/root/autodl-tmp/envs/isaac40/bin/python
tag=${1:-dev-v2}
state=/root/autodl-tmp/stage4-b-right-dev-v2-$tag
mkdir -p "$state"
jsonl=$state/attempts.jsonl
log=$state/batch.log
registry=stage4-b-right-dev-v2-initials.json

say() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$log"; }

# Fail fast if the registered config, manifest and base identity disagree, or if
# the seed set drifts from the registration.
"$python_bin" - <<'PY' || exit 2
import hashlib,json
from pathlib import Path
config=json.loads(Path('stage4-b-right-dev-v2.json').read_text())
manifest=json.loads(Path('square-recovery-fold-right-v2-files.json').read_text())
base=json.loads(Path('square-recovery-fold-files.json').read_text())
for name,digest in manifest.items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
assert set(manifest)==set(base)|{'run-recovery-fold-right-v2.sh','stage4-b-right-dev-v2.json'}
assert all(manifest[k]==v for k,v in base.items())
assert hashlib.sha256(Path('square-recovery-fold-files.json').read_bytes()).hexdigest()==config['base_manifest_sha256']
assert config['execution_modes']==['single'],'v2 registers single only'
cases={c['seed']:c['level'] for c in config['development_cases']}
expected={**{s:'perturbed' for s in range(4201,4210)},**{s:'crumpled' for s in range(4301,4310)}}
assert cases==expected,('seed set drift',sorted(set(cases)^set(expected)))
held=set(range(4210,4230))|set(range(4310,4330))
assert not (set(cases)&held),'held-out seeds are prohibited'
reg=Path(config['initial_registry'])
if reg.exists():
    rows=json.loads(reg.read_text())['seeds']
    assert all(r['seed'] in cases for r in rows),'registry contains an unregistered seed'
print('RIGHT_V2_BATCH_PREFLIGHT_OK',len(cases),flush=True)
PY

seed_rows() {
  "$python_bin" - <<'PY'
import json
for c in json.loads(open('stage4-b-right-dev-v2.json').read())['development_cases']:
    print(c['level'], c['seed'])
PY
}

registry_lookup() {
  "$python_bin" - "$1" <<'PY'
import json,sys
from pathlib import Path
p=Path('stage4-b-right-dev-v2-initials.json')
if not p.exists(): raise SystemExit(0)
row=next((r for r in json.loads(p.read_text())['seeds'] if r['seed']==int(sys.argv[1])),None)
if row: print(row['initial_dir'])
PY
}

registry_append() {
  local seed=$1 level=$2 idir=$3
  "$python_bin" - "$seed" "$level" "$idir" <<'PY' || return 1
import datetime,hashlib,json,sys
from pathlib import Path
seed,level,idir=int(sys.argv[1]),sys.argv[2],sys.argv[3]
p=Path('stage4-b-right-dev-v2-initials.json')
doc={'batch':'b-right-dev-v2','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seeds':[]}
if p.exists(): doc=json.loads(p.read_text())
existing=next((r for r in doc['seeds'] if r['seed']==seed),None)
r=json.loads((Path(idir)/'result.json').read_text())
assert r['passed'] and r['initial_case']['seed']==seed and r['initial_case']['level']==level
files={name:hashlib.sha256((Path(idir)/name).read_bytes()).hexdigest()
       for name in ('result.json','initial_geometry.npz')}
row={'seed':seed,'level':level,'initial_dir':idir,'files':files}
if existing:
    assert existing==row,'registry entry differs for seed %d'%seed
else:
    doc['seeds'].append(row)
doc['seeds'].sort(key=lambda x:x['seed'])
tmp=p.with_suffix('.json.tmp')
tmp.write_text(json.dumps(doc,indent=2)+'\n')
tmp.replace(p)
print('INIT_REGISTERED',seed,level,idir,flush=True)
PY
}

already_done() {
  "$python_bin" - "$jsonl" "$1" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); seed=int(sys.argv[2])
if not p.exists(): raise SystemExit(0)
for line in p.read_text().splitlines():
    try: row=json.loads(line)
    except Exception: continue
    if row.get('seed')==seed and row.get('result_dir'): print('1'); break
PY
}

generate_initial() {
  local level=$1 seed=$2 out rc dir
  say "INIT_BEGIN $level $seed run-square-initial-stripfold.sh"
  out=$(bash run-square-initial-stripfold.sh "$seed" 2>&1); rc=$?
  echo "$out" >> "$state/init-$seed.log"
  dir=$(printf '%s\n' "$out" | sed -n 's/^DOWNLOAD_DIR //p' | tail -1)
  if [ $rc -ne 0 ] || [ -z "$dir" ]; then
    say "INIT_FAILED $level $seed rc=$rc"
    return 1
  fi
  registry_append "$seed" "$level" "$dir" || { say "INIT_REGISTRY_FAILED $level $seed"; return 1; }
  say "INIT_READY $level $seed $dir"
}

record_attempt() {
  local level=$1 seed=$2 idir=$3 rdir=$4 rc=$5
  "$python_bin" - "$jsonl" "$level" "$seed" "$idir" "$rdir" "$rc" <<'PY'
import datetime,json,sys
path,level,seed,idir,rdir,rc=sys.argv[1:7]
row={'variant':'b-right-dev-v2','level':level,'seed':int(seed),'execution':'single',
     'initial_dir':idir,'result_dir':rdir,'exit_code':int(rc),
     'attempted_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
with open(path,'a',encoding='utf-8') as fh:
    fh.write(json.dumps(row)+'\n')
PY
}

while read -r level seed; do
  [ -z "$level" ] && continue
  if [ -n "$(already_done "$seed")" ]; then
    say "SKIP_ALREADY_RECORDED $level $seed"
    continue
  fi
  idir=$(registry_lookup "$seed")
  if [ -z "$idir" ]; then
    generate_initial "$level" "$seed" || { say "BATCH_ABORT initial state $level $seed"; exit 3; }
    idir=$(registry_lookup "$seed")
  fi
  say "FOLD_BEGIN $level $seed single right $idir"
  out=$(RECOVERY_FOLD_EXECUTION=single bash run-recovery-fold-right-v2.sh "$idir" 2>&1); rc=$?
  echo "$out" >> "$state/fold-$level-$seed-single.log"
  rdir=$(printf '%s\n' "$out" | sed -n 's/^DOWNLOAD_DIR //p' | tail -1)
  if [ -z "$rdir" ]; then
    record_attempt "$level" "$seed" "$idir" "" "$rc"
    say "FOLD_INFRASTRUCTURE_ERROR $level $seed single rc=$rc"
    say "BATCH_ABORT no result directory"
    exit 4
  fi
  record_attempt "$level" "$seed" "$idir" "$rdir" "$rc"
  say "FOLD_DONE $level $seed single rc=$rc $rdir"
done < <(seed_rows)

say "BATCH_FINISHED $state"
