"""One offline evaluator and one GPU entry for A5 dev and frozen E runs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
ROOT = Path('/root/autodl-tmp')
MANIFEST = HERE/'a5-manifest.json'
POLICY = HERE/'a5-candidate.json'
RELEASE = HERE/'E_RELEASE.json'


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def save_new(p, data):
    with p.open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())


def preflight():
    for name, digest in read(MANIFEST).items():
        require(sha(HERE/name) == digest, 'Candidate hash mismatch: ' + name)
    from stage4_success_v1 import identity
    identity()


def gate():
    preflight()
    require(RELEASE.is_file(), 'E BLOCKED: missing verified developer release')
    receipt = read(RELEASE)
    require(receipt['manifest_sha256'] == sha(MANIFEST), 'Release belongs to another candidate')
    require(sha(Path(receipt['verification_file'])) == receipt['verification_sha256'], 'Verification receipt changed')


def authorize_initial(initial, split, execution, runner):
    preflight()
    result = read(initial/'result.json')
    case = result['initial_case']
    seed, level = case['seed'], case['level']
    policy = read(POLICY)
    require(result['passed'] is True and ('l1' if level=='flat' else 'recovery') == runner, 'Wrong initial/task')
    require(execution in ('single','arc4'), 'Unknown execution mode')
    plan = read(HERE/'square-initial-plan.json')['episodes']
    require(sum(row == case for row in plan) == 1, 'Initial case differs from registered plan')
    if split == 'formal':
        gate()
        held = read(HERE/'stage4-heldout-seeds.json')['heldout']
        require(case in held, 'Formal case not in fixed held-out list')
    else:
        require(split == 'dev', 'Unknown split')
        item = policy['development'].get(str(seed))
        require(item and execution in item['modes'], 'Unregistered dev seed/mode')
        require(initial.resolve() == ROOT/item['initial'], 'Wrong registered initial directory')
        for name,digest in item['files'].items():
            require(sha(initial/name) == digest, 'Dev initial hash mismatch: '+name)


def assess(directory):
    import numpy as np
    from audit_episode_evidence import audit
    from stage4_success_v1 import evaluate
    result = read(directory/'result.json')
    case = result['initial_case']
    spec = read(POLICY)['tasks'][case['level']]
    expected = spec['actions']
    mode = result['execution_mode']
    horizons = [1]*expected if mode=='single' else [1]*(expected-5)+[4,1]
    out = dict(protocol='stage4-a5-rc1', seed=case['seed'], level=case['level'], mode=mode,
               development_pass=result['passed'], errors=result['errors'], manifest_sha256=sha(MANIFEST),
               status='incomplete', success=None)
    if not all((directory/name).is_file() for name in ('success_trace.npz','success_meta.json','evidence/summary.json')):
        return out
    meta = read(directory/'success_meta.json')
    with np.load(directory/'success_trace.npz', allow_pickle=False) as z:
        data = dict(z)
    quality = evaluate(meta, data)
    capture = audit(directory/'evidence')
    evidence_summary = read(directory/'evidence/summary.json')
    samples = evidence_summary['samples']
    timeline = [json.loads(l) for l in (directory/'evidence/timeline.jsonl').read_text().splitlines()]
    calls = [r for r in timeline if r['kind']=='action_begin']
    end = [r for r in timeline if r['kind']=='action_end']
    labels = [a['label'] for a in result['actions']]
    target = np.array(calls[-1]['targets'][0][:3])
    released = samples['released']
    retreated = samples['retreated']
    start_time = meta['sim_time_s']
    inputs = Path(result['initial_dir'])
    checks = dict(video_and_samples=capture['evidence_complete'], actual_sim=evidence_summary['synthetic'] is False,
        source=result['code_files']==read(MANIFEST) and meta['manifest_sha256']==sha(MANIFEST),
        input_hashes=all(sha(inputs/n)==meta['initial_hashes'][n] for n in ('result.json','initial_geometry.npz')),
        identity=(meta['task'],meta['edge'],meta['seed'],meta['level'],meta['execution_mode'])==
                 (spec['task'],spec['edge'],case['seed'],case['level'],mode),
        actual_budget=capture['attempted_public_actions']==result['action_count']==meta['action_count']==expected,
        horizons=[r['horizon'] for r in calls]==result['call_horizons']==horizons,
        final_open=labels[-1]=='release_retreat' and calls[-1]['commands']==[0] and
                   calls[-1]['call_id']==released['call_id']==end[-1]['call_id'],
        upward_public_target=np.allclose(target, np.array(released['ee_m'])+[0,0,.15],atol=.002,rtol=0)
                             and retreated['ee_m'][2]-released['ee_m'][2]>=.01,
        clock_origin=abs(end[-1]['sim_time_s']-start_time)<1e-6 and abs(retreated['sim_time_s']-start_time)<1e-6,
        absolute_clock=np.array_equal(data['absolute_steps'],meta['absolute_step']+np.arange(331)) and
                       np.allclose(data['sim_time_s'],start_time+np.arange(331)/60,atol=1e-5,rtol=0),
        double_hold=all(np.array_equal(np.load(directory/'evidence'/(key+'.npz'))['vertices'], data['vertices'][i])
                        for key,i in [('hold_3s',180),('hold_4s',240)]),
        terminal_matches=np.array_equal(np.load(directory/'final.npz')['vertices'], data['vertices'][330]))
    out.update(evidence_checks={k:bool(v) for k,v in checks.items()}, criteria=quality)
    if all(checks.values()) and quality['status'] in ('accepted','rejected'):
        out.update(status=quality['status'], success=quality['success'])
    return out


def episode(initial, split, mode, journal):
    case=read(initial/'result.json')['initial_case'];spec=read(POLICY)['tasks'][case['level']]
    runner=spec['runner']
    authorize_initial(initial,split,mode,runner)
    journal.mkdir(parents=True,exist_ok=True)
    attempt=journal/(str(case['seed'])+'-'+mode+'-'+uuid.uuid4().hex);attempt.mkdir()
    save_new(attempt/'started.json',dict(seed=case['seed'],mode=mode,split=split,initial=str(initial),manifest_sha256=sha(MANIFEST)))
    cmd=[sys.executable,'-u',str(HERE/('a5_'+runner+'.py')),'--initial-dir',str(initial),'--allow-root','--execution',mode,'--split',split]
    cmd += ['--overhang','.02'] if runner=='l1' else ['--fold-edge','right']
    env=dict(os.environ,GARMENTLAB_ATTACHMENT_OVERLAP='0.005',GARMENTLAB_DISABLED_ATTACHMENT_PROBE='0')
    with (attempt/'runner.log').open('xb') as log:
        process=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,cwd=ROOT)
    lines=(attempt/'runner.log').read_text(errors='replace').splitlines()
    names=[Path(l[13:]) for l in lines if l.startswith('DOWNLOAD_DIR ')]
    require(len(names)==1,'See retained attempt '+str(attempt))
    directory=names[0]
    require(directory.parent==ROOT and directory.name.startswith('day4-a5-'),'Unexpected output directory')
    verdict=assess(directory)
    verdict.update(split=split, runner_exit=process.returncode, result_dir=str(directory), attempt_dir=str(attempt))
    if process.returncode!=0:
        verdict.update(status='execution_error',success=None)
    save_new(directory/'a5-verdict.json',verdict)
    save_new(attempt/'finished.json',verdict)
    print('DOWNLOAD_DIR', directory, flush=True)
    return verdict


def verify_dev(journal):
    import numpy as np
    policy=read(POLICY); entries={}; targets={}
    for attempt in sorted(journal.iterdir()):
        started=read(attempt/'started.json')
        saved=read(attempt/'finished.json'); d=Path(saved['result_dir']); r=read(d/'result.json')
        require(saved['runner_exit']==0 and saved['split']==started['split']=='dev','Ineligible attempt')
        mode=saved['mode'];seed=saved['seed'];key=(str(seed),mode)
        require(key not in entries,'Duplicate attempt requires separate review and registration')
        require(started['manifest_sha256']==saved['manifest_sha256']==sha(MANIFEST),'Changed candidate')
        require((seed,mode)==(r['initial_case']['seed'],r['execution_mode']),'Wrong dev case')
        spec=policy['tasks'][r['initial_case']['level']]
        authorize_initial(Path(r['initial_dir']),'dev',mode,spec['runner'])
        q=assess(d)
        require(q['status'] in ('rejected','accepted'),'Incomplete development evidence: '+str(d))
        if policy['development'][str(seed)]['positive']:
            require(q['success'] is True,'Expected positive smoke case failed: '+str(d))
        entries[key]=dict(directory=str(d),verdict=q,trace_sha256=sha(d/'success_trace.npz'))
        targets[key]=[a['target_pose'] for a in r['actions']]
    expected={(seed,mode) for seed,i in policy['development'].items() for mode in i['modes']}
    require(set(entries)==expected,'Incomplete registered development matrix')
    for seed,i in policy['development'].items():
        if 'arc4' in i['modes']:
            require(np.allclose(targets[seed,'arc4'],targets[seed,'single'],atol=1e-6,rtol=0),'Mode pair target drift: '+seed)
    return {'manifest_sha256':sha(MANIFEST),'cases':[entries[k] for k in sorted(entries)]}


def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='operation',required=True)
    for name in ('preflight','gate','dev-batch','verify-dev','freeze','run'):
        p=sub.add_parser(name)
        if name in ('dev-batch','verify-dev','freeze','run'): p.add_argument('--journal',required=True,type=Path)
        if name=='run':
            p.add_argument('--initial',type=Path,required=True);p.add_argument('--mode',choices=('single','arc4'),required=True)
            p.add_argument('--split',choices=('dev','formal'),required=True)
    a=ap.parse_args();preflight()
    if a.operation=='preflight': print('A5_CANDIDATE_PREFLIGHT_OK',sha(MANIFEST)); return
    if a.operation=='gate': gate();return
    if a.operation=='run':
        v=episode(a.initial.resolve(),a.split,a.mode,a.journal.resolve())
        raise SystemExit({'accepted':0,'rejected':1}.get(v['status'],3))
    j=a.journal.resolve()
    if a.operation=='dev-batch':
        gpu=subprocess.run(['nvidia-smi','-L'],capture_output=True,text=True)
        require(gpu.returncode==0 and 'GPU ' in gpu.stdout,'Development replay requires GPU')
        j.mkdir(exist_ok=False,parents=True)
        for item in read(POLICY)['development'].values():
            for mode in item['modes']: episode(ROOT/item['initial'],'dev',mode,j)
    verified=verify_dev(j)
    if a.operation=='freeze':
        path=HERE/'verified-dev.json';save_new(path,verified)
        save_new(RELEASE,{'manifest_sha256':sha(MANIFEST),'verification_file':str(path),'verification_sha256':sha(path)})
    print('A5_DEV_VERIFIED',len(verified['cases']))


if __name__=='__main__':
    main()
